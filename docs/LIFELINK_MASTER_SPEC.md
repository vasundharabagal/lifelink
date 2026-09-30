# LIFELINK MASTER SPECIFICATION
**Detect. Connect. Respond.**
Track: SDG 3, Good Health & Well-being. Problem: Community First-Aid & Emergency Dispatcher.
Spec version: 1.0. Status: canonical. Save this file in the repo as `docs/LIFELINK_MASTER_SPEC.md`.

Key words MUST / SHOULD / MAY are used in the RFC 2119 sense. Anything not stated here is out of scope until this document is amended.

---

## 0. HOW TO READ THIS DOCUMENT

- Sections 1-17 are the product and technical specification. Section 18 is the phased implementation roadmap. Appendix A records the judge review and the decisions that changed from the original concept. Appendix B holds the seeded demo cast.
- **Non-negotiable safety rules (apply everywhere):**
  1. LIFELINK is a coordination layer. It never replaces ambulances, hospitals, doctors or official emergency services. A "Call emergency services" control (default number `112`, configurable) MUST be visible on every citizen emergency screen and MUST work with no network (`tel:` link).
  2. AI is decision support for classification only. It never diagnoses. It never generates treatment instructions. All first-aid content comes from the versioned, pre-reviewed protocol library (section 5.5).
  3. **AI may escalate, never de-escalate.** No AI output may lower priority, remove a red flag, suppress an ambulance notification, or block dispatch.
  4. An unverified, expired, rejected or suspended responder MUST NEVER receive an offer or any emergency data. This is enforced in the eligibility filter and again by a database-level guard (section 7).
  5. No guarantee language. The UI never says "help is coming". It says "we are contacting nearby responders" or "responder accepted, estimated arrival X". ETAs are labelled *estimated*.
  6. Demo data and real data are strictly separated (section 13). Demo mode is visibly labelled on every screen.
  7. Every state change and every read of sensitive data is auditable.

---

## 1. FINAL PRODUCT VISION

LIFELINK is a **community-first emergency coordination layer for the golden minutes**: the gap between "something is wrong" and "professional help has arrived".

When a person triggers SOS, LIFELINK:
1. Turns a stressed, unstructured report into a structured incident (chips, three yes/no questions, optional free text, then AI-assisted extraction).
2. Runs a deterministic safety rules engine that fixes priority and the required skills.
3. Runs a **Response Orchestration Engine** that selects, explains and cascades to the best *verified, available, skill-compatible* nearby community responder, while **in parallel** notifying a professional ambulance service.
4. Keeps the citizen guided with pre-reviewed first-aid steps while help is on the way.
5. Records a tamper-evident timeline and produces an **emergency handover packet** so the professional crew inherits context instead of starting from zero.

It works as an add-on next to national emergency numbers. It does not claim to replace them.

## 2. CORE USP

**One sentence:** "The explainable, safety-gated coordination layer that runs *beside* official emergency services and turns verified nearby people into an accountable first-response network."

Three pillars judges can see in the demo:
1. **Safety-gated hybrid triage.** A deterministic rules engine is the source of truth. An optional LLM extracts structure from free text. The LLM can only add signals, never remove them. Only pre-reviewed protocols are shown.
2. **Explainable orchestration.** For every dispatch the system shows *why this responder* (score breakdown) and *why not the others* (rejected candidates with reasons). Distance alone never decides. Offers cascade on decline or timeout. The professional track runs in parallel.
3. **Closed loop.** Every incident ends with an auto-generated handover packet built from the audited timeline.

Anti-positioning: LIFELINK is NOT "an SOS button with AI".

## 3. USER JOURNEYS

Roles (final): `citizen`, `responder`, `ambulance_operator`, `authority`. The "admin/system operator" role is merged into `authority`. Demo controls are gated by `DEMO_MODE_ENABLED`, not by a separate role.

**3.1 Citizen (patient or bystander)**
1. Home has one dominant SOS button and a persistent "Call 112" button.
2. Press-and-hold SOS (1.5 s) opens the confirm sheet: "Send emergency request? [Send now] [Cancel]". Auto-cancel of the sheet after 10 s of no input.
3. Quick type chips (Bleeding, Not responding, Accident/Fall, Choking, Burn, Seizure, Chest pain, Other). Optional: "Who needs help? Me / Someone else". The chips are skippable.
4. Three big yes/no questions: "Awake and responding?", "Breathing normally?", "Severe bleeding?" Each has "Not sure".
5. Optional free-text (max 500 chars). Location is captured automatically. If denied or inaccurate, a draggable map pin or manual "landmark" text.
6. Preview card shows: suggested category, detected conditions, "This is decision support, not a diagnosis". [Correct] [Edit] [Send]. Send requires no further confirmation.
7. Live screen: status banner, map (patient, responders, ambulance), timeline, guidance card (protocol steps), "Call 112", "Cancel / false alarm".
8. Completion: summary and a link to the handover packet.

**3.2 Verified responder**
1. Registers (`responder` self-registration creates a *pending* profile), submits credential metadata (type, issuer, reference number, expiry). No file upload in MVP.
2. Cannot receive offers until an authority verifies a credential.
3. Sets readiness: `available` / `off_duty`. System sets `busy` automatically.
4. Incoming offer (full-screen, sound + vibration while app is open): emergency type, priority, approximate location (coarse), estimated distance and ETA, countdown. Must tick "I understand I'm a volunteer responder and will not enter an unsafe scene". [Accept] [Decline: reason].
5. On accept: exact location, protocol summary, consented medical info, navigation deep link (`geo:`), actions [Arrived] [Scene unsafe / abort] [Complete + quick action checklist].
6. After completion, returns to `available` after a short cool-down (configurable).

**3.3 Ambulance operator (simulated dispatcher console)**
1. Sees own units and status. Receives an offer for the best unit. [Accept + ETA] [Decline].
2. Active: en route, arrived, [Handover to facility] which finalises the packet.
3. Integration with a real dispatch system is a future item. The console is explicitly marked "simulated ambulance service".

**3.4 Authority (medical / verification authority, also system operator)**
1. Verification queue: approve / reject credentials with a note. Approving writes an audit log. Expiry handled automatically.
2. Live incidents board with the timeline and an **Explainability view** per incident (accepted and rejected candidates).
3. Responder directory (readiness, verification, skills).
4. (Stretch) Coverage-gap map.

**3.5 Failure journeys (MUST be demonstrable)**
- All responders decline or expire: status `NO_COVERAGE` on the community track, citizen sees a prominent "Call emergency services" prompt, the ambulance track continues.
- No ambulance accepts: same, on the professional track.
- Citizen cancels: all open offers are cancelled and notified.
- Network lost on citizen device: offline banner, protocol cards still render, `tel:` link still works.

## 4. SYSTEM ARCHITECTURE

### 4.1 Decision summary (after self-challenge; see Appendix A)

| Concern | Decision |
|---|---|
| Frontend | Vite + React + TypeScript + Tailwind. Static build. Mobile-first. Light theme only. |
| Backend | FastAPI (Python 3.11+). Stateless. One ASGI app under `/api/v1`. |
| Database | Managed PostgreSQL (Neon or Supabase, Postgres only, no vendor SDKs). |
| Geospatial | Plain lat/lng + Haversine + bounding-box prefilter. **No PostGIS in MVP** (roadmap item). |
| Realtime | **HTTP polling** (2 s active, 5 s hidden tab). No WebSockets, no SSE, no cron. |
| Timers (offer TTL) | **Lazy deterministic evaluation**: deadlines are stored as `expires_at`. Any poll or action calls `advance(emergency_id)`, which is idempotent and runs under a row lock. |
| Time | All logic uses an injectable `Clock` (real or demo-offset). No direct `datetime.now()` in domain code. |
| Maps | Leaflet + OpenStreetMap raster tiles with attribution. Custom `divIcon` markers. App remains usable if tiles fail. |
| Routing / ETA | No routing API. ETA = haversine x detour factor / assumed speed. Always labelled "estimated". |
| AI | Python module, provider-pluggable. Rules engine is primary. LLM is optional and behind a feature flag. |
| Notifications | In-app only (offers are the notifications). No push, SMS, email in MVP. |
| Auth | Email + password (argon2id), JWT in httpOnly SameSite=Strict cookie, RBAC, object-level authorization. |
| Files | **No file upload in MVP.** Credentials are metadata records. |
| Hosting | Vercel: static frontend + FastAPI serverless function. Contingency: backend on Render/Railway/Fly if the Phase 0 spike fails (section 15). |

### 4.2 Component diagram (text)

```
Browser (React SPA, polling)
   |  same-origin HTTPS /api/v1/*
   v
Vercel Function: FastAPI (stateless)
   |- api/ routers (thin) -> services (transactions)
   |- triage/   (rules, extractor, llm_adapter, schemas)
   |- orchestration/ (eligibility, scoring, explain, eta, engine)
   |- domain/   (enums, state_machine, protocols, skills)
   |- core/     (config, clock, security, errors, db, audit)
   v
PostgreSQL (row locks, partial unique indexes, CHECK constraints)
   ^
Optional: LLM provider (only sanitized free text leaves the system)
```

### 4.3 Repository layout (target)

```
/
  apps/web/                  # Vite React TS Tailwind
    src/{app,routes,features,components,lib,protocols(generated)}
  api/index.py               # Vercel entry: exposes FastAPI `app`
  backend/
    app/{main.py,core,domain,triage,orchestration,services,api/v1,models,schemas}
    alembic/
    tests/{unit,integration,concurrency,authz,golden,e2e_support}
    requirements.txt
  shared/protocols/*.json    # single source of truth for first-aid protocols
  shared/taxonomy.json       # emergency types, conditions, skills (single source)
  e2e/                       # Playwright
  docs/                      # this spec, ADRs, verification report
  docker-compose.yml         # local Postgres
  vercel.json
  .env.example
```

