# Feature Research

**Domain:** Community First-Aid & Emergency Dispatcher (SDG 3, Good Health & Well-being)  
**Researched:** 2026-09-30  
**Confidence:** HIGH (Derived strictly from canonical `docs/LIFELINK_MASTER_SPEC.md`)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in emergency and dispatch software. Missing these makes the product unsafe or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 1.5 s Press-and-Hold SOS Button | Prevents catastrophic accidental pocket-triggers under high adrenaline | LOW | Visual progress ring, confirmation sheet with 10 s auto-cancel |
| Persistent "Call 112" Non-Network Button | Legal and clinical mandate; app never replaces official emergency services | LOW | Visible on all citizen emergency screens; operates via offline `tel:` URI |
| Rapid 3-Question Triage + Chips | Panicked citizens cannot type long paragraphs; needs structured extraction | MEDIUM | Chips (Bleeding, Unresponsive, Fall, etc.) + tri-state answers (Yes/No/Not sure) |
| Deterministic Priority Classification (P1/P2/P3) | Triage must be 100% reproducible, explainable, and clinically grounded | MEDIUM | Table-driven rules engine versioned in code; P1 triggers immediate ambulance |
| Pre-reviewed Offline First-Aid Protocols | Guidance must appear instantly even if network is lost after initial SOS | MEDIUM | Bundled JSON protocols (`shared/protocols/*.json`); step-by-step illustrations |
| Verified-Only Volunteer Matching | Critical safety guarantee: unverified citizens must NEVER receive dispatch offers | HIGH | Hard DB constraint + eligibility filter; verified credentials required |
| Real-time Map & ETA | Citizens and responders need spatial awareness of response progress | MEDIUM | Leaflet map with simulated deterministic movement, arrival countdowns |
| Dual-Track Ambulance Coordination | Community response acts as stop-gap; professional ambulance runs in parallel | HIGH | Independent track state machines running concurrently without blocking |
| Emergency Handover Packet | Hospital/crew needs chronological scene notes and actions taken | MEDIUM | Deterministic generation from audited timeline events; printable to PDF |

### Differentiators (Competitive Advantage)

Features that set LIFELINK apart from simple SOS apps and traditional CAD systems.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Explainable Response Orchestration | Full transparency on *why this responder* and *why not others* | HIGH | Generates score breakdown for ranked candidates and machine-readable reason codes for rejected ones |
| Escalate-Only Safety-Gated Hybrid AI | AI extracts signals from free-text descriptions but can NEVER de-escalate | HIGH | Deterministic rules engine always overrides LLM; strict zero-downgrade property verified by golden test suite |
| Cascading Lazy Dispatch | Automatic cascade on decline, timeout (`OFFER_TTL_S`), or scene-unsafe abort | HIGH | Idempotent `advance()` function executed under PostgreSQL row locks during polling |
| Multi-Tenant Demo Director Panel | Judges can orchestrate, inspect, and step through scenarios deterministically | HIGH | Per-session tenant isolation (`demo_session_id`), Clock offset controls, and full 19-step script |
| Coarse-to-Exact Privacy Tiering | Protects patient location from volunteer stalking | MEDIUM | Coarse ~250 m location before offer accept; exact coordinates only after accept; revoked on close |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing on the surface but introduce fatal liabilities or complexity in emergency systems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| AI Conversational Medical Advice / Chatbot | Citizens want answers to medical questions | LLMs hallucinate treatment advice, creating fatal medical liability | Use static, pre-reviewed protocol libraries cited from official first-aid bodies |
| Direct WebSockets for Timers | Developers default to WebSockets for live countdowns | Silent disconnects on mobile browsers and serverless function cold starts | Client HTTP polling (2 s) with server-side lazy expiration evaluation |
| Full PostGIS Extension Stack | Standard for GIS applications | Heavy installation overhead, managed database compatibility issues | SQL bounding-box prefilter combined with Haversine distance formula |
| File Upload for Credentials (PDF/Images) | Users want to upload certification cards | Requires malware scanning, S3 storage, OCR, and manual review bottlenecks | Typed credential metadata records reviewed by authority persona in MVP |
| Volunteer-Patient Real-Time Chat | App users want to text responders | Distracts volunteers en route and creates harassment/privacy vectors | Standard status updates, action checklists, and protocol cards |
| Distance-Only Responder Ranking | Simple to implement (closest responder wins) | Proximity does not equal skill suitability, availability, or volunteer fatigue | Multi-factor scoring (skills 30, ETA 30, fairness 15, reliability 10, tier 10, headroom 5) |

