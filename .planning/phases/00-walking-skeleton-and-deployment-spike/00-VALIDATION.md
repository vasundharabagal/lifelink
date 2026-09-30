---
phase: 0
slug: walking-skeleton-and-deployment-spike
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-30
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution of the walking skeleton and deployment spike.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend smoke) |
| **Config file** | `backend/pytest.ini` / `apps/web/vite.config.ts` |
| **Quick run command** | `pytest backend/tests/test_health.py -v` |
| **Full suite command** | `pytest backend/tests/ && npm --prefix apps/web run build` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_health.py -v`
- **After every plan wave:** Run `pytest backend/tests/ && npm --prefix apps/web run build`
- **Before `/gsd-verify-work`:** Full suite must be green + live Vercel endpoint verified
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 00-01-01 | 01 | 1 | INFRA-01 | — | FastAPI initializes and responds to `/api/v1/health` | unit | `pytest backend/tests/test_health.py::test_health_schema` | ❌ W0 | ⬜ pending |
| 00-01-02 | 01 | 1 | INFRA-02 | — | SQLAlchemy executes `SELECT 1` against local Docker PostgreSQL | integration | `pytest backend/tests/test_health.py::test_db_connectivity` | ❌ W0 | ⬜ pending |
| 00-01-03 | 01 | 1 | INFRA-01 | — | Vite React SPA builds clean bundle without TypeScript errors | build | `npm --prefix apps/web run build` | ❌ W0 | ⬜ pending |
| 00-02-01 | 02 | 2 | INFRA-01 | T-00-01 | Root `vercel.json` rewrites and CSP headers prevent clickjacking and MIME sniffing | integration | `pytest backend/tests/test_vercel_config.py` | ❌ W0 | ⬜ pending |
| 00-02-02 | 02 | 2 | INFRA-02 | T-00-02 | Serverless execution enforces `NullPool` without persistent connection leakage | unit | `pytest backend/tests/test_db_pool.py` | ❌ W0 | ⬜ pending |
| 00-03-01 | 03 | 3 | INFRA-03 | — | Walking skeleton UI polls `/api/v1/health` every 2 s and tracks latency | component | `npm --prefix apps/web test` | ❌ W0 | ⬜ pending |
| 00-03-02 | 03 | 3 | INFRA-03 | — | ADR-001 documents measured cold-start (<3.0s) and warm latency (<500ms) | manual | `cat docs/ADR-001-deployment.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_health.py` — Test stubs for `/api/v1/health` and database connectivity
- [ ] `backend/pytest.ini` — Pytest configuration for Python path and async testing
- [ ] `backend/requirements.txt` — Pytest and HTTP test client dependencies (`pytest`, `pytest-asyncio`, `httpx`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile Polling & Offline Banner | INFRA-03 | Hardware network disconnect simulation | Open deployed Vercel URL on mobile phone, observe live 2s counter increments, toggle Airplane Mode, verify reconnection banner displays |
| Vercel Deployment Health Ping | INFRA-01 | External CDN deployment verification | Run `curl -i https://<preview-domain>/api/v1/health` and inspect HTTP 200 and security headers |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-30
