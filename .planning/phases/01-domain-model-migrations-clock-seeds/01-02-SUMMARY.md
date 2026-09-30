# Phase 1: Plan 01-02 Summary

**Delivery:** SQLAlchemy 2.0 Domain Models, Alembic Migrations, Check Constraints, Partial Unique Indexes, and Append-Only PostgreSQL Triggers
**Date:** 2026-10-01
**Status:** Completed

---

## 1. Key Accomplishments

- **Installed and Pinned Dependencies (`backend/requirements.txt`):**
  - Added `alembic>=1.14.0` and `argon2-cffi>=23.1.0`.
- **SQLAlchemy 2.0 Type-Annotated Domain Models (`backend/app/models/`):**
  - `Base`: Common declarative base with automatic snake_case table resolution.
  - `User`: Accounts across citizen, responder, operator, authority; argon2 password hashes.
  - `MedicalProfile`: Confidential health and emergency contact data linked 1:1 to User.
  - `ResponderProfile`: Volunteer responder metadata, category, service radius, and last known coordinates.
  - `ResponderSkill`: Granular certifications (levels 1-3) with check constraint `ck_responder_skills_level`.
  - `ResponderCredential`: Verification lifecycle (pending, verified, rejected, expired, suspended) with authority reviewer foreign key.
  - `AmbulanceUnit`: Professional vehicles, callsigns, operational statuses, and base locations.
  - `Emergency`: Dual-track incident coordination record with clinical triage, dispatch plan, status lifecycle, and coordinate bounds.
  - `DispatchOffer`: Polymorphic offers with mutual exclusivity check constraint `ck_offer_target_kind`, expiry timestamps, and response telemetry.
  - `EmergencyEvent`: Append-only incident audit log with sequence ordering.
  - `AuditLog`: Security audit trail capturing authenticated actor, resource mutation, outcome, and client IP hash.
  - `DemoSession`: Isolated multi-tenant sandbox partitions with custom clock offsets and scenario state.
- **Alembic Initial Migration (`backend/alembic/versions/001_initial_schema.py`):**
  - Complete DDL for all 11 tables.
  - Partial unique indexes enforcing single-winner concurrency and deduplication:
    - `uq_offers_active_responder`: `(responder_id) WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED')`
    - `uq_offers_active_ambulance`: `(ambulance_id) WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED')`
    - `uq_offers_active_track`: `(emergency_id, track) WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED')`
    - `uq_emergencies_active_patient`: `(patient_user_id) WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'NO_COVERAGE_CLOSED')`
    - `uq_emergencies_reporter_idempotency`: `(reported_by_user_id, idempotency_key)`
    - `uq_events_emergency_seq`: `(emergency_id, seq)`
    - `uq_ambulance_callsign_session`: `(callsign, demo_session_id)`
  - PL/pgSQL append-only trigger function `prevent_append_only_mutation()` attached as `BEFORE UPDATE OR DELETE` on `emergency_events` and `audit_logs`.
- **Test Suite (`backend/tests/`):**
  - `conftest.py`: Isolated nested transaction savepoints (`session.begin_nested()`, D-10).
  - `test_migrations.py`: Verified downgrade to base and upgrade back to head roundtrip.
  - `test_models.py`: Verified persistence, foreign key relationships, and cascade behaviors across models.
  - `test_constraints.py`: Verified all 4 partial unique indexes, check constraints, and both trigger UPDATE/DELETE rejections.

---

## 2. Verification Results

- `pytest tests/test_migrations.py -v`: PASSED (1/1)
- `pytest tests/test_models.py -v`: PASSED (3/3)
- `pytest tests/test_constraints.py -v`: PASSED (9/9)
- Full pytest suite: 26 passed in 1.06s.
- Frontend build (`npm --prefix apps/web run build`): Clean, zero regressions.

---

## 3. Next Steps

- Execute Plan 01-03:
  - Injectable `Clock` abstraction in `backend/app/core/clock.py` resolving virtual offsets from `demo_sessions`.
  - CI AST test `test_no_direct_datetime_now` banning unmediated `datetime.now()` calls across domain/api layers.
  - Seed script `backend/app/seed.py` loading `shared/taxonomy.json` and Appendix B personas with dynamic distance/bearing calculations.
