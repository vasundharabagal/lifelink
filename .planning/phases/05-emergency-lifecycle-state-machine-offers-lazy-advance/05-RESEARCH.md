# Phase 5: Emergency Lifecycle, State Machine, Offers, Lazy Advance - Research

**Date:** 2026-10-01  
**Status:** Complete  
**Requirements Addressed:** `CORE-01`, `CORE-02`, `CORE-03`, `CORE-04`, `CORE-05`, `CORE-06`, `CORE-07`  

---

## 1. Executive Summary & Domain Scope

Phase 5 builds the core transactional engine of LIFELINK. While Phase 4 created the pure mathematical matching algorithms in memory, Phase 5 connects those algorithms to the database, REST APIs, composite state machines, and real-time client polling cycles.

Per the specification (`docs/LIFELINK_MASTER_SPEC.md` §5, §7, §11) and locked architectural decisions (`05-CONTEXT.md`), Phase 5 delivers:
1. **Incident Creation, Idempotency & Deduplication (`CORE-01`, `CORE-02`)**:
   - `POST /api/v1/emergencies` accepting `Idempotency-Key` header with database-level uniqueness constraint.
   - Spatial and temporal deduplication (active emergencies within 150 m and 10 minutes) returning HTTP `409 Conflict` (`POSSIBLE_DUPLICATE`) with existing incident details and support for `force_create: true` override.
2. **Composite Dual-Track State Machine (`CORE-01`, `CORE-06`)**:
   - Manages top-level `EmergencyStatus` (`CREATED` -> `TRIAGED` -> `DISPATCHING` -> `IN_PROGRESS` -> `COMPLETED` / `CANCELLED` / `NO_COVERAGE_CLOSED`).
   - Manages independent community and professional `TrackStatus` (`NOT_STARTED` -> `SEARCHING` -> `OFFERED` -> `ASSIGNED` -> `ON_SCENE` -> `DONE` / `UNAVAILABLE` / `CANCELLED`).
   - Manages polymorphic `DispatchOfferStatus` (`OFFERED` -> `ACCEPTED` -> `ARRIVED` -> `COMPLETED` / `DECLINED` / `EXPIRED` / `CANCELLED`).
3. **Deterministic Lazy Evaluation (`advance()`) Under Row Locks (`CORE-03`, `CORE-05`)**:
   - Stateless serverless execution requires client-driven HTTP polling (2s active / 5s background) to trigger state advancement.
   - `advance(emergency_id)` acquires PostgreSQL row lock (`SELECT ... FOR UPDATE` on `emergencies`) with double-check locking to expire overdue offers (`OFFER_TTL_S` = 30s) and cascade dispatch.
   - Synchronous cascade immediately dispatches candidate #2 in the same database transaction.
   - Explicit `POST /api/v1/emergencies/{id}/advance` exposed for test automation and Demo Director manual clock advancement.
4. **Offer Action Lifecycle & Concurrency (`CORE-04`, `CORE-05`)**:
   - `POST /api/v1/offers/{id}/action` supporting `ACCEPT`, `DECLINE`, `ARRIVE`, `SCENE_UNSAFE`, and `COMPLETE`.
   - Atomic concurrency protection preventing double-accept races (single active accepted volunteer per incident track).
   - `SCENE_UNSAFE` action cancels assignment, logs `RESPONDER_SCENE_UNSAFE` event, sets hazard warning on incident, and cascades dispatch with prominent alerts.
5. **Location Privacy Tiering (`CORE-07`)**:
   - Deterministic hash-based radial offset (~250 m) before accept ensures stable coarse map pins across repeated polls without leaking exact coordinates.
   - Exact patient coordinates exposed strictly to the responder whose offer is `ACCEPTED` or `ARRIVED`.
   - Immediate coordinate nullification (`lat: null, lng: null, location_revoked: true`) upon completion, decline, expiry, or incident cancellation.

---

## 2. Architecture & Module Structure