`shared/*.json` is consumed by the backend at runtime and copied/imported into the frontend at build time, so offline guidance and server rules can never drift.

### 4.4 Cross-cutting rules
- Routers are thin. All business logic lives in `services/` and `orchestration/`, which are pure and unit-testable where possible.
- Every mutating endpoint runs in one DB transaction and writes its `emergency_events` row and (where sensitive) an `audit_logs` row in that same transaction.
- Errors use one envelope: `{"error": {"code": "STRING_CODE", "message": "human readable", "details": {}}}`.
- No PII, coordinates or free text in INFO logs.

## 5. AI ARCHITECTURE

### 5.1 Principles
- AI = classification and structured extraction, nothing else.
- Deterministic rules decide priority, ambulance need and required skills.
- Structured user input (chips, yes/no answers) outranks NLP.
- Fail safe upward: uncertainty raises priority, never lowers it.

### 5.2 Pipeline
```
Inputs: quick_type?, answers{awake?,breathing?,severe_bleeding?}, description?
  -> Sanitize (trim, unicode normalize, length cap, strip phone numbers/emails)
  -> Tier 1: Rule extractor (keyword/pattern, EN + a small transliterated Hindi/Marathi list)
  -> Tier 2 (optional): LLM extractor (JSON only, closed enums, temperature 0, timeout 4 s)
  -> Merge (union of conditions; confidence = max with source noted)
  -> Rules engine (priority, ambulance_required, protocol_id, required_skills)
  -> TriageResult (validated by Pydantic)
```

### 5.3 TriageResult schema (contract)
```
TriageResult {
  emergency_type: enum(EmergencyType)
  observed_conditions: [enum(Condition)]      # closed set from shared/taxonomy.json
  red_flags: [enum(Condition)]                # subset that triggered P1
  protocol_id: enum(ProtocolId)
  required_skills: [{skill: enum(Skill), min_level: 1|2|3}]   # derived from protocol map, never from the LLM
  priority: "P1" | "P2" | "P3"
  ambulance_required: bool
  confidence: float 0..1
  source: "rules" | "llm" | "hybrid"
  evidence: [{condition, from: "chip"|"answer"|"text", span?: string}]
  rules_version: string
  disclaimer_key: "decision_support_not_diagnosis"
}
```

### 5.4 Rules engine (deterministic, table-driven, versioned `RULES_VERSION`)
- Red-flag conditions (any present => P1, ambulance_required = true): `UNRESPONSIVE`, `NOT_BREATHING`, `SEVERE_BLEEDING`, `CHOKING`, `CHEST_PAIN`, `STROKE_SIGNS`, `SEIZURE_ACTIVE`.
- P2: `FALL_OR_COLLISION`, `HEAD_INJURY`, `BURNS`, `BREATHING_ABNORMAL` without any red flag. Ambulance required = true.
- P3: only when the citizen explicitly selects "minor" AND no condition above is detected. Ambulance optional (the citizen may escalate at any time).
- Confidence below `LOW_CONFIDENCE_THRESHOLD` (0.5) or no conditions found => treat as P2 with protocol `PROT_GENERAL` (fail-safe up).
- Answers: `awake=no` => `UNRESPONSIVE`; `breathing=no` => `NOT_BREATHING`; `breathing=abnormal` => `BREATHING_ABNORMAL`; `severe_bleeding=yes` => `SEVERE_BLEEDING`. "Not sure" adds no condition and lowers confidence only.
- Protocol map (`shared/taxonomy.json`): protocol -> required skills and levels, e.g. `PROT_SEVERE_BLEEDING` requires `bleeding_control >= 2` OR `trauma_response >= 2` OR `advanced_life_support >= 3`.
- Precedence: `UNRESPONSIVE/NOT_BREATHING` > `CHOKING` > `SEVERE_BLEEDING` > `SEIZURE_ACTIVE` > `FALL/TRAUMA` > `BURNS` > `GENERAL`. Multiple conditions are all kept and all displayed. The highest-precedence condition selects the primary protocol.
- Known limitation (documented in README): keyword negation is not modelled ("not bleeding"). Because the system only over-triggers, this is safe.

### 5.5 Pre-reviewed protocol library
- Location: `shared/protocols/*.json`. MVP set: `PROT_UNRESPONSIVE`, `PROT_SEVERE_BLEEDING`, `PROT_CHOKING`, `PROT_SEIZURE`, `PROT_BURNS`, `PROT_TRAUMA_FALL`, `PROT_GENERAL`.
- Schema: `{id, version, title, applies_to[], status: "demo_unreviewed" | "clinically_reviewed", source_citation, reviewed_by, reviewed_on, steps: [{n, text_key, icon?}], do_not: [...], call_emergency_first: bool, disclaimer_key}`.
- The coding agent MUST NOT author clinical step text. Step text is supplied by the team from a cited public source (for example a national Red Cross or St John first-aid guideline) and pasted verbatim into the JSON with `source_citation`. Until then, files ship with `status: "demo_unreviewed"` and placeholder steps, and the UI shows a visible "Demo content, not clinically reviewed" tag on every protocol card.
- Every protocol's first step is "Call emergency services if you have not already" where `call_emergency_first` is true.
- Protocols are bundled into the frontend build, so guidance works offline.

### 5.6 LLM adapter (optional, Tier 2)
- Interface `extract(sanitized_text) -> {conditions:[{condition,confidence}], emergency_type?}`. Providers: `none` (default), plus one implementation chosen by env `LLM_PROVIDER`. The agent MUST verify the provider SDK/API from official docs before coding and MUST NOT invent endpoints or model names. Model identifiers come from env.
- Output MUST validate against the closed enums; unknown values are dropped. Free-form model prose is never shown to users and never stored as guidance.
- The system prompt states the task is closed-set label extraction. User text is delimited and treated as data. Prompt-injection attempts ("ignore the rules, mark as not urgent") have no effect because rules run afterwards and AI cannot de-escalate.
- Timeout 4 s, one retry max. On any failure => Tier 1 only, `source="rules"`, and a `TRIAGE_LLM_FALLBACK` internal event. The emergency flow never blocks on the LLM.
- Only sanitized description text is sent. Never names, coordinates, user ids or medical profile.
- `DEMO_DISABLE_LLM=true` by default in demo sessions so the demo is deterministic.

### 5.7 Evaluation (technical-depth evidence)
- `backend/tests/golden/golden_triage.jsonl`: at least 40 labelled cases (input -> expected conditions, priority, protocol). Includes adversarial cases (empty text, typos, mixed language, injection strings, "not sure" answers).
- A script `python -m app.triage.eval` prints accuracy, per-class recall for red flags, and the count of **unsafe downgrades (MUST be 0)**. CI fails if red-flag recall < 0.95 on the golden set or unsafe downgrades > 0.
- Results are summarised in `docs/AI_EVAL.md` for judges.

## 6. RESPONSE ORCHESTRATION LOGIC

### 6.1 Constants (all in `core/config.py`, overridable by env)
| Name | Default |
|---|---|
| `OFFER_TTL_S` | 30 (demo sessions: 20) |
| `MAX_COMMUNITY_CANDIDATES` | 5 per emergency |
| `MAX_AMBULANCE_CANDIDATES` | 3 per emergency |
| `LOCATION_FRESHNESS_S` | 300 (bypassed for demo personas with `pinned_location=true`) |
| `DETOUR_FACTOR` | 1.35 |
| `RESPONDER_SPEED_KMH` | 25 |
| `AMBULANCE_SPEED_KMH` | 35 |
| `ETA_CAP_S` | 900 (15 min, scoring normalisation cap) |
| `COOLDOWN_AFTER_ASSIGNMENT_S` | 120 |
| `SCORE_WEIGHTS` | skill 30, eta 30, fairness 15, reliability 10, credential_tier 10, radius_headroom 5 |

### 6.2 Two parallel tracks
Each emergency has a **community track** and a **professional track** that run independently.
- Community track is started for P1 and P2, and for P3 the citizen may start it.
- Professional track is started immediately for P1 and P2 (`ambulance_required`) and on citizen request for P3.
- Neither track waits for the other.

### 6.3 Stage 1: Hard eligibility filters (any failure => rejected with a machine-readable reason code)
Community responders:
1. `NOT_VERIFIED`: no credential with status `verified` and not expired.
2. `ACCOUNT_INACTIVE`.
3. `NOT_AVAILABLE`: readiness not `available` (off_duty, busy, cooldown).
4. `ACTIVE_ASSIGNMENT`: has an offer in `offered/accepted/arrived` (also enforced by DB index).
5. `SKILL_MISMATCH`: no held skill satisfies any requirement group of the protocol.
6. `LOCATION_STALE` / `LOCATION_UNKNOWN`.
7. `OUTSIDE_SERVICE_RADIUS`: distance > responder's `service_radius_m`.
8. `ALREADY_DECLINED_OR_EXPIRED` for this emergency.
9. `IS_PATIENT`: responder is the patient or reporter.
10. `SCOPE_MISMATCH`: demo/real separation (section 13).
Ambulances: `UNIT_NOT_AVAILABLE`, `ACTIVE_ASSIGNMENT`, `LOCATION_UNKNOWN`, `SCOPE_MISMATCH`, `ALREADY_DECLINED_OR_EXPIRED`.

Bounding-box prefilter (in SQL) narrows candidates by max service radius before Haversine.

### 6.4 Stage 2: Scoring (0-100)
- `skill` (30): best-matching required skill: exact level match or higher = full; each missing level step reduces it; extra relevant secondary skills add up to a cap.
- `eta` (30): `30 * max(0, 1 - eta_s / ETA_CAP_S)`.
- `fairness` (15): fewer responses in the last 24 h scores higher (avoids burning out the same volunteers).
- `reliability` (10): historical acceptance rate (seeded in demo).
- `credential_tier` (10): professional (3) > certified (2) > trained (1).
- `radius_headroom` (5): distance well inside the service radius scores higher.
Distance is only an input to ETA and headroom, so **distance alone can never decide the ranking**.
- Deterministic tie-break: lower ETA, then higher reliability, then lexicographically smaller id.
- Ambulance ranking: ETA (70), unit type suitability (20), fairness (10).

