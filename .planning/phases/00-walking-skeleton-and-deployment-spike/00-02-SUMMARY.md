---
phase: 00-walking-skeleton-and-deployment-spike
plan: 02
subsystem: infra
tags: [vercel, serverless, nullpool, asgi, security-headers]

requires:
  - phase: 00-01
    provides: FastAPI backend and React 19 frontend
provides:
  - Vercel ASGI serverless function entrypoint in api/index.py
  - Root vercel.json routing rewrites and strict HTTP security headers
  - Environment-aware SQLAlchemy pooling (NullPool on serverless, QueuePool locally)
  - Root monorepo scripts for cross-platform dev, build, and test orchestration
affects: [00-03, phase-1, deployment]

tech-stack:
  added: [concurrently]
  patterns: [serverless-nullpool-pattern, asgi-lambda-bridge, strict-security-headers]

key-files:
  created:
    - api/index.py
    - vercel.json
    - package.json
    - backend/tests/test_vercel_config.py
    - backend/tests/test_db_pool.py
  modified:
    - backend/app/core/db.py

key-decisions:
  - "D-01: NullPool used in production/preview; QueuePool in local development"
  - "D-03: vercel.json rewrites /api/(.*) to api/index.py with CSP and anti-clickjacking headers"
  - "D-04: Cross-platform dev script uses uvicorn --app-dir backend"

patterns-established:
  - "Serverless connection hygiene: NullPool closes DB connections immediately to prevent pool exhaustion"
  - "Vercel path injection: api/index.py resolves backend directory dynamically into sys.path"

requirements-completed: [INFRA-01, INFRA-02]

duration: 10min
completed: 2026-10-01
---

# Phase 00: Plan 02 Summary

**Configured Vercel serverless deployment wiring with ASGI entrypoint, security headers, environment-aware connection pooling, and root developer scripts.**

## Performance
- **Duration:** 10 min
- **Tasks completed:** 3 of 3
- **Files modified/created:** 6 files

## Accomplishments
- Implemented `api/index.py` ASGI handler dynamically injecting `backend/` into `sys.path`.
- Defined root `vercel.json` with API rewrites (`/api/(.*)` -> `api/index.py`), SPA fallback, and security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, strict CSP, `Referrer-Policy: no-referrer`).
- Implemented and verified environment-aware pooling in `backend/app/core/db.py` (`NullPool` for serverless, `QueuePool` for local dev).
- Configured root `package.json` with cross-platform `npm run dev` running Vite and Uvicorn concurrently.

## Verification Evidence
- `api/index.py` import assertion: verified `app` discovery
- `pytest backend/tests/test_vercel_config.py`: verified rewrites and security headers
- `pytest backend/tests/test_db_pool.py`: verified `NullPool` vs `QueuePool` selection
- Full backend suite: 7/7 tests passed
