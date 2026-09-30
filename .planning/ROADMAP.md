# Roadmap: LIFELINK

## Overview

LIFELINK is implemented in 12 sequential, verifiable phases matching Section 18 of `docs/LIFELINK_MASTER_SPEC.md`. Beginning with a deployment spike to validate the serverless architecture on Vercel, the roadmap builds the secure data layer, deterministic triage and orchestration engines, dual-track transactional core, citizen and responder consoles, live Leaflet tracking, authority oversight, multi-tenant demo Director, and final security hardening. Every requirement maps to exactly one phase with observable success criteria.

## Phases

**Phase Numbering:**

- Integer phases (0 to 11): Canonical implementation phases from specification
- Decimal phases: Urgent insertions (if needed)

- [x] **Phase 0: Walking skeleton and deployment spike** - Prove stack deploys and talks to DB on Vercel before feature work (completed 2026-09-30)
- [x] **Phase 1: Domain model, migrations, clock, seeds** - Implement 11 database tables, constraints, Clock, and persona seeds (completed 2026-10-01)
- [ ] **Phase 2: Auth, RBAC, authorization, audit, rate limiting** - Secure access foundation, session cookies, central authz, and audit logs
- [ ] **Phase 3: Protocol library, triage engine, golden set, LLM adapter** - Safe deterministic triage rules, protocol library, and golden CI eval
- [ ] **Phase 4: Orchestration engine (pure logic)** - Hard eligibility filters, 0-100 scoring, explainability, and ambulance ranking
- [ ] **Phase 5: Emergency lifecycle, state machine, offers, lazy advance** - Transactional core, dual-track machine, offer mutations, and lazy advance
- [ ] **Phase 6: Frontend foundation and citizen SOS flow** - Accessible light-theme citizen SOS flow with offline protocol cards
- [ ] **Phase 7: Responder and ambulance consoles** - Volunteer readiness, offer modal with countdown, active assignment, and ambulance console
- [ ] **Phase 8: Live map, timeline, citizen live view** - Leaflet map with simulated movement, live event timeline, and NO_COVERAGE fallback
- [ ] **Phase 9: Authority console, explainability, handover packet UI** - Credential verification queue, live board, and printable handover packet
- [ ] **Phase 10: Demo mode and Director** - Multi-tenant demo sessions, Director split-view, and 19-step scenario runner
- [ ] **Phase 11: Hardening, documentation, final verification** - Full test suite, security audits, README quickstart, and verification report

## Phase Details

### Phase 0: Walking skeleton and deployment spike

**Goal:** Prove the stack deploys and talks to the database before any feature work
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):

1. Deployed Vercel URL serves the React SPA and `/api/v1/health` returns `{ "status": "ok", "db": "ok" }`
2. Client page successfully polls `/api/v1/health` every 2 s with automatic reconnection on network recovery
3. Local development path runs via `docker-compose.yml` against PostgreSQL with measured cold starts documented in `docs/ADR-001-deployment.md`

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 00-01: Scaffold Vite React frontend, FastAPI backend, and local Docker Compose PostgreSQL

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 00-02: Configure Vercel serverless deployment, routing rewrites, and database pooling

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 00-03: Validate health polling, measure cold starts, and document ADR-001 deployment decision

### Phase 1: Domain model, migrations, clock, seeds

**Goal:** Implement database schema, safety constraints, injectable clock, and persona seeds
**Mode:** mvp
**Depends on:** Phase 0
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):

1. Alembic migrations run cleanly up and down across the 11 relational tables matching spec Section 7
2. Database rejects duplicate live offers for the same responder, multiple live offers per track, and multiple active emergencies per patient
3. Triggers reject UPDATE and DELETE queries on `emergency_events` and `audit_logs`
4. Injectable `Clock` abstraction permits simulated offset advancement while direct `datetime.now()` is forbidden in domain code
5. `app/seed.py` idempotently seeds `shared/taxonomy.json` and the Appendix B persona cast

**Plans:** 3/3 plans complete

Plans:

**Wave 1**

- [x] 01-01: Define taxonomy JSON and SQLAlchemy models for all 11 tables with constraints and triggers

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02: Create Alembic migrations and verify migration up/down constraint validation tests

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03: Implement Clock abstraction and idempotent seed script for demo personas and taxonomy

