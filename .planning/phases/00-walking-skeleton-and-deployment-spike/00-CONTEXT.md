# Phase 0: Walking skeleton and deployment spike - Context

**Gathered:** 2026-09-30  
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 0 proves the end-to-end technical foundation before any emergency feature logic is implemented. It delivers a working monorepo walking skeleton: a static Vite + React 19 + TypeScript + Tailwind SPA in `apps/web/`, a stateless FastAPI (Python 3.11+) backend in `backend/` exported via `api/index.py`, a local PostgreSQL container via `docker-compose.yml`, and serverless deployment configuration via `vercel.json`. It validates real HTTP polling (2 s interval) against `/api/v1/health` with database query execution, measures serverless cold starts, and records the architectural verdict in `docs/ADR-001-deployment.md`.

In Scope:
- Scaffolding `apps/web/` with Vite, React 19, TypeScript, and Tailwind CSS (light theme tokens).
- Scaffolding `backend/` with FastAPI, SQLAlchemy 2.0, Pydantic v2, and `/api/v1/health` executing a live DB query.
- Monorepo entrypoint `api/index.py` exposing ASGI `app` for Vercel Serverless Functions.
- `vercel.json` rewrites (`/api/(.*)` -> `api/index.py`, SPA fallback to `apps/web/dist`) and security headers.
- `docker-compose.yml` for local PostgreSQL on port 5432 with healthchecks.
- Root npm scripts to run Vite (with `/api` proxy) and Uvicorn concurrently for local development.
- Walking skeleton UI page with live 2 s polling, diagnostic metrics, latency display, and reconnection banners.
- Measurement of cold-start and warm latency benchmarks, documented in `docs/ADR-001-deployment.md`.

Out of Scope:
- Domain business logic, triage engine, or orchestration matching (Phases 3–5).
- Database migrations or table schemas beyond the basic connection validation query (Phase 1).
- Authentication, JWT cookies, or user registration (Phase 2).
- Leaflet map rendering or incident reporting UI (Phases 6 & 8).
</domain>

<decisions>
## Implementation Decisions

### Database & Pooling Setup
- **D-01:** Environment-aware pooling: Configure SQLAlchemy engine with `NullPool` when deployed to serverless/Vercel (`APP_ENV=production|preview` using pooled DB proxy URL), and standard `QueuePool` (`pool_size=5`, `max_overflow=10`) for local Docker Compose development.
- **D-02:** Local PostgreSQL Docker Compose maps to standard port 5432 with `lifelink_user`, `lifelink_password`, `lifelink_db`, and container healthcheck (`pg_isready`).

### Monorepo & Vercel Wiring
- **D-03:** Monorepo root `vercel.json` rewrites `/api/(.*)` to `api/index.py` (ASGI handler) and static fallback to `apps/web/dist` with Content-Security-Policy and security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`).
- **D-04:** Local development uses root npm script `npm run dev` running Vite on port 5173 (with `/api` proxy to `http://localhost:8000`) and Uvicorn on port 8000 concurrently.

### Walking Skeleton Health UI
- **D-05:** Comprehensive diagnostics card on `/` displaying API status, PostgreSQL connectivity, round-trip latency (ms), poll counter, server UTC timestamp, and environment banner (Vercel vs Local Docker).
- **D-06:** Non-blocking reconnection banner on polling disconnects: subtle banner showing retry countdown and backoff status while preserving previous healthy state.

### Spike Benchmark & ADR Contingency
- **D-07:** Maximum cold-start threshold is set to 3.0 s in `docs/ADR-001-deployment.md`. If cold start <= 3.0 s, remain on Vercel; if > 3.0 s, activate the Render/Railway container contingency.
- **D-08:** Warm roundtrip latency target for `/api/v1/health` (FastAPI execution + `SELECT 1` query) is sub-500 ms p95.

### the agent's Discretion
- Selection of specific npm concurrency runner (`concurrently` or npm workspace script) in root `package.json`.
- Styling tokens for the Phase 0 diagnostic card adhering to the light-theme palette specified in `docs/LIFELINK_MASTER_SPEC.md`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Master Architecture & Deployment Specifications
- `docs/LIFELINK_MASTER_SPEC.md` §4 — System Architecture, component diagram, and cross-cutting rules
- `docs/LIFELINK_MASTER_SPEC.md` §15 — Deployment Architecture for Vercel, serverless constraints, and contingency plan
- `docs/LIFELINK_MASTER_SPEC.md` §18 — Phase 0 Objective, files/modules, tasks, and acceptance criteria
- `docs/ADR-001-deployment.md` — Target document recording walking skeleton benchmarks and deployment decision
- `.planning/research/STACK.md` — Recommended versions, dependencies, and serverless compatibility rules
- `.planning/research/PITFALLS.md` — Pitfall 1 (Serverless timeout and connection drops)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield codebase; no legacy application code.
- `.agent/` directory houses GSD tools and agent configurations.
- `docs/LIFELINK_MASTER_SPEC.md` is the canonical specification.

### Established Patterns
- All backend routes will reside under `/api/v1/*`.
- Standard API error envelope: `{"error": {"code": "STRING_CODE", "message": "human readable", "details": {}}}`.
- Monorepo structure separating static web app (`apps/web/`) from Python ASGI backend (`backend/` and `api/index.py`).

### Integration Points
- Frontend connects to backend via same-origin `/api/v1/*` URLs (proxied locally by Vite, rewritten by `vercel.json` in production).
- Backend connects to PostgreSQL via `DATABASE_URL` environment variable.
</code_context>

<specifics>
## Specific Ideas

- The Phase 0 test screen should display a live ping counter that increments every 2 seconds, demonstrating active client-driven polling and immediate visual confirmation that the serverless function is warm.
- Provide a clear curl walkthrough in `docs/ADR-001-deployment.md` demonstrating both local Docker and Vercel endpoint verification.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed strictly within Phase 0 scope.
</deferred>

---

*Phase: 0-Walking skeleton and deployment spike*  
*Context gathered: 2026-09-30*
