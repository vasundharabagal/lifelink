# Plan 05-01: Emergency Incident Creation, Idempotency Replay, and Spatial Deduplication - Summary

**Executed:** 2026-10-01  
**Commit:** `[pending]`  
**Status:** Complete  

---

## 1. Key Accomplishments

1. **Strict Pydantic Contracts**:
   - Created `backend/app/schemas/emergency.py` with strict Pydantic v2 schemas (`extra="forbid"`):
     - `EmergencyCreateRequest`: Input contract validating lat/lng [-90..90, -180..180], triage inputs, location hints, and demo scope.
     - `DuplicateEmergencyErrorResponse`: Standardized 409 error model with `existing_emergency_id`, `distance_m`, and `can_force_create: true`.
     - `EmergencyResponse`: Public emergency projection including clinical priority, track states, dispatch plan summary, and active offers.
     - `EmergencyEventResponse`: Append-only chronological timeline event representation.

2. **Emergency Creation Domain Service**:
   - Created `backend/app/services/emergency.py`:
     - Implemented `create_emergency()` with atomic idempotency replay check on `(reported_by_user_id, idempotency_key)`. Returns existing emergency if already submitted.
     - Implemented 150m and 10-minute spatial deduplication prefilter using Haversine calculation against active emergencies. Rejects with `DuplicateEmergencyError` unless `force_create: true`.
     - Evaluates deterministic triage rules via `evaluate_rules` and classifies clinical priority (`P1_CRITICAL`, `P2_SERIOUS`, etc.).
     - Triggers candidate matching via `find_and_rank_candidates` and creates initial offers for candidate #1 on community and professional tracks.
     - Logs initial append-only events (`EMERGENCY_CREATED`, `TRIAGE_COMPLETED`, `OFFER_CREATED`) with monotonic sequence numbers.

3. **API Routing & Registration**:
   - Created `backend/app/api/v1/emergencies.py` exposing `POST /api/v1/emergencies`.
     - Returns HTTP 201 Created on new incident creation.
     - Returns HTTP 200 OK on idempotent replay.
     - Returns HTTP 409 Conflict with `POSSIBLE_DUPLICATE` error on spatial duplicate without force_create.
   - Mounted `emergencies` router under `/emergencies` in `backend/app/api/v1/__init__.py`.

4. **Integration Verification Suite**:
   - Created `backend/tests/test_emergency_creation_and_dedup.py` with 5 automated test cases:
     - `test_emergency_creation_successful`: Verifies incident creation, triage protocol matching, dual-track offer generation to Asha Shinde and AMB-01, and append-only event logging.
     - `test_emergency_creation_idempotent_replay`: Verifies duplicate submissions return 200/201 with identical IDs without duplicate DB records.
     - `test_emergency_creation_deduplication_409`: Verifies reports within 150m and 10 minutes return 409 POSSIBLE_DUPLICATE.
     - `test_emergency_creation_deduplication_force_create_override`: Verifies `force_create=true` bypasses 409 duplicate rejection.
     - `test_emergency_creation_coordinate_validation`: Verifies lat/lng bounds [-90..90, -180..180] are strictly enforced.

---

## 2. Verification Evidence

```text
backend\tests\test_emergency_creation_and_dedup.py .....                 [100%]
============================== 5 passed in 1.10s ==============================
```

---

## 3. Threat Mitigations Delivered

- **T-05-01 (Idempotency Key Collisions & Race Insertion)**: Enforced via `(reported_by_user_id, idempotency_key)` unique check with idempotent replay.
- **T-05-02 (Near-Simultaneous Duplicate Flooding)**: 150m and 10min Haversine check rejects potential duplicates with 409 until explicitly confirmed by caller.
- **T-05-06 (Maligned Coordinates / Injection)**: Pydantic field bounds `-90 <= lat <= 90` and `-180 <= lng <= 180` reject malformed or out-of-range spatial coordinates at the gateway.
