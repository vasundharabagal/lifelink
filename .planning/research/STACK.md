# Stack Research

**Domain:** Community First-Aid & Emergency Dispatcher (SDG 3, Good Health & Well-being)  
**Researched:** 2026-09-30  
**Confidence:** HIGH (Derived strictly from canonical `docs/LIFELINK_MASTER_SPEC.md` and verified 2025/2026 ecosystem patterns)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| React + TypeScript | 19.x / TS 5.x | Mobile-first SPA frontend | Component model, type safety for complex emergency contracts, fast static delivery on Vercel CDN |
| Vite | 6.x | Frontend build tool | Ultra-fast HMR, tiny production bundles (<200 KB gzip target for citizen flow), seamless ESM bundling |
| Tailwind CSS | 4.x / 3.4.x | CSS framework | Utility-first styling for strict light-theme design system, WCAG AA compliance, and accessible touch targets (>=48px) |
| FastAPI | 0.115+ (Python 3.11+) | Backend API framework | High-performance async ASGI, native Pydantic v2 validation, OpenAPI schema generation, pure testability |
| PostgreSQL | 16+ (Neon/Supabase) | Primary relational database | Atomic row locks (`FOR UPDATE`), partial unique indexes, check constraints, append-only triggers, JSONB support |
| SQLAlchemy + Alembic | 2.0+ / 1.14+ | ORM & DB migrations | Strict schema migrations, query builder, connection pooling compatible with serverless (`NullPool`) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | v2.10+ | Strict contract validation | All API request/response models, TriageResult, HandoverPacket schemas with `extra="forbid"` |
| argon2-cffi | 23.x+ | Password hashing | Industry-standard memory-hard password hashing for citizen and responder accounts |
| PyJWT | 2.10+ | Session tokens | httpOnly, SameSite=Strict cookie authentication (`ll_session`) containing sub, role, demo_session_id |
| Leaflet | 1.9+ | Interactive emergency maps | Lightweight, mobile-friendly raster tile maps with custom `divIcon` markers; remains functional if tiles fail |
| pytest + pytest-asyncio | 8.x+ | Test suite runner | Unit testing, golden dataset evaluation, concurrency race tests, and authz matrix verification |
| Playwright | 1.49+ | End-to-end browser automation | Mobile viewport verification of the 19-step scenario and multi-role context tests |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker & Docker Compose | Local PostgreSQL & API containerization | Fallback environment for reliable offline judging and reproducible integration tests |
| Alembic | Migration runner | Generates up/down migrations for the 11 database tables and constraint validation |
| pip-audit & npm audit | Dependency vulnerability scanning | Verifies supply-chain hygiene before production deployment |

## Installation

```bash
# Frontend (apps/web)
npm install react react-dom leaflet
npm install -D typescript @types/react @types/react-dom @types/leaflet vite @vitejs/plugin-react tailwindcss @tailwindcss/vite

# Backend (backend/requirements.txt)
pip install fastapi uvicorn pydantic sqlalchemy psycopg2-binary alembic argon2-cffi pyjwt python-multipart httpx pytest pytest-asyncio
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI (Python) | Next.js API Routes | Next.js offers unified TS, but Python was chosen for AI evaluation tooling, golden test harness, and pure algorithm testability |
| HTTP Polling (2 s / 5 s) | WebSockets / SSE | WebSockets suit long-lived server architectures, but fail silently on serverless Vercel function instances |
| Lazy deterministic `advance()` | Scheduled Cron / Celery | Cron works when persistent worker infrastructure exists; lazy evaluation runs deterministically within HTTP poll requests |
| Haversine + Bounding Box | PostGIS spatial queries | PostGIS is optimal at city scale with millions of rows; Haversine avoids extension risks in MVP and satisfies bounding-box filters |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| WebSockets / Socket.io | Dropped connections on serverless cold starts and scale-to-zero | Client-driven HTTP polling with `since_seq` and exponential backoff |
| Celery / Background Workers | Requires Redis/RabbitMQ infrastructure, unsupported on stateless serverless | Lazy deterministic evaluation (`advance()`) triggered on incident reads/mutations |
| PostGIS Extensions | Heavy dependency requiring specialized database builds; unnecessary for MVP radiuses | SQL bounding-box prefilter + Haversine formula with detour factor |
| Direct `datetime.now()` | Breaks deterministic time testing and demo scenario clock advancement | Injectable `Clock` abstraction supporting session-specific offsets |
| In-memory rate limiters | Ineffective across multi-instance serverless functions | Database-derived rate limiting calculated from `audit_logs` |
| Client-side LLM calls | Exposes API keys and allows client-side tampering | Secure backend Tier 2 extractor with prompt-injection sanitization |

## Stack Patterns by Variant

**If running on Vercel Serverless (Target):**
- FastAPI exported via `api/index.py` using ASGI handler
- SQLAlchemy engine configured with `NullPool` against managed pooled PostgreSQL (Neon/Supabase)
- Static React frontend deployed to Vercel CDN rewriting `/api/*` to the serverless function

**If Vercel Serverless Spike Fails (Contingency):**
- Keep frontend on Vercel
- Deploy unchanged FastAPI backend container to Render / Railway / Fly
- Set `VITE_API_BASE_URL` and configure CORS headers and cookie `SameSite=None; Secure`

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Pydantic v2.10+ | FastAPI 0.115+ | Uses Rust core for sub-millisecond serialization; requires Pydantic v2 settings syntax |
| SQLAlchemy 2.0+ | Alembic 1.14+ | Requires explicit typed models and `Mapped[...]` syntax |
| React 19 | Leaflet 1.9+ | Ensure Leaflet container lifecycle is managed inside `useEffect` or dedicated wrapper |

## Sources

- `docs/LIFELINK_MASTER_SPEC.md` — Section 4 (System Architecture) & Section 15 (Deployment Architecture)
- FastAPI official documentation — Serverless ASGI patterns and dependency injection
- PostgreSQL documentation — Concurrency control, partial unique indexes, row-level locking

---
*Stack research for: Community First-Aid & Emergency Dispatcher (LIFELINK)*  
*Researched: 2026-09-30*