The Phase 5 deliverables integrate into `backend/app/services/` and `backend/app/api/v1/`:

```
backend/app/
├── services/
│   ├── emergency.py          # Emergency lifecycle service (create, dedup, cancel, resolve)
│   ├── advance.py            # Lazy evaluation engine under row lock (advance, timeout, cascade)
│   ├── offer.py              # Offer actions (accept, decline, arrive, scene_unsafe, complete)
│   └── privacy.py            # Location privacy tiering (coarse hash offset, role filtering)
├── schemas/
│   ├── emergency.py          # Emergency create/response schemas, duplicate 409 schema
│   └── offer.py              # Offer action schemas, pending offer schemas
├── api/v1/
│   ├── emergencies.py        # REST endpoints for /emergencies (POST, GET, advance, cancel, resolve, timeline)
│   └── offers.py             # REST endpoints for /offers (GET pending, POST action)
└── tests/
    ├── test_emergency_creation_and_dedup.py
    ├── test_lazy_advance_and_locking.py
    ├── test_offer_action_lifecycle.py
    ├── test_location_privacy_tiers.py
    └── test_appendix_b_walkthrough_api.py
```

### Module Responsibilities

1. **`services/emergency.py`**:
   - `create_emergency(db, payload, reporter_user, clock, idempotency_key, force_create)`:
     - Checks `(reported_by_user_id, idempotency_key)` in `emergencies`. If exists, returns existing incident (HTTP 200/201).
     - Checks spatial deduplication: queries active emergencies in same `demo_session_id` where Haversine distance $\le 150\,\text{m}$ and `created_at >= clock.now() - 10 min`. If found and `force_create == False`, raises `DuplicateEmergencyError` (HTTP 409).
     - Runs deterministic triage rules (`classify_emergency`) to assign `priority`, `protocol_id`, `required_skills`, and ambulance requirement.
     - Compiles initial dispatch plan using `find_and_rank_candidates`.
     - Creates `Emergency` record, creates initial `DispatchOffer` for candidate #1 (`OFFERED`, `expires_at = clock.now() + 30s`), sets track statuses, and logs `EMERGENCY_CREATED`, `TRIAGE_COMPLETED`, and `OFFER_CREATED` to `emergency_events`.
   - `cancel_emergency(db, emergency_id, user, reason, clock)`:
     - Verifies user is reporter, patient, or authority.
     - Cancels active offers, sets status to `CANCELLED`, records `closed_at`, logs event.
   - `resolve_emergency(db, emergency_id, user, reason, clock)`:
     - Verifies user is authority or assigned ambulance operator.
     - Finalizes active offers, sets status to `COMPLETED`, logs event.

2. **`services/advance.py`**:
   - `advance_emergency(db, emergency_id, clock) -> Emergency`:
     - Executes `SELECT * FROM emergencies WHERE id = :id FOR UPDATE`.
     - If status in `['COMPLETED', 'CANCELLED', 'NO_COVERAGE_CLOSED']`: returns emergency.
     - Checks community track:
       - If an offer is `OFFERED` and `clock.now() >= offer.expires_at`:
         - Sets offer `status = 'EXPIRED'`, logs `OFFER_EXPIRED` event.
         - Queries remaining eligible candidates via `find_and_rank_candidates` (excluding previously declined/expired IDs).
         - If candidate #2 exists: creates new `DispatchOffer` in `OFFERED` status, `expires_at = clock.now() + OFFER_TTL_S`, emits `OFFER_CREATED`.
         - If no candidates remain: sets `community_track = 'UNAVAILABLE'`, emits `TRACK_EXHAUSTED`.
     - Checks professional ambulance track:
       - Evaluates ambulance unit availability and status transitions similarly.
     - If both tracks are exhausted and no responders are active: transitions emergency to `NO_COVERAGE_CLOSED` (or triggers escalation prompts).
     - Updates `emergency.updated_at = clock.now()`, commits.