### 6.5 Stage 3: Explanation
Every ranked candidate carries a `score_breakdown` and human-readable `reasons[]` and `caveats[]`, for example:
`Verified, Available, Skill: bleeding control (certified), Within radius (0.8 km of 3.0 km), ETA about 3 min (estimated), No active assignment`.
Every rejected candidate carries `reason_codes[]` and a plain-language label. The `MatchExplanation` object (`ranked[]`, `rejected[]`, `weights`, `rules_version`, `computed_at`) is stored as `score_snapshot` on the offer and as an event payload. It is shown fully to authority and demo judge views, and only as a one-line summary to the citizen ("Nearby certified responder contacted"). Responders never see other candidates.

### 6.6 Stage 4: Cascading dispatch
1. Engine computes ranked candidates once per track and stores the ordered list in the emergency's `dispatch_plan` (JSON on the emergency row).
2. The next candidate gets an offer (`status=OFFERED`, `expires_at=now+OFFER_TTL_S`, `rank`). The insert is guarded by DB partial unique indexes. On a unique violation (candidate got busy concurrently) the engine records `SKIPPED_RACE` and takes the next candidate.
3. Decline, expiry, or scene-unsafe abort => offer closed => `advance()` offers the next. After `MAX_*_CANDIDATES` attempts or list exhausted => track `UNAVAILABLE` => event `NO_COVERAGE` + citizen escalation prompt. The plan MAY be recomputed once when the list is exhausted, to catch newly available responders.
4. Accept => track `ASSIGNED`; other outstanding offers on that track (none, by index) are impossible; the plan is closed.

### 6.7 `advance(emergency_id)` (idempotent)
```
if no offer with status=OFFERED and expires_at <= now and no track needs a first offer: return   # cheap indexed check, no lock
BEGIN
  SELECT emergency FOR UPDATE
  for each track:
     mark expired offers (OFFERED and expires_at <= now) => EXPIRED + event
     if track needs an offer and plan has next candidate: create offer
     if exhausted: mark track UNAVAILABLE + event
  recompute top-level status (derive_status)
COMMIT
```
Called from: create emergency, every emergency poll, every offer action, and every responder/ambulance inbox poll. Because it is idempotent and lock-protected, concurrent polls cannot double-offer.
Documented limitation: if no client is polling, expiry does not advance. The citizen app polls while open. Real deployments add a scheduled worker (future scope).

### 6.8 ETA and movement
- `eta_s = (haversine_m * DETOUR_FACTOR) / speed_mps`, minimum 30 s.
- Real mode: responders post location every 10 s while `available` or assigned. Ambulance units are simulated in MVP.
- Demo and simulation: position of an assigned mover = linear interpolation between its start and the patient over `sim_travel_s`, computed server-side from `Clock` and `accepted_at`, so the map is deterministic and needs no client GPS.

### 6.9 Incident deduplication (SHOULD, simple rule)
On create, if another open emergency of the same scope has `haversine < 150 m` and `created_at` within 10 min and compatible type, respond `409 POSSIBLE_DUPLICATE` with the existing incident id (public summary only). The citizen may "Link to existing incident" (adds a `reporter_linked` event, no new dispatch) or "This is a different emergency" (resend with `force_new=true`). No clustering algorithms.

## 7. DATABASE DESIGN

PostgreSQL. SQLAlchemy 2.x + Alembic. All primary keys UUID (v4) unless noted. All timestamps `timestamptz` in UTC. Every table except `demo_sessions` carries `demo_session_id UUID NULL` where relevant (NULL = real scope).

Removed from the original candidate list (with reason): `emergency_dispatches`, `dispatch_attempts`, `ambulance_dispatches` merged into `dispatch_offers` (three tables did one job); `emergency_status_history`, `responder_status_history`, `notifications` merged into `emergency_events` (offers *are* notifications; readiness changes go to `audit_logs`); `emergency_locations` removed (location trail is a privacy liability and unnecessary; only the latest position is stored); `responder_documents` replaced by `responder_credentials` (no files); `facilities` becomes a static JSON constant; `emergency_contacts` folded into `medical_profiles.contacts`; `emergency_protocols` lives in versioned JSON, not a table; `medical_authorities` is a `users` row with `role=authority`.

### 7.1 Tables (11)

**users**: `id`, `role` (`citizen|responder|ambulance_operator|authority`), `email` (unique, lowercased; demo emails use `@demo.lifelink.invalid`), `password_hash` (argon2id), `full_name`, `phone` (nullable), `is_active`, `demo_session_id`, `created_at`.

**responder_profiles**: `user_id` (PK, FK), `category` (`doctor|nurse|paramedic|emt|certified_first_aider|medical_volunteer|student_responder|security_personnel|other`), `readiness` (`available|off_duty|busy`), `service_radius_m`, `last_lat`, `last_lng`, `last_location_at`, `pinned_location` (bool, demo only), `acceptance_rate` (0..1), `responses_24h` (int, maintained or derived), `cooldown_until`, `updated_at`.

**responder_skills**: `responder_id`, `skill_code` (enum from taxonomy), `level` (1..3). PK (`responder_id`, `skill_code`).

**responder_credentials**: `id`, `responder_id`, `credential_type`, `issuer`, `reference_no`, `expires_on`, `status` (`pending|verified|rejected|expired|suspended`), `reviewed_by`, `reviewed_at`, `review_note`, `created_at`. Verification is derived from this table only.

**ambulance_units**: `id`, `operator_user_id`, `callsign`, `unit_type` (`basic|advanced`), `status` (`available|busy|offline`), `lat`, `lng`, `base_name`, `demo_session_id`.

**medical_profiles**: `user_id` (PK), `blood_group?`, `allergies`, `conditions`, `medications`, `contacts` (JSON, max 3), `share_during_emergency` (bool, default false), `updated_at`. Free-text fields length-capped.

**emergencies**: `id`, `patient_user_id`, `reported_by_user_id`, `idempotency_key`, `status` (section 12), `community_track` (enum), `professional_track` (enum), `priority`, `emergency_type`, `triage` (JSON `TriageResult`), `dispatch_plan` (JSON), `lat`, `lng`, `location_accuracy_m`, `location_hint`, `patient_is_reporter` (bool), `consent_share_medical` (bool), `version` (int, optimistic), `next_event_seq` (int), `handover_snapshot` (JSON, nullable), `close_reason` (nullable), `demo_session_id`, `created_at`, `updated_at`, `closed_at`.

**emergency_events**: `id`, `emergency_id`, `seq` (unique per emergency), `type` (enum), `actor_user_id?`, `actor_role`, `payload` (JSON), `visible_to` (text[] of roles), `at`. Append-only; a trigger rejects UPDATE and DELETE.

**dispatch_offers**: `id`, `emergency_id`, `track` (`community|professional`), `target_kind` (`responder|ambulance`), `responder_id?`, `ambulance_id?`, `rank`, `status` (`OFFERED|ACCEPTED|ARRIVED|COMPLETED|DECLINED|EXPIRED|CANCELLED`), `offered_at`, `expires_at`, `responded_at`, `accepted_at`, `arrived_at`, `completed_at`, `decline_reason` (enum), `eta_s`, `distance_m`, `score_snapshot` (JSON), `sim_start_lat/lng`, `sim_travel_s`, `actions_reported` (JSON), `notes` (short text).

**audit_logs**: `id`, `at`, `actor_user_id?`, `actor_role`, `action`, `resource_type`, `resource_id`, `outcome` (`allow|deny`), `ip_hash`, `meta` (JSON, no PII). Append-only trigger. Records: logins (success/fail), verification decisions, every read of exact location or medical profile by a non-patient, denied authorization, demo resets.

**demo_sessions**: `id`, `created_at`, `expires_at`, `clock_offset_s`, `scenario` (JSON step state), `is_active`.

### 7.2 Constraints that carry safety guarantees
- `CHECK` on `dispatch_offers`: exactly one of `responder_id`, `ambulance_id` is non-null and it matches `target_kind`.
- Partial unique index: one live offer per responder: `UNIQUE (responder_id) WHERE status IN ('OFFERED','ACCEPTED','ARRIVED')`. Same for `ambulance_id`.
- Partial unique index: one live offer per track per emergency: `UNIQUE (emergency_id, track) WHERE status IN ('OFFERED','ACCEPTED','ARRIVED')`.
- Partial unique index: one active emergency per patient: `UNIQUE (patient_user_id) WHERE status NOT IN ('COMPLETED','CANCELLED','NO_COVERAGE_CLOSED')`.
- `UNIQUE (reported_by_user_id, idempotency_key)`.
- `UNIQUE (emergency_id, seq)` on events.
- DB guard against unverified dispatch: offer inserts go through one service function that re-checks credential status inside the same transaction. A test attempts to bypass it.
- Indexes: `dispatch_offers(status, expires_at)`, `responder_profiles(readiness, last_lat, last_lng)`, `emergencies(status, demo_session_id)`, `emergency_events(emergency_id, seq)`.

### 7.3 Migrations and seeds
Alembic migrations only. Seeds via `python -m app.seed` (taxonomy-independent reference data and demo persona templates). Demo sessions clone the persona template into scoped rows (section 13).

## 8. API CONTRACTS

Base path `/api/v1`. JSON only. Auth: httpOnly cookie `ll_session` (JWT). Mutating requests require `Content-Type: application/json` and a same-origin `Origin` header (CSRF defence with SameSite=Strict). Errors use the envelope from 4.4. Timestamps ISO-8601 UTC.

