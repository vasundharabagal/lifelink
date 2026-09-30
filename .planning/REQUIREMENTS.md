# Requirements: LIFELINK

**Defined:** 2026-09-30  
**Core Value:** The explainable, safety-gated coordination layer that runs beside official emergency services and turns verified nearby people into an accountable first-response network, delivering immediate community first-aid guidance and deterministic dual-track response within strict safety boundaries.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure & Deployment (`INFRA`)

- [x] **INFRA-01**: Developer can deploy Vite React frontend and FastAPI backend walking skeleton to Vercel serving `/api/v1/health`
- [x] **INFRA-02**: System connects to managed PostgreSQL with `NullPool` serverless configuration and supports local Docker Compose fallback
- [x] **INFRA-03**: Deployed client page successfully polls `/api/v1/health` every 2 s and records cold-start benchmarks in `docs/ADR-001-deployment.md`

### Domain Model & Data Primitives (`DATA`)

- [ ] **DATA-01**: Database enforces 11 relational tables matching spec Section 7 via Alembic migrations
- [ ] **DATA-02**: Database enforces partial unique indexes preventing multiple active offers per responder, per track, and active emergencies per patient
- [ ] **DATA-03**: Database enforces append-only protection on `emergency_events` and `audit_logs` rejecting UPDATE and DELETE queries
- [ ] **DATA-04**: Domain logic uses injectable `Clock` supporting test offsets and forbids direct `datetime.now()` calls
- [ ] **DATA-05**: Seed script idempotently provisions taxonomy from `shared/taxonomy.json` and demo persona templates (Appendix B)

### Authentication, Authorization & Security (`AUTH`)

- [ ] **AUTH-01**: Citizen and responder users can register with email and password hashed using argon2id
- [ ] **AUTH-02**: Users can authenticate via email/password receiving an httpOnly SameSite=Strict cookie JWT (`ll_session`)
- [ ] **AUTH-03**: System enforces role-based access control (`require_role`) across all non-public endpoints with automated route enumeration testing
- [ ] **AUTH-04**: Centralized object-level authorization (`services/authz.py`) strictly enforces ownership, incident access, and tenant scope isolation
- [ ] **AUTH-05**: System records immutable audit logs for logins, verification decisions, and non-patient reads of exact location or medical data
- [ ] **AUTH-06**: System enforces rate limiting on login attempts and SOS creation calculated from database audit history

### Triage & Clinical Protocols (`TRIAGE`)

- [ ] **TRIAGE-01**: System bundles pre-reviewed first-aid protocol JSONs in `shared/protocols/*.json` with clinical citations and explicit unreviewed demo disclaimers
- [ ] **TRIAGE-02**: Deterministic rules engine classifies priority (P1/P2/P3), ambulance requirement, protocol ID, and required skill levels from structured inputs
- [ ] **TRIAGE-03**: Triage rules engine enforces precedence (`UNRESPONSIVE`/`NOT_BREATHING` > `CHOKING` > `SEVERE_BLEEDING` > `SEIZURE` > `FALL` > `BURNS` > `GENERAL`) and fail-safe upward escalation
- [ ] **TRIAGE-04**: Optional Tier 2 LLM extractor maps free text to closed enums with a 4 s timeout and strict escalate-only invariant
- [ ] **TRIAGE-05**: Automated evaluation script runs 40+ golden triage cases in CI, enforcing >=0.95 red-flag recall and zero unsafe downgrades

### Response Orchestration Engine (`ORCH`)

- [ ] **ORCH-01**: Orchestration engine applies hard eligibility filters rejecting candidates for verification, status, skills, radius, scope, or active assignments
- [ ] **ORCH-02**: Orchestration engine calculates 0-100 multi-factor scores (skills 30, ETA 30, fairness 15, reliability 10, tier 10, headroom 5) with deterministic tie-breaking
- [ ] **ORCH-03**: Orchestration engine generates full `MatchExplanation` containing score breakdowns for ranked candidates and reason codes for rejected ones
- [ ] **ORCH-04**: Ambulance ranking orders available units by ETA, unit suitability, and fairness independently of volunteer scoring

### Emergency Lifecycle & Dual-Track Dispatch (`CORE`)

- [ ] **CORE-01**: Citizen can create emergency with `Idempotency-Key` initiating parallel community volunteer and professional ambulance tracks
- [ ] **CORE-02**: System deduplicates near-simultaneous reports within 150 m and 10 minutes, returning `409 POSSIBLE_DUPLICATE` with linking options
- [ ] **CORE-03**: Lazy deterministic evaluation (`advance(emergency_id)`) advances expired offers and updates composite state machines under row locks during client polling
- [ ] **CORE-04**: Assigned candidate can accept, decline (with reason), report scene arrival, or complete assignment with quick action checklist
- [ ] **CORE-05**: Declining, timing out (`OFFER_TTL_S`), or aborting an offer cascades dispatch to the next eligible candidate in the dispatch plan
- [ ] **CORE-06**: Citizen or authority can cancel active emergency or resolve incident, safely closing open offers and updating track states
- [ ] **CORE-07**: Location privacy tiers ensure candidates receive coarse coordinates (~250 m) before accept, exact coordinates only upon accept, and immediate revocation at close