### Phase 2: Auth, RBAC, authorization, audit, rate limiting

**Goal:** Establish secure access control, session handling, central authorization, and audit logging
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):

1. Users can register (citizen and responder only) and authenticate with argon2id and httpOnly SameSite=Strict cookie JWT
2. All non-public endpoints require valid role tokens verified by route enumeration tests
3. Central `services/authz.py` strictly prevents IDOR and cross-session data access
4. Every sensitive data access, login attempt, and verification action writes an immutable record to `audit_logs`
5. Database-derived rate limiting blocks brute-force authentication and rapid false-alarm SOS creation

**Plans:** 3 plans

Plans:

- [ ] 02-01: Security Core, Password Hashing, JWT Sessions, and Auth Endpoints
- [ ] 02-02: RBAC, Centralized Object Authorization, and Route Enumeration
- [ ] 02-03: Security Audit Pipeline and DB-Derived Rate Limiting

### Phase 3: Protocol library, triage engine, golden set, LLM adapter

**Goal:** Deliver safe, deterministic triage classification and pre-reviewed protocol guidance
**Mode:** mvp
**Depends on:** Phase 1, Phase 2
**Requirements:** TRIAGE-01, TRIAGE-02, TRIAGE-03, TRIAGE-04, TRIAGE-05
**Success Criteria** (what must be TRUE):

1. Pre-reviewed protocol JSON library loads from `shared/protocols/*.json` with citations and unreviewed demo disclaimers
2. Triage rules engine deterministically assigns priority (P1/P2/P3), ambulance requirement, protocol ID, and required skills
3. Red-flag conditions trigger immediate P1 escalation with fail-safe upward handling for low confidence
4. Optional LLM extractor validates against closed enums, times out cleanly at 4 s, and respects the escalate-only invariant
5. Golden test suite of 40+ cases passes in CI with >=0.95 red-flag recall and 0 unsafe downgrades

**Plans:** TBD

Plans:

- [ ] 03-01: Author protocol JSON library, input sanitizer, and deterministic table-driven rules engine
- [ ] 03-02: Implement optional Tier 2 LLM extractor with closed-enum parsing and prompt injection defense
- [ ] 03-03: Create 40+ case golden triage evaluation suite and verify zero-downgrade CI test gates

### Phase 4: Orchestration engine (pure logic)

**Goal:** Implement pure matching logic: eligibility filtering, multi-factor scoring, and explainability
**Mode:** mvp
**Depends on:** Phase 1, Phase 3
**Requirements:** ORCH-01, ORCH-02, ORCH-03, ORCH-04
**Success Criteria** (what must be TRUE):

1. Hard eligibility filters reject unverified, busy, expired, out-of-radius, or skill-mismatched candidates with machine-readable reason codes
2. Multi-factor scoring (0-100) deterministically ranks eligible candidates with tested tie-breaking
3. Closer but unqualified responders (e.g. Karan) rank below farther qualified responders (Asha, Ravi)
4. Full `MatchExplanation` object accurately reflects score breakdowns for ranked candidates and rejection reasons for disqualified ones
5. Independent ambulance ranking evaluates unit type, ETA, and fairness

**Plans:** TBD

Plans:

- [ ] 04-01: Implement Haversine distance, bounding box prefilter, and hard eligibility filters
- [ ] 04-02: Implement multi-factor candidate scoring and deterministic tie-breaking algorithms
- [ ] 04-03: Implement MatchExplanation builder and independent ambulance ranking logic

### Phase 5: Emergency lifecycle, state machine, offers, lazy advance

**Goal:** Build the transactional core: dual-track state machine, atomic offer handling, and lazy evaluation
**Mode:** mvp
**Depends on:** Phase 2, Phase 4
**Requirements:** CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07
**Success Criteria** (what must be TRUE):

1. `POST /emergencies` creates an emergency with `Idempotency-Key` and initiates independent community and ambulance tracks
2. Client polling triggers `advance(emergency_id)` under row lock to expire overdue offers and cascade dispatch
3. Offer actions (accept, decline, arrive, scene-unsafe, complete) execute conditionally with atomic concurrency guarantees
4. Decline, timeout (`OFFER_TTL_S`), or scene-unsafe abort immediately cascades to candidate #2
5. Location privacy tiers provide coarse coordinates (~250 m) before accept and exact coordinates only upon accept

