---
phase: 5
slug: 05-emergency-lifecycle-state-machine-offers-lazy-advance
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_emergency*.py backend/tests/test_lazy*.py backend/tests/test_offer*.py backend/tests/test_location*.py -v` |
| **Full suite command** | `pytest backend/tests -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run corresponding test module
- **After every plan wave:** Run `pytest backend/tests -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CORE-01 | T-05-01 | Idempotency-Key replay returns existing incident | integration | `pytest backend/tests/test_emergency_creation_and_dedup.py` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CORE-02 | T-05-01 | 150m/10min deduplication rejects duplicate with 409 | integration | `pytest backend/tests/test_emergency_creation_and_dedup.py` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | CORE-03 | T-05-04 | advance() under row lock expires overdue offers | integration | `pytest backend/tests/test_lazy_advance_and_locking.py` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | CORE-05 | T-05-04 | Timeout expiry cascades to candidate #2 in same tx | integration | `pytest backend/tests/test_lazy_advance_and_locking.py` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | CORE-04 | T-05-02 | Offer accept/arrive/complete; single active responder | integration | `pytest backend/tests/test_offer_action_lifecycle.py` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | CORE-05 | T-05-04 | Offer decline and SCENE_UNSAFE cascade with alerts | integration | `pytest backend/tests/test_offer_action_lifecycle.py` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 3 | CORE-07 | T-05-03 | Location privacy tiers (coarse vs exact vs revoked) | integration | `pytest backend/tests/test_location_privacy_tiers.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_emergency_creation_and_dedup.py` — creation, idempotency replay, 409 deduplication, `force_create`
- [ ] `backend/tests/test_lazy_advance_and_locking.py` — `advance()` row locking, double-check pattern, timeout expiration, candidate #2 cascade
- [ ] `backend/tests/test_offer_action_lifecycle.py` — offer action transitions, double-accept race rejection, scene-unsafe alerts
- [ ] `backend/tests/test_location_privacy_tiers.py` — coarse location hash offset (~250m), exact coordinate gating, nullification on termination
- [ ] `backend/tests/test_appendix_b_walkthrough_api.py` — end-to-end API walkthrough of Appendix B Incident 1

---

## Manual-Only Verifications

None — Phase 5 is backend transactional and API logic with 100% automated test coverage.
