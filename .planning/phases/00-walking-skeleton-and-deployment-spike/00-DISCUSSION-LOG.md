# Phase 0: Walking skeleton and deployment spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-30  
**Phase:** 0-walking-skeleton-and-deployment-spike  
**Areas discussed:** Database & Pooling Setup, Monorepo & Vercel Wiring, Walking Skeleton Health UI, Spike Benchmark & ADR Contingency  

---

## Database & Pooling Setup

| Option | Description | Selected |
|--------|-------------|----------|
| Environment-aware pooling | NullPool in serverless/Vercel (pooled DB proxy), standard QueuePool (pool_size=5) for local Docker Compose | ✓ |
| NullPool everywhere | Disable pooling across both local development and production to guarantee identical connection semantics | |

**User's choice:** Environment-aware pooling (NullPool in serverless, QueuePool for local Docker)  
**Notes:** Local Docker avoids exhausting connections during rapid HMR development while serverless complies with pooled proxy limits.

| Option | Description | Selected |
|--------|-------------|----------|
| Standard port 5432 | Map Postgres to 5432 with lifelink_user/lifelink_db and container healthcheck | ✓ |
| Alternate port 5433 | Map Postgres to 5433 to avoid port collisions with pre-existing local PostgreSQL service | |

**User's choice:** Standard port 5432  
**Notes:** Default standard port makes local environment intuitive and matches docker-compose conventions.

---

## Monorepo & Vercel Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Standard monorepo vercel.json | Rewrites /api/(.*) to api/index.py and routes SPA traffic to apps/web/dist with CSP/security headers | ✓ |
| Explicit build command routing | Configure Vercel Project Root Directory pointing to apps/web with external api/ directory mapping | |

**User's choice:** Standard monorepo vercel.json  
**Notes:** Preserves monorepo cleanliness with single root configuration for headers and function rewrites.

| Option | Description | Selected |
|--------|-------------|----------|
| Root npm scripts + Vite proxy | Single "npm run dev" command in root running Vite (proxying /api to 8000) and Uvicorn concurrently | ✓ |
| Separate terminal processes | Run frontend and backend independently in their respective directories without root concurrency scripts | |

**User's choice:** Root npm scripts + Vite proxy  
**Notes:** Single developer entrypoint accelerates testing and local reproducibility.

---

## Walking Skeleton Health UI

| Option | Description | Selected |
|--------|-------------|----------|
| Comprehensive diagnostics card | API status, DB connectivity, round-trip latency (ms), poll counter, server timestamp, and environment banner | ✓ |
| Minimalist status badge | Simple green/red connectivity indicator with expandable raw JSON debug view | |

**User's choice:** Comprehensive diagnostics card  
**Notes:** Visible polling counter and round-trip latency offer immediate visual proof of health check execution for judges.

| Option | Description | Selected |
|--------|-------------|----------|
| Non-blocking reconnection banner | Subtle banner showing retry countdown and backoff status while preserving previous state | ✓ |
| Immediate error alert | Show a prominent error state immediately replacing the dashboard on any failed poll | |

**User's choice:** Non-blocking reconnection banner  
**Notes:** Ensures resilient UX during brief cold-start lags or network blips without jarring screen replacements.

---

## Spike Benchmark & ADR Contingency

| Option | Description | Selected |
|--------|-------------|----------|
| 3.0 s cold-start threshold | Cold start <= 3.0 s acceptable on Vercel; > 3.0 s triggers Render/Railway container contingency | ✓ |
| 5.0 s cold-start threshold | Up to 5.0 s tolerable since client polling warms the function before active emergency interactions | |

**User's choice:** 3.0 s cold-start threshold  
**Notes:** Enforces the strict latency boundary defined in Section 15 of LIFELINK_MASTER_SPEC.md.

| Option | Description | Selected |
|--------|-------------|----------|
| Sub-500 ms p95 | Warm /health roundtrip (FastAPI + DB query) under 500 ms | ✓ |
| Sub-250 ms p95 | Strict latency target requiring optimal pooled proxy region placement | |

**User's choice:** Sub-500 ms p95  
**Notes:** Realistic and robust target for serverless function with managed database query execution.

---

## the agent's Discretion

- Selection of root concurrency script tooling (`concurrently` dependency in root `package.json`).
- Fine-grained Tailwind styling tokens for the Phase 0 diagnostics card adhering to the light-theme palette.

## Deferred Ideas

None — discussion remained strictly focused on Phase 0 scope.
