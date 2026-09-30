# Plan 04-01: Spatial Primitives, Orchestration Contracts, Constants, and Hard Eligibility Filters - Summary

**Executed:** 2026-10-01  
**Commit:** `[pending]`  
**Status:** Complete  

---

## 1. Key Accomplishments

1. **Configuration Constants**:
   - Added core orchestration constants to `backend/app/core/config.py`: `OFFER_TTL_S` (30), `DEMO_OFFER_TTL_S` (20), `MAX_COMMUNITY_CANDIDATES` (5), `MAX_AMBULANCE_CANDIDATES` (3), `LOCATION_FRESHNESS_S` (300), `DETOUR_FACTOR` (1.35), `RESPONDER_SPEED_KMH` (25.0), `AMBULANCE_SPEED_KMH` (35.0), `ETA_CAP_S` (900), and `COOLDOWN_AFTER_ASSIGNMENT_S` (120).
2. **Eligibility Rejection Reason Codes**:
   - Added `EligibilityRejectionReason(str, Enum)` to `backend/app/domain/enums.py` covering all 12 rejection conditions: `NOT_VERIFIED`, `ACCOUNT_INACTIVE`, `NOT_AVAILABLE`, `ACTIVE_ASSIGNMENT`, `SKILL_MISMATCH`, `LOCATION_STALE`, `LOCATION_UNKNOWN`, `OUTSIDE_SERVICE_RADIUS`, `ALREADY_DECLINED_OR_EXPIRED`, `IS_PATIENT`, `SCOPE_MISMATCH`, and `UNIT_NOT_AVAILABLE`.
3. **Spatial Math & Bounding-Box Math**:
   - Implemented `backend/app/orchestration/distance.py`:
     - `haversine_distance_m`: Great-circle spherical distance using $R = 6,371,000\,\text{m}$.
     - `calculate_eta_seconds`: Travel time applying $1.35\times$ detour factor, assumed speed, and minimum 30s clamp.
     - `bounding_box_delta_deg`: Converts radius in meters to latitude and longitude degree offsets for SQL bounding-box prefiltering.
4. **Strict Pydantic Contracts**:
   - Implemented `backend/app/orchestration/schemas.py` with strict Pydantic v2 schemas (`extra="forbid"`): `CandidateProfile`, `CandidateSkill`, `CandidateCredential`, `AmbulanceCandidate`, `EmergencyContext`, `ScoreBreakdown`, `AmbulanceScoreBreakdown`, `ScoredCandidate`, `ScoredAmbulance`, `RejectionDetail`, `MatchExplanation`, and `OrchestrationResult`.
5. **Hard Eligibility Filters**:
   - Implemented `backend/app/orchestration/filters.py`:
     - `evaluate_responder_eligibility`: Evaluates scope, self-dispatch conflict, account status, readiness, active assignments, prior decline/expiry, verified credential validity, location freshness/existence, service radius, and skill compatibility (including ALS level 3 wildcard proficiency).
     - `evaluate_ambulance_eligibility`: Evaluates scope, unit operational status, active assignments, and prior decline/expiry.
6. **Automated Unit Testing**:
   - `backend/tests/test_orchestration_distance.py`: 6 tests covering distance, clamp, and bounding box math.
   - `backend/tests/test_orchestration_filters.py`: 16 tests covering every individual rejection reason code, pinned demo persona stale-location bypass, and eligible pass-through.

---

## 2. Verification Evidence

```text
backend\tests\test_orchestration_distance.py ......                      [ 56%]
backend\tests\test_orchestration_filters.py ................             [ 72%]
======================= 102 passed, 4 warnings in 3.65s =======================
```
- Total test count expanded from 80 to 102 passing tests.
- Zero AST direct `datetime.now()` violations.

---

## 3. Threat Mitigations Delivered

- **T-04-01 (Unverified Volunteer Dispatch)**: `NOT_VERIFIED` check strictly requires verified status and non-expired date.
- **T-04-02 (Scope Leakage Between Demo and Production)**: `SCOPE_MISMATCH` check verifies exact `demo_session_id` match.
- **T-04-03 (Ghost Location / Stale Telemetry)**: `LOCATION_STALE` rejects non-demo locations older than 300 seconds.
- **T-04-04 (Self-Dispatch Conflict of Interest)**: `IS_PATIENT` rejects candidates matching patient or reporter IDs.
