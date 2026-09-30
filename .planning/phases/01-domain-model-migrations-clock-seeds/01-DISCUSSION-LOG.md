# Phase 1: Domain model, migrations, clock, seeds - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01  
**Phase:** 1-Domain model, migrations, clock, seeds  
**Areas discussed:** Test Database Strategy, Clock Service Architecture, Demo Seed Provisioning, Monorepo Shared Taxonomy Structure  

---

## Test Database Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Strict PostgreSQL | Run all tests against real PostgreSQL (Docker/Neon via TEST_DATABASE_URL) so partial unique indexes, row-level locks, and append-only triggers are 100% verified | ✓ |
| Dual-engine fallback | Allow SQLite in-memory for pure unit tests (skipping PG-specific triggers/indexes) and require PostgreSQL only for migration and constraint tests | |

**User's choice:** Strict PostgreSQL  
**Notes:** Ensures safety-critical DB features (append-only triggers, partial unique indexes) are always exercised.

| Option | Description | Selected |
|--------|-------------|----------|
| Nested transaction rollback | Run Alembic migrations once per test session, wrap each test in a transaction and roll back at teardown (sub-10ms per test) | ✓ |
| Database truncation | Run migrations once, commit transactions normally in tests, and truncate all 11 tables between tests | |
| Dynamic ephemeral database | Create and drop a unique PostgreSQL test database for each pytest session | |

**User's choice:** Nested transaction rollback  
**Notes:** Provides fast test execution without losing schema consistency.

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated up/down migration test | An explicit test (`test_migrations.py`) that exercises `alembic upgrade head` -> `downgrade base` -> `upgrade head` against PostgreSQL to guarantee reversibility | ✓ |
| Session-setup only | Run `alembic upgrade head` inside pytest `conftest.py` fixture without testing downgrade reversibility | |

**User's choice:** Dedicated up/down migration test  
**Notes:** Guarantees database migration rollbacks are tested in CI.

| Option | Description | Selected |
|--------|-------------|----------|
| Direct DB constraint & trigger test module | Explicitly test that raw SQL and ORM `UPDATE` and `DELETE` on `emergency_events` and `audit_logs` raise PostgreSQL trigger exceptions, and duplicate active offers fail with `IntegrityError` | ✓ |
| Service-level assertions only | Test that service methods do not issue updates, without testing raw DB trigger rejection | |

**User's choice:** Direct DB constraint & trigger test module  
**Notes:** Directly validates database-level security invariants.

---

## Clock Service Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| DB-backed with session lookup | `Clock.now(session_id, db=None)` uses `demo_sessions.clock_offset_s` when session_id is provided, guaranteeing exact synchronization across stateless Vercel lambdas | ✓ |
| Dual-mode Clock | In-memory offset dictionary for unit tests/local dev, and DB `demo_sessions.clock_offset_s` lookup in production serverless runtime | |

**User's choice:** DB-backed with session lookup  
**Notes:** Ensures stateless serverless instances remain synchronized.

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI dependency injection `Depends(get_clock)` | Injectable `Clock` protocol/class that services and endpoints consume via FastAPI DI and pytest fixtures | ✓ |
| Global module singleton `core.clock` | Global helper functions `get_virtual_now(db, session_id)` directly imported across services and routes | |

**User's choice:** FastAPI dependency injection `Depends(get_clock)`  
**Notes:** Clean dependency injection without global mutable state.

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated AST test in pytest + static check | A test `test_no_direct_datetime_now` that parses AST of all domain/service files to fail CI if `datetime.now()` or `datetime.utcnow()` is called outside `core/clock.py` | ✓ |
| Ruff / Flake8 lint configuration only | Ban `datetime.now` via linter rules in repo configuration | |

**User's choice:** Dedicated AST test in pytest + static check  
**Notes:** Automatically blocks direct time calls in CI.

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit UTC timezone-aware datetimes | `Clock.now()` returns `datetime.now(timezone.utc)` and rejects naive datetimes, mapping cleanly to PostgreSQL `TIMESTAMPTZ` and ISO-8601 UTC strings | ✓ |
| Epoch integer seconds | `Clock.now()` returns float/integer epoch seconds, converting to datetimes only at database write boundary | |

**User's choice:** Explicit UTC timezone-aware datetimes  
**Notes:** Avoids any naive vs aware datetime mismatch bugs.

---

## Demo Seed Provisioning

