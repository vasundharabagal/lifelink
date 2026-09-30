<!-- GSD:project-start source:PROJECT.md -->

## Project

**LIFELINK**

LIFELINK is an explainable, safety-gated community-first emergency coordination layer for the "golden minutes" — the critical gap between when an emergency occurs and when professional emergency services arrive. It operates beside national emergency services (default `112`, configurable) without replacing them, turning verified nearby citizens into an accountable, rapid first-response network while simultaneously dispatching professional ambulance services.

**Core Value:** The explainable, safety-gated coordination layer that runs beside official emergency services and turns verified nearby people into an accountable first-response network, delivering immediate community first-aid guidance and deterministic dual-track response within strict safety boundaries.

### Constraints

- **Safety Architecture**: "Call 112" non-network control must exist on every citizen emergency screen; UI never guarantees help arrival ("we are contacting nearby responders", ETAs labelled "estimated")
- **AI Safety**: AI only extracts structured signals; deterministic rules decide priority and skills; AI may escalate, never de-escalate
- **Verification Gate**: Unverified, expired, rejected, or suspended responders must never receive offers or incident data (enforced in eligibility logic and DB transaction guard)
- **Privacy**: Coarse location (~250 m) before accept; exact location only for accepted target; immediate revocation upon incident termination; medical data shared only with explicit consent
- **Deployment Platform**: Stateless serverless execution requires client-driven HTTP polling, lazy deadline advancement under row lock, and minimal cold-start footprint
- **Auditability**: Every state change, authorization failure, and sensitive data read must write to append-only logs (`emergency_events` and `audit_logs`)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

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

# Frontend (apps/web)

# Backend (backend/requirements.txt)

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

- FastAPI exported via `api/index.py` using ASGI handler
- SQLAlchemy engine configured with `NullPool` against managed pooled PostgreSQL (Neon/Supabase)
- Static React frontend deployed to Vercel CDN rewriting `/api/*` to the serverless function
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

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agent/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
