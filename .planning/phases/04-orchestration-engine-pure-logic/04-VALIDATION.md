---
phase: 4
slug: 04-orchestration-engine-pure-logic
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_orchestration*.py -v` |
| **Full suite command** | `pytest backend/tests -v` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_orchestration*.py -v`
- **After every plan wave:** Run `pytest backend/tests -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | ORCH-01 | T-04-01 | Spatial math & bounding-box calculation | unit | `pytest backend/tests/test_orchestration_distance.py` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | ORCH-01 | T-04-02 | Hard eligibility filters reject ineligible responders | unit | `pytest backend/tests/test_orchestration_filters.py` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | ORCH-02 | T-04-03 | Multi-factor scoring (0-100) & curves | unit | `pytest backend/tests/test_orchestration_scoring.py` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | ORCH-04 | T-04-04 | Independent ambulance ranking (ALS vs BLS) | unit | `pytest backend/tests/test_orchestration_scoring.py` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | ORCH-03 | T-04-05 | MatchExplanation builder & citizen summary | unit | `pytest backend/tests/test_orchestration_explanation.py` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | ORCH-01..04 | T-04-06 | Seeded demo personas match Appendix B | integration | `pytest backend/tests/test_orchestration_service.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_orchestration_distance.py` — unit tests for Haversine, ETA, and bounding-box
- [ ] `backend/tests/test_orchestration_filters.py` — unit tests for all hard eligibility reason codes
- [ ] `backend/tests/test_orchestration_scoring.py` — unit tests for 0-100 scoring curves and tie-breaking
- [ ] `backend/tests/test_orchestration_explanation.py` — unit tests for MatchExplanation and citizen summary
- [ ] `backend/tests/test_orchestration_service.py` — integration tests for DB bounding-box query and Appendix B persona validation

---

## Manual-Only Verifications

None — Phase 4 is pure backend matching logic with 100% automated test coverage.