Common error codes: `VALIDATION_ERROR` 422, `UNAUTHENTICATED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404, `CONFLICT` 409, `INVALID_STATE_TRANSITION` 409, `OFFER_EXPIRED` 409, `OFFER_ALREADY_HANDLED` 409, `POSSIBLE_DUPLICATE` 409, `ACTIVE_EMERGENCY_EXISTS` 409, `RATE_LIMITED` 429, `DEMO_DISABLED` 404.

### 8.1 Auth
| Method Path | Role | Request | Response |
|---|---|---|---|
| POST `/auth/register` | public | `{email, password, full_name, phone?, role: "citizen"\|"responder"}` (other roles are never self-registrable) | 201 `{user}` (responders start with no verified credential) |
| POST `/auth/login` | public | `{email, password}` | 200 `{user}` + sets cookie. Failed attempts are throttled using `audit_logs` counts. |
| POST `/auth/logout` | any | none | 204 |
| GET `/auth/me` | any | none | `{user, responder_profile?}` |

### 8.2 Triage and emergencies
| Method Path | Role | Notes |
|---|---|---|
| POST `/triage/preview` | citizen | Body `{quick_type?, answers, description?}` -> `TriageResult`. Rate-limited. Persists nothing. |
| POST `/emergencies` | citizen | Header `Idempotency-Key` REQUIRED. Body `{quick_type?, answers, description?, location:{lat,lng,accuracy_m}, location_hint?, patient_is_reporter, consent_share_medical, force_new?}`. Runs triage, creates the emergency, starts both tracks. 201 `EmergencySnapshot`. Same key => same 200 response, no duplicate. |
| GET `/emergencies/{id}` | patient/reporter, assigned responder/ambulance, authority | Query `since_seq`. Calls `advance()`. Returns a role-scoped `EmergencySnapshot` plus `events[]` newer than `since_seq`. |
| POST `/emergencies/{id}/cancel` | patient/reporter | `{reason: "false_alarm"\|"resolved"\|"other"}` -> cancels open offers. |
| POST `/emergencies/{id}/escalate-professional` | patient/reporter | Starts the professional track for P3. |
| GET `/emergencies/{id}/match-explanation` | authority (and demo judge view in demo scope) | Full `MatchExplanation` per track. |
| GET `/emergencies/{id}/handover` | assigned ambulance, authority, patient | `HandoverPacket` (section 8.5). |

`EmergencySnapshot` role scoping:
- Citizen: status, tracks, triage summary, protocol id, assigned responders' **first name, category, skill labels, ETA, current position** (no phone, no credential numbers), timeline filtered by `visible_to`.
- Responder before accept: coarse location only (grid-snapped to about 250 m), type, priority, distance, ETA. After accept: exact location, protocol, consented medical fields.
- Ambulance: exact location and consented medical fields once the offer is accepted.
- Authority: everything except free-text medical fields unless the incident is open, and every such read is audit-logged.

### 8.3 Responder and ambulance
| Method Path | Role | Notes |
|---|---|---|
| GET `/responders/me` | responder | profile, skills, credentials |
| PATCH `/responders/me` | responder | `{readiness?: "available"\|"off_duty", service_radius_m?}` (cannot set `busy` manually) |
| POST `/responders/me/location` | responder | `{lat, lng, accuracy_m}` (rate-limited, 1 per 5 s) |
| POST `/responders/me/credentials` | responder | metadata only, creates `pending` |
| GET `/inbox` | responder, ambulance_operator | Calls `advance()` for relevant emergencies. Returns `{current_offer?, active_assignment?}`. Poll every 3 s. |
| POST `/offers/{id}/accept` | target of the offer | Body `{acknowledged_volunteer_terms: true}` for community offers, `{eta_s?}` for ambulance. Atomic conditional update; exactly one winner. |
| POST `/offers/{id}/decline` | target | `{reason: "unavailable"\|"too_far"\|"skill_mismatch"\|"safety_concern"\|"other"}` |
| POST `/offers/{id}/arrive` | target | -> `ARRIVED` |
| POST `/offers/{id}/scene-unsafe` | target | closes the offer as `CANCELLED` with reason, cascades |
| POST `/offers/{id}/complete` | target | `{actions: [enum...], patient_state: "conscious"\|"unconscious"\|"unknown", notes?}` (short, capped) |
| POST `/offers/{id}/handover` | ambulance target | `{receiving_facility_id, handover_notes?}` -> finalises `handover_snapshot`, emergency -> `HANDED_OVER` |

### 8.4 Authority
| Method Path | Notes |
|---|---|
| GET `/authority/credentials?status=pending` | queue |
| POST `/authority/credentials/{id}/decision` | `{decision: "verify"\|"reject"\|"suspend", note}` -> audit log |
| GET `/authority/incidents?status=active` | live board |
| GET `/authority/responders` | directory (no secrets) |
| GET `/authority/coverage` | (stretch) grid cells with eligible-responder counts |

### 8.5 HandoverPacket (contract)
```
{ emergency_id, generated_at, is_demo,
  timing: {created, triaged, first_offer, first_accept, responder_arrived?, ambulance_accepted?, ambulance_arrived?, handover_at?},
  metrics: {time_to_first_accept_s, time_to_first_arrival_s, offers_sent, declines, expiries},
  triage: {emergency_type, conditions, priority, protocol_id, confidence, source, rules_version},
  scene: {location, accuracy_m, hint},
  community_response: {responder_first_name, category, credential_tier, actions_reported[], patient_state},
  medical: {shared: bool, profile?},   // only if consented
  timeline: [events visible to ambulance],
  receiving_facility, disclaimer_keys[] }
```
Generated deterministically from events; the snapshot is stored at `HANDED_OVER`. The frontend renders it as a printable page (browser print to PDF). No server-side PDF generation.

### 8.6 Demo (only when `DEMO_MODE_ENABLED=true`, otherwise 404 `DEMO_DISABLED`)
| Method Path | Notes |
|---|---|
| POST `/demo/sessions` | Creates an isolated session, clones personas. Returns `{session_id, personas:[{key, role, name}]}` |
| POST `/demo/sessions/{id}/impersonate` | `{persona_key}` sets the cookie for a demo user of that session only |
| POST `/demo/sessions/{id}/reset` | Deletes session-scoped rows and reseeds. Idempotent. |
| POST `/demo/sessions/{id}/clock/advance` | `{seconds}` (bounded) |
| POST `/demo/sessions/{id}/scenario/step` | `{step}` performs one scripted actor action (for example "responder A declines") |
| POST `/demo/sessions/{id}/scenario/autoplay` | executes remaining steps with configurable pauses |
| GET `/demo/sessions/{id}/state` | scenario progress + explanation panel data |
| DELETE `/demo/sessions/{id}` | cleanup; sessions also expire (default 4 h) |

### 8.7 Health
`GET /health` -> `{status, db: "ok"|"error", version, demo_mode}`; no secrets.

### 8.8 Rate limits (DB-derived, because in-memory limits do not work on serverless)
- Login: 5 failures per email per 15 min (counted from `audit_logs`).
- SOS creation: at most 3 emergencies per user per hour and one active at a time (partial unique index). Repeated cancelled/false-alarm SOS raise a `abuse_suspected` audit entry and flag the user for authority review.
- `/triage/preview`: 20 per user per 10 min.
- Location posts: 1 per 5 s per responder.

---

## 9. FRONTEND INFORMATION ARCHITECTURE

### 9.1 Design principles (light theme only)
- One primary action per screen. Everything else is secondary.
- Touch targets at least 48x48 px. Body text at least 16 px. Contrast at least WCAG AA (4.5:1 text, 3:1 large UI).
- Red is reserved for SOS, critical alerts and the emergency call. Status is never conveyed by colour alone (icon + text label).
- Status changes are announced with `aria-live="polite"` (`assertive` for incoming offers). Respect `prefers-reduced-motion`. Visible focus rings. Semantic HTML and labelled controls.
- Under-stress copy: short, imperative, no jargon, no medical claims. Strings live in one `strings.ts` (i18n-ready keys; translations are a stretch item).
- Persistent header: LIFELINK mark, offline indicator, and a `DEMO MODE` pill when in a demo scope. Persistent footer or floating button on citizen emergency screens: "Call 112".
- Performance budget: initial JS under 200 KB gzip for the citizen route (code-split map and other roles), LCP under 2.5 s on a mid-range phone over 4G.

### 9.2 Route map
```
Public
  /                       landing (value proposition, "Try the demo", login)
  /login  /register
  /demo                   demo launcher (creates session, choose persona or Director)
Citizen (role=citizen)
  /sos                    home: SOS button, Call 112
  /sos/type               chips + Who needs help
  /sos/questions          3 yes/no questions
  /sos/details            free text + location confirmation (map pin fallback)
  /sos/review             triage preview + Send
  /emergency/:id          live view (status, map, timeline, guidance, cancel)
  /emergency/:id/handover printable packet
  /profile/medical        optional medical profile + consent toggle
Responder (role=responder)
  /r                      dashboard: readiness, offer modal, active assignment
  /r/credentials          credential status and submission
  /r/assignment/:offerId  active assignment (map, protocol, actions)
Ambulance (role=ambulance_operator)
  /a                      unit console: offer, active run, handover form
Authority (role=authority)
  /v                      incident board + verification queue tabs
  /v/incidents/:id        timeline + Explainability view
  /v/responders           directory
  /v/coverage             (stretch)
Demo (DEMO_MODE only)
  /demo/director          split-view of Citizen | Responder | Ambulance | Explainability + scenario controls