### Citizen SOS Interface (`CITIZEN`)

- [ ] **CITIZEN-01**: Citizen can trigger SOS via 1.5 s press-and-hold button with confirmation sheet and 10 s auto-cancel
- [ ] **CITIZEN-02**: Citizen can access a persistent "Call 112" non-network emergency control working offline via `tel:` URI from any screen
- [ ] **CITIZEN-03**: Citizen can select quick-type chips, answer 3 yes/no triage questions, provide optional text, and set location via GPS or map pin
- [ ] **CITIZEN-04**: Citizen can review triage classification card and send emergency request without redundant confirmation
- [ ] **CITIZEN-05**: Citizen can view bundled protocol guidance cards and offline status banner when disconnected from network

### Responder & Ambulance Consoles (`RESPONDER`)

- [ ] **RESPONDER-01**: Responder can view profile, submitted credentials, and toggle readiness between `available` and `off_duty`
- [ ] **RESPONDER-02**: Responder receives full-screen incoming offer modal with server-synchronized countdown and mandatory volunteer safety acknowledgment
- [ ] **RESPONDER-03**: Responder can accept or decline offer, view exact patient location upon accept, open `geo:` navigation, and execute arrival/completion actions
- [ ] **RESPONDER-04**: Responder can report scene-unsafe condition, cancelling assignment and triggering automated dispatch cascade
- [ ] **RESPONDER-05**: Simulated ambulance operator console displays unit offers, allows ETA input, tracks status, and finalizes facility handover

### Live Emergency Tracking & Map (`MAP`)

- [ ] **MAP-01**: Citizen live emergency screen renders responsive Leaflet map with custom divIcon markers for patient, responder, and ambulance
- [ ] **MAP-02**: Map smoothly interpolates responder and ambulance positions server-side based on travel speed and elapsed Clock time
- [ ] **MAP-03**: Citizen live view displays accessible chronological timeline populated from role-scoped `emergency_events`
- [ ] **MAP-04**: Citizen view displays prominent `NO_COVERAGE` fallback banner and emergency service escalation prompt if all tracks exhaust candidates

### Authority Oversight & Closed Loop Handover (`AUTHORITY`)

- [ ] **AUTHORITY-01**: Authority user can inspect pending responder credentials and submit verify, reject, or suspend decisions with audit logging
- [ ] **AUTHORITY-02**: Authority user can monitor live incident board with real-time status and access full `MatchExplanation` view for every dispatch
- [ ] **AUTHORITY-03**: System deterministically compiles tamper-evident `HandoverPacket` from timeline events upon ambulance facility handover
- [ ] **AUTHORITY-04**: Handover packet renders as a browser-printable, clean emergency medical report (print to PDF)

### Multi-Tenant Demo Mode & Director (`DEMO`)

- [ ] **DEMO-01**: System creates isolated demo sessions (`POST /demo/sessions`) cloning seeded personas with tenant-scoped `demo_session_id`
- [ ] **DEMO-02**: Demo Director panel (`/demo/director`) renders responsive split-view across Citizen, Responder, Ambulance, and Explainability tabs
- [ ] **DEMO-03**: Demo Director allows manual single-step advancement, autoplay scenario execution, and arbitrary Clock offset advancement
- [ ] **DEMO-04**: Scripted 19-step scenario runs end-to-end through real API endpoints demonstrating Asha decline, Ravi accept, ambulance handover, and packet generation
- [ ] **DEMO-05**: Demo Director provides idempotent reset button restoring initial session data state without affecting other concurrent demo sessions
- [ ] **DEMO-06**: Production builds enforce `DEMO_MODE_ENABLED=false`, returning 404 for all demo routes and hiding demo UI indicators

### Hardening, Testing & Quality Gates (`HARDEN`)

- [ ] **HARDEN-01**: Pytest suite validates concurrency safety: parallel offer accepts, race against expiry, and duplicate idempotency keys
- [ ] **HARDEN-02**: Authorization test matrix validates role restrictions, coarse location tiering, and medical consent gating across all routes
- [ ] **HARDEN-03**: Playwright test suite automates the 19-step scenario and failure branches in a mobile viewport
- [ ] **HARDEN-04**: Security and accessibility audits confirm `pip-audit`/`npm audit` zero high findings, WCAG AA contrast, and axe compliance
- [ ] **HARDEN-05**: Project produces comprehensive `docs/VERIFICATION.md` documenting evidence and test artifacts across all roadmap phases