3. **`services/offer.py`**:
   - `execute_offer_action(db, offer_id, action, user, clock, payload) -> DispatchOffer`:
     - Acquires row lock on offer and parent emergency.
     - Verifies authorization (user is assigned candidate or authority).
     - On `ACCEPT`:
       - Requires `status == 'OFFERED'` and `clock.now() < expires_at`.
       - Validates atomic single-active-responder constraint: ensures no other offer on this incident has `status IN ('ACCEPTED', 'ARRIVED')`.
       - Sets `status = 'ACCEPTED'`, `accepted_at = clock.now()`. Updates track to `ASSIGNED`, emergency to `IN_PROGRESS`. Emits `OFFER_ACCEPTED`.
     - On `DECLINE`:
       - Requires `status == 'OFFERED'`.
       - Sets `status = 'DECLINED'`, records `decline_reason`. Emits `OFFER_DECLINED`.
       - Calls synchronous cascade to dispatch candidate #2 immediately.
     - On `ARRIVE`:
       - Requires `status == 'ACCEPTED'`. Sets `status = 'ARRIVED'`, `arrived_at = clock.now()`. Updates track to `ON_SCENE`. Emits `RESPONDER_ARRIVED`.
     - On `SCENE_UNSAFE`:
       - Requires `status IN ('ACCEPTED', 'ARRIVED')`.
       - Sets `status = 'CANCELLED'`. Sets `scene_safety_warning` on emergency. Emits `RESPONDER_SCENE_UNSAFE`.
       - Cascades to candidate #2 with safety warning alert.
     - On `COMPLETE`:
       - Requires `status == 'ARRIVED'`. Sets `status = 'COMPLETED'`, records `actions_reported`. Updates track to `DONE`. Emits `RESPONDER_COMPLETED`.

4. **`services/privacy.py`**:
   - `calculate_coarse_coordinates(lat, lng, incident_id) -> Tuple[float, float]`:
     - Uses SHA-256 hash of `str(incident_id)` to derive deterministic angle and distance (~250 m):
       $$\text{hash\_val} = \text{int}(\text{SHA256}(\text{str}(incident\_id))[:8], 16)$$
       $$\theta = (\text{hash\_val} \pmod{360}) \cdot \frac{\pi}{180}$$
       $$r = 200.0 + (\text{hash\_val} \pmod{100})$$
       $$\Delta \text{lat} = \frac{r \cdot \cos(\theta)}{111,320}, \quad \Delta \text{lng} = \frac{r \cdot \sin(\theta)}{111,320 \cdot \cos(\text{lat}_{\text{rad}})}$$
   - `filter_emergency_for_user(emergency, user, db) -> EmergencyResponse`:
     - Determines user's relationship to incident (reporter, patient, authority, responder with offer status).
     - If reporter, patient, authority, or assigned responder with offer `ACCEPTED`/`ARRIVED`: returns exact `lat`, `lng`.
     - If candidate with offer `OFFERED`: returns `coarse_lat`, `coarse_lng`, `location_tier="coarse"`.
     - If candidate with offer `DECLINED`, `EXPIRED`, `CANCELLED`, `COMPLETED` or unrelated: returns `lat=None, lng=None, location_tier="revoked"`.

---

## 3. Concurrency Control & Deadlock Prevention

### 3.1 Lock Ordering
To prevent database deadlocks when multiple transactions interact with emergencies and dispatch offers, all database operations must follow a strict hierarchical lock order:
1. `emergencies` table row lock (`SELECT FOR UPDATE WHERE id = :emergency_id`) ALWAYS acquired first.
2. `dispatch_offers` rows locked secondary (`SELECT FOR UPDATE WHERE id = :offer_id`).
3. Never acquire `dispatch_offers` lock before `emergencies` lock.

### 3.2 Idempotency Key Atomicity
The database table `emergencies` enforces:
```sql
CREATE UNIQUE INDEX uq_emergencies_reporter_idempotency 
ON emergencies(reported_by_user_id, idempotency_key);
```
When `POST /emergencies` is executed:
- The service queries for existing `(reported_by_user_id, idempotency_key)` before inserting.
- If a concurrent race condition occurs, the unique index catches duplicate insertion and raises `IntegrityError`, which the service catches and translates into returning the existing record with HTTP 200.

