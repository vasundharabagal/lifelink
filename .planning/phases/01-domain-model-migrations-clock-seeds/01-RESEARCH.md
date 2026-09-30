# Phase 1: Domain model, migrations, clock, seeds - Research

**Researched:** 2026-10-01  
**Domain:** Relational Database Architecture (PostgreSQL 16 / SQLAlchemy 2.0 / Alembic), Database-Enforced Safety Constraints & Append-Only Triggers, Multi-Tenant Virtual Clock Service, and Reproducible Persona Seeding  
**Confidence:** HIGH (Grounded in canonical `docs/LIFELINK_MASTER_SPEC.md` §5, §7, §12, §13, §18, and PostgreSQL 16 standard features)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-09 (Strict PostgreSQL testing):** All tests execute against real PostgreSQL (Docker container on port 5432 or Neon via `TEST_DATABASE_URL`) to guarantee 100% fidelity for partial unique indexes, row-level locks, and append-only PL/pgSQL triggers.
- **D-10 (Nested transaction rollback):** Alembic migrations run once per test session in `conftest.py`; each test executes inside `session.begin_nested()` and rolls back at teardown for sub-10ms test execution.
- **D-11 (Dedicated up/down migration test):** `test_migrations.py` exercises `alembic upgrade head` -> `downgrade base` -> `upgrade head` against PostgreSQL to guarantee reversible schema migrations.
- **D-12 (Direct DB constraint & trigger test module):** `test_constraints.py` directly tests that raw SQL and ORM `UPDATE`/`DELETE` queries on `emergency_events` and `audit_logs` raise PostgreSQL trigger exceptions, and duplicate concurrent active offers fail with `IntegrityError`.
- **D-13 (DB-backed virtual clock offsets):** `Clock.now(session_id, db=None)` resolves virtual offsets from `demo_sessions.clock_offset_s` when `session_id` is provided, guaranteeing multi-tenant virtual time synchronization across stateless Vercel lambdas (returns real UTC time when `session_id` is None).
- **D-14 (FastAPI dependency injection):** `Clock` is provided via `Depends(get_clock)` in FastAPI routes and injectable into domain services and pytest fixtures.
- **D-15 (Ban on direct `datetime.now()` via AST CI test):** `test_clock.py::test_no_direct_datetime_now` parses the Python AST across `domain/`, `services/`, and `api/` to fail CI if `datetime.now()` or `datetime.utcnow()` is invoked outside `core/clock.py`.
- **D-16 (Strict timezone-aware UTC datetimes):** `Clock` exclusively produces `datetime.now(timezone.utc)` and rejects naive datetimes, mapping cleanly to PostgreSQL `TIMESTAMPTZ` and ISO-8601 UTC strings.
- **D-17 (Dual-mode seed provisioning):** `backend/app/seed.py` provisions base archetype persona templates (`demo_session_id=None`) matching Appendix B AND a pre-cloned default session (`demo_session_id='00000000-0000-0000-0000-000000000001'`) for immediate local dev and test availability.
- **D-18 (Precomputed argon2id hash constant):** Demo accounts share a standard password (`LifelinkDemo2026!`) with a precomputed valid argon2id hash string constant in `seed.py` for instant, zero-delay seeding.
- **D-19 (Idempotent upserts by natural unique keys):** `seed.py` uses `ON CONFLICT` clauses on unique constraints (e.g. `email` for users, `user_id` for profiles, `(callsign, demo_session_id)` for ambulance units) to update or insert records safely without corrupting session data.
- **D-20 (Configurable center with fixed offsets):** Compute persona coordinates in `seed.py` dynamically relative to `(DEMO_CENTER_LAT, DEMO_CENTER_LNG)` in `config.py` using fixed distance and bearing offsets matching Appendix B exact distances (Asha 0.8km, Ravi 1.3km, Meera 2.1km, Karan 0.3km, Dr. Iyer 0.6km, Sana 4.5km, etc.).
- **D-21 (Canonical root `shared/taxonomy.json`):** Backend resolves it via filesystem path, and Vite directly imports it into the web frontend bundle for offline guidance.
- **D-22 (Strongly typed Python `StrEnum` with CI parity test):** Define explicit Python `StrEnum` classes in `backend/app/domain/enums.py` matching `taxonomy.json`, backed by an automated CI test verifying 100% bijective parity.
- **D-23 (Type-safe frontend TypeScript declarations):** Create `apps/web/src/types/taxonomy.ts` deriving strict literal union types directly from `taxonomy.json`.
- **D-24 (Complete 5-block taxonomy structure):** `shared/taxonomy.json` defines `emergency_types`, `conditions`, `skills` (with levels 1–3), `responder_categories`, and `protocol_skill_requirements` with strict JSON schema validation.

