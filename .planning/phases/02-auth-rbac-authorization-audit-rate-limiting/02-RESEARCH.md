# Phase 2: Auth, RBAC, Authorization, Audit, Rate Limiting - Research

**Phase:** 02-auth-rbac-authorization-audit-rate-limiting  
**Domain:** Security, Authentication, Object-Level Authorization, Audit Logging, and Serverless Rate Limiting  
**Requirements:** `AUTH-01`, `AUTH-02`, `AUTH-03`, `AUTH-04`, `AUTH-05`, `AUTH-06`  
**Date:** 2026-10-01  

---

## 1. Architecture & System Overview

Phase 2 implements the security, identity, access control, and audit infrastructure for LIFELINK. It sits directly atop the Phase 1 domain models (`User`, `MedicalProfile`, `AuditLog`, `DemoSession`) and ensures that all subsequent feature phases (triage, dispatch orchestration, live incident tracking, responder/authority consoles) operate within strictly enforced boundaries.

```
                      ┌───────────────────────────────────────┐
                      │            HTTP Request               │
                      └──────────────────┬────────────────────┘
                                         │
                 ┌───────────────────────▼──────────────────────┐
                 │ 1. Rate Limiting Dependency (DB-derived)     │
                 │    - Checks audit_logs (login failures)      │
                 │    - Checks emergencies (SOS creation flood) │
                 │    - Clock-aware rolling window              │
                 └───────────────────────┬──────────────────────┘
                                         │ Pass
                 ┌───────────────────────▼──────────────────────┐
                 │ 2. Authentication (get_current_user)         │
                 │    - Cookie 'll_session' or 'Bearer' header  │
                 │    - PyJWT signature & expiration validation │
                 │    - DB user re-verification (fresh status)  │
                 └───────────────────────┬──────────────────────┘
                                         │ Authenticated
                 ┌───────────────────────▼──────────────────────┐
                 │ 3. RBAC (require_role(*roles))               │
                 │    - Deny-by-default route enforcement       │
                 │    - Role enum validation                    │
                 └───────────────────────┬──────────────────────┘
                                         │ Authorized Role
                 ┌───────────────────────▼──────────────────────┐
                 │ 4. Object-Level Authz (services/authz.py)    │
                 │    - Incident ownership & tenant matching    │
                 │    - Offer assignment permissions            │
                 │    - Anti-enumeration 404 vs 403             │
                 └───────────────────────┬──────────────────────┘
                                         │
                      ┌──────────────────┴──────────────────┐
                      ▼                                     ▼
           ┌─────────────────────┐               ┌─────────────────────┐
           │ Allow Operation     │               │ Deny Operation      │
           │ Log sensitive reads │               │ Log 'deny' to audit │
           │ (coords, medical)   │               │ Raise HTTPException │
           └─────────────────────┘               └─────────────────────┘
```

---

## 2. Key Technical Decisions & Patterns

### 2.1 Password Hashing & Registration (`AUTH-01`)
- **Argon2id Memory-Hard Hashing**:
  - Implemented using `argon2.PasswordHasher()`.
  - Enforces minimum 10 characters, common-password denylist check, and non-empty name/email.
  - Role restriction: Public registration endpoint `/api/v1/auth/register` strictly allows `role="citizen"` or `role="responder"`. Any request attempting to register `authority` or `ambulance_operator` is rejected with `422 VALIDATION_ERROR`.
  - Responders begin with an unverified profile (`is_active=True`, but unverified credentials).

### 2.2 JWT Session & Dual Transport (`AUTH-02`)
- **Token Claims**:
  - `sub`: User UUID as string.
  - `role`: Role string (`citizen`, `responder`, `ambulance_operator`, `authority`).
  - `demo_session_id`: Tenant UUID string or `None`.
  - `iat`, `exp`: Issued-at and expiration (12 hours).
- **Dual Transport (D-25, D-26)**:
  - Cookie `ll_session`: Primary browser transport with `HttpOnly; Path=/; Max-Age=43200`.
  - Environment-aware flags: `Secure=False, SameSite='Lax'` in development/preview; `Secure=True, SameSite='Strict'` in production.
  - Fallback header: If cookie is absent, inspects `Authorization: Bearer <token>`.
- **Database Re-Verification (D-27)**:
  - Tokens are verified cryptographically via `jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])`.
  - User is fetched from database to verify `user.is_active is True` and ensure immediate revocation if deactivated or suspended.

