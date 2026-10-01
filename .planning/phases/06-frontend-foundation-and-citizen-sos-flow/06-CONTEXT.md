# Phase 6: Frontend foundation and citizen SOS flow - Context

**Gathered:** 2026-10-01  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 6 delivers the frontend foundation, strict light-theme design system, authentication interfaces, and the core citizen SOS emergency workflow:
- Layout shell featuring a persistent header (LIFELINK mark, offline indicator, and `DEMO MODE` badge when in demo scope) and persistent non-network "Call 112" control (`tel:112` URI) visible and operational on all citizen emergency screens without network dependency. Note: The `tel:112` action is device/environment dependent (requires OS telephony/dialer capability); the application must never claim that an emergency call was actually placed, especially during demo mode.
- Responsive, mobile-first design tokens complying with WCAG AA contrast (≥4.5:1 text, ≥3:1 large UI), touch targets ≥48×48px, minimum font size 16px, and mobile layout tested down to 360px width.
- Authentication screens (`/login`, `/register`) supporting citizen and responder roles, managing `ll_session` httpOnly cookies, role redirection, and error handling.
- Multi-step, route-based SOS workflow matching Master Spec §9.2:
  - `/sos`: Home screen with 1.5s press-and-hold `SosButton`, opening a 10s auto-cancelling bottom confirmation sheet with `[Add Details / Guided Triage]` and `[Send Now (Instant Fast Dispatch)]`. Fast Dispatch routes strictly through the backend safety pipeline (Create emergency → deterministic triage → Phase 4 eligibility/filtering → Phase 4 scoring/ranking → parallel community/professional dispatch → offer/cascade), never bypassing Phase 3/4 logic or directly dispatching the nearest responder.
  - `/sos/type`: Quick-type emergency chips (Bleeding, Not responding, Accident/Fall, Choking, Burn, Seizure, Chest pain, Other) with "Who needs help? Me / Someone else" toggle. Skippable.
  - `/sos/questions`: Three large tri-state triage questions (Awake & responding?, Breathing normally?, Severe bleeding? with Yes / No / Not sure).
  - `/sos/details`: Free-text field (max 500 chars) plus location confirmation featuring immediate GPS auto-acquisition, interactive Leaflet mini-map with draggable pin, and manual landmark/access text input. If GPS permission is denied or unavailable, fallback `DEMO_CENTER_LAT/LNG` is visually explicit and labelled as "Demo location used", never implying it is real GPS.
  - `/sos/review`: Triage classification preview card calling `POST /api/v1/triage/preview`, displaying priority, detected conditions, primary protocol, confidence disclaimer, dynamic location accuracy (browser-provided accuracy when available or "Accuracy unavailable", with simulated/fallback clearly distinguished from real GPS in demo mode), privacy badge, and single-tap `[Send Emergency Request]`.
- Resilient client state management using shared React Context backed by `sessionStorage` draft persistence, with client-generated UUIDv4 `Idempotency-Key` preserved across retries.
- Duplicate incident resolution dialog handling HTTP `409 Conflict` (`POSSIBLE_DUPLICATE`) with options to `[Join Existing Incident]` (redirecting to `/emergency/:id` in observer mode) or `[Report as Separate Incident]` (`force_create: true`).
- Two-step citizen emergency cancellation / false-alarm sheet capturing mandatory cancellation reason chips before calling `POST /api/v1/emergencies/{id}/cancel`.
- Offline emergency support featuring a high-visibility amber disconnection banner and an offline protocol guidance viewer powered by static build-time bundled protocols (`shared/protocols/*.json`) with multi-condition segmented tabs and prominent "DO NOT" warnings.

</domain>

<decisions>
## Implementation Decisions