### the agent's Discretion
- Bearing offsets for demo persona placement around Pune center to achieve clear map separation.
- Migration script organization in `backend/alembic/`.
- Dependency additions to `backend/requirements.txt` (`alembic`, `argon2-cffi`).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed strictly within Phase 1 scope.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Domain Entities & Relations | Database / Models (`app/models/*.py`) | Storage / Alembic (`alembic/versions/*`) | Declares 11 canonical entities using SQLAlchemy 2.0 `Mapped` attributes and relationship definitions |
| Concurrency Guard (Offers) | Database Engine (PostgreSQL Indexes) | API / Service (`dispatch_offers`) | Partial unique indexes prevent multiple concurrent active offers per responder/track at the physical DB layer |
| Append-Only Immutability | Database Engine (PostgreSQL Triggers) | API / Service (`emergency_events`, `audit_logs`) | PL/pgSQL triggers reject any `UPDATE` or `DELETE` attempt even if application code is compromised |
| Virtual Time & Offset Sync | Core Services (`app/core/clock.py`) | Database / Session (`demo_sessions`) | Resolves virtual time per `demo_session_id` using persisted DB offsets across stateless Vercel lambdas |
| Direct Time Call Ban | Test / CI (`tests/test_clock.py`) | Development Tooling | AST scanner prevents non-deterministic `datetime.now()` calls from creeping into domain or service layers |
| Shared Medical Taxonomy | File Asset (`shared/taxonomy.json`) | Domain Enums (`app/domain/enums.py`, `apps/web/src/types`) | Single JSON definition guarantees backend rules and frontend offline protocol guidance remain strictly aligned |
| Idempotent Persona Seeding | CLI / Seeder (`app/seed.py`) | Storage (`PostgreSQL`) | Provisions deterministic Appendix B personas with natural key conflict resolution and dynamic coordinates |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 1 constructs the database backbone and determinism primitives upon which all subsequent LIFELINK emergency logic depends.

The core challenge is translating the canonical RFC-level safety invariants from `docs/LIFELINK_MASTER_SPEC.md` §5 & §7 into robust database structures that enforce security unconditionally:
1. **11 Relational Tables:** `users`, `responder_profiles`, `responder_skills`, `responder_credentials`, `ambulance_units`, `medical_profiles`, `emergencies`, `emergency_events`, `dispatch_offers`, `audit_logs`, `demo_sessions`.
2. **Partial Unique Indexes:** Crucial for preventing race conditions in serverless environments where two parallel requests might try to offer the same volunteer simultaneously. A partial unique index `UNIQUE (responder_id) WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED')` guarantees single-winner concurrency at the database level.
3. **Append-Only Triggers:** Security and clinical governance require that `emergency_events` and `audit_logs` are tamper-evident. PostgreSQL `BEFORE UPDATE OR DELETE` triggers raise an exception on any mutation attempt.
4. **Deterministic Multi-Tenant Clock:** Because Vercel serverless functions scale across ephemeral containers, an in-memory dictionary is insufficient for session time offsets. The `Clock` abstraction resolves offsets directly from `demo_sessions.clock_offset_s`. Furthermore, an AST verification test inspects all Python code to ensure `datetime.now()` is banned outside `core/clock.py`.
5. **Shared Taxonomy & Seeds:** `shared/taxonomy.json` serves as the monorepo root single source of truth for both Python `StrEnum` classes and React TypeScript types, while `app/seed.py` implements mathematical distance/bearing offsets from `DEMO_CENTER` to position Appendix B personas deterministically.

