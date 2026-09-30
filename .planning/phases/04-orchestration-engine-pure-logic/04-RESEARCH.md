# Phase 4: Orchestration Engine (Pure Logic) - Research

**Date:** 2026-10-01  
**Status:** Complete  
**Requirements Addressed:** `ORCH-01`, `ORCH-02`, `ORCH-03`, `ORCH-04`

---

## 1. Executive Summary & Domain Scope

Phase 4 delivers the matching and ranking core of LIFELINK. It operates beside the clinical triage engine (Phase 3) and produces ranked candidate lists for both community responders and professional ambulances.

Per the specification (`docs/LIFELINK_MASTER_SPEC.md` §6) and locked architectural decisions (`04-CONTEXT.md`), Phase 4 implements:
1. **Mathematical Spatial Primitives**: Haversine distance, realistic detour multiplier (`DETOUR_FACTOR = 1.35`), and travel time estimation based on responder/ambulance speeds.
2. **Hard Eligibility Filters**: Strict exclusion gates rejecting candidates with machine-readable rejection reason codes (`NOT_VERIFIED`, `ACCOUNT_INACTIVE`, `NOT_AVAILABLE`, `ACTIVE_ASSIGNMENT`, `SKILL_MISMATCH`, `LOCATION_STALE`, `LOCATION_UNKNOWN`, `OUTSIDE_SERVICE_RADIUS`, `ALREADY_DECLINED_OR_EXPIRED`, `IS_PATIENT`, `SCOPE_MISMATCH`, `UNIT_NOT_AVAILABLE`).
3. **Multi-Factor Scoring (0–100)**: Multi-attribute scoring for community responders and ambulances with tested, deterministic tie-breaking.
4. **Transparent Explainability (`MatchExplanation`)**: Transparent score breakdown for authority oversight, reasons for rejected candidates, and privacy-safe citizen one-line summaries.
5. **Database-Decoupled Two-Layer Architecture**: A pure in-memory calculation core (`engine.py`) wrapped by an optimized SQL loader (`service.py`) using bounding-box spatial prefiltering.

---

## 2. Architecture & Module Structure

The orchestration logic is organized in `backend/app/orchestration/`:

```
backend/app/orchestration/
├── __init__.py           # Public exports
├── schemas.py            # Pydantic v2 strict models for engine I/O
├── distance.py           # Haversine distance, bounding box, and ETA math
├── engine.py             # Pure in-memory matching, scoring, and explanation core
└── service.py            # Database loader service with SQL bounding-box query
```

### Module Responsibilities

1. **`schemas.py`**:
   - `CandidateProfile`: In-memory representation of a volunteer responder (user, readiness, location, skills, credentials, recent responses).
   - `AmbulanceCandidate`: In-memory representation of an ambulance unit (id, callsign, unit_type, status, lat, lng, recent runs).
   - `EmergencyContext`: Incident details needed for matching (id, location, priority, emergency_type, required_skills, patient_user_id, reported_by_user_id, demo_session_id, excluded_responder_ids, excluded_ambulance_ids).
   - `ScoreBreakdown`: Component scores (skill, eta, fairness, reliability, credential_tier, radius_headroom).
   - `ScoredCandidate`: Candidate with rank, total score (0–100), breakdown, ETA, distance, reasons, and caveats.
   - `RejectionDetail`: Disqualified candidate with `reason_codes: List[EligibilityRejectionReason]` and human-readable `summary`.
   - `MatchExplanation`: Complete audit and UI snapshot (`emergency_id`, `track`, `ranked[]`, `rejected[]`, `weights`, `rules_version`, `computed_at`, `citizen_summary`).
   - `OrchestrationResult`: Contains `community_plan: List[ScoredCandidate]`, `professional_plan: List[ScoredAmbulance]`, `community_explanation: MatchExplanation`, `professional_explanation: MatchExplanation`.