**Plans:** TBD

Plans:

- [ ] 05-01: Implement composite state machine and emergency creation with idempotency and deduplication
- [ ] 05-02: Implement lazy deterministic `advance()` evaluation under PostgreSQL row locks
- [ ] 05-03: Implement offer lifecycle endpoints, location privacy tiering, and simulated movement

### Phase 6: Frontend foundation and citizen SOS flow

**Goal:** Deliver stress-proof, accessible citizen SOS interface with offline protocol guidance
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** CITIZEN-01, CITIZEN-02, CITIZEN-03, CITIZEN-04, CITIZEN-05
**Success Criteria** (what must be TRUE):

1. Citizen can trigger emergency via 1.5 s press-and-hold button with confirmation sheet in under 20 seconds
2. "Call 112" non-network emergency button remains permanently visible and functional offline
3. Quick-type chips, 3 yes/no questions, optional text, and location picker submit reliably to preview card
4. Review card displays triage preview and submits emergency request with client-generated idempotency key
5. Offline banner and protocol guidance cards render seamlessly when device network is disconnected

**Plans:** TBD

Plans:

- [ ] 06-01: Build light-theme design system, layout shell, auth screens, and API polling client
- [ ] 06-02: Implement press-and-hold SosButton, persistent Call 112 control, and triage question steps
- [ ] 06-03: Build review preview card, submission handler, and offline protocol guidance viewer

### Phase 7: Responder and ambulance consoles

**Goal:** Implement the receiving side of dispatch: volunteer workflows and ambulance operator console
**Mode:** mvp
**Depends on:** Phase 5, Phase 6
**Requirements:** RESPONDER-01, RESPONDER-02, RESPONDER-03, RESPONDER-04, RESPONDER-05
**Success Criteria** (what must be TRUE):

1. Responder dashboard displays readiness toggle (`available`/`off_duty`) and polls inbox every 3 s
2. Incoming offer modal renders full-screen alert with server-synced countdown and volunteer safety acknowledgment
3. Accepting an offer reveals exact location, protocol guidance, navigation deep link, and action checklist
4. Reporting "Scene unsafe / abort" closes assignment and triggers immediate automated cascade
5. Simulated ambulance console accepts dispatch offers with ETA, tracks en route status, and provides handover form

**Plans:** TBD

Plans:

- [ ] 07-01: Build responder dashboard, readiness switch, and credential submission form
- [ ] 07-02: Implement incoming offer modal with server-time countdown and active assignment actions
- [ ] 07-03: Build simulated ambulance console for offer acceptance, ETA updates, and handover form

### Phase 8: Live map, timeline, citizen live view

**Goal:** Provide real-time spatial awareness and chronological tracking for citizens and judges
**Mode:** mvp
**Depends on:** Phase 5, Phase 6, Phase 7
**Requirements:** MAP-01, MAP-02, MAP-03, MAP-04
**Success Criteria** (what must be TRUE):

1. Live emergency view renders Leaflet map with custom divIcon markers for patient, responder, and ambulance
2. Responder and ambulance markers smoothly interpolate travel positions based on server Clock and elapsed travel time
3. Chronological timeline displays role-scoped events with accessible live announcement (`aria-live`)
4. System displays prominent `NO_COVERAGE` prompt with direct emergency call link if all responders decline or expire

**Plans:** TBD

Plans:

- [ ] 08-01: Implement Leaflet map component with custom markers, bounds fitting, and tile fallbacks
- [ ] 08-02: Build server-simulated movement animation and position interpolation hook
- [ ] 08-03: Build accessible live timeline component and NO_COVERAGE escalation view

### Phase 9: Authority console, explainability, handover packet UI

**Goal:** Implement oversight, credential verification, and closed-loop medical handover packets
**Mode:** mvp
**Depends on:** Phase 5, Phase 7
**Requirements:** AUTHORITY-01, AUTHORITY-02, AUTHORITY-03, AUTHORITY-04
**Success Criteria** (what must be TRUE):