### 2.3 RBAC & Route Enumeration (`AUTH-03`)
- **Role Guard**:
  - `require_role(*allowed_roles: UserRole)` returns a dependency that verifies `current_user.role in allowed_roles`.
  - Non-conforming roles receive `403 FORBIDDEN`.
- **Route Enumeration Audit**:
  - CI test `test_authz_matrix.py` introspects `app.routes`.
  - Verifies that 100% of non-public endpoints declare an authentication dependency (`get_current_user` or `require_role`).
  - Public whitelist strictly bounded to `/health`, `/auth/register`, `/auth/login`, and OpenAPI metadata (`/docs`, `/openapi.json`).

### 2.4 Centralized Object-Level Authorization (`AUTH-04`)
- **Explicit Guard Functions in `services/authz.py` (D-28)**:
  - `assert_can_view_emergency(user, emergency, db)`: Patient, reporter, assigned/offered responder, assigned ambulance operator, or authority.
  - `assert_can_act_on_offer(user, offer, db)`: Only the targeted responder or ambulance unit operator.
  - `assert_can_view_medical(user, emergency, medical_profile, db)`: Patient, or accepted responder/ambulance when `emergency.consent_share_medical is True`.
- **Anti-Enumeration Masking (D-29)**:
  - If a user attempts to read or mutate a resource with which they have zero association (or tenant mismatch), raises `404 NOT_FOUND` with error code `NOT_FOUND` rather than `403 FORBIDDEN` to prevent IDOR enumeration.
  - If a user is a valid participant but lacks permission for the specific action, raises `403 FORBIDDEN`.
- **Multi-Tenant Scope Isolation (D-30)**:
  - `user.demo_session_id == resource.demo_session_id` strictly enforced across all object checks.

### 2.5 Security Audit Logging Pipeline (`AUTH-05`)
- **Dedicated Immediate Commit (D-34)**:
  - `services/audit.py:log_security_event()` uses an independent database connection/session or immediate `commit()` so records are persisted even if the calling request transaction rolls back or raises an exception.
- **Salted IP Anonymization (D-35)**:
  - Client IP anonymized via HMAC-SHA256: `hmac.new(settings.JWT_SECRET.encode(), ip.encode(), hashlib.sha256).hexdigest()`.
- **Actions Logged**:
  - `auth_login` (success & failure with email as `resource_id`)
  - `auth_register`, `auth_logout`
  - `authz_deny` (any forbidden/unauthorized attempt)
  - `incident_view_exact_location` (non-patient read of coordinates)
  - `incident_view_medical` (non-patient read of medical profile)

### 2.6 Database-Derived Rate Limiting (`AUTH-06`)
- **Stateless Serverless Execution (D-31, D-32, D-33)**:
  - No in-memory dictionaries or Redis dependencies.
  - Login Throttling:
    ```sql
    SELECT COUNT(*) FROM audit_logs
    WHERE action = 'auth_login' AND outcome = 'deny'
      AND resource_id = :email AND at >= :cutoff
    ```
    Cutoff = `clock.now(demo_session_id, db) - timedelta(minutes=15)`. Limit = 5.
  - SOS Creation Throttling:
    ```sql
    SELECT COUNT(*) FROM emergencies
    WHERE reported_by_user_id = :user_id AND created_at >= :cutoff
    ```
    Cutoff = `clock.now(demo_session_id, db) - timedelta(hours=1)`. Limit = 3.
  - On limit breach: Returns HTTP 429 with `Retry-After: <seconds>` header and `{ "error": { "code": "RATE_LIMITED", "message": "...", "retry_after_s": N } }`.

---

## 3. Threat Modeling & Security Mitigations (ASVS L1)

| Threat ID | Description | Impact | Mitigation Strategy |
|-----------|-------------|--------|---------------------|
| **T-02-01** | Brute force password guessing | Account takeover | DB-derived rate limiter locks email after 5 failed attempts in 15 min; generic error message ("Invalid email or password"). |
| **T-02-02** | Credential stuffing / Common passwords | Bulk account breach | Argon2id memory-hard hashing + denylist check for top 100 common passwords. |
| **T-02-03** | Insecure token storage / XSS theft | Session hijacking | JWT stored in `HttpOnly; SameSite=Strict` cookie, completely inaccessible to JavaScript. |
| **T-02-04** | Cross-Site Request Forgery (CSRF) | Unauthorized state change | `SameSite=Strict` cookie attribute; mutating endpoints require JSON `Content-Type` + same-origin verification. |
| **T-02-05** | IDOR resource enumeration | Data leak of patient incidents | Centralized `services/authz.py` masking unowned resources with `404 NOT_FOUND`. |
| **T-02-06** | Cross-tenant data leakage | Breach of judge demo sessions | Strict `demo_session_id` tenant scoping on all queries and object authorization checks. |
| **T-02-07** | Sensitive data read without audit trail | Lack of accountability | Non-patient access to exact coordinates or medical records triggers immediate audit record. |
| **T-02-08** | In-memory rate limiter evasion on serverless | DoS / SOS flooding | Rate limits calculated directly from persistent PostgreSQL `audit_logs` and `emergencies`. |

