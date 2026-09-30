# Phase 5: Emergency lifecycle, state machine, offers, lazy advance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01  
**Phase:** 05-emergency-lifecycle-state-machine-offers-lazy-advance  
**Areas discussed:** Idempotency & Deduplication, Lazy Evaluation & Row Locking, Offer Cascade & Scene Safety, Location Privacy Tiering  

---

## Idempotency & Deduplication

| Option | Description | Selected |
|--------|-------------|----------|
| Store `idempotency_key` on emergencies with unique index; `force_create: true` in body to bypass 409 | Dedicated column and unique constraint scoped by session/tenant; body override for duplicates | ✓ |
| Check idempotency via `audit_logs`; require explicit `POST /emergencies/{id}/link` | Extracted from audit log records | |
| Pure header-based approach | `Idempotency-Key` for replays, `X-Override-Duplicate: true` header for 409 bypass | |

**User's choice:** Store idempotency_key on emergencies table with unique index; allow force_create=true in body to bypass 409 duplicate check.  
**Notes:** Provides atomic database-level enforcement against race conditions and clean REST payload ergonomics.

---

## Lazy Evaluation & Row Locking

| Option | Description | Selected |
|--------|-------------|----------|
| Transparent advance with `SELECT FOR UPDATE` double-check locking + `POST /advance` test endpoint | Evaluates on polling `GET /emergencies/{id}` and offer mutations; manual trigger for tests | ✓ |
| Dedicated poll endpoint only | `POST /emergencies/{id}/poll` only, keeping `GET` pure read-only | |
| Opportunistic advance with `SKIP LOCKED` | Skips advance if another client is actively holding row lock | |

**User's choice:** Transparent advance inside GET /emergencies/{id} and all offer mutations using SELECT FOR UPDATE with double-check locking, plus expose POST /emergencies/{id}/advance for test/director control.  
**Notes:** Essential for stateless serverless execution on Vercel where background workers are absent.

---

## Offer Cascade & Scene Safety

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate synchronous cascade + safety hazard warning | Instantly dispatches candidate #2 in same transaction on decline/timeout; SCENE_UNSAFE alerts incident | ✓ |
| Two-step lazy cascade | Sets track to PENDING, dispatches candidate #2 on next poll cycle; suspends volunteer track on danger | |
| Manual fallback on decline | Requires citizen or authority intervention to cascade; alerts authority only | |

**User's choice:** Immediate synchronous cascade: advance() or decline instantly creates offer for candidate #2 in same transaction; SCENE_UNSAFE logs critical safety alert event, sets scene_safety_warning on incident, and offers next responder with prominent hazard warning.  
**Notes:** Eliminates response delays during the golden minutes when volunteer #1 declines or cannot respond.

---

## Location Privacy Tiering

| Option | Description | Selected |
|--------|-------------|----------|
| Stable hash-based radial offset (~250m) before accept; exact on accept; nullify coordinates on close | Deterministic offset seeded by emergency ID; coordinates zeroed out upon incident termination | ✓ |
| Grid snapping (~250m); return 403 Forbidden after close | Coordinates snapped to grid; hard 403 on close | |
| Neighborhood landmark bounding box center | Bounding box center before accept; nullify on close | |

**User's choice:** Stable hash-based radial offset (~250m) before accept; exact coordinates only while offer is ACCEPTED/ARRIVED; nullify coordinates (lat: null, lng: null) immediately upon completion, decline, or cancellation.  
**Notes:** Ensures candidate map marker does not jump during polling countdown, while guaranteeing zero location leakage after incident completion.

---

## the agent's Discretion

None — all 4 gray areas were explicitly selected and decided by the user.

## Deferred Ideas

None — discussion remained strictly within Phase 5 scope.