**Primary recommendation:** Author `shared/taxonomy.json` and TypeScript types; implement SQLAlchemy 2.0 models with partial indexes, check constraints, and triggers; generate and test Alembic migrations; implement `Clock` and AST ban tests; and write idempotent seed logic for Appendix B personas.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36+ | Declarative ORM & Table Schemas | Modern `Mapped[...]` syntax, type safety, custom DDL hooks, transactional nesting |
| Alembic | 1.14.0+ | Database Migrations | Industry-standard PostgreSQL schema migration runner with reversible revision tracking |
| psycopg2-binary | 2.9.10+ | PostgreSQL Driver | Battle-tested DBAPI driver compatible with PostgreSQL 16 and managed pooling proxies |
| Pydantic | 2.10.0+ | Contract validation | Strict parsing and validation for JSON payloads in models and Clock schemas |
| argon2-cffi | 23.1.0+ | Password verification & hashing | Memory-hard password hashing specified in Master Spec §7.1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.3.0+ | Test framework | Unit and integration test runner |
| pytest-asyncio | 0.24.0+ | Async test support | Testing async FastAPI and database operations |
| pytest-mock | 3.14.0+ | Mocking library | Mocking external boundaries during unit tests |

### Additions to `backend/requirements.txt`
```text
alembic>=1.14.0
argon2-cffi>=23.1.0
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### 1. Database Schema & Constraints Pattern

#### Table Structures (Spec §7.1)
- `users`: `id UUID PK`, `role VARCHAR(32)`, `email VARCHAR(255) UNIQUE`, `password_hash VARCHAR(255)`, `full_name VARCHAR(255)`, `phone VARCHAR(64) NULL`, `is_active BOOLEAN DEFAULT TRUE`, `demo_session_id UUID NULL`, `created_at TIMESTAMPTZ`.
- `responder_profiles`: `user_id UUID PK FK(users.id)`, `category VARCHAR(64)`, `readiness VARCHAR(32)`, `service_radius_m INTEGER`, `last_lat DOUBLE PRECISION NULL`, `last_lng DOUBLE PRECISION NULL`, `last_location_at TIMESTAMPTZ NULL`, `pinned_location BOOLEAN DEFAULT FALSE`, `acceptance_rate DOUBLE PRECISION DEFAULT 1.0`, `responses_24h INTEGER DEFAULT 0`, `cooldown_until TIMESTAMPTZ NULL`, `updated_at TIMESTAMPTZ`.
- `responder_skills`: `responder_id UUID FK(users.id)`, `skill_code VARCHAR(64)`, `level INTEGER CHECK (level BETWEEN 1 AND 3)`. PK `(responder_id, skill_code)`.
- `responder_credentials`: `id UUID PK`, `responder_id UUID FK(users.id)`, `credential_type VARCHAR(64)`, `issuer VARCHAR(255)`, `reference_no VARCHAR(128)`, `expires_on DATE`, `status VARCHAR(32)`, `reviewed_by UUID NULL FK(users.id)`, `reviewed_at TIMESTAMPTZ NULL`, `review_note TEXT NULL`, `created_at TIMESTAMPTZ`.
- `ambulance_units`: `id UUID PK`, `operator_user_id UUID FK(users.id)`, `callsign VARCHAR(64)`, `unit_type VARCHAR(32)`, `status VARCHAR(32)`, `lat DOUBLE PRECISION`, `lng DOUBLE PRECISION`, `base_name VARCHAR(255)`, `demo_session_id UUID NULL`.
- `medical_profiles`: `user_id UUID PK FK(users.id)`, `blood_group VARCHAR(8) NULL`, `allergies TEXT NULL`, `conditions TEXT NULL`, `medications TEXT NULL`, `contacts JSONB DEFAULT '[]'`, `share_during_emergency BOOLEAN DEFAULT FALSE`, `updated_at TIMESTAMPTZ`.
- `emergencies`: `id UUID PK`, `patient_user_id UUID FK(users.id)`, `reported_by_user_id UUID FK(users.id)`, `idempotency_key VARCHAR(128)`, `status VARCHAR(32)`, `community_track VARCHAR(32)`, `professional_track VARCHAR(32)`, `priority VARCHAR(16)`, `emergency_type VARCHAR(64)`, `triage JSONB`, `dispatch_plan JSONB DEFAULT '{}'`, `lat DOUBLE PRECISION`, `lng DOUBLE PRECISION`, `location_accuracy_m DOUBLE PRECISION DEFAULT 10.0`, `location_hint TEXT NULL`, `patient_is_reporter BOOLEAN DEFAULT TRUE`, `consent_share_medical BOOLEAN DEFAULT FALSE`, `version INTEGER DEFAULT 1`, `next_event_seq INTEGER DEFAULT 1`, `handover_snapshot JSONB NULL`, `close_reason VARCHAR(64) NULL`, `demo_session_id UUID NULL`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`, `closed_at TIMESTAMPTZ NULL`.
- `emergency_events`: `id UUID PK`, `emergency_id UUID FK(emergencies.id)`, `seq INTEGER`, `type VARCHAR(64)`, `actor_user_id UUID NULL FK(users.id)`, `actor_role VARCHAR(32)`, `payload JSONB DEFAULT '{}'`, `visible_to JSONB DEFAULT '[]'`, `at TIMESTAMPTZ`.
- `dispatch_offers`: `id UUID PK`, `emergency_id UUID FK(emergencies.id)`, `track VARCHAR(32)`, `target_kind VARCHAR(32)`, `responder_id UUID NULL FK(users.id)`, `ambulance_id UUID NULL FK(ambulance_units.id)`, `rank INTEGER`, `status VARCHAR(32)`, `offered_at TIMESTAMPTZ`, `expires_at TIMESTAMPTZ`, `responded_at TIMESTAMPTZ NULL`, `accepted_at TIMESTAMPTZ NULL`, `arrived_at TIMESTAMPTZ NULL`, `completed_at TIMESTAMPTZ NULL`, `decline_reason VARCHAR(64) NULL`, `eta_s INTEGER NULL`, `distance_m DOUBLE PRECISION NULL`, `score_snapshot JSONB NULL`, `sim_start_lat DOUBLE PRECISION NULL`, `sim_start_lng DOUBLE PRECISION NULL`, `sim_travel_s INTEGER NULL`, `actions_reported JSONB DEFAULT '[]'`, `notes TEXT NULL`.
- `audit_logs`: `id UUID PK`, `at TIMESTAMPTZ`, `actor_user_id UUID NULL FK(users.id)`, `actor_role VARCHAR(32)`, `action VARCHAR(64)`, `resource_type VARCHAR(64)`, `resource_id VARCHAR(128)`, `outcome VARCHAR(16)`, `ip_hash VARCHAR(128)`, `meta JSONB DEFAULT '{}'`.
- `demo_sessions`: `id UUID PK`, `created_at TIMESTAMPTZ`, `expires_at TIMESTAMPTZ`, `clock_offset_s INTEGER DEFAULT 0`, `scenario JSONB DEFAULT '{}'`, `is_active BOOLEAN DEFAULT TRUE`.