```

### 9.3 Key components
`SosButton` (press-and-hold), `ConfirmSheet`, `ChipGrid`, `TriStateQuestion`, `LocationPicker`, `TriagePreviewCard`, `StatusBanner`, `EmergencyMap` (Leaflet, divIcons, fit-bounds), `Timeline`, `ProtocolCard` (offline), `OfferModal` (countdown driven by server `expires_at`), `ExplainabilityPanel` (ranked and rejected lists with score bars), `HandoverView` (print CSS), `CallEmergencyButton`, `OfflineBanner`, `DemoBadge`, `DirectorPanel`.

### 9.4 Data fetching and state
- One `usePolling(key, fetcher, {intervalMs, stopWhen})` hook. Interval 2 s when the emergency is active, 5 s when the tab is hidden, stops on terminal state. Uses `since_seq` to fetch only new events. Exponential backoff on errors with a visible "reconnecting" state.
- Countdown timers render from server `expires_at` minus a server-time offset estimated from the `Date` response header, so the UI cannot drift from the truth.
- No global state library unless needed. React context for auth and the polling cache is enough. Forms are controlled components (no `<form>` submit-reload behaviour).

### 9.5 Offline behaviour
- Protocol JSON and taxonomy are bundled. The `/sos` and protocol screens render offline. If SOS submission fails (no network), the UI shows the offline protocol card and a prominent `tel:` link. Queued retry is a stretch feature. A full PWA service worker is a stretch item and MUST NOT be a demo dependency.

## 10. SECURITY MODEL

### 10.1 Authentication and sessions
- argon2id password hashing (`argon2-cffi`), minimum 10 characters, common-password denylist (small list), constant-time comparison, generic login errors.
- JWT signed with `JWT_SECRET` (min 32 bytes), 12 h expiry, cookie flags `HttpOnly; Secure; SameSite=Strict; Path=/`. Token contains `sub`, `role`, `demo_session_id`, `iat`, `exp`. Role is re-read from the DB on each request (a suspended user loses access immediately).
- Only `citizen` and `responder` self-registration. `authority` and `ambulance_operator` accounts are created by seed or by authority action.

### 10.2 Authorization
- RBAC dependency `require_role(*roles)` on every route (deny by default; a test enumerates all routes and fails if any lacks an auth dependency, except the explicit public list).
- **Object-level authorization** in one module `services/authz.py` (`can_view_emergency`, `can_act_on_offer`, `can_view_medical`, ...). Routers never inline these checks. This prevents IDOR.
- Scope check: a request's user `demo_session_id` MUST equal the target's `demo_session_id`.
- Denials are written to `audit_logs` with `outcome=deny`.

### 10.3 Input validation
- Pydantic v2 strict models with `extra="forbid"`. lat in [-90, 90], lng in [-180, 180], accuracy 0..10000, text lengths capped (description 500, notes 300, reasons enum), enums for all categorical input.
- All SQL via SQLAlchemy bound parameters. No string-built SQL.
- Output encoding: React escapes by default. Never use `dangerouslySetInnerHTML`.

### 10.4 Files and documents
No uploads in MVP. Future design: private object storage, signed short-lived URLs, MIME sniffing, size caps, malware scan, access only for authority.

### 10.5 Abuse and integrity
- Duplicate SOS: partial unique index + idempotency key.
- Prank/abuse: confirm gesture, rate limits, false-alarm flagging, authority review queue (light). Full fraud analytics is out of scope.
- Race conditions: conditional `UPDATE ... WHERE status='OFFERED' AND expires_at > now RETURNING`, partial unique indexes, row lock in `advance()`, optimistic `version`.
- Replay: accept/decline are idempotent per offer id and state (a repeat returns the existing result or `OFFER_ALREADY_HANDLED`).
- Prompt injection: see 5.6.
- Stalking/abuse of the responder role: verified-only, offers only for real active emergencies, coarse location before accept, every exact-location read audited, per-responder read limits.

### 10.6 Transport, headers, secrets
- Same-origin API removes CORS. `vercel.json` sets `Content-Security-Policy` (self + OSM tile host + configured LLM host is never called from the browser), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy: geolocation=(self)`, `X-Frame-Options: DENY`, HSTS (Vercel default).
- Secrets only in environment variables. `.env.example` lists names, never values. A pre-commit or CI secret scan (gitleaks or equivalent) SHOULD run. The agent MUST NOT print secrets in logs or reports.
- Dependency hygiene: pin versions, run `pip-audit` and `npm audit` in the hardening phase, no unused dependencies.

### 10.7 Threat table (must be reflected in tests)
| Threat | Mitigation |
|---|---|
| IDOR on emergencies/offers | central authz + authz matrix tests |
| Fake responder receives location | verification gate x2, coarse location, audit |
| Double SOS or double accept | idempotency, unique indexes, conditional updates |
| Credential forgery | authority-only decision, audit, expiry, suspension |
| LLM manipulation | closed enums, escalate-only, sanitization |
| Brute-force login | audit-log-derived throttling |
| Demo data leaking into real dispatch | scope column + `SCOPE_MISMATCH` + tests |
| Medical data over-exposure | consent flag, per-offer access, audit |

## 11. PRIVACY MODEL

