# Plan 05-03: Offer Action Lifecycle, Double-Accept Protection, Location Privacy Tiers, and Appendix B Walkthrough - Summary

**Executed:** 2026-10-01  
**Commit:** `[pending]`  
**Status:** Complete  

---

## 1. Key Accomplishments

1. **Offer Action Lifecycle Engine**:
   - Implemented `backend/app/services/offer.py`:
     - Enforces atomic single-active-responder constraint: parallel accept attempts on the same emergency track reject with HTTP 409 `OFFER_ALREADY_CLAIMED` (CORE-04, T-05-02).
     - State machine actions: `ACCEPT` (transitions offer to `ACCEPTED`, incident to `IN_PROGRESS`, track to `ASSIGNED`), `DECLINE` (cascades synchronously to candidate #2 within the same database transaction), `ARRIVE` (transitions offer to `ARRIVED`, track to `ON_SCENE`), `SCENE_UNSAFE` (cancels offer, tags incident dispatch plan with hazard warning, logs critical safety alert event, and cascades to candidate #2 with safety warning), `COMPLETE` (records reported clinical action checklist and marks track `DONE`).
     - Monotonically serializes append-only timeline events (`OFFER_ACCEPTED`, `OFFER_DECLINED`, `RESPONDER_ARRIVED`, `RESPONDER_SCENE_UNSAFE`, `RESPONDER_COMPLETED`).

2. **Deterministic Location Privacy Tiers**:
   - Implemented `backend/app/services/privacy.py`:
     - `calculate_coarse_coordinates()` computes a deterministic pseudo-random bearing and distance (~200m–300m, mean ~250m) derived from `hashlib.sha256(str(incident_id).encode())`. Stable across repeated polls without map jumping.
     - `filter_emergency_location_for_user()` enforces strict privacy boundaries:
       - `exact`: Incident reporter, patient, authority, or assigned responders with `ACCEPTED` or `ARRIVED` status.
       - `coarse`: Unaccepted responders with active `OFFERED` status (~250m offset).
       - `revoked`: Declining, expired, completed responders, or unauthorized viewers (`lat: None, lng: None, location_revoked: True`).

3. **REST Endpoints for Offers and Incident Lifecycle**:
   - Created `backend/app/api/v1/offers.py`:
     - `GET /api/v1/offers/pending`: Returns open unexpired offers tailored to authenticated user role with location privacy masking.
     - `POST /api/v1/offers/{id}/action`: Executes lifecycle actions under PostgreSQL row locks.
   - Mounted `offers` router in `backend/app/api/v1/__init__.py`.
   - Updated `backend/app/api/v1/emergencies.py`:
     - `POST /api/v1/emergencies/{id}/cancel`: Citizen reporter or authority cancels incident and terminates open offers.
     - `POST /api/v1/emergencies/{id}/resolve`: Authority or ambulance operator formally completes incident.

4. **Integration Verification & E2E Walkthrough**:
   - `backend/tests/test_location_privacy_tiers.py` (3 tests): Verifies 200–300m coarse distance bounds, 100% deterministic hash stability across repeated queries, and strict role/state filtering.
   - `backend/tests/test_offer_action_lifecycle.py` (6 tests): Verifies accept, double-accept conflict 409, decline cascade, arrive/complete, scene-unsafe hazard tagging, and cancel/resolve endpoints.
   - `backend/tests/test_appendix_b_walkthrough_api.py` (1 test): Simulates the full Master Spec Appendix B Incident 1 scenario end-to-end through public REST endpoints (Priya creates P1 incident -> Asha declines -> Ravi cascades and accepts -> location unmasks from coarse to exact -> Ravi arrives and completes care -> authority resolves -> append-only audit log verified).

---

## 2. Verification Evidence

```text
backend\tests\test_emergency_creation_and_dedup.py .....                 [ 25%]
backend\tests\test_lazy_advance_and_locking.py .....                     [ 50%]
backend\tests\test_location_privacy_tiers.py ...                         [ 65%]
backend\tests\test_offer_action_lifecycle.py ......                      [ 95%]
backend\tests\test_appendix_b_walkthrough_api.py .                       [100%]
============================== 20 passed in 2.46s ==============================
```

- Total backend test suite: **139 passed in 7.34s**.
- Zero direct `datetime.now()` AST violations.

---

## 3. Threat Mitigations Delivered

- **T-05-02 (Double-Accept Race Condition)**: Single-active-responder check rejects concurrent claims with HTTP 409 `OFFER_ALREADY_CLAIMED`.
- **T-05-03 (Location Leakage to Unverified or Declining Responder)**: Revoked/non-active responders strictly receive null coordinates (`lat: null, lng: null, location_revoked: true`).
- **T-05-05 (Unauthorized Incident Cancellation)**: Centralized authorization enforces that only the incident reporter, patient, or authority can cancel an incident.