2. **`distance.py`**:
   - `haversine_distance_m(lat1, lng1, lat2, lng2) -> float`
   - `calculate_eta_seconds(distance_m, speed_kmh, detour_factor, min_seconds=30) -> int`
   - `bounding_box_delta_deg(radius_m, lat) -> Tuple[float, float]`

3. **`engine.py`**:
   - Pure functions with no SQLAlchemy or DB dependencies:
     - `filter_and_rank_responders(candidates, emergency, clock, config) -> Tuple[List[ScoredCandidate], List[RejectionDetail]]`
     - `filter_and_rank_ambulances(units, emergency, clock, config) -> Tuple[List[ScoredAmbulance], List[RejectionDetail]]`
     - `build_match_explanation(emergency, track, ranked, rejected, config) -> MatchExplanation`
     - `build_citizen_summary(ranked, track) -> str`

4. **`service.py`**:
   - Takes `db: Session`, `emergency_id: UUID`, `clock: Clock`.
   - Uses SQL bounding-box prefilter to query candidate responder profiles from PostgreSQL:
     ```sql
     WHERE last_lat BETWEEN :min_lat AND :max_lat
       AND last_lng BETWEEN :min_lng AND :max_lng
       AND readiness = 'available'
     ```
   - Eager-loads user, skills, and credentials to prevent N+1 query overhead.
   - Queries `dispatch_offers` for already handled / declined responders and ambulances for this incident.
   - Hydrates `CandidateProfile` objects, passes them to `engine.py`, and returns `OrchestrationResult`.

---

## 3. Mathematical Formulations & Configuration

### 3.1 Spatial Distance (Haversine)
Using mean Earth radius $R = 6,371,000\,\text{m}$:
$$\Delta \phi = \text{radians}(\text{lat}_2 - \text{lat}_1), \quad \Delta \lambda = \text{radians}(\text{lng}_2 - \text{lng}_1)$$
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\text{radians}(\text{lat}_1))\cos(\text{radians}(\text{lat}_2))\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$c = 2 \cdot \operatorname{atan2}(\sqrt{a}, \sqrt{1 - a}), \quad d = R \cdot c$$

### 3.2 Estimated Time of Arrival (ETA)
$$\text{speed\_mps} = \frac{\text{speed\_kmh} \cdot 1000}{3600}$$
$$\text{eta\_s} = \max\left(30, \operatorname{round}\left(\frac{d \cdot \text{DETOUR\_FACTOR}}{\text{speed\_mps}}\right)\right)$$
- Responder speed: `25.0 km/h` ($\approx 6.94\,\text{m/s}$)
- Ambulance speed: `35.0 km/h` ($\approx 9.72\,\text{m/s}$)
- `DETOUR_FACTOR`: `1.35`
- `ETA_CAP_S`: `900` (15 minutes)

### 3.3 SQL Bounding-Box Delta
To avoid scanning the entire database:
$$\Delta \text{lat\_deg} = \frac{r}{111,320}$$
$$\Delta \text{lng\_deg} = \frac{r}{111,320 \cdot \cos(\text{radians}(\text{emergency\_lat}))}$$
For an emergency with maximum search radius $r = 5,000\,\text{m}$ at latitude $18.52^\circ$, $\Delta \text{lat\_deg} \approx 0.0449^\circ$ and $\Delta \text{lng\_deg} \approx 0.0474^\circ$.

---

## 4. Multi-Factor Scoring Curves (0–100)

### 4.1 Community Responder Scoring Weights
Total score is out of 100:
$$\text{Score} = S_{\text{skill}} + S_{\text{eta}} + S_{\text{fairness}} + S_{\text{reliability}} + S_{\text{credential\_tier}} + S_{\text{radius\_headroom}}$$

1. **Skill ($S_{\text{skill}}$, Max 30 pts):**
   - Minimum required skill level met: **22 pts** baseline.
   - Surplus level: **+4 pts** per level above the minimum required level.
   - Secondary relevant skills: **+2 pts** for each additional skill matching the emergency type or protocol.
   - Capped at **30 pts**.
