# Phase 6: Frontend foundation and citizen SOS flow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01  
**Phase:** 06-frontend-foundation-and-citizen-sos-flow  
**Areas discussed:** SOS flow navigation & state management, Location capture & fallback UX, Offline protocol viewer & emergency guidance access, Duplicate incident resolution UX  

---

## SOS flow navigation & state management

| Option | Description | Selected |
|--------|-------------|----------|
| Separate URL routes | Separate URL routes (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`) matching Master Spec §9.2 route map, supporting hardware back button | ✓ |
| Single-page stepper | In-memory animated stepper at `/sos` without route transitions | |
| You decide | Agent chooses between routing or stepper | |

**User's choice:** Separate URL routes (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`)  
**Notes:** Provides standard browser navigation, back button safety, and distinct step URLs while preventing accidental resets.

| Option | Description | Selected |
|--------|-------------|----------|
| React Context + sessionStorage | Shared React Context with `sessionStorage` draft persistence across accidental refresh or tab switch | ✓ |
| Pure React Context | In-memory only state tree, resets on hard browser refresh | |
| You decide | Agent discretion on storage approach | |

**User's choice:** Shared React Context with `sessionStorage` draft persistence  
**Notes:** Automatically purged upon successful creation or user cancellation.

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom action sheet | Bottom sheet on mobile / modal on desktop with 10s auto-cancel countdown bar, haptic feedback, and big touch targets | ✓ |
| Full-screen overlay | Full-screen urgent takeover overlay with countdown ring | |
| You decide | Agent discretion | |

**User's choice:** Bottom action sheet with 10s auto-cancel countdown bar and haptic feedback  
**Notes:** Prevents accidental pocket triggers while keeping stress low.

| Option | Description | Selected |
|--------|-------------|----------|
| Dual actions on sheet | `[Add Details / Guided Triage]` (to `/sos/type`) and `[Send Now (Instant Fast Dispatch)]` (creates minimal emergency immediately) | ✓ |
| Single action | `[Continue]` routing to `/sos/type` where questions are skippable | |
| You decide | Agent discretion | |

**User's choice:** Dual actions on confirmation sheet (`[Add Details / Guided Triage]` and `[Send Now (Instant Fast Dispatch)]`)  
**Notes:** Supports both structured triage for bystander scenarios and instant fast-dispatch for extreme panic. Fast Dispatch MUST execute the full existing backend safety pipeline (Create emergency → deterministic triage rules → Phase 4 eligibility/filtering → Phase 4 scoring/ranking → parallel community/professional dispatch → offer/cascade), never directly dispatching the nearest responder or bypassing Phase 3/4 safety/orchestration logic.

---

## Location capture & fallback UX

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate GPS request | Request GPS on `/sos` mount to pre-warm cache and accuracy | ✓ |
| Request on details screen | Request GPS only on `/sos/details` | |
| You decide | Agent discretion | |

**User's choice:** Request GPS immediately on `/sos` home mount  
**Notes:** Minimizes latency when the user reaches the review and dispatch step.

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked map + text | Compact interactive Leaflet map with draggable pin & re-center button, plus landmark text input | ✓ |
| Draggable map only | Visual pin placement without text input | |
| Text landmark only | Fast text-only landmark without map tiles | |
| You decide | Agent discretion | |

**User's choice:** Both stacked: Compact interactive Leaflet map with draggable pin and landmark text input  
**Notes:** Ensures tactical scene accuracy for arriving responders (e.g. gate, floor, apartment).

| Option | Description | Selected |
|--------|-------------|----------|
| Default center coordinates | Fallback to configured center coordinates (`DEMO_CENTER_LAT/LNG`) with amber warning badge without blocking dispatch | ✓ |
| Block until manual pin placed | Require user to interact with map before proceeding | |
| You decide | Agent discretion | |

**User's choice:** Default to configured center coordinates (`DEMO_CENTER_LAT/LNG`) with amber badge without blocking  
**Notes:** If GPS is denied/unavailable, fallback coordinates are visually explicit and labelled as "Demo location used — GPS unavailable", never implying that it is the user's real location.

| Option | Description | Selected |
|--------|-------------|----------|
| Accuracy & privacy card | Display dynamic browser accuracy or 'Accuracy unavailable', distinguish demo/fallback from real GPS, and show privacy guarantee badge | ✓ |
| Minimal location pill | Coordinates only without privacy notice | |
| You decide | Agent discretion | |

