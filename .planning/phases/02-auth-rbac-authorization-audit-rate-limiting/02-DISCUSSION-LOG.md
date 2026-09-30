# Phase 2: Auth, RBAC, Authorization, Audit, Rate Limiting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01  
**Phase:** 02-auth-rbac-authorization-audit-rate-limiting  
**Areas discussed:** Cookie & Token Transport, Object-Level Authorization Architecture, DB-Derived Rate Limiting Engine, Audit Logging Pipeline  

---

## Cookie & Token Transport

| Option | Description | Selected |
|--------|-------------|----------|
| Dual transport | Read cookie 'll_session' first, fallback to 'Authorization: Bearer' header (simplifies pytest, curl, cross-origin dev) | ✓ |
| Strict cookie-only | Reject Authorization header entirely, requiring all API calls to pass 'll_session' cookie | |

**User's choice:** Dual transport: Read cookie 'll_session' first, fallback to 'Authorization: Bearer' header.  
**Notes:** Provides production browser security with SameSite cookie while enabling clean headless testing and automated test execution.

| Option | Description | Selected |
|--------|-------------|----------|
| Environment-aware | Secure=False and SameSite='Lax' in development/preview; Secure=True and SameSite='Strict' in production | ✓ |
| Always Secure=True | HTTPS required in all environments (requires local self-signed certs) | |

**User's choice:** Environment-aware flags.  
**Notes:** Avoids local HTTPS certification overhead during development while strictly locking production down.

---

## Object-Level Authorization Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit guard functions | authz.assert_can_view_emergency(user, emergency, db) executing checks, logging denials, and raising exceptions | ✓ |
| FastAPI path dependencies | Depends(get_authorized_emergency) loading entities before router body | |

**User's choice:** Explicit guard functions.  
**Notes:** Clear programmatic call sites, simple unit testability, and decoupling from framework-specific routing dependency trees.

| Option | Description | Selected |
|--------|-------------|----------|
| Anti-enumeration 404/403 | 404 NOT_FOUND on ownership/tenancy mismatch to prevent resource enumeration; 403 FORBIDDEN on permission lack | ✓ |
| Standard 403 FORBIDDEN | Return 403 FORBIDDEN for all authorization and ownership failures | |

**User's choice:** Anti-enumeration 404 on ownership/tenancy mismatch; 403 on permission lack.  
**Notes:** Aligns with OWASP IDOR mitigation guidelines by never confirming existence of unowned incidents or profiles.

---

## DB-Derived Rate Limiting Engine

| Option | Description | Selected |
|--------|-------------|----------|
| Standard 429 response | 429 with 'Retry-After' header and JSON error envelope with 'retry_after_s' and friendly message | ✓ |
| Simple 429 status code | Generic error message and no Retry-After calculation | |

**User's choice:** Standard 429 response with 'Retry-After' header and structured error envelope.  
**Notes:** Allows frontend countdown timers and user-friendly unlock guidance.

| Option | Description | Selected |
|--------|-------------|----------|
| Clock-aware | Rate limiter calculates rolling time windows relative to Clock.now(demo_session_id) | ✓ |
| Wall-clock only | Rate limiter strictly uses system UTC datetime.now() | |

**User's choice:** Clock-aware time windows.  
**Notes:** Ensures automated CI test runs and demo scenario time-travel evaluate rate limit windows deterministically.

---

## Audit Logging Pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate dedicated commit | Audit logs commit immediately in a dedicated transaction so records survive request aborts/rollbacks | ✓ |
| Rely on main request commit | Rely on main request transaction commit (risk: rollbacks discard audit entries) | |

**User's choice:** Immediate dedicated commit.  
**Notes:** Critical for security: failed login attempts and unauthorized access attempts must be permanently recorded even when the HTTP transaction aborts.

| Option | Description | Selected |
|--------|-------------|----------|
| Salted SHA-256 | Salted SHA-256 hash using settings.JWT_SECRET as salt | ✓ |
| Plain unsalted SHA-256 | Plain unsalted SHA-256 of IP string | |

**User's choice:** Salted SHA-256 hash.  
**Notes:** Protects user privacy under GDPR while enabling per-IP attack clustering and abuse prevention.

---

## the agent's Discretion

None — all implementation decisions explicitly aligned with user input.

## Deferred Ideas

None — discussion remained strictly within the boundaries of Phase 2.