#### PostgreSQL Partial Unique Indexes (Spec §7.2)
```sql
CREATE UNIQUE INDEX uq_offers_active_responder 
ON dispatch_offers(responder_id) 
WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');

CREATE UNIQUE INDEX uq_offers_active_ambulance 
ON dispatch_offers(ambulance_id) 
WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');

CREATE UNIQUE INDEX uq_offers_active_track 
ON dispatch_offers(emergency_id, track) 
WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');

CREATE UNIQUE INDEX uq_emergencies_active_patient 
ON emergencies(patient_user_id) 
WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'NO_COVERAGE_CLOSED');

CREATE UNIQUE INDEX uq_emergencies_reporter_idempotency 
ON emergencies(reported_by_user_id, idempotency_key);

CREATE UNIQUE INDEX uq_events_emergency_seq 
ON emergency_events(emergency_id, seq);
```

#### Append-Only Trigger Functions
```sql
CREATE OR REPLACE FUNCTION prevent_append_only_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only: UPDATE and DELETE operations are forbidden.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_emergency_events_append_only
BEFORE UPDATE OR DELETE ON emergency_events
FOR EACH ROW EXECUTE FUNCTION prevent_append_only_mutation();

CREATE TRIGGER trg_audit_logs_append_only
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_append_only_mutation();
```