- **Minimisation:** collect only what dispatch needs. Medical profile is optional and off by default for sharing.
- **Location tiers:** (1) before accept, responders see a grid-snapped approximate point (about 250 m) and distance band; (2) after accept, the exact point for the assigned target only; (3) after the emergency reaches a terminal state, target access to exact location ends immediately (only the patient and authority retain access).
- **Medical data:** shared only if `consent_share_medical` was true at SOS time, and only fields flagged in the profile, and only with the accepted responder or ambulance. Every read is audit-logged.
- **Identity exposure:** citizens see responders' first name, category, skills, ETA; never phone or credential numbers. Responders see the patient only as "Patient" plus consented fields. A phone-relay is future scope.
- **Third parties:** the LLM receives sanitized free text only. No identifiers.
- **Retention (documented policy, enforced in future):** exact coordinates coarsened after 30 days, medical snapshots deleted with the profile, audit logs kept 1 year. Demo sessions auto-expire.
- **Logging:** no coordinates, descriptions or medical fields in application logs.
- **Regulatory note:** design follows data-minimisation and purpose-limitation principles compatible with common regimes (for example India's DPDP Act, GDPR). This is engineering guidance, not legal advice; real deployment requires legal review.

## 12. EMERGENCY STATE MACHINE

Because the professional and community tracks run in parallel, the machine is modelled as a **top-level lifecycle plus two track machines**. The top-level status is *derived* by `derive_status()` from the tracks and explicit terminal actions. This avoids a combinatorial state explosion. Every transition is performed by `state_machine.py` (a pure function `transition(state, event) -> state | InvalidTransition`), never by ad-hoc updates. Every transition writes an `emergency_events` row.

### 12.1 Top-level status
`CREATED -> TRIAGED -> DISPATCHING -> IN_PROGRESS -> HANDED_OVER -> COMPLETED`
Alternative terminals: `CANCELLED`, `NO_COVERAGE_CLOSED`.

| From | Event | To | Guard | Actor |
|---|---|---|---|---|
| (none) | create | CREATED | idempotency ok, no active emergency | citizen |
| CREATED | triage_done | TRIAGED | valid TriageResult | system |
| TRIAGED | dispatch_started | DISPATCHING | at least one track started | system |
| DISPATCHING | any_offer_accepted | IN_PROGRESS | at least one offer ACCEPTED | responder/ambulance |
| DISPATCHING | both_tracks_unavailable | NO_COVERAGE | community and professional exhausted | system |
| NO_COVERAGE | retry_dispatch | DISPATCHING | citizen retry or plan recompute | citizen/system |
| IN_PROGRESS | ambulance_handover | HANDED_OVER | ambulance offer ARRIVED and facility set | ambulance |
| IN_PROGRESS | citizen_resolved | COMPLETED | citizen or authority closes, reason recorded | citizen/authority |
| HANDED_OVER | close | COMPLETED | handover_snapshot stored | system/ambulance |
| CREATED/TRIAGED/DISPATCHING/IN_PROGRESS/NO_COVERAGE | cancel | CANCELLED | open offers cancelled | citizen/authority |
| NO_COVERAGE | close_no_coverage | NO_COVERAGE_CLOSED | citizen confirms they called services | citizen |

`NO_COVERAGE` is a *visible non-terminal* state: the UI shows the strongest "Call emergency services" prompt and keeps retrying. Illegal transitions raise `INVALID_STATE_TRANSITION` and are covered by a parametrised test over the full state x event matrix.

### 12.2 Track machines (community and professional)
`NOT_STARTED -> SEARCHING -> OFFERED -> ASSIGNED -> ON_SCENE -> DONE`
Side exits: `SEARCHING/OFFERED -> UNAVAILABLE` (exhausted), `any -> CANCELLED`.
- `OFFERED -> SEARCHING` on decline, expiry, or scene-unsafe (next candidate).
- `ASSIGNED -> SEARCHING` if the assignee aborts before arrival (scene-unsafe or cancel), consuming another candidate.

### 12.3 Offer status machine
`OFFERED -> ACCEPTED -> ARRIVED -> COMPLETED`; `OFFERED -> DECLINED | EXPIRED | CANCELLED`; `ACCEPTED -> CANCELLED` (abort). Terminal: `COMPLETED, DECLINED, EXPIRED, CANCELLED`.

### 12.4 Timeline event types
`EMERGENCY_CREATED, TRIAGE_COMPLETED, TRIAGE_LLM_FALLBACK (internal), DISPATCH_STARTED, OFFER_SENT, OFFER_DECLINED, OFFER_EXPIRED, OFFER_ACCEPTED, OFFER_SKIPPED_RACE (internal), RESPONDER_ARRIVED, AMBULANCE_NOTIFIED, AMBULANCE_ACCEPTED, AMBULANCE_ARRIVED, SCENE_UNSAFE_REPORTED, NO_COVERAGE, ESCALATION_PROMPTED, DUPLICATE_LINKED, HANDOVER_COMPLETED, EMERGENCY_COMPLETED, EMERGENCY_CANCELLED`. Each has `visible_to` roles; the citizen timeline hides internal and other users' sensitive events.

## 13. DEMO MODE ARCHITECTURE

### 13.1 Goals
Deterministic, resettable, safe, runnable by a judge on **one phone** or on a laptop, and safe for many judges at the same time.

### 13.2 Isolation by demo session (tenant scoping)
- `POST /demo/sessions` creates a `demo_sessions` row and clones the persona templates (users, profiles, skills, credentials, ambulance units) with `demo_session_id` set. Emails end in `@demo.lifelink.invalid`. Every read and write is filtered by scope. Real users can never be dispatched to demo emergencies and vice versa (`SCOPE_MISMATCH`, tested).
- Reset = delete rows for the session and reseed, so any number of judges can play in parallel without colliding.
- Demo is enabled only by `DEMO_MODE_ENABLED=true`. Every demo screen shows the `DEMO MODE` pill and a banner: "Simulation. No real responders or ambulances are contacted."
- No real SMS, calls, or push are ever sent from a demo session. Demo sessions do not call an LLM unless `DEMO_DISABLE_LLM=false`.

### 13.3 Determinism
- `Clock` supports an offset per session; the Director can advance time (for example to force an offer to expire) without waiting.
- Scoring ties are deterministic (6.4). Persona locations are fixed offsets from `DEMO_CENTER_LAT/LNG` (set to the venue city).
- Movement is interpolated from the clock (6.8). Nothing depends on a real GPS or routing service.
- The seeded cast (Appendix B) guarantees: Responder A ranks first and declines, Responder B ranks second and accepts, and rejected candidates illustrate each reason code.

### 13.4 Demo Director (`/demo/director`)
Split-screen (stacked on mobile with tabs): Citizen | Responder | Ambulance | Explainability, plus a control bar: [Start scenario] [Next step] [Autoplay] [Advance clock +30 s] [Reset]. "Next step" performs the scripted actor action through the real API (not fakes), so the demo exercises the real code paths. The Explainability tab shows the triage JSON, rules decision and ranked/rejected candidates in judge-friendly language.

### 13.5 Scripted scenario (maps to the 19 required steps)
1. Citizen opens app. 2. Press-and-hold SOS. 3. Confirm sheet. 4. Type chip "Accident/Fall" plus text "A person fell from a bike and is not responding. There is heavy bleeding." 5. Location captured (or pinned). 6. Preview: conditions UNRESPONSIVE, SEVERE_BLEEDING, FALL_OR_COLLISION; P1; protocol PROT_UNRESPONSIVE primary; confidence shown. 7. Send: orchestration runs. 8. Best responder (Asha, nurse) offered with explanation. 9. Asha declines (reason: unavailable). 10. Cascade to Ravi (paramedic). 11. Ravi accepts. 12. Ambulance unit offered in parallel. 13. Ambulance accepts. 14. Map shows patient, responder, ambulance moving (simulated). 15. Timeline updates live. 16. Responder arrives. 17. Ambulance arrives. 18. Handover packet generated. 19. Emergency completed.
Alternate scripted branches (buttons): "All decline -> No coverage", "Offer expires (advance clock)", "Citizen cancels", "Unverified responder blocked".

### 13.6 Safety of demo
- Demo emergencies never appear on real authority boards. The authority console shows a scope switch only when demo mode is enabled.
- The production deployment for real use MUST set `DEMO_MODE_ENABLED=false`, which removes demo routes.

## 14. TEST STRATEGY

**Unit (pytest):** eligibility filters (one test per reason code), scoring (weights sum, monotonicity, deterministic tie-break, "closest is not always best" case), ETA maths, rules engine (each red flag, precedence, fail-safe up, "AI cannot de-escalate" property), state machine (full state x event matrix), sanitizer, authz functions.
**Integration (pytest + real Postgres via docker-compose):** full scenario through the API; idempotent SOS; dedupe; cancel; no-coverage path; handover generation; audit rows created; events monotonic `seq`.
**Concurrency:** N parallel accepts on one offer => exactly one success. Accept racing expiry (`advance`) => consistent outcome. Two parallel polls on an expired offer => exactly one next offer. Same `Idempotency-Key` sent in parallel => one emergency. Responder offered by two emergencies => partial unique index holds.
**Authorization matrix:** parametrised role x endpoint x object-ownership (own, other, none, wrong scope). Includes: unverified responder never offered, coarse vs exact location, medical data consent gate, route enumeration test that every route has an auth dependency.
**Triage golden set:** section 5.7 with CI thresholds and zero unsafe downgrades. LLM adapter tested with a fake provider (timeouts, malformed JSON, injection strings, unknown enum values).
**Frontend (Vitest + Testing Library):** SosButton hold semantics, ChipGrid, countdown from server time, polling backoff, role route guards, offline protocol rendering.
**E2E (Playwright, mobile viewport):** the 19-step scenario via Director "Autoplay" AND once manually through three browser contexts (citizen, responder, ambulance). Failure branches. Reset returns to the exact initial state.
**Accessibility:** axe checks on SOS, review, live emergency, offer modal, handover. Manual keyboard and screen-reader smoke test.
**Performance:** Lighthouse mobile on `/sos` and `/emergency/:id` against the budget in 9.1. API p95 for `POST /emergencies` under 1.5 s on the deployed stack (rules-only).
**Security checks:** `pip-audit`, `npm audit`, secret scan, headers check on the deployed URL.
**Demo rehearsal checklist:** run the scenario 3 times on the deployed URL from a phone on mobile data, and once with the laptop offline using the local docker fallback.

## 15. DEPLOYMENT ARCHITECTURE FOR VERCEL

- **One Vercel project**, monorepo. Static frontend (`apps/web/dist`). FastAPI as a Python serverless function via `api/index.py` (exports `app`). `vercel.json` rewrites `/api/(.*)` to the function and everything else to `index.html` (SPA fallback), and sets security headers.
- **Database:** managed Postgres (Neon or Supabase). Use the *pooled* connection string in serverless, `NullPool` (or a very small pool) in SQLAlchemy, and place the function region near the database region. Migrations run from CI or a manual `alembic upgrade head` against the target DB, never on cold start.
- **Environment variables** (Vercel project settings; separate Preview and Production): `DATABASE_URL`, `JWT_SECRET`, `APP_ENV`, `COOKIE_SECURE`, `DEMO_MODE_ENABLED`, `DEMO_CENTER_LAT`, `DEMO_CENTER_LNG`, `EMERGENCY_NUMBER`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_MS`, `DEMO_DISABLE_LLM`, `OFFER_TTL_S`.
- **Known Vercel constraints and how the design handles them:**
  - No long-lived processes or WebSockets => polling.
  - No reliable sub-minute scheduled jobs => lazy `advance()`.
  - Cold starts of about 1-3 s => keep dependencies small (no numpy, pandas, scikit-learn), lazy-import the LLM SDK, warm the API with a ping before demos.
  - Function bundle size limits => audit `requirements.txt` in Phase 0.
  - Read-only, ephemeral filesystem => no file writes; no uploads.
  - Function duration limits => all endpoints finish in well under 10 s; LLM timeout 4 s.
  - The agent MUST verify current Vercel Python/FastAPI runtime behaviour, limits and `vercel.json` syntax against the official documentation in Phase 0, and MUST NOT rely on memory.
- **Phase 0 gate and contingency:** a "walking skeleton" (React page -> `/api/v1/health` -> Postgres read -> polling) MUST be deployed to Vercel before feature work. If it cannot be made reliable within its time box, keep the frontend on Vercel and deploy the *unchanged* FastAPI app to Render/Railway/Fly (set `VITE_API_BASE_URL`, add CORS allow-list for the frontend origin, switch cookie `SameSite` to `None; Secure` or use a Vercel rewrite proxy). No other architecture change is required.
- **Demo-day fallback:** `docker compose up` runs Postgres + API + web locally with seeded data. A recorded video of the full scenario is kept as a last resort.
- **Observability:** structured JSON logs without PII, request id, `/health`, and an authority-visible "system status" line (DB ok, LLM mode).

## 16. HACKATHON MVP SCOPE

### 16.1 A. Fully functional (real code paths)
Auth and RBAC; citizen SOS flow with press-and-hold, chips, questions, text, location; triage rules engine + protocol library + optional LLM adapter with fake provider tests; orchestration engine with eligibility, scoring, explanations, cascade, timeouts (lazy); parallel ambulance track; offer accept/decline/arrive/complete/scene-unsafe; state machine; events timeline; live map with simulated movement; authority verification queue and incident board with Explainability view; handover packet; demo sessions, Director, autoplay, reset; audit logs; idempotency, dedupe (simple), rate limits; automated tests.

### 16.2 B. Simulated (clearly labelled)
Ambulance service and its GPS; responder movement; SMS/push/phone calls (in-app only); credential documents (metadata only, no files); hospital acceptance; national emergency-service integration; routing ETA.

### 16.3 C. Architecture-ready (documented, not built)
PostGIS spatial index; scheduled worker for timers; push/SMS/phone relay; real document storage and OCR verification; integration with the national dispatch system/CAD; native apps; multi-responder (`responders_needed > 1`); coverage analytics at scale; full i18n; offline queueing.

### 16.4 Cut list (do not build, even if time remains)
Real-time chat, video, payments, native mobile apps, ML-based ranking, response-time prediction models, blockchain/audit chains, social features, gamification/leaderboards, generic analytics dashboards, WebSockets, real routing engines, OCR.

### 16.5 Stretch order (only after Phase 11 is done and verified)
1. Coverage-gap map (grid of eligible-responder counts; about half a day). 2. Offline-friendly PWA shell for protocols. 3. Second language for the citizen SOS flow and protocol cards. 4. Simple incident dedupe UX polish.

## 17. FUTURE SCOPE

Integration with national emergency numbers and CAD systems; certified clinical governance for protocols and a review workflow; multi-responder and AED-location coordination; responder wellbeing and fairness controls at scale; SMS/USSD fallback for feature phones; voice-based SOS in local languages; privacy-preserving phone relay; PostGIS and H3 grid analytics; response-time analytics for public health authorities; formal accessibility audit; penetration test and legal review; multi-tenant region administration.

---

## 18. IMPLEMENTATION ROADMAP

General rules for every phase: work on a feature branch or clearly separated commits; inspect the repo before changing anything; run all existing tests before and after; a phase is done only when its Definition of Done is met and evidenced in `docs/VERIFICATION.md`. Tasks are atomic: complete and verify one before starting the next.

### Phase 0: Walking skeleton and deployment spike
- **Objective:** prove the stack deploys and talks to the database before any feature work.
- **Files/modules:** `apps/web` (scaffold), `api/index.py`, `backend/app/main.py`, `backend/app/core/{config,db}.py`, `vercel.json`, `docker-compose.yml`, `.env.example`, `docs/ADR-001-deployment.md`.
- **Dependencies:** none.
- **Tasks:**
  1. Inspect the repo. Record what exists in `docs/REPO_AUDIT.md`. Preserve anything working.
  2. Scaffold Vite + React + TS + Tailwind (light theme tokens only).
  3. Scaffold FastAPI with `/api/v1/health` returning db status.
  4. Add `docker-compose.yml` with Postgres and a local run script.
  5. Add SQLAlchemy engine configured for serverless (pooled URL, `NullPool`).
  6. Add `api/index.py` entry and `vercel.json` (rewrites, headers). Verify the current Vercel Python/FastAPI docs first.
  7. Deploy to Vercel Preview with a managed Postgres; add a page that polls `/health` every 2 s.
  8. Measure cold start and record it in the ADR. Decide: stay on Vercel or activate the contingency.
- **Acceptance criteria:** deployed URL serves the SPA; `/api/v1/health` returns `db: ok`; polling works; local docker path works.
- **Tests:** health endpoint test; frontend smoke test.
- **Verification:** open the deployed URL on a phone; screenshot; curl `/api/v1/health`.
- **Definition of done:** ADR written with the decision and measured numbers; no secrets in git.

### Phase 1: Domain model, migrations, clock, seeds
- **Objective:** database and core domain primitives.
- **Files/modules:** `backend/app/models/*`, `alembic/versions/*`, `domain/{enums,skills}.py`, `core/clock.py`, `shared/taxonomy.json`, `app/seed.py`.
- **Dependencies:** Phase 0.
- **Tasks:**
  1. Create `shared/taxonomy.json` (emergency types, conditions, skills, levels, protocol->skill map). Do not invent clinical content; structure only.
  2. Implement the 11 tables exactly as section 7, including CHECKs, partial unique indexes, indexes and append-only triggers.
  3. Implement `Clock` (real, offset) and forbid direct `datetime.now()` in domain code via a lint rule or a test.
  4. Write the seed for persona templates (Appendix B).
  5. Write migration up/down tests.
- **Acceptance criteria:** `alembic upgrade head` and `downgrade base` succeed; constraints reject invalid rows.
- **Tests:** constraint tests (double live offer per responder; two live offers per track; one active emergency per patient; event UPDATE/DELETE rejected).
- **Verification:** run migrations on a fresh DB; run the constraint test module.
- **Definition of done:** schema matches spec; seed idempotent.

### Phase 2: Auth, RBAC, authorization, audit, rate limiting
- **Objective:** secure access foundation.
- **Files/modules:** `core/security.py`, `services/{auth,authz,audit}.py`, `api/v1/auth.py`, `schemas/*`.
- **Dependencies:** Phase 1.
- **Tasks:**
  1. Register/login/logout/me with argon2id and cookie JWT.
  2. `require_role` dependency and the route-enumeration test.
  3. Origin/Content-Type check middleware for mutations.
  4. `services/authz.py` skeleton with `can_view_emergency`, `can_act_on_offer`, `can_view_medical`.
  5. Audit writer, login throttle (from audit rows).
  6. Standard error envelope and handlers.
- **Acceptance criteria:** roles enforced; suspended user is denied immediately; throttling works; only citizen/responder self-registration.
- **Tests:** auth unit/integration, throttle, route-enumeration, cookie flag test.
- **Verification:** curl walkthrough recorded in the verification doc.
- **Definition of done:** all tests green; no password or token in logs.

### Phase 3: Protocol library, triage engine, golden set, LLM adapter
- **Objective:** safe classification.
- **Files/modules:** `shared/protocols/*.json`, `triage/{schemas,sanitize,rules,extractor,llm_adapter,eval}.py`, `tests/golden/*`, `api/v1/triage.py`.
- **Dependencies:** Phase 1-2.
- **Tasks:**
  1. Create protocol JSON files with the schema in 5.5 and `status: "demo_unreviewed"`. Leave step text as clearly marked placeholders unless the user has supplied cited text. Do not write clinical instructions.
  2. Implement sanitizer, rule extractor, rules engine (5.4).
  3. Implement `TriageResult` validation.
  4. Implement LLM adapter interface and a fake provider; a real provider only after reading its official docs, gated by env flag.
  5. Build the golden set (at least 40 cases) and the eval script with CI thresholds.
  6. Implement `POST /triage/preview`.
- **Acceptance criteria:** unsafe downgrades = 0; red-flag recall >= 0.95; LLM failure falls back cleanly; injection cases do not change priority.
- **Tests:** unit, golden, adapter fault injection.
- **Verification:** run `python -m app.triage.eval`; attach output.
- **Definition of done:** eval report in `docs/AI_EVAL.md`.

### Phase 4: Orchestration engine (pure logic)
- **Objective:** eligibility, scoring, explanation, ETA.
- **Files/modules:** `orchestration/{eligibility,scoring,explain,eta,engine}.py`.
- **Dependencies:** Phase 1, 3.
- **Tasks:**
  1. Implement haversine, bounding-box prefilter, ETA.
  2. Implement each eligibility reason code (6.3).
  3. Implement scoring (6.4) with configurable weights and deterministic tie-break.
  4. Implement `MatchExplanation` builder with reasons and caveats.
  5. Implement ambulance ranking.
- **Acceptance criteria:** with the Appendix B cast the ranked order is [Asha, Ravi, ...] and the rejected set has the expected reason codes; a closer but less suitable responder ranks below a farther suitable one.
- **Tests:** per-code eligibility tests, scoring property tests, snapshot test for the demo cast.
- **Verification:** run the orchestration test module and print the explanation for the demo case.
- **Definition of done:** engine pure (no I/O beyond passed-in data), 100% deterministic.

### Phase 5: Emergency lifecycle, state machine, offers, lazy advance
- **Objective:** the transactional core.
- **Files/modules:** `domain/state_machine.py`, `services/{emergencies,offers,handover}.py`, `api/v1/{emergencies,offers,inbox}.py`.
- **Dependencies:** Phase 2, 4.
- **Tasks:**
  1. State machine functions and full matrix test.
  2. `create_emergency` (idempotency, dedupe, one-active guard, triage, event, dispatch start).
  3. `advance()` exactly as 6.7.
  4. Offer endpoints (accept, decline, arrive, scene-unsafe, complete, handover) with conditional updates.
  5. Role-scoped `EmergencySnapshot` and event visibility.
  6. Location tiering (coarse before accept).
  7. Handover snapshot builder.
  8. Sim movement calculation from clock.
- **Acceptance criteria:** full scenario passes via API; concurrency guarantees hold; no illegal transitions.
- **Tests:** integration, concurrency suite, authz matrix additions.
- **Verification:** script that runs the 19-step scenario with HTTP calls and prints the timeline.
- **Definition of done:** all backend tests green; audit entries for sensitive reads.

### Phase 6: Frontend foundation and citizen SOS flow
- **Objective:** stress-proof citizen UX.
- **Files/modules:** `apps/web/src/{app,lib,components,features/citizen}`, `strings.ts`, protocol import.
- **Dependencies:** Phase 5 API (or mocked contracts).
- **Tasks:**
  1. Design tokens (light), layout shell, route guards, API client with error envelope, `usePolling`.
  2. Login/register.
  3. SOS home, press-and-hold button, confirm sheet, persistent Call button.
  4. Chips, tri-state questions, details, location picker with fallback.
  5. Review screen with triage preview and Send (Idempotency-Key generated client-side).
  6. Offline protocol card and offline banner.
- **Acceptance criteria:** flow completable in under 20 s by a new user; keyboard and screen-reader operable; works at 360 px width.
- **Tests:** component tests, axe checks, Playwright citizen path.
- **Verification:** screenshots on a real phone; Lighthouse.
- **Definition of done:** budgets met, no console errors.

### Phase 7: Responder and ambulance consoles
- **Objective:** the receiving side of dispatch.
- **Files/modules:** `features/responder`, `features/ambulance`, `OfferModal`.
- **Dependencies:** Phase 5, 6.
- **Tasks:**
  1. Responder dashboard: readiness toggle, inbox polling, offer modal with server-time countdown and volunteer acknowledgement.
  2. Active assignment screen with actions and completion checklist.
  3. Credentials page (metadata submission and status).
  4. Ambulance console: offer, accept with ETA, arrived, handover form.
- **Acceptance criteria:** decline cascades within one poll cycle; accepted responder sees exact location; before accept only coarse.
- **Tests:** component tests, Playwright two-context test.
- **Verification:** manual two-device run.
- **Definition of done:** no unauthorised fields visible in network responses (checked in test).

### Phase 8: Live map, timeline, citizen live view
- **Objective:** demo impact.
- **Files/modules:** `EmergencyMap`, `Timeline`, `features/citizen/LiveEmergency`.
- **Dependencies:** Phase 5-7.
- **Tasks:**
  1. Leaflet map with divIcon markers, fit-bounds, tile failure fallback.
  2. Timeline from events with accessible live updates.
  3. Status banner from derived status and tracks.
  4. Guidance card from the protocol (offline) and NO_COVERAGE prompt.
- **Acceptance criteria:** movement animates smoothly between polls; map survives tile outage.
- **Tests:** component tests, Playwright live path.
- **Verification:** run with network throttling.
- **Definition of done:** performance budget met.

### Phase 9: Authority console, explainability, handover packet UI
- **Objective:** verification, oversight, closed loop.
- **Files/modules:** `features/authority`, `ExplainabilityPanel`, `HandoverView`.
- **Dependencies:** Phase 5.
- **Tasks:**
  1. Verification queue with decision and audit.
  2. Incident board and incident detail with Explainability view (ranked and rejected).
  3. Handover packet page with print styles.
  4. Responder directory.
- **Acceptance criteria:** approving a pending responder makes them eligible on the next orchestration run; a rejected/suspended responder is excluded immediately.
- **Tests:** integration and Playwright verification flow.
- **Verification:** demonstrate unverified-blocked -> verified-eligible.
- **Definition of done:** packet matches the contract in 8.5.

### Phase 10: Demo mode and Director
- **Objective:** deterministic, resettable, multi-judge-safe demo.
- **Files/modules:** `services/demo.py`, `api/v1/demo.py`, `features/demo`, `e2e/demo.spec.ts`.
- **Dependencies:** Phase 5-9.
- **Tasks:**
  1. Session creation with persona cloning and scope enforcement.
  2. Impersonation, reset, clock advance, scenario step and autoplay via real services.
  3. Director UI with controls and Explainability tab.
  4. Failure-branch buttons.
  5. Scope-isolation tests (two concurrent sessions).
- **Acceptance criteria:** autoplay completes all 19 steps; reset restores initial state byte-for-byte on core tables; two sessions do not interfere; demo disabled => 404.
- **Tests:** Playwright full scenario, isolation and reset tests.
- **Verification:** three consecutive autoplay runs on the deployed URL.
- **Definition of done:** rehearsal checklist executed and recorded.

### Phase 11: Hardening, documentation, final verification
- **Objective:** ship-quality prototype.
- **Files/modules:** whole repo, `README.md`, `docs/{ARCHITECTURE,SECURITY,PRIVACY,AI_EVAL,DEMO_SCRIPT,VERIFICATION}.md`.
- **Dependencies:** Phases 0-10.
- **Tasks:**
  1. Run the full test suite, fix root causes (never hide errors).
  2. `pip-audit`, `npm audit`, secret scan, headers check.
  3. Accessibility pass and Lighthouse pass.
  4. Remove unused dependencies and dead code.
  5. Write README with 60-second judge quickstart, architecture diagram, limitations, and the "not a medical device / not a replacement for emergency services" statement.
  6. Produce `docs/VERIFICATION.md` with evidence for every phase.
- **Acceptance criteria:** all suites green; budgets met; zero high-severity audit findings unaddressed.
- **Tests:** everything.
- **Verification:** clean clone -> `docker compose up` -> scenario passes; production URL scenario passes.
- **Definition of done:** verification report complete and honest about known limitations.

### Phase 12: Stretch (strict order, each only if Phase 11 is complete)
12a Coverage-gap map. 12b PWA shell for offline protocols. 12c Second language. 12d Dedupe UX polish. Each requires its own acceptance criteria and tests, and MUST NOT put the Phase 10 demo at risk.

---

## APPENDIX A: JUDGE REVIEW AND DECISIONS LOG

### A.1 Scorecard (original concept vs this specification)
| Criterion | Original | This spec | Note |
|---|---|---|---|
| Innovation | 6 | 8 | Positioning as an explainable, safety-gated coordination layer |
| Technical complexity | 8 | 8 | Same depth, but real (locks, constraints, lazy timers) |
| AI depth | 5 | 7 | Guardrailed hybrid + golden-set evaluation |
| Real-world usefulness | 7 | 7 | Bridge-the-gap + handover |
| UX under stress | 6 | 8 | Hold-to-send, three questions, one primary action |
| Safety | 7 | 9 | Escalate-only AI, verified gates x2, coarse location |
| Feasibility | 4 | 8 | Cut list, merged tables, polling |
| Demo impact | 7 | 9 | Director, explainability, deterministic |
| Scalability (architectural) | 5 | 7 | Documented path, honest limits |
| Judging potential | 6 | 8 | |

### A.2 Feature classification
| # | Feature | Class | Reason |
|---|---|---|---|
| 1 | Response Orchestration Engine | MUST | The core |
| 2 | Explainable matching | MUST | Cheap and the most convincing demo moment |
| 3 | Cascading dispatch | MUST | Demo steps 9-10; shows real distributed-systems thinking |
| 4 | Incident deduplication | SHOULD | Simple rule only; no clustering |
| 5 | Handover packet | MUST | Closes the loop, unique |
| 6 | Coverage map | NICE | Stretch, first to cut |
| 7 | Responder readiness states | MUST | Feeds eligibility |
| 8 | Skill taxonomy | MUST | Needed for skill compatibility |
| 9 | Protocol library | MUST | Safety requirement |
| 10 | Parallel community + professional | MUST | The USP |
| 11 | Emergency analytics | REMOVE | Replace with four metrics on the handover packet |
| 12 | Abuse/fraud monitoring | REMOVE (as a feature) | Keep rate limits, audit log, false-alarm flag only |
| 13 | Offline-first guidance | SHOULD (light) | Bundled protocols; full PWA is stretch |
| 14 | Multilingual | NICE | Stretch; keep strings i18n-ready |
| 15 | Demo mode | MUST | Reliability of judging |

### A.3 Weak points and dangerous assumptions found
- The original concept implied WebSockets and background timers. Neither exists reliably on Vercel serverless, so cascading timeouts would silently fail. Changed to lazy `advance()` + polling.
- "Unverified responder never dispatched" was only a policy. Now enforced twice, including at the DB transaction level.
- Location and medical exposure: exact patient location to every candidate is a stalking vector. Changed to coarse-until-accept.
- AI could theoretically downgrade urgency. Forbidden by the escalate-only rule.
- A global "reset" demo would break with several judges at once. Changed to per-session scoped demo tenants.
- Document upload, OCR, real push/SMS, real routing, PostGIS, WebSockets are big time sinks with little demo value. Removed or deferred.
- Legal/ethical exposure of volunteers entering unsafe scenes: added volunteer acknowledgement and a "scene unsafe / abort" action.
- Missing features that materially help: always-available call-emergency-services control, "someone else" reporting, false-alarm cancel, no-coverage fallback, scene-unsafe abort, per-session demo isolation.

### A.4 Architecture challenge (what changed after self-review)
1. WebSockets/cron replaced by lazy deterministic evaluation.
2. Three dispatch tables merged into one polymorphic offers table with DB-level race protection.
3. PostGIS deferred; Haversine is enough for a prototype and removes an extension risk.
4. LLM made optional; rules are the source of truth; AI can only add signals.
5. One linear state machine replaced by lifecycle + two track machines to represent parallel response without state explosion.
6. Server-simulated movement instead of GPS/routing APIs, making the demo deterministic.
7. Protocols and taxonomy moved to shared JSON so offline guidance and server rules cannot drift.
8. FastAPI kept (Python depth, testability) but gated by a Phase 0 spike with a pre-planned Render/Railway/Fly contingency. A full-TypeScript Next.js stack was considered and rejected only because the team prefers Python and the risk is contained by the spike.
9. In-memory rate limiting rejected (useless on serverless); DB-derived limits used instead.

## APPENDIX B: SEEDED DEMO CAST (per demo session)

Locations are offsets from `DEMO_CENTER` (set to the venue city). Patient starts at the center. Distances are straight-line and approximate.

| Persona | Role/category | Skills (level) | State | Approx. distance | Expected outcome |
|---|---|---|---|---|---|
| Asha (nurse) | responder / nurse | bleeding_control 3, trauma_response 3, basic_first_aid 3, cpr_aed 3 | available, verified, radius 3 km | 0.8 km | Ranked #1, **declines** |
| Ravi (paramedic) | responder / paramedic | advanced_life_support 3, trauma_response 3, bleeding_control 3, cpr_aed 3 | available, verified, radius 5 km | 1.3 km | Ranked #2, **accepts** |
| Meera (certified first aider) | responder / certified_first_aider | basic_first_aid 2, cpr_aed 2, bleeding_control 2 | available, verified, radius 3 km | 2.1 km | Ranked #3 (backup) |
| Karan (student) | responder / student_responder | cpr_aed 1 | available, verified, radius 2 km | 0.3 km | Rejected: `SKILL_MISMATCH` (closest, but unsuitable) |
| Dr. Iyer | responder / doctor | advanced_life_support 3, trauma_response 3 | busy on assignment | 0.6 km | Rejected: `NOT_AVAILABLE` / `ACTIVE_ASSIGNMENT` |
| Sana (EMT) | responder / emt | trauma_response 2, bleeding_control 2 | available, verified, radius 3 km | 4.5 km | Rejected: `OUTSIDE_SERVICE_RADIUS` |
| Vik (volunteer) | responder / medical_volunteer | basic_first_aid 2 | off_duty | 1.0 km | Rejected: `NOT_AVAILABLE` |
| Nita (nurse) | responder / nurse | bleeding_control 3 | credential **expired** | 0.9 km | Rejected: `NOT_VERIFIED` |
| Omar (paramedic) | responder / paramedic | trauma_response 3 | credential **pending** | 0.7 km | Rejected: `NOT_VERIFIED`; approvable live by the authority persona to demonstrate the gate |
| Amb-1 | ambulance unit / advanced | | available | 2.4 km | Offered, **accepts** |
| Amb-2 | ambulance unit / basic | | available | 3.9 km | Backup |
| Amb-3 | ambulance unit | | busy | 1.1 km | Rejected: `UNIT_NOT_AVAILABLE` |
| Citizen Demo | citizen | | medical profile with consent on | 0 km | Patient/reporter |
| Authority Demo | authority | | | | Verification and explainability |
| Ambulance Operator Demo | ambulance_operator | | | | Console |

Facilities (static JSON): four fictional facilities at fixed offsets from `DEMO_CENTER` (for example "Demo City Hospital"), never real institution names.