## v2 Requirements

Deferred to future release. Tracked but not in current MVP roadmap.

### Stretch Features (Phase 12)

- **STRETCH-01**: Authority coverage-gap map visualizing eligible responder density grid cells
- **STRETCH-02**: Full offline PWA service worker shell for client caching
- **STRETCH-03**: Multilingual support for Hindi/Marathi translations in citizen SOS and protocol guidance
- **STRETCH-04**: Incident deduplication UI polish with interactive incident merge dialog

### Future Vision

- **FUTURE-01**: Direct integration with national CAD emergency dispatch systems
- **FUTURE-02**: Push notifications, SMS gateway, and privacy-preserving telephone relay
- **FUTURE-03**: Native mobile applications and multi-responder coordination (`responders_needed > 1`)
- **FUTURE-04**: Certified clinical governance review workflows and PostGIS/H3 spatial analytics

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Replacing official emergency services or doctors | Non-negotiable safety constraint: LIFELINK is strictly a coordination layer |
| AI medical diagnosis or AI-generated treatment text | Hallucination liability; all first-aid guidance comes from pre-reviewed protocols |
| File uploads or OCR document processing | High security/infrastructure overhead; credentials are typed metadata records in MVP |
| WebSockets, Server-Sent Events, or background cron | Unreliable on serverless Vercel function instances; replaced by HTTP polling and lazy evaluation |
| Full PostGIS database extensions | Extension dependency risks on managed databases; Haversine and SQL bounding box suffice |
| Real-time routing engines or turn-by-turn navigation | Unnecessary API cost/complexity; approximate ETA calculated mathematically; navigation opens `geo:` URI |
| Citizen-responder direct chat or video calling | High distraction risk for volunteer en route; harassment vector; action checklists used instead |
| In-app payments, social leaderboards, or gamification | Inappropriate for emergency response; undermines serious volunteer accountability |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 0 | Complete |
| INFRA-02 | Phase 0 | Complete |
| INFRA-03 | Phase 0 | Complete |
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| AUTH-06 | Phase 2 | Pending |
| TRIAGE-01 | Phase 3 | Pending |
| TRIAGE-02 | Phase 3 | Pending |
| TRIAGE-03 | Phase 3 | Pending |
| TRIAGE-04 | Phase 3 | Pending |
| TRIAGE-05 | Phase 3 | Pending |
| ORCH-01 | Phase 4 | Pending |
| ORCH-02 | Phase 4 | Pending |
| ORCH-03 | Phase 4 | Pending |
| ORCH-04 | Phase 4 | Pending |
| CORE-01 | Phase 5 | Pending |
| CORE-02 | Phase 5 | Pending |
| CORE-03 | Phase 5 | Pending |
| CORE-04 | Phase 5 | Pending |
| CORE-05 | Phase 5 | Pending |
| CORE-06 | Phase 5 | Pending |
| CORE-07 | Phase 5 | Pending |
| CITIZEN-01 | Phase 6 | Pending |
| CITIZEN-02 | Phase 6 | Pending |
| CITIZEN-03 | Phase 6 | Pending |
| CITIZEN-04 | Phase 6 | Pending |
| CITIZEN-05 | Phase 6 | Pending |
| RESPONDER-01 | Phase 7 | Pending |
| RESPONDER-02 | Phase 7 | Pending |
| RESPONDER-03 | Phase 7 | Pending |
| RESPONDER-04 | Phase 7 | Pending |
| RESPONDER-05 | Phase 7 | Pending |
| MAP-01 | Phase 8 | Pending |
| MAP-02 | Phase 8 | Pending |
| MAP-03 | Phase 8 | Pending |
| MAP-04 | Phase 8 | Pending |
| AUTHORITY-01 | Phase 9 | Pending |
| AUTHORITY-02 | Phase 9 | Pending |
| AUTHORITY-03 | Phase 9 | Pending |
| AUTHORITY-04 | Phase 9 | Pending |
| DEMO-01 | Phase 10 | Pending |
| DEMO-02 | Phase 10 | Pending |
| DEMO-03 | Phase 10 | Pending |
| DEMO-04 | Phase 10 | Pending |
| DEMO-05 | Phase 10 | Pending |
| DEMO-06 | Phase 10 | Pending |
| HARDEN-01 | Phase 11 | Pending |
| HARDEN-02 | Phase 11 | Pending |
| HARDEN-03 | Phase 11 | Pending |
| HARDEN-04 | Phase 11 | Pending |
| HARDEN-05 | Phase 11 | Pending |

**Coverage:**

- v1 requirements: 56 total
- Mapped to phases: 56
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-30*  
*Last updated: 2026-09-30 after initial definition*
