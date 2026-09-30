# Phase 5: Emergency lifecycle, state machine, offers, lazy advance - Context

**Gathered:** 2026-10-01  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 5 builds the core transactional engine of LIFELINK:
- Emergency creation via `POST /emergencies` with client-provided `Idempotency-Key` and spatial/temporal deduplication (150 m, 10 min).
- Dual-track response initiation managing independent community volunteer and professional ambulance tracks.
- Composite state machines across Incident (`EmergencyStatus`), Tracks (`TrackStatus`), and Offers (`DispatchOfferStatus`).
- Deterministic lazy evaluation (`advance(emergency_id)`) executed under PostgreSQL row locks (`SELECT ... FOR UPDATE`) triggered during client polling and mutations.
- Immediate cascading dispatch to candidate #2 upon offer decline, timeout (`OFFER_TTL_S`), or scene-unsafe abort.
- Responder offer lifecycle actions (`ACCEPT`, `DECLINE`, `ARRIVE`, `SCENE_UNSAFE`, `COMPLETE`) with atomic single-active-responder enforcement.
- Location privacy tiers: stable coarse coordinates (~250 m) before accept, exact coordinates during active response, and instant coordinate revocation upon resolution or cancellation.
- Incident cancellation and resolution workflows with clean offer closure and append-only event logging.

</domain>

<decisions>
## Implementation Decisions

### Idempotency & Deduplication
- **D-01:** `emergencies` table stores `idempotency_key` with a unique index scoped by `demo_session_id`. Re-submitting an identical request with the same `Idempotency-Key` returns the existing incident record without creating duplicate entries.
- **D-02:** Spatial deduplication queries active emergencies within 150 meters and 10 minutes (using Haversine and bounding-box filters). If found, the server responds with HTTP `409 Conflict` (`POSSIBLE_DUPLICATE`) including `existing_emergency_id`, distance, triage priority, and timestamp. Submitting with `force_create: true` in the request body bypasses deduplication to create an independent incident.

### Lazy Evaluation Engine & Row Locking
- **D-03:** Transparent lazy evaluation: `advance(emergency_id)` executes inside `GET /emergencies/{id}` (client polling) and all offer mutation endpoints.
- **D-04:** PostgreSQL row lock concurrency: `advance()` acquires a row-level lock (`SELECT ... FOR UPDATE` on `emergencies`) and uses a double-check pattern comparing `updated_at` to avoid redundant computations if another concurrent request just completed advancement.
- **D-05:** Explicit manual trigger endpoint `POST /emergencies/{id}/advance` is exposed for test suite assertions and Demo Director manual clock advancement.

### Offer Cascade & Scene Safety
- **D-06:** Synchronous cascading dispatch: When an active offer expires or is declined, `advance()` / the decline handler transitions the current offer to `EXPIRED` or `DECLINED`, logs the event, and immediately compiles and dispatches an offer to candidate #2 in the same database transaction.
- **D-07:** Scene-unsafe protocol: Submitting `action: SCENE_UNSAFE` cancels the responder's assignment, logs a critical `RESPONDER_SCENE_UNSAFE` event in `emergency_events`, sets `scene_safety_warning` on the incident, and ensures subsequent volunteer offers include prominent hazard alerts.

### Location Privacy Tiering
- **D-08:** Coarse location algorithm: Before an offer is accepted, the API exposes coarse coordinates generated via a stable, deterministic pseudo-random radial offset (~250 m) seeded by the incident's UUID. This prevents map-pin jumping across repeated polling requests while keeping exact patient coordinates hidden.
- **D-09:** Exact location gating: Exact latitude and longitude are exposed strictly to the responder whose offer is in `ACCEPTED` or `ARRIVED` status.
- **D-10:** Instant revocation: Upon offer completion, decline, cancellation, or incident resolution, coordinates are immediately nullified (`lat: null, lng: null, location_revoked: true`) in all responder responses.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### LIFELINK Master Specification
- `docs/LIFELINK_MASTER_SPEC.md` §5 — Composite Lifecycles & State Transitions (`EmergencyStatus`, `TrackStatus`, `DispatchOfferStatus`)
- `docs/LIFELINK_MASTER_SPEC.md` §7 — Dispatch Lifecycle & Concurrency Control
- `docs/LIFELINK_MASTER_SPEC.md` §7.1 — Incident Creation, Idempotency & Deduplication
- `docs/LIFELINK_MASTER_SPEC.md` §7.2 — Lazy Evaluation Engine (`advance()`, row locks, timeout cascade)
- `docs/LIFELINK_MASTER_SPEC.md` §7.3 — Offer Transitions & Atomic Concurrency
- `docs/LIFELINK_MASTER_SPEC.md` §11 — Privacy & Data Protection (Coarse vs exact location tiers)
- `docs/LIFELINK_MASTER_SPEC.md` Appendix B — Demo Walkthrough Incident 1 (Asha decline, Ravi accept, cascade)

### Architecture Decisions
- `docs/ADR-001-deployment.md` — Stateless Serverless HTTP Polling & In-Request Lazy Evaluation Architecture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/orchestration/service.py`: `find_and_rank_candidates` for compiling eligible candidate rankings and dispatch plans.
- `backend/app/orchestration/schemas.py`: `CandidateProfile`, `EmergencyContext`, `OrchestrationResult`.
- `backend/app/core/clock.py`: `Clock` abstraction for testable, deterministic time advancement.
- `backend/app/core/config.py`: `OFFER_TTL_S` (30s), `DEMO_OFFER_TTL_S` (20s), `LOCATION_FRESHNESS_S` (300s).
- `backend/app/domain/enums.py`: `EmergencyStatus`, `TrackStatus`, `DispatchOfferStatus`, `OfferAction`, `TrackKind`.
- `backend/app/services/authz.py`: `require_emergency_access`, `require_offer_action_authorized`.

### Established Patterns
- Pure domain services decoupled from HTTP controllers.
- Strict Pydantic v2 schemas with `extra="forbid"`.
- Atomic database transactions with rollback protection and append-only event logging (`emergency_events`, `audit_logs`).

### Integration Points
- API routers for `/api/v1/emergencies` (`POST /emergencies`, `GET /emergencies/{id}`, `POST /emergencies/{id}/advance`, `POST /emergencies/{id}/cancel`, `POST /emergencies/{id}/resolve`).
- API routers for `/api/v1/offers` (`GET /offers/pending`, `POST /offers/{id}/action`).

</code_context>

<specifics>
## Specific Ideas

- Ensure Appendix B walkthrough sequence runs flawlessly: Citizen creates P1 emergency -> Asha offered -> Asha declines -> Ravi instantly offered -> Ravi accepts -> Ravi arrives.
- Offer timeout test must prove that advancing clock by 31 seconds in `POST /emergencies/{id}/advance` causes Asha's offer to expire and cascades to Ravi.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion remained strictly within Phase 5 scope.

</deferred>

---

*Phase: 05-emergency-lifecycle-state-machine-offers-lazy-advance*  
*Context gathered: 2026-10-01*  
