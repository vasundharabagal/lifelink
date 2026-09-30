# Phase 1: Plan 01-03 Summary

**Delivery:** Injectable Clock Service, Virtual Session Offset Management, Direct Datetime AST Ban Scanner, and Idempotent Appendix B Persona Seeding
**Date:** 2026-10-01
**Status:** Completed

---

## 1. Key Accomplishments

- **Injectable Deterministic Clock Service (`backend/app/core/clock.py`):**
  - Implemented `Clock` abstraction supporting real-time UTC operations and virtual offset time travel per `demo_session_id`.
  - Added `now(demo_session_id, db)` resolving offsets from `demo_sessions.clock_offset_s` (DATA-04, D-13, D-16).
  - Added atomic `advance(demo_session_id, seconds, db)` and `reset(demo_session_id, db)` utilizing `with_for_update()` row locking.
  - Exported `get_clock` FastAPI dependency and refactored `/api/v1/health` to consume the injected clock.
- **CI AST Datetime Ban Scanner (`backend/tests/test_clock.py`):**
  - Implemented `test_no_direct_datetime_now` using Python's `ast` parser.
  - Recursively inspects all `.py` files across `app/domain/`, `app/services/`, and `app/api/`.
  - Strictly bans direct calls to `datetime.now()` and `datetime.utcnow()`, ensuring all runtime time reads remain deterministic and demo-friendly (DATA-04, D-15).
- **Idempotent Persona & Taxonomy Seeding (`backend/app/seed.py`):**
  - Precomputed argon2id hash constant `DEFAULT_DEMO_PASSWORD_HASH` for instant zero-overhead execution (`LifelinkDemo2026!`, D-18, T-01-05).
  - Geodesic coordinate calculation `calculate_offset_coordinates` generating exact Haversine target distances and bearings from `(DEMO_CENTER_LAT, DEMO_CENTER_LNG)` (D-20).
  - Complete Appendix B persona cast:
    - 10 Responders: Asha (0.8 km), Ravi (1.3 km), Meera (2.1 km), Karan (0.3 km), Dr. Iyer (0.6 km), Sana (4.5 km), Vik (1.0 km), Nita (0.9 km), Omar (0.7 km), Dev (1.8 km).
    - 3 Ambulances: AMB-01 (2.4 km), AMB-02 (3.9 km), AMB-03 (1.1 km).
    - Citizen Demo: Aarav Sharma (0.0 km) with consenting medical profile (`share_during_emergency=True`).
    - Authority Demo: Chief Inspector Rao.
    - Ambulance Operator Demo: Dispatcher Deshmukh.
  - Full upsert idempotency: repeated execution yields invariant row counts with 0 errors (D-19).
- **Verification Tests (`backend/tests/test_seed.py` & `backend/tests/test_clock.py`):**
  - Verified persona counts, role bindings, and ambulance callsigns.
  - Haversine distance verification confirms Asha (0.8 km), Ravi (1.3 km), Karan (0.3 km), and AMB-01 (2.4 km) fall strictly within tight ±50 m bounds.
  - Verified Argon2 password hash validation and rejection of invalid passwords.
  - Verified repeated `seed_all()` idempotency.

---

## 2. Verification Results

- `pytest tests/test_clock.py -v`: PASSED (5/5)
- `pytest tests/test_seed.py -v`: PASSED (4/4)
- Full test suite (`pytest tests/ -v`): 35 passed in 1.30s across all 9 test suites.
- Frontend build (`npm --prefix apps/web run build`): PASSED in 2.17s.

---

## 3. Phase 1 Completion

All three plans for Phase 1 are now complete:
1. `01-01`: Shared taxonomy JSON, typed Python StrEnums, and TypeScript types.
2. `01-02`: SQLAlchemy 2.0 models, Alembic migrations, partial unique indexes, and PostgreSQL append-only triggers.
3. `01-03`: Clock abstraction, virtual session offsets, AST datetime ban scanner, and Appendix B persona seeding.