2. **ETA ($S_{\text{eta}}$, Max 30 pts):**
   $$S_{\text{eta}} = 30 \cdot \max\left(0.0, 1.0 - \frac{\text{eta\_s}}{\text{ETA\_CAP\_S}}\right)$$
3. **Fairness ($S_{\text{fairness}}$, Max 15 pts):**
   Protects volunteers from burnout:
   $$S_{\text{fairness}} = 15 \cdot \max\left(0.0, 1.0 - \frac{\text{responses\_24h}}{5.0}\right)$$
4. **Reliability ($S_{\text{reliability}}$, Max 10 pts):**
   Historical acceptance rate:
   $$S_{\text{reliability}} = 10 \cdot \text{clamp}(\text{acceptance\_rate}, 0.0, 1.0)$$
5. **Credential Tier ($S_{\text{credential\_tier}}$, Max 10 pts):**
   - Professional (`doctor`, `nurse`, `paramedic`): **10 pts**
   - Certified (`emt`, `certified_first_aider`): **7 pts**
   - Trained (`medical_volunteer`, `student_responder`): **4 pts**
   - Other: **2 pts**
6. **Radius Headroom ($S_{\text{radius\_headroom}}$, Max 5 pts):**
   $$\text{ratio} = \frac{\text{distance\_m}}{\text{service\_radius\_m}}$$
   - If $\text{ratio} \le 0.5$: **5.0 pts**
   - If $0.5 < \text{ratio} \le 1.0$: $5.0 \cdot \left(1.0 - \frac{\text{ratio} - 0.5}{0.5}\right) = 10.0 \cdot (1.0 - \text{ratio})$
   - If $\text{ratio} > 1.0$: 0 pts (hard-rejected in stage 1 anyway).

### 4.2 Ambulance Unit Scoring Weights
Total score is out of 100:
$$\text{Score} = S_{\text{eta}} + S_{\text{suitability}} + S_{\text{fairness}}$$

1. **ETA ($S_{\text{eta}}$, Max 70 pts):**
   $$S_{\text{eta}} = 70 \cdot \max\left(0.0, 1.0 - \frac{\text{eta\_s}}{\text{ETA\_CAP\_S}}\right)$$
2. **Unit Suitability ($S_{\text{suitability}}$, Max 20 pts):**
   - For P1 emergencies:
     - `advanced` (ALS): **20 pts**
     - `basic` (BLS): **10 pts**
   - For P2 / P3 emergencies:
     - `basic` (BLS): **20 pts**
     - `advanced` (ALS): **15 pts** (preserves ALS units for high-acuity life threats)
3. **Fairness ($S_{\text{fairness}}$, Max 10 pts):**
   $$S_{\text{fairness}} = 10 \cdot \max\left(0.0, 1.0 - \frac{\text{runs\_24h}}{5.0}\right)$$

---

## 5. Hard Eligibility Filter Matrix

Every rejected candidate is tagged with one or more machine-readable reason codes:

| Reason Code | Target | Trigger Condition |
|:---|:---|:---|
| `NOT_VERIFIED` | Responder | No credential with `status == 'verified'` AND `expires_on >= clock.now().date()` |
| `ACCOUNT_INACTIVE` | Responder | `user.is_active is False` |
| `NOT_AVAILABLE` | Responder | `readiness != 'available'` OR `cooldown_until > clock.now()` |
| `ACTIVE_ASSIGNMENT` | Both | Existing offer with status in `('OFFERED', 'ACCEPTED', 'ARRIVED')` |
| `SKILL_MISMATCH` | Responder | Fails to hold any required skill at or above `min_level` |
| `LOCATION_UNKNOWN` | Both | `lat is None` or `lng is None` |
| `LOCATION_STALE` | Responder | `pinned_location is False` and `(clock.now() - last_location_at) > 300s` |
| `OUTSIDE_SERVICE_RADIUS` | Responder | `haversine_distance_m > service_radius_m` |
| `ALREADY_DECLINED_OR_EXPIRED` | Both | Handled prior offer for this emergency with status in `('DECLINED', 'EXPIRED', 'CANCELLED')` |
| `IS_PATIENT` | Responder | Responder user ID matches `patient_user_id` or `reported_by_user_id` |
| `SCOPE_MISMATCH` | Both | `candidate.demo_session_id != emergency.demo_session_id` |
| `UNIT_NOT_AVAILABLE` | Ambulance | `unit.status != 'available'` |

