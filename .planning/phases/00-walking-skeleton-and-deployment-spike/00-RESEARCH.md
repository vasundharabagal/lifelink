# Phase 0: Walking skeleton and deployment spike - Research

**Researched:** 2026-09-30  
**Domain:** Monorepo architecture, Vercel Serverless Python (FastAPI ASGI), Vite React 19 SPA, and PostgreSQL connection pooling  
**Confidence:** HIGH (Grounded in canonical `docs/LIFELINK_MASTER_SPEC.md`, Vercel documentation, and SQLAlchemy serverless patterns)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (Pooling Strategy):** Environment-aware SQLAlchemy pooling: `NullPool` in serverless/Vercel (`APP_ENV=production|preview` using pooled DB proxy URL), and standard `QueuePool` (`pool_size=5`, `max_overflow=10`) for local Docker Compose development.
- **D-02 (Local Container):** Local PostgreSQL Docker Compose maps to standard port 5432 with `lifelink_user`, `lifelink_password`, `lifelink_db`, and container healthcheck (`pg_isready`).
- **D-03 (Routing & Security):** Monorepo root `vercel.json` rewrites `/api/(.*)` to `api/index.py` (ASGI handler) and static fallback to `apps/web/dist` with Content-Security-Policy and security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`).
- **D-04 (Local Orchestration):** Local development uses root npm script `npm run dev` running Vite on port 5173 (with `/api` proxy to `http://localhost:8000`) and Uvicorn on port 8000 concurrently.
- **D-05 (Diagnostics Card):** Comprehensive diagnostics card on `/` displaying API status, PostgreSQL connectivity, round-trip latency (ms), poll counter, server UTC timestamp, and environment banner (Vercel vs Local Docker).
- **D-06 (Resilience UI):** Non-blocking reconnection banner on polling disconnects: subtle banner showing retry countdown and backoff status while preserving previous healthy state.
- **D-07 (Cold-Start Gate):** Maximum cold-start threshold is set to 3.0 s in `docs/ADR-001-deployment.md`. If cold start <= 3.0 s, remain on Vercel; if > 3.0 s, activate the Render/Railway container contingency.
- **D-08 (Latency Target):** Warm roundtrip latency target for `/api/v1/health` (FastAPI execution + `SELECT 1` query) is sub-500 ms p95.

### the agent's Discretion
- Selection of specific npm concurrency runner (`concurrently` in root `package.json`).
- Styling tokens for the Phase 0 diagnostic card adhering to the light-theme palette specified in `docs/LIFELINK_MASTER_SPEC.md`.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed strictly within Phase 0 scope.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Static Asset Delivery | CDN / Static (Vercel Edge) | — | Ultra-fast global distribution of static HTML/JS/CSS bundles from `apps/web/dist` |
| Health Check UI & Polling | Browser / Client (React SPA) | — | Client-driven HTTP polling (2 s) with `usePolling` hook, latency timing, and reconnection handling |
| API Request Routing | CDN / Routing (`vercel.json`) | API / Backend (`api/index.py`) | Vercel rewrites `/api/(.*)` to Python serverless function while routing all other paths to `index.html` |
| Health Endpoint (`/api/v1/health`) | API / Backend (FastAPI) | Database / Storage (Postgres) | Validates ASGI bootstrap, executes `SELECT 1` via SQLAlchemy session, and serializes JSON envelope |
| Database Connection & Pooling | Database / Storage (PostgreSQL) | API / Backend (`core/db.py`) | `NullPool` prevents serverless connection exhaustion against managed Postgres pooled endpoints |
| Local Dev Containerization | Local Environment (Docker Compose) | — | PostgreSQL 16 container with persistent volumes and healthcheck on port 5432 |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 0 validates the core architectural premise of LIFELINK: can a monorepo containing a modern React SPA and a stateless FastAPI backend deploy seamlessly to Vercel Serverless Functions and reliably query PostgreSQL via HTTP polling without WebSocket infrastructure?

The research confirms that Vercel Serverless Functions natively support Python ASGI applications exported through `api/index.py`. By structuring the monorepo with `apps/web/` for the Vite frontend and `backend/app/` for the Python package, root configuration files (`vercel.json`, `package.json`, and `docker-compose.yml`) maintain clean boundaries without path pollution.

