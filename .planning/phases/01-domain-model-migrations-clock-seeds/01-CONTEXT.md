# Phase 1: Domain model, migrations, clock, seeds - Context

**Gathered:** 2026-10-01  
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 establishes the relational data foundation, database-enforced safety invariants, deterministic virtual clock, and persona seeds for LIFELINK. It delivers the canonical 11 database tables in PostgreSQL matching spec Section 7 via Alembic migrations, database-level integrity constraints (partial unique indexes for single-winner concurrency, append-only triggers for `emergency_events` and `audit_logs`), the multi-tenant injectable `Clock` service supporting session-scoped virtual time offsets across stateless serverless instances, and idempotent seed provisioning for `shared/taxonomy.json` and Appendix B personas.

In Scope:
- Authoring canonical `shared/taxonomy.json` (emergency types, conditions, skills 1-3, responder categories, protocol skill mappings) and TypeScript types in `apps/web/src/types/taxonomy.ts`.
- Defining SQLAlchemy 2.0 models for all 11 tables (`users`, `responder_profiles`, `responder_skills`, `responder_credentials`, `ambulance_units`, `medical_profiles`, `emergencies`, `emergency_events`, `dispatch_offers`, `audit_logs`, `demo_sessions`).
- Implementing PostgreSQL-level check constraints, partial unique indexes (one active offer per responder, one active offer per track, one active emergency per patient), and append-only trigger functions rejecting `UPDATE` and `DELETE` on `emergency_events` and `audit_logs`.
- Setting up Alembic migrations for PostgreSQL with migration up/down reversibility tests (`test_migrations.py`).
- Implementing injectable `Clock` service (`backend/app/core/clock.py`) with `demo_sessions.clock_offset_s` resolution, FastAPI dependency `get_clock`, and AST CI test banning direct `datetime.now()` in domain/services.
- Implementing `backend/app/seed.py` idempotently provisioning base persona templates (`demo_session_id=None`) and a default working session (`demo_session_id='00000000-0000-0000-0000-000000000001'`) with precomputed argon2id hash constants and dynamic geographic offsets from `(DEMO_CENTER_LAT, DEMO_CENTER_LNG)`.

Out of Scope:
- User registration/login endpoints, JWT cookie generation, and RBAC middleware (Phase 2).
- Triage rules engine, clinical protocol guidance JSONs, and LLM adapter (Phase 3).
- Orchestration eligibility filter and scoring algorithms (Phase 4).
- Emergency lifecycle state transitions and offer dispatch endpoints (Phase 5).
- Web UI screens or Leaflet map components (Phases 6–8).
</domain>

<decisions>
## Implementation Decisions

### Test Database Strategy
- **D-09:** Strict PostgreSQL testing: All tests execute against real PostgreSQL (local Docker container on port 5432 or Neon via `TEST_DATABASE_URL`) to guarantee 100% fidelity for partial unique indexes (`UNIQUE (responder_id) WHERE status IN ('OFFERED','ACCEPTED','ARRIVED')`), PostgreSQL `FOR UPDATE` row locks, and PL/pgSQL append-only triggers.
- **D-10:** Fast test isolation via nested transaction rollbacks: Alembic migrations run once per test session in `conftest.py`, and each individual test runs within a nested transaction rolled back at teardown (`session.begin_nested()`), delivering sub-10ms test execution without dropping/recreating tables.
- **D-11:** Dedicated migration reversibility test (`tests/test_migrations.py`): Explicit test exercising `alembic upgrade head` -> `alembic downgrade base` -> `alembic upgrade head` against PostgreSQL to verify clean up/down migration paths.
- **D-12:** Direct DB constraint & trigger test module (`tests/test_constraints.py`): Explicit test verifying that raw SQL and ORM `UPDATE` and `DELETE` statements on `emergency_events` and `audit_logs` raise PostgreSQL trigger exceptions, and duplicate concurrent active offers fail with `IntegrityError`.

### Clock Service Architecture
- **D-13:** DB-backed virtual clock offsets: `Clock.now(session_id, db=None)` resolves the virtual offset from `demo_sessions.clock_offset_s` when `session_id` is supplied, ensuring consistent virtual time synchronization across stateless Vercel lambdas. When `session_id` is `None`, real UTC time is returned.
- **D-14:** Injectable FastAPI dependency: `Clock` is provided via `Depends(get_clock)` in FastAPI routes and consumed as an injectable service in domain functions and test fixtures.
- **D-15:** Ban on direct `datetime.now()` enforced via AST CI test: A dedicated test `tests/test_clock.py::test_no_direct_datetime_now` inspects the Python AST across `domain/`, `services/`, and `api/` to fail CI if `datetime.now()` or `datetime.utcnow()` is invoked outside `core/clock.py`.
- **D-16:** Strict timezone-aware UTC datetimes: `Clock` exclusively produces timezone-aware `datetime.now(timezone.utc)` datetimes and rejects naive datetimes, mapping cleanly to PostgreSQL `TIMESTAMPTZ` and ISO-8601 UTC strings.