---

## 4. Validation Architecture

### 4.1 Automated Test Suites
1. **`backend/tests/test_auth.py`**:
   - `test_register_citizen_success`: Creates citizen, verifies argon2id hash, issues session cookie.
   - `test_register_responder_success`: Creates responder, initializes responder profile.
   - `test_register_forbidden_roles`: Attempting to register `authority` or `ambulance_operator` raises 422.
   - `test_register_validation`: Invalid email, weak password (<10 chars), common password rejected.
   - `test_login_success_and_cookie`: Valid credentials return user data and set `ll_session` cookie.
   - `test_login_bearer_fallback`: Valid token passed in `Authorization: Bearer` authenticated successfully.
   - `test_login_invalid_password`: Bad password logs `outcome='deny'` to `audit_logs` and returns generic 401.
   - `test_login_deactivated_user`: Deactivated user (`is_active=False`) rejected even with valid password.
   - `test_logout`: Clears session cookie (`Max-Age=0`).
   - `test_auth_me`: Returns current user and profile.
2. **`backend/tests/test_authz_matrix.py`**:
   - `test_route_enumeration_deny_by_default`: Scans all registered routes in FastAPI app; asserts non-public routes require authentication.
   - `test_rbac_matrix`:
     - Citizen calling responder/authority routes receives 403.
     - Responder calling authority routes receives 403.
     - Authority calling responder private endpoints receives 403.
3. **`backend/tests/test_object_authz.py`**:
   - `test_emergency_ownership_idor_defense`: Non-participant citizen accessing emergency gets 404 NOT_FOUND.
   - `test_emergency_tenant_isolation`: User in demo session A accessing emergency in demo session B gets 404 NOT_FOUND.
   - `test_offer_action_authorization`: Responder A attempting to accept offer assigned to Responder B receives 403 FORBIDDEN.
   - `test_medical_profile_privacy`: Non-participant denied access; unconsented emergency hides medical fields.
4. **`backend/tests/test_audit.py`**:
   - `test_audit_login_events`: Verifies `action='auth_login'` records with `outcome='allow'` and `outcome='deny'`.
   - `test_audit_persistence_on_abort`: Verifies audit denial record is written and committed even when HTTP exception is raised.
   - `test_audit_ip_hashing`: Verifies `ip_hash` is a 64-char hex HMAC-SHA256 string, not plain IP.
   - `test_audit_sensitive_data_reads`: Verifies reading exact coords or medical records emits audit logs.
5. **`backend/tests/test_rate_limiter.py`**:
   - `test_login_rate_limiting`: 5 failed login attempts succeed, 6th attempt returns 429 with `Retry-After`.
   - `test_sos_rate_limiting`: User creating >3 emergencies in 1 hour returns 429.
   - `test_rate_limiter_clock_awareness`: Advancing virtual clock by 15 minutes clears login lockout.

---

## 5. Research Conclusion & Plan Decomposition

The phase decomposes naturally into 3 sequential, verifiable plans:
1. **Plan 02-01: Security Core, Password Hashing, JWT Sessions, and Auth Endpoints (`AUTH-01`, `AUTH-02`)**:
   - `core/security.py`, `schemas/auth.py`, `api/v1/auth.py`, session cookie management, `test_auth.py`.
2. **Plan 02-02: RBAC, Centralized Object Authorization, and Route Enumeration (`AUTH-03`, `AUTH-04`)**:
   - `api/deps.py`, `services/authz.py`, IDOR anti-enumeration defense, `test_authz_matrix.py`, `test_object_authz.py`.
3. **Plan 02-03: Security Audit Pipeline and DB-Derived Rate Limiting (`AUTH-05`, `AUTH-06`)**:
   - `services/audit.py`, `services/rate_limiter.py`, `test_audit.py`, `test_rate_limiter.py`.