1. Authority console provides verification queue where verifying/rejecting credentials immediately updates eligibility
2. Live incident board allows authorities to inspect full `MatchExplanation` (ranked vs rejected candidates)
3. Ambulance handover completion deterministically generates immutable `HandoverPacket` from event history
4. Handover packet renders as a browser-printable, clean clinical emergency report (print to PDF)

**Plans:** TBD

Plans:

- [ ] 09-01: Build authority credential verification queue and live incident oversight board
- [ ] 09-02: Implement ExplainabilityPanel displaying score breakdowns and rejection reason codes
- [ ] 09-03: Build HandoverView component with print-to-PDF styles and audit log viewer

### Phase 10: Demo mode and Director

**Goal:** Build deterministic, resettable, multi-judge-safe evaluation panel and scenario runner
**Mode:** mvp
**Depends on:** Phase 5, Phase 6, Phase 7, Phase 8, Phase 9
**Requirements:** DEMO-01, DEMO-02, DEMO-03, DEMO-04, DEMO-05, DEMO-06
**Success Criteria** (what must be TRUE):

1. Demo Director (`/demo/director`) provides responsive split-view across Citizen, Responder, Ambulance, and Explainability
2. Scripted 19-step scenario runs via step-by-step or autoplay through real API endpoints without mocks
3. Clock controls allow arbitrary time advancement (e.g. +30 s) to force offer timeouts on demand
4. Idempotent reset restores initial session state without interfering with other concurrent judge sessions
5. Production flag (`DEMO_MODE_ENABLED=false`) completely disables demo routes with 404 responses

**Plans:** TBD

Plans:

- [ ] 10-01: Implement demo session isolation service, persona cloning, and reset endpoints
- [ ] 10-02: Build Demo Director UI with split-role views, Clock controls, and step buttons
- [ ] 10-03: Wire the 19-step automated scenario runner and failure-branch demonstrations

### Phase 11: Hardening, documentation, final verification

**Goal:** Complete comprehensive end-to-end verification, security audits, and judging documentation
**Mode:** mvp
**Depends on:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9, Phase 10
**Requirements:** HARDEN-01, HARDEN-02, HARDEN-03, HARDEN-04, HARDEN-05
**Success Criteria** (what must be TRUE):

1. Full test suite (unit, integration, concurrency, golden set, Playwright E2E) passes with 100% green status
2. Concurrency test suite proves single-winner offer acceptance and race-free lazy expiration
3. Security audits (`pip-audit`, `npm audit`, secret scan) report zero unaddressed high-severity vulnerabilities
4. Accessibility audits confirm WCAG AA contrast compliance and axe-core validation across all primary flows
5. `docs/VERIFICATION.md` and `README.md` provide 60-second judge quickstart and complete phase verification evidence

**Plans:** TBD

Plans:

- [ ] 11-01: Run full concurrency and authorization test suites, resolving any discovered race conditions
- [ ] 11-02: Execute security scans, dependency audits, accessibility checks, and performance benchmarks
- [ ] 11-03: Compile README quickstart, architecture documentation, and complete verification report

## Progress

**Execution Order:**
Phases execute in numeric order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Walking skeleton and deployment spike | 3/3 | Complete    | 2026-09-30 |
| 1. Domain model, migrations, clock, seeds | 0/3 | Not started | - |
| 2. Auth, RBAC, authorization, audit, rate limiting | 0/3 | Not started | - |
| 3. Protocol library, triage engine, golden set, LLM adapter | 0/3 | Not started | - |
| 4. Orchestration engine (pure logic) | 0/3 | Not started | - |
| 5. Emergency lifecycle, state machine, offers, lazy advance | 0/3 | Not started | - |
| 6. Frontend foundation and citizen SOS flow | 0/3 | Not started | - |
| 7. Responder and ambulance consoles | 0/3 | Not started | - |
| 8. Live map, timeline, citizen live view | 0/3 | Not started | - |
| 9. Authority console, explainability, handover packet UI | 0/3 | Not started | - |
| 10. Demo mode and Director | 0/3 | Not started | - |
| 11. Hardening, documentation, final verification | 0/3 | Not started | - |

---
*Roadmap defined: 2026-09-30*  
*Last updated: 2026-09-30 after initial definition*