### Demo Seed Provisioning
- **D-17:** Dual-mode seed provisioning: `backend/app/seed.py` provisions both the base persona archetype templates (`demo_session_id=None`) matching Appendix B AND an instantiated default working session (`demo_session_id='00000000-0000-0000-0000-000000000001'`), enabling immediate local dev and automated test execution.
- **D-18:** Precomputed argon2id hash constant: Demo users share a standard password (`LifelinkDemo2026!`) with a precomputed valid argon2id hash string constant in `seed.py`, eliminating compute overhead and providing instant, zero-delay seeding.
- **D-19:** Idempotent upserts by natural unique keys: `seed.py` uses `ON CONFLICT` clauses on unique constraints (e.g. `email` for users, `user_id` for profiles, `(callsign, demo_session_id)` for ambulance units) to update or insert records safely without corrupting existing data.
- **D-20:** Configurable center with fixed offsets: Dynamic calculation of Appendix B persona lat/lng relative to `(settings.DEMO_CENTER_LAT, settings.DEMO_CENTER_LNG)` using fixed bearing/distance offsets matching Appendix B exact distances (Asha 0.8km, Ravi 1.3km, Meera 2.1km, Karan 0.3km, Dr. Iyer 0.6km, Sana 4.5km, Vik 1.0km, Nita 0.9km, Omar 0.7km, Amb-1 2.4km, Amb-2 3.9km, Amb-3 1.1km).

### Monorepo Shared Taxonomy Structure
- **D-21:** Canonical single source of truth at monorepo root `shared/taxonomy.json`: Backend resolves the file path from monorepo root, and Vite directly imports it into the web frontend bundle for offline guidance.
- **D-22:** Strongly typed Python `StrEnum` classes with CI parity test: Define explicit Python `StrEnum` classes in `backend/app/domain/enums.py` matching `taxonomy.json`, backed by an automated CI test `tests/test_taxonomy.py` asserting exact bijective parity between Python enums and the JSON file.
- **D-23:** Type-safe frontend TypeScript declarations: Create `apps/web/src/types/taxonomy.ts` deriving strict literal union types directly from `taxonomy.json` (`typeof taxonomy.skills[number]["code"]`).
- **D-24:** Complete declarative 5-block taxonomy structure: `shared/taxonomy.json` defines `emergency_types`, `conditions`, `skills` (levels 1-3), `responder_categories`, and `protocol_skill_requirements` with strict JSON schema validation.

### the agent's Discretion
- Selection of specific bearing angles for persona placement around Pune center to provide clear spatial separation on the Leaflet map.
- Organization and naming of Alembic migration scripts and helper functions in `backend/alembic/`.
- Addition of `alembic` and `argon2-cffi` to `backend/requirements.txt`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Master Architecture & Data Specifications
- `docs/LIFELINK_MASTER_SPEC.md` §5 — Data Architecture & Database Constraints
- `docs/LIFELINK_MASTER_SPEC.md` §7 — Database Design (11 tables, constraints, triggers, indexes)
- `docs/LIFELINK_MASTER_SPEC.md` §12 — Emergency State Machine & Timeline Event Types
- `docs/LIFELINK_MASTER_SPEC.md` §13 — Demo Mode Architecture & Session Scoping
- `docs/LIFELINK_MASTER_SPEC.md` §18 — Phase 1 Checklist & Acceptance Criteria
- `docs/LIFELINK_MASTER_SPEC.md` Appendix B — Seeded Demo Cast & Facilities

### Prior Architectural Decisions
- `docs/ADR-001-deployment.md` — Accepted deployment architecture & pooling strategy (D-01, D-02)
- `.planning/phases/00-walking-skeleton-and-deployment-spike/00-CONTEXT.md` — Phase 0 decisions on monorepo structure and connection pooling
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/core/db.py`: SQLAlchemy session engine configured with `NullPool` (serverless) and `QueuePool` (local Docker), with `get_db` generator.
- `backend/app/core/config.py`: Pydantic settings loading `DATABASE_URL`, `APP_ENV`, etc.
- `docker-compose.yml`: PostgreSQL 16 container running on port 5432 with health check.
- `apps/web/`: Vite + React 19 + TypeScript frontend with Tailwind CSS.

### Established Patterns
- All backend routes live under `/api/v1/*`.
- Serverless Vercel compatibility: zero persistent in-memory global state across lambdas.
- Database access through SQLAlchemy 2.0 `select()` and `Mapped[...]` syntax.

### Integration Points
- `backend/app/models/`: New SQLAlchemy models for the 11 tables, inheriting from a shared declarative base.
- `backend/app/core/clock.py`: New clock service module exposing `Clock` and `get_clock`.
- `backend/alembic/`: Alembic configuration and versions folder for migration management.
- `backend/app/seed.py`: Standalone seed CLI script executable via `python -m app.seed`.
- `shared/taxonomy.json`: Root taxonomy file consumed by backend models/enums and frontend types.
</code_context>

<specifics>
## Specific Ideas

- Persona placement around the Pune center (`18.5204, 73.8567`): Distribute Asha (0.8km Northeast), Ravi (1.3km East), Meera (2.1km Southeast), Karan (0.3km North), Dr. Iyer (0.6km West), Sana (4.5km Southwest), Vik (1.0km Northwest), Nita (0.9km South), Omar (0.7km Southwest), Amb-1 (2.4km Northwest), Amb-2 (3.9km Northeast), Amb-3 (1.1km South). This creates clear directional separation on the Leaflet map.
- Precomputed argon2id hash for demo accounts: generated once with standard parameters (`m=65536, t=3, p=4`) for `LifelinkDemo2026!` and hardcoded as a constant string in `seed.py`.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed strictly within Phase 1 scope.
</deferred>

---

*Phase: 1-Domain model, migrations, clock, seeds*  
*Context gathered: 2026-10-01*
