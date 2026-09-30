# LIFELINK

## What This Is

LIFELINK is an explainable, safety-gated community-first emergency coordination layer for the "golden minutes" — the critical gap between when an emergency occurs and when professional emergency services arrive. It operates beside national emergency services (default `112`, configurable) without replacing them, turning verified nearby citizens into an accountable, rapid first-response network while simultaneously dispatching professional ambulance services.

## Core Value

The explainable, safety-gated coordination layer that runs beside official emergency services and turns verified nearby people into an accountable first-response network, delivering immediate community first-aid guidance and deterministic dual-track response within strict safety boundaries.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Citizen SOS flow with 1.5 s press-and-hold, skippable quick-type chips, 3 yes/no triage questions, optional text, automated/manual location, and preview review card
- [ ] Persistent "Call 112" emergency control visible on every citizen emergency screen working offline via `tel:` URI
- [ ] Deterministic rules engine as primary triage truth for priority (P1/P2/P3), ambulance need, protocol selection, and required responder skills
- [ ] Pre-reviewed protocol library (`shared/protocols/*.json`) bundled in frontend for zero-network offline rendering with clinical source citations
- [ ] Optional Tier 2 LLM extractor with closed-enum outputs, strict "escalate only, never de-escalate" invariant, prompt-injection immunity, and 4 s fallback
- [ ] Response Orchestration Engine with hard eligibility filters (verification, status, skills, radius, scope, race prevention) and 0-100 multi-factor scoring
- [ ] Full explainability engine producing human-readable score breakdowns for ranked candidates and specific machine-readable reason codes for rejected candidates
- [ ] Cascading dispatch across candidates upon decline, offer expiry (`OFFER_TTL_S`), or volunteer scene-unsafe abort
- [ ] Parallel dual-track architecture running community volunteer and professional ambulance tracks independently without mutual blocking
- [ ] Lazy deterministic timer evaluation (`advance(emergency_id)`) driven by client HTTP polling (2 s active / 5 s background) with PostgreSQL row locks
- [ ] Composite state machine (top-level lifecycle + community track + professional track + offer lifecycle) preventing invalid state transitions
- [ ] Append-only tamper-evident `emergency_events` timeline with role-scoped visibility and audit logging for sensitive data access
- [ ] Verified responder console with readiness toggle, incoming offer modal with server-synced countdown and volunteer acknowledgment, and active assignment actions
- [ ] Simulated ambulance console for unit offers, ETA acceptance, arrival tracking, and facility handover finalization
- [ ] Authority oversight console with credential verification queue, live incident board with Explainability view, and responder directory
- [ ] Tamper-evident emergency handover packet generated deterministically from timeline events for professional crews
- [ ] Multi-tenant demo session isolation (`demo_session_id`), seeded persona cast, Clock manipulation, 19-step scripted scenario, Director panel, and clean reset
- [ ] Hardened security and privacy: argon2id password hashing, cookie JWT, RBAC, centralized object-level authz, coarse-until-accepted location tiering, and medical consent gating

### Out of Scope

- Replacing official emergency services, hospitals, or doctors — LIFELINK is strictly a coordination layer
- AI medical diagnosis or AI-generated treatment instructions — all first-aid guidance comes from pre-reviewed protocols
- File uploads or OCR document verification — credentials are typed metadata records in MVP
- WebSockets, Server-Sent Events, or persistent background workers — replaced by HTTP polling and lazy evaluation
- PostGIS spatial database extensions — plain lat/lng with Haversine and SQL bounding-box prefilter is used
- Real-time routing engines or turn-by-turn navigation APIs — approximate ETA is calculated via Haversine and detour factor; navigation opens `geo:` links
- Direct SMS, push notifications, or telephone relay — in-app notifications and offer alerts only
- In-app chat, video streaming, payments, social leaderboards, or ML-based predictive ranking models

## Context

- Canonical specification: `docs/LIFELINK_MASTER_SPEC.md` (Spec version 1.0, status: canonical)
- Track: SDG 3, Good Health & Well-being (Problem: Community First-Aid & Emergency Dispatcher)
- Technical ecosystem: Monorepo targeting Vercel deployment with Vite + React + TypeScript + Tailwind frontend and stateless FastAPI (Python 3.11+) backend under `/api/v1`
- Database: Managed PostgreSQL (Neon / Supabase) using SQLAlchemy 2.x and Alembic
- Contingency: Phase 0 walking skeleton validates Vercel serverless Python runtime; if unviable, backend deploys to Render/Railway/Fly with zero architectural change
- Seeded demo cast per session: Asha (nurse, declines), Ravi (paramedic, accepts), Meera (first aider, backup), Karan (skill mismatch), Dr. Iyer (busy), Sana (outside radius), Vik (off duty), Nita (expired credential), Omar (pending credential), Amb-1 (accepts), Amb-2, Amb-3

## Constraints

- **Safety Architecture**: "Call 112" non-network control must exist on every citizen emergency screen; UI never guarantees help arrival ("we are contacting nearby responders", ETAs labelled "estimated")
- **AI Safety**: AI only extracts structured signals; deterministic rules decide priority and skills; AI may escalate, never de-escalate
- **Verification Gate**: Unverified, expired, rejected, or suspended responders must never receive offers or incident data (enforced in eligibility logic and DB transaction guard)
- **Privacy**: Coarse location (~250 m) before accept; exact location only for accepted target; immediate revocation upon incident termination; medical data shared only with explicit consent
- **Deployment Platform**: Stateless serverless execution requires client-driven HTTP polling, lazy deadline advancement under row lock, and minimal cold-start footprint
- **Auditability**: Every state change, authorization failure, and sensitive data read must write to append-only logs (`emergency_events` and `audit_logs`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HTTP polling over WebSockets/SSE | Serverless platforms (Vercel) lack long-lived socket persistence; 2 s polling satisfies latency requirements | — Pending |
| Lazy deterministic `advance()` over cron | Serverless cannot guarantee sub-minute background cron; evaluate deadlines on poll and state queries under row lock | — Pending |
| Polymorphic `dispatch_offers` table | Merges 3 redundant dispatch tables into one table guarded by partial unique indexes | — Pending |
| Haversine + bounding box over PostGIS | Eliminates PostgreSQL extension dependencies for MVP; mathematically accurate enough for local community radiuses | — Pending |
| Deterministic rules engine with optional LLM | Safety-critical triage requires deterministic, verifiable outcomes; LLM serves strictly as an auxiliary NLP extractor | — Pending |
| Escalate-only AI principle | Prevents prompt injection or model hallucination from downplaying life-threatening conditions | — Pending |
| Composite state machine | Decouples top-level emergency lifecycle from independent parallel volunteer and ambulance track states | — Pending |
| Server-simulated movement from Clock | Eliminates dependency on client GPS or external routing services for deterministic judging demos | — Pending |
| Shared JSON taxonomy and protocols | `shared/*.json` bundled into frontend and loaded by backend guarantees offline guidance and zero rule drift | — Pending |
| Per-session demo tenant isolation | Scoping all rows by `demo_session_id` ensures multiple judges can run scenarios concurrently without collisions | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-30 after initialization*
