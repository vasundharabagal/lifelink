# Phase 2: Auth, RBAC, Authorization, Audit, Rate Limiting - Context

**Gathered:** 2026-10-01  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 2 establishes the secure access control and governance foundation for LIFELINK. It implements citizen and responder registration with Argon2id password hashing, JWT session authentication via httpOnly `ll_session` cookies with Bearer header fallback, centralized role-based access control (`require_role`), object-level authorization (`services/authz.py`) enforcing incident ownership and tenant isolation, immutable security audit logging (`audit_logs`), and database-derived rate limiting calculated directly from PostgreSQL records without in-memory state.

Emergency lifecycle state machines, clinical triage, and live dispatch orchestration belong in subsequent phases (Phases 3-5).
</domain>

<decisions>
## Implementation Decisions

### 1. Cookie & Token Transport Strategy
- **D-25:** Dual token transport. Authentication first inspects the httpOnly `ll_session` cookie; if absent, it falls back to parsing the `Authorization: Bearer <token>` header. This ensures strong web browser security while supporting automated pytest suites, CLI testing, and cross-origin frontend development.
- **D-26:** Environment-aware cookie attributes. Cookies set `HttpOnly`, `Path=/`, and max-age 12 hours. In `development` and `preview` environments, `Secure=False` and `SameSite='Lax'` to support unencrypted local HTTP testing; in `production`, `Secure=True` and `SameSite='Strict'`.
- **D-27:** Real-time database verification. JWT tokens contain `sub` (user UUID), `role`, `demo_session_id`, `iat`, and `exp`. Every authenticated request re-verifies the user against the database to guarantee that suspended or deactivated accounts lose access immediately.

### 2. Object-Level Authorization Architecture (`services/authz.py`)
- **D-28:** Explicit guard functions. Object-level checks are isolated in `backend/app/services/authz.py` as explicit assertion guards (e.g. `assert_can_view_emergency`, `assert_can_act_on_offer`, `assert_can_view_medical`). Route handlers call these guards directly rather than inlining authorization logic, preventing IDOR vulnerabilities.
- **D-29:** Anti-enumeration error masking. When a user attempts to access an incident, offer, or medical profile that does not belong to them or their tenant session, the guard raises `HTTPException(404, "NOT_FOUND")` to avoid revealing resource existence. If the user is a verified participant in the incident but lacks permissions for the specific action, it raises `HTTPException(403, "FORBIDDEN")`.
- **D-30:** Multi-tenant session scope isolation. All object-level checks strictly enforce that `request.user.demo_session_id == resource.demo_session_id`. Any cross-tenant read or mutation is treated as an ownership mismatch and rejected.

### 3. DB-Derived Rate Limiting Engine (`services/rate_limiter.py`)
- **D-31:** Database-derived rate limiting without in-memory stores. To accommodate stateless serverless scaling on Vercel, rate limits are computed dynamically via SQL queries against `audit_logs` and `emergencies`:
  - Login attempts: At most 5 failed attempts per email per 15 minutes (queried from `audit_logs` where `action = 'auth_login'` and `outcome = 'deny'`).
  - SOS creation: At most 3 emergencies created per user per hour (queried from `emergencies` or `audit_logs`).
  - Location updates: Throttled to 1 update per 5 seconds per responder.
- **D-32:** Standardized 429 response structure. When a rate limit is exceeded, the endpoint responds with HTTP 429 `RATE_LIMITED`, includes a standard `Retry-After: <seconds>` HTTP header, and returns a JSON envelope containing `{ "error": { "code": "RATE_LIMITED", "message": "...", "retry_after_s": N } }`.
- **D-33:** Clock-aware time windows. Rolling time windows for rate limit queries are evaluated relative to `Clock.now(demo_session_id, db)` rather than direct system time, enabling deterministic scenario time-travel and CI testing.

### 4. Audit Logging Pipeline (`services/audit.py`)
- **D-34:** Dedicated immediate commit. Security audit records (`audit_logs`) for authentication events, authorization denials, credential verifications, and sensitive data reads are committed immediately in a dedicated database transaction. This ensures audit records persist even if the primary HTTP request is aborted or rolls back.
- **D-35:** Salted client IP anonymization. Client IP addresses extracted from `Request.client.host` or `X-Forwarded-For` are hashed using HMAC/SHA-256 with `settings.JWT_SECRET` as the salt (`ip_hash`). This satisfies privacy regulations (GDPR) while preserving per-IP brute-force and abuse correlation.
- **D-36:** Sensitive data access audit triggers. Non-patient reads of exact patient coordinates or consented medical profiles automatically emit `action = 'incident_view_exact_location'` and `action = 'incident_view_medical'` audit records with `outcome = 'allow'`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and API Specifications
- `docs/LIFELINK_MASTER_SPEC.md` §8.1 — Auth API contracts (`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`).
- `docs/LIFELINK_MASTER_SPEC.md` §8.8 — Database-derived rate limiting rules and thresholds.
- `docs/LIFELINK_MASTER_SPEC.md` §10.1 — Authentication, password hashing, and JWT session rules.
- `docs/LIFELINK_MASTER_SPEC.md` §10.2 — Authorization, RBAC, object-level rules, and tenant scoping.
- `docs/LIFELINK_MASTER_SPEC.md` §14 — Security audit logging and sensitive data read tracking.
- `docs/LIFELINK_MASTER_SPEC.md` §18 Phase 2 — Implementation checklist and verification criteria.

### Project Context
- `.planning/PROJECT.md` — Security principles, explainability invariants, and architecture constraints.
- `.planning/REQUIREMENTS.md` — Requirements `AUTH-01` through `AUTH-06`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/user.py`: `User` and `MedicalProfile` models with role strings and demo session IDs.
- `backend/app/models/audit.py`: `AuditLog` model with append-only PostgreSQL trigger rejecting UPDATE/DELETE.
- `backend/app/core/clock.py`: `Clock.now(demo_session_id, db)` for deterministic virtual time window calculations.
- `backend/app/core/config.py`: `settings.JWT_SECRET`, `settings.APP_ENV`, `settings.DEMO_MODE_ENABLED`.
- `backend/app/core/db.py`: `get_db()`, `SessionLocal`, and serverless-compatible connection pooling.

### Established Patterns
- SQLAlchemy 2.0 type-annotated queries and models (`Mapped[...]`).
- Dependency injection via FastAPI `Depends(...)`.
- StrEnum role and action definitions in `app.domain.enums` (`UserRole`, `AuditOutcome`).
- Isolated test savepoint rollbacks in `backend/tests/conftest.py`.

### Integration Points
- `backend/app/api/v1/auth.py`: New auth router mounting `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`.
- `backend/app/core/security.py`: Password hashing (Argon2id) and JWT creation/verification utilities.
- `backend/app/services/authz.py`: Centralized object-level access control guards.
- `backend/app/services/audit.py`: Security audit logger emitting immutable records.
- `backend/app/services/rate_limiter.py`: Database-derived rate limiting checks.
- `backend/app/main.py`: Include `auth_router` in `/api/v1`.

</code_context>

<specifics>
## Specific Ideas

- Route enumeration test (`test_authz_matrix.py`) must inspect the FastAPI OpenAPI / route registry to ensure that 100% of non-public endpoints enforce an authentication dependency (deny-by-default).
- Self-registration is strictly restricted to `citizen` and `responder` roles; `authority` and `ambulance_operator` accounts can never be registered via public endpoints.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 2 scope.
</deferred>

---

*Phase: 02-auth-rbac-authorization-audit-rate-limiting*  
*Context gathered: 2026-10-01*  
