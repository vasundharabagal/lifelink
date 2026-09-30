# Plan 05-02: Deterministic Lazy Advance Engine, Offer Expiry, and Candidate Cascading - Summary

**Executed:** 2026-10-01  
**Commit:** `[pending]`  
**Status:** Complete  

---

## 1. Key Accomplishments

1. **Lazy Evaluation Engine (`advance_emergency`)**:
   - Implemented `backend/app/services/advance.py`:
     - Acquires PostgreSQL row lock `with_for_update()` on parent `Emergency` record first, enforcing strict lock hierarchy (T-05-08).
     - Checks offer timeout expiration against `OFFER_TTL_S` (30s) using the injectable `Clock` service.
     - Transitions expired unacknowledged offers to `EXPIRED` status and records `responded_at` timestamp.
     - Immediately triggers synchronous cascading dispatch to candidate #2 (`community_plan[0]` or `professional_plan[0]`) within the same atomic database transaction (CORE-05).
     - Detects track candidate exhaustion, transitions track status to `UNAVAILABLE`, and appends `TRACK_EXHAUSTED` events.
     - Evaluates terminal condition: transitions incident to `NO_COVERAGE_CLOSED` with `close_reason="NO_COVERAGE"` when both tracks are unavailable and no active responders are assigned.
     - Serializes timeline events with strictly monotonic sequence numbers (`emergency.next_event_seq`).

2. **REST Endpoints for Polling and Advancement**:
   - Updated `backend/app/api/v1/emergencies.py`:
     - `GET /api/v1/emergencies/{id}`: Transparently triggers `advance_emergency` under row lock on every client poll, evaluating timeouts and cascades before returning the freshest incident state.
     - `POST /api/v1/emergencies/{id}/advance`: Explicit deterministic advancement with optional virtual clock offset (`offset_seconds`) for automated test suites and Demo Director time jumps.
     - `GET /api/v1/emergencies/{id}/timeline`: Returns chronological timeline events filtered by role visibility (`visible_to`).
   - Extended `backend/app/schemas/emergency.py` with `EmergencyAdvanceRequest`.

3. **Integration Verification Suite**:
   - Created `backend/tests/test_lazy_advance_and_locking.py` with 5 automated test cases:
     - `test_advance_before_timeout_is_noop`: Verifies calling advance at $t=10\text{s}$ leaves Asha Shinde's offer in `OFFERED` status without new events.
     - `test_advance_past_timeout_expires_and_cascades_to_candidate_2`: Verifies calling advance at $t=35\text{s}$ transitions Asha Shinde to `EXPIRED` and immediately dispatches Ravi Gaikwad with rank 2.
     - `test_advance_polling_triggers_cascade_transparently`: Verifies regular `GET /emergencies/{id}` client status polling drives timeout expiration and cascading dispatch without background workers.
     - `test_advance_exhaustion_marks_track_unavailable`: Verifies continuous advancement across all candidates transitions track to `UNAVAILABLE` and terminates in `NO_COVERAGE_CLOSED`.
     - `test_row_lock_concurrency_no_duplicate_events`: Verifies repeated sequential and concurrent advance calls produce zero sequence number gaps or duplicates.

---

## 2. Verification Evidence

```text
backend\tests\test_lazy_advance_and_locking.py .....                     [100%]
============================== 5 passed in 1.28s ==============================
```

---

## 3. Threat Mitigations Delivered

- **T-05-04 (Zombie Offer Starvation)**: `advance_emergency` verifies `clock.now() >= expires_at` on every poll request and cascades immediately within the same transaction.
- **T-05-08 (Lock Contention & Deadlock)**: Parent `Emergency` row is always locked first with `SELECT FOR UPDATE`, serializing child offer evaluations.
- **T-05-09 (Event Sequence Gap / Out-of-Order Timeline)**: Enforces atomic increment of `emergency.next_event_seq` under the emergency row lock.