---

## 6. Deterministic Tie-Breaking Invariant

To ensure multi-tenant demo predictability:
- **Responders**:
  Sort key = `(-total_score, eta_s, -reliability, candidate_id)`
  - Higher total score first.
  - If equal, lower ETA first.
  - If equal, higher reliability first.
  - If equal, lexicographically smaller UUID string first.
- **Ambulance Units**:
  Sort key = `(-total_score, eta_s, -suitability, unit_id)`
  - Higher total score first.
  - If equal, lower ETA first.
  - If equal, higher suitability score first.
  - If equal, lexicographically smaller UUID string first.

---

## 7. Seeded Demo Cast Validation (Appendix B)

The test suite must verify the seeded demo cast under a P1 bleeding emergency (`DEMO_CENTER_LAT = 18.5204`, `DEMO_CENTER_LNG = 73.8567`):

1. **Asha Shinde (Nurse)**: 0.8 km, Level 3 bleeding control, verified. **Ranks #1** (Total score ~89).
2. **Ravi Gaikwad (Paramedic)**: 1.3 km, Level 3 ALS/bleeding control, verified. **Ranks #2** (Total score ~84).
3. **Meera Kulkarni (Certified First Aider)**: 2.1 km, Level 2 bleeding control, verified. **Ranks #3** (Total score ~73).
4. **Karan Joshi (Student Responder)**: 0.3 km, CPR Level 1 only. Disqualified: `SKILL_MISMATCH` (closer than Asha, but rejected).
5. **Dr. Subhash Iyer (Doctor)**: 0.6 km, busy on assignment. Disqualified: `NOT_AVAILABLE` / `ACTIVE_ASSIGNMENT`.
6. **Sana Khan (EMT)**: 4.5 km, radius 3 km. Disqualified: `OUTSIDE_SERVICE_RADIUS`.
7. **Vikram Malhotra (Volunteer)**: 1.0 km, off duty. Disqualified: `NOT_AVAILABLE`.
8. **Nita Sen (Nurse)**: 0.9 km, credential expired. Disqualified: `NOT_VERIFIED`.
9. **Omar Farooq (Paramedic)**: 0.7 km, credential pending. Disqualified: `NOT_VERIFIED`.
10. **Amb-1 (Advanced unit)**: 2.4 km, available. **Ranks #1** for professional track.
11. **Amb-2 (Basic unit)**: 3.9 km, available. **Ranks #2** for professional track.
12. **Amb-3 (Basic unit)**: 1.1 km, busy. Disqualified: `UNIT_NOT_AVAILABLE`.

---

## 8. Implementation Plan Breakdown

Phase 4 breaks into 3 sequential, independently verifiable plans:

1. **Plan 04-01**: Spatial calculations (`distance.py`), config constants in `core/config.py`, Pydantic contracts in `schemas.py`, and hard eligibility filters.
2. **Plan 04-02**: Multi-factor scoring algorithms (0–100), curve implementations, deterministic tie-breaking, and independent ambulance ranking logic.
3. **Plan 04-03**: `MatchExplanation` builder, citizen summary generation, database loader service (`service.py`) with bounding-box prefilter, and end-to-end seeded persona test suite matching Appendix B.