### 2. Multi-Tenant Clock Pattern
```python
# backend/app/core/clock.py
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.demo import DemoSession

class Clock:
    def now(self, demo_session_id: Optional[UUID] = None, db: Optional[Session] = None) -> datetime:
        base_now = datetime.now(timezone.utc)
        if not demo_session_id or not db:
            return base_now
        
        session = db.query(DemoSession).filter(DemoSession.id == demo_session_id).first()
        if session and session.clock_offset_s:
            return base_now + timedelta(seconds=session.clock_offset_s)
        return base_now

    def advance(self, demo_session_id: UUID, seconds: int, db: Session) -> datetime:
        session = db.query(DemoSession).filter(DemoSession.id == demo_session_id).first()
        if not session:
            raise ValueError(f"Demo session {demo_session_id} not found")
        session.clock_offset_s += seconds
        db.commit()
        return self.now(demo_session_id, db)
```

### 3. Dynamic Persona Bearing Placement
To achieve exact straight-line Haversine distances from `DEMO_CENTER`:
```python
import math

def calculate_offset_coordinates(center_lat: float, center_lng: float, distance_km: float, bearing_deg: float) -> tuple[float, float]:
    """Calculate target coordinates given a center point, distance in km, and bearing in degrees."""
    R = 6371.0 # Earth radius in km
    bearing_rad = math.radians(bearing_deg)
    lat1_rad = math.radians(center_lat)
    lng1_rad = math.radians(center_lng)

    lat2_rad = math.asin(
        math.sin(lat1_rad) * math.cos(distance_km / R) +
        math.cos(lat1_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
    )
    lng2_rad = lng1_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat1_rad),
        math.cos(distance_km / R) - math.sin(lat1_rad) * math.sin(lat2_rad)
    )
    return math.degrees(lat2_rad), math.degrees(lng2_rad)
```
</architecture_patterns>

<validation_architecture>
## Validation Architecture

### Automated Verification Plan
1. **Taxonomy Schema & Parity Test (`pytest backend/tests/test_taxonomy.py`):**
   - Asserts `shared/taxonomy.json` conforms to JSON schema.
   - Asserts Python `StrEnum` classes in `app/domain/enums.py` match `shared/taxonomy.json` bijectively (100% value parity).
2. **Alembic Reversibility Test (`pytest backend/tests/test_migrations.py`):**
   - Runs `alembic upgrade head`.
   - Runs `alembic downgrade base`.
   - Runs `alembic upgrade head` to confirm clean idempotency on PostgreSQL.
3. **Database Constraints & Triggers Test (`pytest backend/tests/test_constraints.py`):**
   - Asserts that inserting two active offers for the same responder fails with `IntegrityError`.
   - Asserts that inserting two active offers for the same track fails with `IntegrityError`.
   - Asserts that inserting two active emergencies for the same patient fails with `IntegrityError`.
   - Asserts that raw SQL `UPDATE emergency_events` or `DELETE emergency_events` raises PostgreSQL trigger exception.
   - Asserts that raw SQL `UPDATE audit_logs` or `DELETE audit_logs` raises PostgreSQL trigger exception.
   - Asserts that `dispatch_offers` CHECK constraint rejects rows with both or neither responder_id and ambulance_id.