## Feature Dependencies

```
[SOS Submission]
    └──requires──> [Triage Rules Engine]
                        └──requires──> [Protocol Library (shared JSON)]
                        └──requires──> [Response Orchestration Engine]
                                            ├──requires──> [Verified Responder Pool]
                                            └──requires──> [Dual-Track State Machine]
                                                                ├──requires──> [Offer Cascading (advance())]
                                                                └──requires──> [Emergency Handover Packet]
```

### Dependency Notes

- **Triage requires Protocol Library:** Triage rules select the protocol ID, which dictates required volunteer skills.
- **Orchestration requires Triage Results:** Priority (P1/P2/P3) and required skill levels determine responder eligibility.
- **Cascading requires Dual-Track State Machine:** Decline, expiry, or abort on the volunteer track triggers the next candidate without affecting the ambulance track.
- **Handover Packet requires Emergency Events:** Handover summary is deterministically built from the chronological `emergency_events` table.

## MVP Definition

### Launch With (v1 / Hackathon MVP)

- [x] Citizen SOS trigger (press-and-hold, confirmation, Call 112)
- [x] Triage flow (quick chips, 3 yes/no questions, optional text, location)
- [x] Deterministic triage rules engine + pre-reviewed protocol library
- [x] Verified responder matching with hard eligibility filters and multi-factor scoring
- [x] Explainable matching (score breakdown and rejection reasons)
- [x] Dual-track response (community volunteers + simulated ambulance console)
- [x] Offer lifecycle: accept, decline, arrive, scene-unsafe abort, complete
- [x] Cascading dispatch with lazy timeout evaluation (`advance()`)
- [x] Live tracking map with deterministic server-interpolated movement
- [x] Authority verification queue and live incident oversight board
- [x] Emergency handover packet generated from immutable event history
- [x] Multi-tenant demo mode with Director panel and 19-step scenario runner
- [x] Hardened security: argon2id, JWT cookies, RBAC, central authz, audit logging

### Add After Validation (v1.x / Stretch)

- [ ] Coverage-gap map for authorities (grid showing eligible responder density)
- [ ] Offline-friendly PWA service worker shell for protocol caching
- [ ] Multilingual support (second language for citizen flow and protocols)
- [ ] Incident deduplication UX polish (handling near-simultaneous reports)

### Future Consideration (v2+)

- [ ] Real-time integration with national emergency CAD systems
- [ ] Direct push notifications and SMS / telephone relay fallback
- [ ] Real document OCR verification with private cloud storage
- [ ] Multi-responder dispatch coordination (`responders_needed > 1`)
- [ ] H3 hexagonal spatial indexing and public health response analytics

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Citizen SOS & Call 112 | HIGH | LOW | P1 |
| Deterministic Rules Triage | HIGH | MEDIUM | P1 |
| Verified Responder Matching | HIGH | HIGH | P1 |
| Explainability Engine | HIGH | MEDIUM | P1 |
| Cascading Dispatch & Lazy Advance | HIGH | HIGH | P1 |
| Live Interactive Map & Timeline | HIGH | MEDIUM | P1 |
| Handover Packet Generation | HIGH | MEDIUM | P1 |
| Demo Director & Scenario Runner | HIGH | MEDIUM | P1 |
| Authority Verification Queue | MEDIUM | LOW | P1 |
| Optional Tier 2 LLM Extractor | MEDIUM | MEDIUM | P1 |
| Coverage Gap Grid | MEDIUM | MEDIUM | P2 (Stretch) |
| Offline PWA Shell | MEDIUM | MEDIUM | P2 (Stretch) |
| CAD System Integration | HIGH | VERY HIGH | P3 (Future) |

---
*Feature research for: Community First-Aid & Emergency Dispatcher (LIFELINK)*  
*Researched: 2026-09-30*