### SOS Flow Navigation & State Management
- **D-01:** Separate URL routes (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`) are implemented in `react-router` matching Master Spec §9.2. This ensures full browser and hardware back button functionality, distinct step bookmarking, and clear step-by-step progress tracking.
- **D-02:** Shared React Context with `sessionStorage` draft persistence preserves all input fields (selected chips, "Who needs help", answers to the 3 questions, free text, captured coordinates, and landmark notes) across accidental page refreshes or mobile browser tab switches. The draft is automatically purged upon successful emergency creation or user cancellation.
- **D-03:** The 1.5s press-and-hold `SosButton` triggers haptic feedback (via `navigator.vibrate([40])` where supported) and opens a bottom action sheet on mobile (centered modal dialog on desktop) with a visible 10-second auto-cancel countdown progress bar and prominent touch targets for `[Send Now]` and `[Cancel]`.
- **D-04:** The 10s confirmation sheet offers two distinct pathways: `[Add Details / Guided Triage]` (advances to `/sos/type` for structured multi-step intake) and `[Send Now (Instant Fast Dispatch)]` (creates the emergency immediately via `POST /api/v1/emergencies`). The Fast Dispatch path MUST execute the full existing backend safety pipeline: Create emergency → deterministic triage rules (Phase 3) → hard eligibility filtering (Phase 4) → multi-factor candidate scoring/ranking (Phase 4) → parallel community/professional track dispatch → atomic offer/cascade (Phase 5). Fast Dispatch must NEVER directly dispatch the nearest responder or bypass any Phase 3/4 safety, verification, or orchestration logic.

### Location Capture & Fallback UX
- **D-05:** Geolocation auto-acquisition (`navigator.geolocation.getCurrentPosition`) is initiated immediately on `/sos` home mount to pre-warm the browser location cache so coordinates and accuracy radius are instantly available when SOS is pressed.
- **D-06:** On `/sos/details`, location is presented via a stacked layout: a compact interactive Leaflet map featuring a draggable pin with a "Re-center GPS" button, paired with a dedicated text input for landmark/entry details (e.g. "Gate 2, 3rd floor, apt 301").
- **D-07:** If browser GPS permission is denied or unavailable, the map defaults to configured fallback coordinates (`DEMO_CENTER_LAT/LNG`) and makes this visually explicit in the UI with a prominent label: "Demo location used — GPS unavailable". The system must never imply that this fallback is the user's real location, while still allowing the citizen to drag the pin, enter landmarks, or proceed without blocking acute dispatch.
- **D-08:** The review card (`/sos/review`) presents a dynamic location accuracy indicator displaying the browser-provided geolocation accuracy when available (e.g. `±{Math.round(coords.accuracy)}m`), or "Accuracy unavailable" if the browser does not provide accuracy data. In demo mode, the UI clearly distinguishes simulated/fallback location from real GPS via explicit badging, alongside the privacy guarantee badge: "Privacy-gated: Exact location revealed only to accepted responder" (reinforcing Master Spec §11).

### Offline Protocol Viewer & Guidance Access
- **D-09:** The 7 clinically cited emergency protocols (`shared/protocols/*.json`) are statically imported into the client bundle at build time, ensuring 100% instantaneous offline availability with zero network latency, no runtime API dependencies, and no browser storage quota eviction risks.
- **D-10:** When the device disconnects (`navigator.onLine === false` or API connection failure), a persistent high-visibility amber banner appears below the header: "Offline mode — Emergency calls work via 112. First-aid protocols available below". The "Call 112" button and offline protocol viewer remain fully functional and prominently displayed. The offline `tel:112` action triggers the operating system dialer via standard `tel:` URI and is device/environment dependent (requiring OS telephony/dialer capability); the application must never claim or imply that an emergency call was actually placed, especially during demo mode.
- **D-11:** Protocol instructions render as vertical step-by-step cards with bold step numbering, action icons (Lucide), highlighted imperative instructions, a prominent red/amber "DO NOT" warning callout box, and source citations with the required unreviewed demo disclaimer footer.
- **D-12:** When triage detects multiple clinical conditions (e.g. Unresponsive + Severe Bleeding from trauma), the protocol viewer provides segmented tabs with the primary triage protocol active by default (e.g. CPR) and adjacent tabs for secondary conditions, plus a "Browse All Protocols" drawer for manual search and lookup.

### Duplicate Incident Resolution UX
- **D-13:** When `POST /api/v1/emergencies` returns HTTP `409 Conflict` (`POSSIBLE_DUPLICATE`), the review screen displays a dedicated modal dialog showing proximity and elapsed time (e.g. "Active incident 45m away, reported 2 min ago") with two clear choices: `[Join Existing Incident]` and `[Report as Separate Incident]` (which retries with `force_create: true`).
- **D-14:** Choosing `[Join Existing Incident]` redirects the citizen directly to `/emergency/{existing_emergency_id}` in linked observer mode, allowing them to follow response progress and protocol guidance without dispatching duplicate community volunteers.
- **D-15:** The client generates a unique UUIDv4 `Idempotency-Key` upon entry to `/sos/review` (stored in draft state). The "Send" button is immediately disabled upon click to prevent rapid double-taps, and identical keys are reused across network retries.
- **D-16:** Emergency cancellation and false-alarm handling from `/emergency/:id` is protected by a two-step confirmation sheet requiring a cancellation reason chip (`false_alarm`, `resolved_on_scene`, `called_112_instead`, `other`) before issuing `POST /api/v1/emergencies/{id}/cancel`.

### the agent's Discretion
- Micro-animations: Smooth CSS transitions for button press feedback (1.5s filling ring on `SosButton`), countdown progress animations, and tab transitions.
- Iconography: Semantic Lucide React icon pairings for quick-type chips (Activity, Droplet, AlertTriangle, Shield, HeartPulse, UserX).
- Keyboard Accessibility: Visible high-contrast focus rings (`focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-red-600`), semantic landmarks, and `aria-live="polite"` step announcements.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Master Specification
- `docs/LIFELINK_MASTER_SPEC.md` §0 — Non-negotiable safety rules: Call 112 offline, AI decision-support only, no guarantee language
- `docs/LIFELINK_MASTER_SPEC.md` §3.1 — Citizen User Journey: 1.5s hold, chips, 3 questions, details, preview, send
- `docs/LIFELINK_MASTER_SPEC.md` §8.1 — Citizen API Endpoints (`POST /emergencies`, `GET /emergencies/{id}`, `POST /emergencies/{id}/cancel`)
- `docs/LIFELINK_MASTER_SPEC.md` §8.2 — Triage Preview API (`POST /triage/preview`)
- `docs/LIFELINK_MASTER_SPEC.md` §9.1 — Frontend Design Principles: Light theme only, WCAG AA, touch targets ≥48px, performance budget <200KB gzip
- `docs/LIFELINK_MASTER_SPEC.md` §9.2 — Frontend Route Map (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`, `/login`, `/register`)
- `docs/LIFELINK_MASTER_SPEC.md` §11 — Privacy & Data Protection: Coarse vs exact coordinates
- `docs/LIFELINK_MASTER_SPEC.md` §13.5 — 19-Step Demo Walkthrough Steps 1 to 7 (Citizen creation through dispatch)
- `docs/LIFELINK_MASTER_SPEC.md` §18 — Phase 6 Tasks, Acceptance Criteria, and Definition of Done

### Architecture & Protocols
- `docs/ADR-001-deployment.md` — Stateless Serverless HTTP Polling & Client Reconnection Architecture
- `shared/protocols/*.json` — 7 pre-reviewed clinical emergency protocol JSONs (Burns, Choking, General, Seizure, Bleeding, Fall, Unresponsive)
- `shared/taxonomy.json` — Categorization and skill requirements taxonomy

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/web/src/lib/usePolling.ts`: Existing robust HTTP polling hook with exponential backoff and error tracking.
- `apps/web/src/components/ReconnectionBanner.tsx`: Offline and reconnection banner component.
- `apps/web/src/types/taxonomy.ts`: Shared TypeScript taxonomy and skill types.
- `shared/protocols/*.json`: Complete protocol definitions ready for static TypeScript import.

### Established Patterns
- Strict light theme styling with Tailwind CSS utility classes and semantic color variables (`#f8fafc` background, `#0f172a` text, `#dc2626` emergency red).
- Responsive mobile container constrained to 360px-480px width for stress-proof mobile ergonomics.
- httpOnly cookie session authentication (`ll_session`) with `credentials: "include"` on all `fetch` requests.

### Integration Points
- Backend Auth Router: `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- Backend Triage Router: `POST /api/v1/triage/preview` for generating live triage preview on `/sos/review`.
- Backend Emergency Router: `POST /api/v1/emergencies` (with `Idempotency-Key` and `force_create: true` on duplicate override), `GET /api/v1/emergencies/{id}`, `POST /api/v1/emergencies/{id}/cancel`.

</code_context>

<specifics>
## Specific Ideas

- Ensure Appendix B walkthrough sequence starts cleanly: Citizen opens app -> holds SOS for 1.5s -> completes confirmation -> enters "Accident/Fall" with text "A person fell from a bike and is not responding. There is heavy bleeding." -> receives UNRESPONSIVE and SEVERE_BLEEDING preview -> submits emergency -> initiates parallel dispatch.
- Fast Dispatch safety pipeline invariant: Triggering `[Send Now (Instant Fast Dispatch)]` immediately invokes `POST /api/v1/emergencies`, entering the full existing backend safety pipeline (Create emergency → deterministic triage rules → Phase 4 eligibility/filtering → Phase 4 scoring/ranking → parallel community/professional dispatch → offer/cascade). It must NEVER directly dispatch the nearest responder or bypass Phase 3/4 safety and orchestration logic.
- Dynamic accuracy & demo location distinction: Display browser-provided geolocation accuracy when available (e.g. `±{accuracy}m`), or display "Accuracy unavailable" if absent. In demo mode, clearly distinguish simulated/fallback location from real GPS via distinct badges.
- Visually explicit fallback coordinates: If GPS permission is denied or unavailable, `DEMO_CENTER_LAT/LNG` is visually explicit and labelled as "Demo location used — GPS unavailable", never implying it is the user's real location.
- Non-network "Call 112" control: Permanently floating or pinned at the bottom of the viewport with a red border, clear phone icon, and direct `href="tel:112"`. The action is device/environment dependent (requires OS telephony/dialer capability), and the application must never claim or imply that an emergency call was actually placed during demo mode.

</specifics>

<deferred>
## Deferred Ideas

- Full live tracking map with simulated moving responder/ambulance markers and real-time event timeline (deferred to Phase 8).
- Responder dashboard, incoming offer modal, and ambulance console (deferred to Phase 7).
- Authority verification queue, live board, and printable handover packet UI (deferred to Phase 9).
- Multilingual i18n support (Hindi/Marathi) and full PWA service worker shell (deferred to stretch Phase 12).

</deferred>

---

*Phase: 06-frontend-foundation-and-citizen-sos-flow*  
*Context gathered: 2026-10-01*  