| Option | Description | Selected |
|--------|-------------|----------|
| Dual provisioning | Seed base archetype templates (`demo_session_id=None`) AND a pre-cloned default session (`00000000-0000-0000-0000-000000000001`) so developers and tests have immediate working data | ✓ |
| Archetype templates only | Seed only the template cast with `demo_session_id=None`; any execution must call `POST /demo/sessions` or the cloning service to instantiate a session | |

**User's choice:** Dual provisioning  
**Notes:** Immediate usability out of the box for developers and integration tests.

| Option | Description | Selected |
|--------|-------------|----------|
| Precomputed argon2id hash constant | Use a fixed standard password (e.g., `LifelinkDemo2026!`) with a precomputed valid argon2id hash string in `seed.py` for instant, zero-delay seeding | ✓ |
| Dynamic argon2id hashing | Compute fresh argon2id hashes for every demo user dynamically during `seed.py` execution (adds ~1-2s per seed) | |

**User's choice:** Precomputed argon2id hash constant  
**Notes:** Instant zero-overhead seeding for demo personas.

| Option | Description | Selected |
|--------|-------------|----------|
| Upsert by natural unique keys | Use `ON CONFLICT (email)` / unique constraints to update or insert records idempotently, making repeated `python -m app.seed` safe and non-destructive | ✓ |
| Scoped purge & re-seed | Delete rows where `demo_session_id IS NULL OR demo_session_id = '00000000-0000-0000-0000-000000000001'` and re-insert cleanly in a single transaction | |
| Skip if present | Check if seed users exist; if found, exit with 'already seeded' without modifying existing rows | |

**User's choice:** Upsert by natural unique keys  
**Notes:** Fully idempotent without deleting session modifications.

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable center with fixed offsets | Compute persona lat/lng dynamically from `(DEMO_CENTER_LAT, DEMO_CENTER_LNG)` in `config.py` using fixed distance/bearing offsets, matching Appendix B distances exactly | ✓ |
| Fixed hardcoded Pune coordinates | Hardcode exact Pune coordinates in `seed.py` matching Appendix B distances directly | |

**User's choice:** Configurable center with fixed offsets  
**Notes:** Adapts to demo venue while preserving exact distances in Appendix B.

---

## Monorepo Shared Taxonomy Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical root `shared/taxonomy.json` | Maintain `shared/taxonomy.json` at monorepo root; backend loads it via resolved Path, Vite imports it directly into the frontend bundle | ✓ |
| Backend-first with build sync | Store taxonomy inside `backend/app/shared/taxonomy.json` and copy to `apps/web/src/shared/` during build | |

**User's choice:** Canonical root `shared/taxonomy.json`  
**Notes:** Single source of truth across Python backend and React frontend.

| Option | Description | Selected |
|--------|-------------|----------|
| Strongly typed `StrEnum` with CI parity test | Define explicit Python `StrEnum` classes for IDE autocompletion and static type checking, backed by a test verifying exact parity with `shared/taxonomy.json` | ✓ |
| Dynamic runtime enum generation | Generate enums dynamically on backend startup from `shared/taxonomy.json` (less static type safety) | |

**User's choice:** Strongly typed `StrEnum` with CI parity test  
**Notes:** Maximizes IDE support while guaranteeing parity.

| Option | Description | Selected |
|--------|-------------|----------|
| Type-safe TS declarations | Create TypeScript types in `apps/web/src/types/taxonomy.ts` deriving strict literal types directly from `taxonomy.json` (e.g., `type SkillCode = typeof taxonomy.skills[number]["code"]`) | ✓ |
| Defer frontend types to Phase 6 | Limit Phase 1 strictly to backend domain models and `shared/taxonomy.json`, wiring frontend TypeScript bindings in Phase 6 | |

**User's choice:** Type-safe TS declarations  
**Notes:** Ensures early end-to-end type safety.

| Option | Description | Selected |
|--------|-------------|----------|
| Complete 5-block taxonomy | Author emergency_types, conditions, skills (with levels 1-3), responder_categories, and protocol_skill_requirements in `shared/taxonomy.json` with strict JSON schema validation | ✓ |
| Minimal skills/types only | Author only skills and emergency types in Phase 1, leaving protocol requirement mappings to Phase 3 | |

**User's choice:** Complete 5-block taxonomy  
**Notes:** Gives a comprehensive, robust taxonomy foundation upfront.

---

## the agent's Discretion

- Persona bearing angles around center point (`18.5204, 73.8567`) to ensure visually distinct spatial layout.
- Alembic configuration structure (`backend/alembic.ini`, `backend/alembic/env.py`).
- Addition of `alembic` and `argon2-cffi` to `backend/requirements.txt`.

## Deferred Ideas

None — discussion stayed strictly within Phase 1 scope.
