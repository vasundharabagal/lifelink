# Plan 04-02: Multi-Factor Candidate Scoring, Curves, Tie-Breaking, and Ambulance Ranking - Summary

**Executed:** 2026-10-01  
**Commit:** `[pending]`  
**Status:** Complete  

---

## 1. Key Accomplishments

1. **Community Responder Scoring Algorithm (0–100 pts)**:
   - Implemented `calculate_skill_score`: Base 22.0 pts for meeting minimum required skill level, +4.0 pts per surplus proficiency level, +2.0 pts per secondary relevant skill held, capped at 30.0 pts. Supported ALS level 3 wildcard.
   - Implemented `calculate_eta_score`: 30.0 pt linear curve based on assumed 25 km/h urban speed and 900s cap.
   - Implemented `calculate_fairness_score`: 15.0 pt linear curve penalizing high 24h volunteer dispatches to avoid volunteer burnout.
   - Implemented `calculate_reliability_score`: 10.0 pt curve based on historical acceptance rate.
   - Implemented `calculate_credential_tier_score`: 10.0 pt categorical tiering (Professional=10, Certified=7, Trained=4, Other=2).
   - Implemented `calculate_radius_headroom_score`: 5.0 pts if distance $\le 50\%$ service radius, linearly scaling to 0.0 pts at 100%.
   - Implemented `score_responder`: Computes total score (0–100), full itemized breakdown (`ScoreBreakdown`), and context-aware `reasons[]` and `caveats[]`.
2. **Professional Ambulance Unit Scoring (0–100 pts)**:
   - Implemented `calculate_ambulance_suitability_score`: Priority-aware suitability curve awarding ALS 20 pts / BLS 10 pts for P1 emergencies, and BLS 20 pts / ALS 15 pts for P2/P3 emergencies (preserving scarce ALS resources for cardiac arrest).
   - Implemented `calculate_ambulance_eta_score`: 70.0 pt linear curve based on 35 km/h speed and 900s cap.
   - Implemented `calculate_ambulance_fairness_score`: 10.0 pt linear curve based on 24h unit runs.
   - Implemented `score_ambulance`: Returns `ScoredAmbulance` with total score, `AmbulanceScoreBreakdown`, and explainability notes.
3. **Deterministic Tie-Breaking**:
   - Responders: `rank_scored_responders` sorts by `(-score_total, eta_s, -reliability, candidate_id)`.
   - Ambulances: `rank_scored_ambulances` sorts by `(-score_total, eta_s, -suitability, unit_id)`.
4. **Automated Unit Testing**:
   - `backend/tests/test_orchestration_scoring.py`: 10 unit tests covering skill curves, ETA curves, fairness curves, reliability curves, tiering, radius headroom, ALS/BLS suitability curves, and 4-level deterministic tie-breaking.

---

## 2. Verification Evidence

```text
backend\tests\test_orchestration_scoring.py ..........                   [ 75%]
======================= 112 passed, 4 warnings in 3.72s =======================
```
- Total test count expanded from 102 to 112 passing tests.
- Zero AST direct `datetime.now()` violations.

---

## 3. Threat Mitigations Delivered

- **T-04-05 (Algorithmic Discrimination / Distance Monopoly)**: Distance alone never decides ranking; skill is weighted at 30 pts, and fairness awards up to 15 pts to prevent burning out the closest volunteer.
- **T-04-06 (Non-Deterministic Jitter in Ranking)**: 4-level tie-breaking hierarchy ensures absolute determinism across all multi-judge demo executions.
- **T-04-07 (ALS Resource Depletion)**: Ambulance suitability scores BLS higher for P2/P3 emergencies, reserving ALS units for high-acuity life threats.
