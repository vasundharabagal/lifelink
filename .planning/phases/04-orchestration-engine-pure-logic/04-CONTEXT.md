# Phase 4: Orchestration engine (pure logic) - Context

**Gathered:** 2026-10-01
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase implements the pure matching and ranking engine for both community responders and professional ambulances. It encompasses:
1. Spatial calculations: Haversine distance, detour multiplier (`1.35`), ETA estimation based on responder/ambulance speeds, and SQL bounding-box prefilter.
2. Hard eligibility filters rejecting ineligible responders and ambulances with machine-readable reason codes (`NOT_VERIFIED`, `ACCOUNT_INACTIVE`, `NOT_AVAILABLE`, `ACTIVE_ASSIGNMENT`, `SKILL_MISMATCH`, `LOCATION_STALE`, `LOCATION_UNKNOWN`, `OUTSIDE_SERVICE_RADIUS`, `ALREADY_DECLINED_OR_EXPIRED`, `IS_PATIENT`, `SCOPE_MISMATCH`, `UNIT_NOT_AVAILABLE`).
3. Multi-factor scoring (0–100) for community responders and (0–100) for ambulances with deterministic tie-breaking.
4. Comprehensive `MatchExplanation` generator detailing score breakdowns for ranked candidates, rejection reason codes for disqualified candidates, and a privacy-safe one-line `citizen_summary`.
5. Independent ambulance ranking evaluating unit suitability (ALS vs BLS), ETA, and fairness.

Transactional state machine transitions, offer record mutations, and lazy polling cascades belong strictly to Phase 5.
</domain>

<decisions>
## Implementation Decisions

### Scoring Nuance & Curves
- **D-01 (Skill Scoring curve, max 30 pts):**
  - Base score of 22 pts for meeting the minimum required skill level specified in the protocol.
  - +4 pts per surplus skill level above the requirement (e.g., Level 3 when Level 2 required gives +4).
  - +2 pts per relevant secondary skill held by the responder that matches the protocol or emergency type.
  - Total skill score is hard-capped at 30 pts.
- **D-02 (Ambulance Suitability curve, max 20 pts):**
  - For P1 emergencies: Advanced Life Support (`advanced` / ALS) receives 20 pts; Basic Life Support (`basic` / BLS) receives 10 pts.
  - For P2 and P3 emergencies: BLS receives 20 pts; ALS receives 15 pts (preserving critical ALS resources for high-acuity life threats).
  - Ambulance ETA: 70 pts (`70 * max(0, 1 - eta_s / ETA_CAP_S)`).
  - Ambulance Fairness: 10 pts based on 24h response history.

### Engine Architecture & DB Decoupling
- **D-03 (Two-Layer Pure Core + DB Loader):**
  - Layer 1 (`app/orchestration/engine.py` or `core.py`): Pure in-memory matching logic working exclusively on typed Pydantic models / dataclasses. No SQLAlchemy imports, no database access. Deterministic and 100% unit-testable in isolation.
  - Layer 2 (`app/orchestration/service.py`): Database-aware loader that takes `db: Session`, computes the SQL bounding box (`lat +/- delta`, `lng +/- delta`), fetches candidate profiles with their skills and credentials, hydrates the in-memory models, invokes Layer 1, and returns an `OrchestrationResult`.

### MatchExplanation & Citizen Summary
- **D-04 (Multi-Tiered Explanation Structure):**
  - `MatchExplanation` contains:
    - Metadata: `emergency_id`, `track`, `computed_at`, `rules_version`, `weights`.
    - `ranked[]`: list of ranked candidates with `rank`, `candidate_id`, `name`, `score_total`, `score_breakdown` (subscores for skill, eta, fairness, reliability, credential_tier, radius_headroom), `eta_s`, `distance_m`, `reasons[]`, `caveats[]`.
    - `rejected[]`: list of rejected candidates with `candidate_id`, `name`, `reason_codes[]` (from spec enum), and human-readable `rejection_summary`.
    - `citizen_summary`: Privacy-safe one-line description (e.g., "Contacting nearby certified responder (~3 min ETA)" or fallback "Searching for qualified responders nearby") that reveals no private names or coordinates.

### Tie-Breaking & Freshness Policy
- **D-05 (Deterministic Tie-Breaking):**
  - Responders: `(score_total DESC, eta_s ASC, reliability DESC, id ASC)`.
  - Ambulances: `(score_total DESC, eta_s ASC, id ASC)`.
- **D-06 (Location Freshness & Demo Pinning):**
  - Location is valid only if `(clock.now() - last_location_at <= LOCATION_FRESHNESS_S)` (300 s). If older, reject with `LOCATION_STALE`.
  - If `last_lat` or `last_lng` is null, reject with `LOCATION_UNKNOWN`.
  - Exception: If `pinned_location == True` (seeded demo personas like Asha, Ravi, Karan), coordinates are always treated as fresh regardless of `last_location_at`.