**User's choice:** Display location card with dynamic accuracy indicator and privacy guarantee badge  
**Notes:** Displays browser-provided geolocation accuracy when available or 'Accuracy unavailable'. In demo mode, clearly distinguishes simulated/fallback location from real GPS via distinct badges. Reassures citizen on privacy safeguards per Master Spec §11.

---

## Offline protocol viewer & emergency guidance access

| Option | Description | Selected |
|--------|-------------|----------|
| Static build-time import | Static build-time import of `shared/protocols/*.json` into client bundle | ✓ |
| API fetch with IndexedDB | Fetch on demand with local caching | |
| You decide | Agent discretion | |

**User's choice:** Static build-time import of `shared/protocols/*.json`  
**Notes:** 100% offline availability with zero network dependency or quota eviction risk.

| Option | Description | Selected |
|--------|-------------|----------|
| Persistent amber banner | Persistent high-visibility banner: 'Offline — Emergency calls work via 112. First-aid protocols available below' | ✓ |
| Modal overlay | Modal overlay pausing SOS and forcing choice between 112 and protocols | |
| You decide | Agent discretion | |

**User's choice:** Persistent high-visibility amber banner below header  
**Notes:** Keeps both Call 112 and protocol guidance immediately accessible without blocking navigation. The offline `tel:112` action is device/environment dependent (requires OS telephony capability), and the application must never claim or imply that an emergency call was actually placed during demo mode.

| Option | Description | Selected |
|--------|-------------|----------|
| Vertical step cards | Bold step numbering, action icons, prominent 'DO NOT' warning callout, and demo disclaimer banner | ✓ |
| Swipeable carousel | One instruction per slide with next button | |
| Accordion list | Expanding steps one at a time | |
| You decide | Agent discretion | |

**User's choice:** Step-by-step vertical cards with bold numbering, action icons, and 'DO NOT' warning callout  
**Notes:** Fastest comprehension for bystanders administering CPR or first aid under stress.

| Option | Description | Selected |
|--------|-------------|----------|
| Segmented multi-protocol tabs | Primary protocol active by default, adjacent tabs for secondary conditions, plus 'Browse All Protocols' drawer | ✓ |
| Single protocol display | Shows only primary protocol with dropdown | |
| You decide | Agent discretion | |

**User's choice:** Multi-protocol segmented tabs with 'Browse All Protocols' drawer  
**Notes:** Prevents critical secondary trauma interventions (e.g. bleeding control during arrest) from being missed.

---

## Duplicate incident resolution UX

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated conflict dialog | Modal showing proximity and age, offering `[Join Existing Incident]` and `[Report as Separate Incident]` (`force_create: true`) | ✓ |
| Inline conflict banner | Inline warning on review screen | |
| You decide | Agent discretion | |

**User's choice:** Dedicated duplicate resolution dialog with distance, time, and two clear choices  
**Notes:** Directly integrates with Phase 5's HTTP 409 `POSSIBLE_DUPLICATE` response envelope.

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect in observer mode | Redirect directly to `/emergency/{existing_id}` in linked observer mode | ✓ |
| Info modal with status | Status popup without redirecting | |
| You decide | Agent discretion | |

**User's choice:** Redirect directly to `/emergency/{existing_emergency_id}` in linked observer mode  
**Notes:** Citizen monitors response and protocols without generating duplicate volunteer dispatches.

| Option | Description | Selected |
|--------|-------------|----------|
| Single UUIDv4 per review entry | Generate UUIDv4 once per draft and lock button immediately upon click to prevent double-tap | ✓ |
| New key on every attempt | Generate new UUID on each click | |
| You decide | Agent discretion | |

**User's choice:** Generate UUIDv4 once per draft/review entry and reuse across network retries  
**Notes:** Protects against duplicate emergencies during network flakiness.

| Option | Description | Selected |
|--------|-------------|----------|
| Two-step cancellation sheet | Confirmation sheet requiring reason chip (`false_alarm`, `resolved_on_scene`, `called_112_instead`, `other`) | ✓ |
| Immediate cancel with undo | Instant cancel with 5s snackbar | |
| You decide | Agent discretion | |

**User's choice:** Two-step confirmation sheet requiring cancellation reason chip  
**Notes:** Guards against accidental aborts while ensuring structured audit trail.

---

## Agent's Discretion

- Micro-animations: Smooth 1.5s press ring progress for `SosButton`, countdown bar CSS transition, tab animations.
- Iconography: Lucide React semantic icons for emergency categories and protocol steps.
- Accessibility: Focus rings, touch targets (≥48px), WCAG AA color contrast, and `aria-live` announcements.

## Deferred Ideas

- None — all topics discussed stayed strictly within Phase 6 scope.