---

## 4. Threat Modeling (ASVS L1 & Emergency Coordination)

- **T-05-01 (Duplicate SOS Storm / Resource Exhaustion)**: Rapid double-taps on citizen SOS create duplicate incidents.
  - *Mitigation*: Client `Idempotency-Key` + 150m/10min deduplication engine returning HTTP 409.
- **T-05-02 (Double-Accept Race Condition)**: Two volunteers accept the same offer simultaneously at the exact millisecond of timeout.
  - *Mitigation*: `SELECT FOR UPDATE` on `emergencies` + offer status check; first committer wins; second committer receives HTTP 409 `OFFER_ALREADY_CLAIMED`.
- **T-05-03 (Location Leakage to Unverified or Declining Responder)**: A responder who declines or whose offer expires continues to track the citizen's exact location.
  - *Mitigation*: `services/privacy.py` immediately nullifies coordinates for non-active offers; API contract tests assert `lat is None and lng is None`.
- **T-05-04 (Zombie Offer Starvation)**: A volunteer leaves their phone unattended; the incident remains locked in `OFFERED` status forever.
  - *Mitigation*: `advance()` expires offers after `OFFER_TTL_S` (30s) and immediately dispatches candidate #2.
- **T-05-05 (Unauthorized Incident Cancellation)**: A malicious actor or bystander cancels another citizen's active emergency.
  - *Mitigation*: Centralized authorization (`services/authz.py`) restricts cancellation strictly to the reporter, patient, or authority.

---

## 5. Validation Architecture & Test Strategy

### Test Matrix

| Test Suite | Purpose | Key Assertions |
|:---|:---|:---|
| `test_emergency_creation_and_dedup.py` | Verify `POST /emergencies`, idempotency, and deduplication | 1. Idempotent key replay returns existing incident without creating duplicates.<br>2. Report within 150m and 10 min returns HTTP 409 `POSSIBLE_DUPLICATE`.<br>3. `force_create: true` creates a second incident.<br>4. Missing fields rejected by Pydantic v2. |
| `test_lazy_advance_and_locking.py` | Verify `advance()` under row locks and timeout cascades | 1. `advance()` on active offer before timeout does not change status.<br>2. Advancing clock past 30s expires offer #1 (`EXPIRED`).<br>3. Candidate #2 immediately receives offer (`OFFERED`) in same transaction.<br>4. Exhausting all candidates transitions track to `UNAVAILABLE`. |
| `test_offer_action_lifecycle.py` | Verify offer state transitions and concurrency safety | 1. Accept transitions offer to `ACCEPTED`, track to `ASSIGNED`, incident to `IN_PROGRESS`.<br>2. Parallel accept attempt returns 409 `OFFER_ALREADY_CLAIMED`.<br>3. Decline transitions offer to `DECLINED` and immediately cascades to candidate #2.<br>4. Arrive transitions offer to `ARRIVED` and track to `ON_SCENE`.<br>5. Scene-unsafe abort sets incident warning, logs safety alert, and cascades.<br>6. Complete records checklist actions and closes track (`DONE`). |
| `test_location_privacy_tiers.py` | Verify location obfuscation and revocation | 1. Unaccepted offer returns deterministic coarse coordinates (~250m offset).<br>2. Coarse coordinates remain identical across repeated polls (no jitter).<br>3. Accepted offer exposes exact coordinates.<br>4. Declined, expired, or completed offer returns null coordinates (`location_revoked: true`). |
| `test_appendix_b_walkthrough_api.py` | Verify full Appendix B scenario via real REST endpoints | End-to-end execution of Walkthrough Incident 1 (Citizen SOS -> Asha offer -> Asha decline -> Ravi offer -> Ravi accept -> Ravi arrive -> Complete). |