4. **Clock Virtual Offsets & AST Ban Test (`pytest backend/tests/test_clock.py`):**
   - Asserts `Clock.now(session_id, db)` respects `clock_offset_s`.
   - Asserts `Clock.advance()` updates offset correctly.
   - Asserts AST across `backend/app/domain`, `backend/app/services`, and `backend/app/api` contains ZERO direct calls to `datetime.now()` or `datetime.utcnow()`.
5. **Idempotent Persona Seeding Test (`pytest backend/tests/test_seed.py`):**
   - Runs `app.seed.seed_all()`.
   - Asserts all 10 Appendix B personas and 3 ambulance units exist with correct credentials, skills, and coordinates.
   - Runs `app.seed.seed_all()` a second time and asserts zero duplicate records or errors.
6. **Frontend TypeScript Compilation (`npm --prefix apps/web run build`):**
   - Verifies `apps/web/src/types/taxonomy.ts` compiles cleanly with Vite and TS 5.x.

### Manual-Only Verification
- Inspection of generated PostgreSQL tables via `psql` or `docker compose exec postgres psql -U lifelink_user -d lifelink_db -c '\d'`.
</validation_architecture>

<pitfalls>
## Critical Pitfalls to Avoid

1. **Alembic Migration in Serverless Cold Start:**
   - *Problem:* Running `alembic upgrade head` inside FastAPI startup event (`@app.on_event("startup")` or lifespan) slows down serverless cold starts by several seconds and risks migration locking deadlocks across parallel serverless containers.
   - *Prevention:* Migrations run exclusively via CLI (`alembic upgrade head` in CI/deploy script or local docker setup), never on application startup.
2. **PostgreSQL Triggers vs SQLite:**
   - *Problem:* Trying to run trigger tests against SQLite fails because PL/pgSQL syntax is PostgreSQL-specific.
   - *Prevention:* Per D-09, strictly run tests against real PostgreSQL (`TEST_DATABASE_URL` pointing to local Docker container).
3. **Naive Datetime Comparison Bugs:**
   - *Problem:* Comparing `datetime.utcnow()` (naive in older Python) with `Clock.now()` (aware) causes `TypeError: can't compare offset-naive and offset-aware datetimes`.
   - *Prevention:* Strictly use `datetime.now(timezone.utc)` everywhere in `core/clock.py`, and enforce `TIMESTAMPTZ` in SQLAlchemy models.
4. **Argon2id Hashing Overhead in Test Setup:**
   - *Problem:* Computing argon2id hashes on the fly for 15 users in every test fixture adds 2-3 seconds per test run.
   - *Prevention:* Hardcode a precomputed valid argon2 hash constant for `LifelinkDemo2026!` in `seed.py`.
5. **Frontend/Backend Taxonomy Drift:**
   - *Problem:* Hardcoding skill names in React and separate skill names in Python causes dispatch mismatch bugs in later phases.
   - *Prevention:* Monorepo root `shared/taxonomy.json` is the sole source of truth; tests enforce parity.
</pitfalls>

<sources>
## Sources

### Primary
- `docs/LIFELINK_MASTER_SPEC.md` — Section 5 (Data Architecture), Section 7 (Database Design), Section 12 (Determinism & Clock), Section 18 (Phase 1 Checklist), Appendix B (Demo Cast)
- SQLAlchemy Documentation — Declarative Mapping, Constraints, and Custom DDL Execution
- PostgreSQL 16 Documentation — Trigger Procedures (`plpgsql`) and Partial Indexes
- Alembic Documentation — Reversible Migrations & Operations

### Secondary
- RFC 2119 — Requirement Levels
</sources>

---
*Phase: 01-domain-model-migrations-clock-seeds*  
*Research completed: 2026-10-01*  
*Ready for planning: yes*
