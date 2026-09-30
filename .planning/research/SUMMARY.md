# Project Research Summary

**Project:** LIFELINK  
**Domain:** Community First-Aid & Emergency Dispatcher (SDG 3, Good Health & Well-being)  
**Researched:** 2026-09-30  
**Confidence:** HIGH (Derived strictly from canonical `docs/LIFELINK_MASTER_SPEC.md`)

## Executive Summary

LIFELINK is an explainable, safety-gated community-first emergency coordination layer designed for the "golden minutes" — the critical window between emergency occurrence and professional service arrival. Operating beside national emergency numbers (`112`), it mobilizes nearby verified citizens into an accountable first-response network while notifying professional ambulances in parallel.

Research confirms that building safety-critical dispatch software for serverless deployment requires strict architectural discipline. Rather than relying on fragile WebSockets, unverified AI chat, or complex spatial extensions, the optimal approach pairs a lightweight React SPA with a stateless FastAPI backend and managed PostgreSQL. Real-time updates and offer timeouts are driven by deterministic client HTTP polling (2 s active / 5 s background) and lazy state advancement (`advance()`) under atomic PostgreSQL row locks.

The primary systemic risks — AI triage hallucinations, unverified responder dispatch, patient location stalking, and multi-judge demo collisions — are systematically neutralized by hard architecture boundaries: deterministic rules engine primacy with an escalate-only AI invariant, double verification gates at the database transaction level, coarse-to-exact location tiering, and per-session tenant isolation (`demo_session_id`).

## Key Findings

### Recommended Stack

The recommended stack is a high-performance monorepo targeting Vercel deployment:
- **Frontend:** Vite + React 19 + TypeScript + Tailwind CSS (mobile-first, light-only, touch >= 48px, WCAG AA compliant).
- **Backend:** FastAPI (Python 3.11+) stateless ASGI under `/api/v1` exposed via `api/index.py`.
- **Database:** PostgreSQL (Neon / Supabase) with SQLAlchemy 2.0 and Alembic migrations, utilizing row locks (`FOR UPDATE`), partial unique indexes, and append-only triggers.
- **Security & Mapping:** argon2id + httpOnly SameSite=Strict cookie JWT; Leaflet with OSM raster tiles and graceful offline fallback.
- **Contingency:** Phase 0 walking skeleton validates Vercel serverless Python runtime; if unviable, backend deploys to Render/Railway/Fly with zero architectural change.

### Expected Features

**Must have (table stakes):**
- Citizen SOS flow (1.5 s press-and-hold, confirmation sheet, skippable chips, 3 yes/no questions, location picker).
- Persistent "Call 112" non-network button visible on all emergency screens (`tel:` URI).
- Deterministic rules engine (P1/P2/P3 classification, ambulance requirement, protocol selection).
- Pre-reviewed protocol library (`shared/protocols/*.json`) bundled in frontend for offline guidance.
- Verified responder matching with hard eligibility filters (verification, status, skills, radius, scope).
- Dual-track response: community volunteer track and simulated ambulance console track running concurrently.
- Cascading dispatch with lazy expiration evaluation (`advance()`).
- Emergency handover packet generated from immutable `emergency_events` timeline.

**Should have (competitive differentiators):**
- Explainability engine: score breakdown for ranked candidates and reason codes for rejected ones.
- Escalate-only safety-gated AI: LLM extracts signals from free text but can NEVER de-escalate priority.
- Multi-tenant demo mode with Director panel, 19-step scenario runner, and Clock offset advancement.
- Coarse-until-accepted location privacy tiering.

**Defer (v2+ / Stretch):**
- Authority coverage-gap map grid (Phase 12a stretch).
- Offline-friendly PWA service worker (Phase 12b stretch).
- Integration with national CAD dispatch systems (v2).

### Architecture Approach

The architecture cleanly decouples concerns across thin routers, transactional services, pure domain logic, and immutable persistence:
1. **Presentation:** React SPA utilizing a custom `usePolling` hook polling every 2 s when active.
2. **Domain & Services:** Pure triage rules engine, pure orchestration scoring, pure composite state machine, and centralized authorization (`services/authz.py`).
3. **Data Layer:** 11 relational tables with PostgreSQL partial unique indexes guarding against double-dispatch, and append-only triggers protecting event timelines and audit logs.

### Critical Pitfalls