To prevent serverless connection starvation against PostgreSQL (Neon/Supabase), SQLAlchemy engine configuration must be environment-aware: instantiating `NullPool` under serverless execution (where Neon's PgBouncer pooled proxy manages connections) and standard `QueuePool` during local development. The walking skeleton frontend verifies active 2 s polling against `/api/v1/health`, measures cold start and warm latency, and documents the operational verdict in `docs/ADR-001-deployment.md`.

**Primary recommendation:** Scaffold `apps/web` with Vite React 19 and `backend` with FastAPI 0.115+; export ASGI `app` via `api/index.py`; wire root `vercel.json` with security headers; enforce `NullPool` for serverless; and benchmark `/api/v1/health` to prove the 3.0 s cold-start gate.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vite | 6.x | Frontend build tool & HMR | Sub-second dev reload, clean ESM output under 200 KB gzip target |
| React + TypeScript | 19.x / TS 5.x | Web UI layer | Industry standard for mobile-first interactive emergency applications |
| Tailwind CSS | 4.x / 3.4.x | Utility CSS framework | Accessible touch targets (>=48px), light-only design system, WCAG AA compliance |
| FastAPI | 0.115+ | Backend ASGI API | Native Pydantic v2 validation, sub-millisecond route handling, pure testability |
| Uvicorn | 0.32+ | ASGI web server | High-performance local development server for Python 3.11+ |
| SQLAlchemy | 2.0+ | SQL toolkit & ORM | Declarative models, connection pooling control (`NullPool`), robust transaction lifecycle |
| psycopg2-binary | 2.9+ | PostgreSQL DBAPI driver | Proven PostgreSQL adapter compatible with managed Neon/Supabase endpoints |
| Pydantic | 2.10+ | Contract validation | Strict schema serialization with `extra="forbid"` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| concurrently | 9.x | Monorepo task runner | Concurrently launches Vite and Uvicorn in local development |
| httpx | 0.28+ | Async HTTP client | Used in pytest suite for end-to-end testing of FastAPI ASGI application |
| pytest + pytest-asyncio | 8.x | Test framework | Automated unit and integration testing of `/api/v1/health` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Monorepo Vercel (`api/index.py`) | Separate backend on Render | Render eliminates serverless cold starts but requires managing two deployment pipelines; retained as contingency in ADR-001 |
| Client-driven HTTP polling (2s) | WebSockets / SSE | WebSockets drop on serverless execution freezes; polling is completely resilient and stateless |
| `NullPool` (Serverless) | `QueuePool` (Serverless) | QueuePool leaks idle connections across ephemeral function instances, leading to `too many clients` errors |

**Installation:**
```bash
# Root tooling
npm install -D concurrently

# Frontend (apps/web)
cd apps/web && npm install react react-dom
cd apps/web && npm install -D typescript @types/react @types/react-dom vite @vitejs/plugin-react tailwindcss @tailwindcss/vite

# Backend (backend)
cd backend && pip install -r requirements.txt
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```
[Local Development]
Browser (localhost:5173) ──Vite Proxy (/api)──> Uvicorn (localhost:8000) ──QueuePool──> Local Docker Postgres (:5432)

[Vercel Production / Preview]
Browser (https://*.vercel.app)
  │
  ├── static assets (/*) ──────────> Vercel Edge CDN (apps/web/dist)
  └── api requests (/api/v1/*) ────> Vercel Serverless Function (api/index.py)
                                           │
                                       NullPool
                                           │
                                           v
                               Managed PostgreSQL (Neon / Supabase Pooled Endpoint)
```

### Monorepo Structure

```
/
├── apps/
│   └── web/
│       ├── src/
│       │   ├── App.tsx          # Walking skeleton diagnostic view
│       │   ├── index.css        # Tailwind light theme tokens
│       │   ├── main.tsx         # React root mounting
│       │   └── usePolling.ts    # Reusable 2s polling hook with backoff
│       ├── package.json
│       ├── tsconfig.json
│       └── vite.config.ts       # Configured with proxy for /api -> localhost:8000
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py        # Settings loaded via pydantic-settings
│   │   │   └── db.py            # SQLAlchemy engine with environment-aware pooling
│   │   ├── api/v1/
│   │   │   └── health.py        # GET /api/v1/health endpoint executing DB check
│   │   └── main.py              # FastAPI app definition with standard error envelopes
│   ├── tests/
│   │   └── test_health.py       # Pytest verifying /api/v1/health response contract
│   └── requirements.txt
├── api/
│   └── index.py                 # Vercel entrypoint importing `app` from backend.app.main
├── docs/
│   └── ADR-001-deployment.md    # Architecture Decision Record for deployment spike
├── docker-compose.yml           # Local PostgreSQL 16 container with healthcheck
├── package.json                 # Root scripts: dev, build, test
└── vercel.json                  # Routing rewrites, CSP, and security headers
```

### Environment-Aware Engine Pattern (`backend/app/core/db.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool
from app.core.config import settings

def get_engine():
    if settings.APP_ENV in ("production", "preview"):
        # Serverless environment: do not maintain connection pools across function freezes
        return create_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,
            connect_args={"connect_timeout": 5}
        )
    else:
        # Local development: maintain small pool for fast local responses
        return create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
```

### Root `vercel.json` Routing Pattern

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "api/index.py"
    },
    {
      "source": "/(.*)",
      "destination": "/apps/web/dist/$1"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "no-referrer" },
        { "key": "Permissions-Policy", "value": "geolocation=(self)" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: *.tile.openstreetmap.org; connect-src 'self';" }
      ]
    }
  ]
}
```
</architecture_patterns>

<validation_architecture>
## Validation Architecture

### Automated Verification Plan
1. **Local Backend Health Test (`pytest backend/tests/test_health.py`):**
   - Validates that `GET /api/v1/health` returns HTTP 200 with JSON payload `{"status": "ok", "db": "ok", "version": "1.0", "demo_mode": bool}`.
   - Validates DB connectivity by executing `SELECT 1` on the active session.
   - Validates error handling by simulating DB outage and asserting `{"status": "error", "db": "error"}`.
2. **Frontend Build & Smoke Test (`npm --prefix apps/web run build`):**
   - Validates TypeScript compilation and Vite static asset bundling into `apps/web/dist`.
3. **Local Monorepo Dev Command (`npm run dev`):**
   - Validates that root npm script concurrently starts Vite and Uvicorn.
4. **Vercel Serverless Health Ping (`curl https://<preview-domain>/api/v1/health`):**
   - Measures cold-start execution time (< 3.0 s threshold).
   - Measures warm execution roundtrip latency (< 500 ms p95 threshold).

### Manual-Only Verification
- Opening deployed walking skeleton page on a mobile device to visually verify live 2 s polling counter increments and disconnection banner appears when toggling Airplane Mode.
</validation_architecture>

<pitfalls>
## Critical Pitfalls to Avoid

1. **Python Path Issues in `api/index.py`:**
   - *Problem:* When Vercel executes `api/index.py`, Python's `sys.path` may not include `backend/`, causing `ModuleNotFoundError: No module named 'app'`.
   - *Prevention:* Explicitly insert the root directory and `backend/` into `sys.path` inside `api/index.py` before importing `app`.
2. **Heavy Python Dependencies on Serverless:**
   - *Problem:* Installing scientific libraries (numpy, pandas, scipy) explodes the serverless function bundle, driving cold starts past 5–10 seconds.
   - *Prevention:* Keep `backend/requirements.txt` minimal (FastAPI, Uvicorn, SQLAlchemy, psycopg2-binary, Pydantic).
3. **Database Connection Exhaustion:**
   - *Problem:* Every serverless container spin-up creates a new connection pool. Under load, PostgreSQL runs out of available connection slots.
   - *Prevention:* Use `NullPool` and connect exclusively through Neon/Supabase pooled proxy endpoints (`sslmode=require`).
4. **CORS Complications:**
   - *Problem:* Local frontend on 5173 calling backend on 8000 without proxy causes browser CORS blocks.
   - *Prevention:* Configure Vite `server.proxy` to route `/api` to `http://localhost:8000`, matching production same-origin semantics.
</pitfalls>

<sources>
## Sources

### Primary
- `docs/LIFELINK_MASTER_SPEC.md` — Section 4 (Architecture), Section 15 (Deployment), Section 18 (Phase 0)
- Vercel Documentation — Python Serverless Functions & Monorepo configuration
- SQLAlchemy Documentation — Engine Configuration & Disabling Pooling with `NullPool`

### Secondary
- Vite Documentation — Server Proxy & Multi-Page Configurations
</sources>

---
*Phase: 0-walking-skeleton-and-deployment-spike*  
*Research completed: 2026-09-30*  
*Ready for planning: yes*
