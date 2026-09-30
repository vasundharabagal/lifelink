---
phase: 2
slug: auth-rbac-authorization-audit-rate-limiting
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio against PostgreSQL |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_auth.py` |
| **Full suite command** | `pytest backend/tests/` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test suite for the modified module
- **After every plan wave:** Run full test suite (`pytest backend/tests/`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | AUTH-01 | T-02-01 | Registration with Argon2id password hash | integration | `pytest backend/tests/test_auth.py -k test_register` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AUTH-01 | T-02-02 | Reject authority/operator self-registration | unit | `pytest backend/tests/test_auth.py -k test_register_forbidden_roles` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AUTH-02 | T-02-03 | Login sets httpOnly SameSite cookie and Bearer fallback | integration | `pytest backend/tests/test_auth.py -k test_login` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AUTH-02 | T-02-03 | Deactivated user rejected on request | integration | `pytest backend/tests/test_auth.py -k test_deactivated` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | AUTH-03 | — | 100% of non-public routes require authentication | static | `pytest backend/tests/test_authz_matrix.py -k test_route_enumeration` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | AUTH-03 | T-02-05 | Role-based access control matrix (citizen/resp/auth) | unit | `pytest backend/tests/test_authz_matrix.py -k test_rbac` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | AUTH-04 | T-02-05 | IDOR anti-enumeration defense returns 404 NOT_FOUND | unit | `pytest backend/tests/test_object_authz.py -k test_idor` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 2 | AUTH-04 | T-02-06 | Multi-tenant demo session isolation enforced | unit | `pytest backend/tests/test_object_authz.py -k test_tenant` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | AUTH-05 | T-02-07 | Audit logs written in dedicated immediate transaction | integration | `pytest backend/tests/test_audit.py -k test_audit_persistence` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | AUTH-05 | T-02-07 | Salted IP anonymization in audit logs | unit | `pytest backend/tests/test_audit.py -k test_ip_hash` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 3 | AUTH-06 | T-02-08 | 5 failed logins triggers 429 RATE_LIMITED | integration | `pytest backend/tests/test_rate_limiter.py -k test_login_rate` | ❌ W0 | ⬜ pending |
| 02-03-04 | 03 | 3 | AUTH-06 | T-02-08 | Clock-aware time window unlocks throttled user | integration | `pytest backend/tests/test_rate_limiter.py -k test_clock` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_auth.py` — registration, login, session cookies, and logout
- [ ] `backend/tests/test_authz_matrix.py` — route enumeration and role boundary matrix
- [ ] `backend/tests/test_object_authz.py` — object-level authorization, IDOR masking, and tenant scoping
- [ ] `backend/tests/test_audit.py` — audit logging pipeline and IP anonymization
- [ ] `backend/tests/test_rate_limiter.py` — database-derived rate limiting and Clock-aware time windows