1. **Serverless timeout and WebSocket drops:** Solved by HTTP polling and lazy evaluation (`advance()`) under row locks.
2. **Unverified responder dispatch:** Solved by dual-gate enforcement (eligibility filter + database transaction guard).
3. **AI de-escalation / prompt injection:** Solved by closed enums, deterministic rules primacy, and zero-downgrade CI test gates.
4. **Patient location privacy leaks:** Solved by coarse (~250 m) location before accept, exact location only after accept, and immediate revocation on terminal state.
5. **Multi-judge demo collisions:** Solved by scoped demo sessions (`demo_session_id`) isolating records per judge.

## Implications for Roadmap

The research directly validates the 13 phased milestones defined in Section 18 of `docs/LIFELINK_MASTER_SPEC.md`:

### Phase 0: Walking skeleton and deployment spike
- **Rationale:** Proves the Vite + FastAPI + PostgreSQL stack deploys and polls reliably on Vercel before any feature code is written.
- **Delivers:** Scaffolds, `/health` endpoint, Docker Compose Postgres, Vercel configuration, and deployment ADR.
- **Avoids:** Pitfall 1 (Serverless deployment failure caught early).

### Phase 1: Domain model, migrations, clock, seeds
- **Rationale:** Foundational schema and data primitives must exist before application logic.
- **Delivers:** 11 database tables, Alembic migrations, constraints, triggers, injectable `Clock`, and persona seeds.
- **Avoids:** Pitfall 5 & 6 (Multi-tenant schema and deterministic Clock established from day one).

### Phase 2: Auth, RBAC, authorization, audit, rate limiting
- **Rationale:** Security infrastructure must protect all downstream endpoints.
- **Delivers:** argon2id, JWT cookies, role checks, `services/authz.py`, audit logger, and standard error envelopes.
- **Avoids:** Pitfall 4 (IDOR and unauthorized access prevented centrally).

### Phase 3: Protocol library, triage engine, golden set, LLM adapter
- **Rationale:** Safe incident classification is the prerequisite for dispatch orchestration.
- **Delivers:** Protocol JSONs, deterministic rules engine, 40+ case golden test harness, and optional LLM adapter.
- **Avoids:** Pitfall 3 (Zero-downgrade AI safety enforced).

### Phase 4: Orchestration engine (pure logic)
- **Rationale:** Pure matching logic should be fully verified in isolation before transactional wiring.
- **Delivers:** Haversine, hard eligibility filters, 0-100 multi-factor scoring, and explainability builders.
- **Avoids:** Pitfall 2 (Unverified candidates rejected with clear reason codes).

### Phase 5: Emergency lifecycle, state machine, offers, lazy advance
- **Rationale:** Transactional core tying triage, orchestration, offers, and timers together.
- **Delivers:** State machines, `create_emergency`, `advance()`, offer endpoints, and simulated movement.
- **Avoids:** Race conditions and timer failures on serverless.

### Phase 6: Frontend foundation and citizen SOS flow
- **Rationale:** Stress-proof citizen entry point into the system.
- **Delivers:** Accessible light-theme UI, press-and-hold SOS, triage chips, questions, and preview review card.

### Phase 7: Responder and ambulance consoles
- **Rationale:** Receiving side of the dispatch loop.
- **Delivers:** Responder dashboard, incoming offer modal with countdown, active assignment, and ambulance console.

### Phase 8: Live map, timeline, citizen live view
- **Rationale:** Visual feedback loop for citizens and high demo impact.
- **Delivers:** Leaflet map with simulated movement, accessible live timeline, and protocol guidance card.

### Phase 9: Authority console, explainability, handover packet UI
- **Rationale:** Oversight, credential verification, and closed-loop clinical handover.
- **Delivers:** Verification queue, live board with Explainability view, and printable handover packet.

### Phase 10: Demo mode and Director
- **Rationale:** Delivers deterministic, resettable, multi-judge-safe evaluation experience.
- **Delivers:** Scoped sessions, persona cloning, Clock controls, Director split-view, and 19-step scenario.

### Phase 11: Hardening, documentation, final verification
- **Rationale:** Guarantees ship-ready quality, security compliance, and comprehensive verification evidence.
- **Delivers:** Full test suite green, `pip-audit`/`npm audit` clean, README quickstart, and `docs/VERIFICATION.md`.

### Phase 12: Stretch (Strict order after Phase 11)
- **Rationale:** Optional enhancements (12a Coverage map, 12b PWA shell, 12c Second language, 12d Dedupe polish) that must not jeopardize core stability.

---
*Research summary for: Community First-Aid & Emergency Dispatcher (LIFELINK)*  
*Researched: 2026-09-30*