- **D-07 (Radius Headroom Scoring, max 5 pts):**
  - Scores the maximum 5 pts when distance $\le 50\%$ of the responder's `service_radius_m`.
  - Linearly degrades from 5 pts to 0 pts as distance scales from 50% to 100% of `service_radius_m`.

### the agent's Discretion
- Exact file layout within `backend/app/orchestration/` (e.g. `schemas.py`, `distance.py`, `engine.py`, `service.py`).
- Exact bounding box delta formula for SQL prefilter using latitude/longitude degree conversion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Master Specification
- `docs/LIFELINK_MASTER_SPEC.md` §6 — Response Orchestration Logic (Constants, two parallel tracks, hard eligibility filters, 0–100 scoring, explanation, cascading dispatch, ETA/movement calculations)
- `docs/LIFELINK_MASTER_SPEC.md` §7.1-7.2 — Database schema for `responder_profiles`, `responder_skills`, `responder_credentials`, `ambulance_units`, `dispatch_offers`
- `docs/LIFELINK_MASTER_SPEC.md` Appendix B — Seeded demo cast personas and expected ranking outcomes (Asha #1, Ravi #2, Meera #3, Karan rejected `SKILL_MISMATCH`, Dr. Iyer `ACTIVE_ASSIGNMENT`, Sana `OUTSIDE_SERVICE_RADIUS`, Vik `NOT_AVAILABLE`, Nita `NOT_VERIFIED` expired, Omar `NOT_VERIFIED` pending, Amb-1 #1, Amb-2 #2, Amb-3 `UNIT_NOT_AVAILABLE`)

### Data & Taxonomy
- `shared/taxonomy.json` — Skill codes, skill levels, categories, responder categories
- `shared/protocols/*.json` — Required skills and skill levels per protocol ID

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/domain/models.py`: `User`, `ResponderProfile`, `ResponderSkill`, `ResponderCredential`, `AmbulanceUnit`, `Emergency`, `DispatchOffer` models.
- `backend/app/core/clock.py`: `Clock` dependency for deterministic time and freshness checks without `datetime.now()`.
- `backend/app/core/config.py`: Core configuration constants (`DETOUR_FACTOR`, `RESPONDER_SPEED_KMH`, `AMBULANCE_SPEED_KMH`, `ETA_CAP_S`, `LOCATION_FRESHNESS_S`, `MAX_COMMUNITY_CANDIDATES`, `MAX_AMBULANCE_CANDIDATES`).
- `backend/app/schemas/triage.py`: `TriageResult`, `RequiredSkill` schemas defining protocol IDs and skill levels output by Phase 3 triage engine.

### Established Patterns
- Pydantic v2 strict models (`extra="forbid"`) for all schema input/output contracts.
- Injectable `Clock` parameter passed to services to prevent test flakiness and enable demo clock manipulation.
- Strict audit and safety invariants: unverified responders must never be ranked or receive offers.

### Integration Points
- `backend/app/orchestration/`: New package housing distance calculations, eligibility checks, scoring engine, explanation builder, and candidate loading service.
- Integration with Phase 5: Phase 5's emergency lifecycle and `advance()` will call `service.compute_dispatch_plan(db, emergency)` to generate the initial or cascading dispatch lists.

</code_context>

<specifics>
## Specific Ideas

### Seeded Persona Test Matrix
The test suite for Phase 4 must explicitly validate the seeded demo cast from Appendix B against a mock cardiac/bleeding P1 emergency at `DEMO_CENTER`:
1. **Asha** ranks #1 (qualified, verified, closest eligible at 0.8 km).
2. **Ravi** ranks #2 (qualified ALS, verified, eligible at 1.3 km).
3. **Meera** ranks #3 (certified first aider, backup at 2.1 km).
4. **Karan** rejected with `SKILL_MISMATCH` (at 0.3 km, closest responder, but lacks required bleeding/trauma skill).
5. **Dr. Iyer** rejected with `ACTIVE_ASSIGNMENT` / `NOT_AVAILABLE` (on active assignment).
6. **Sana** rejected with `OUTSIDE_SERVICE_RADIUS` (at 4.5 km, exceeds 3 km radius).
7. **Vik** rejected with `NOT_AVAILABLE` (status is `off_duty`).
8. **Nita** rejected with `NOT_VERIFIED` (credential expired).
9. **Omar** rejected with `NOT_VERIFIED` (credential pending).
10. **Amb-1** ranks #1 for ambulance track (ALS unit, available, 2.4 km).
11. **Amb-2** ranks #2 for ambulance track (BLS backup, available, 3.9 km).
12. **Amb-3** rejected with `UNIT_NOT_AVAILABLE` (busy).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed strictly within Phase 4 pure orchestration scope.
</deferred>

---

*Phase: 04-orchestration-engine-pure-logic*
*Context gathered: 2026-10-01*
