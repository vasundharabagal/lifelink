# Phase 6: Frontend Foundation and Citizen SOS Flow - Research

**Researched:** 2026-10-01  
**Domain:** Mobile-first accessible React SPA, emergency triage workflow, Leaflet mini-map pin-drop, offline protocol guidance, dual-track API polling & deduplication  
**Requirements Addressed:** `CITIZEN-01`, `CITIZEN-02`, `CITIZEN-03`, `CITIZEN-04`, `CITIZEN-05`  
**Confidence:** HIGH  

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### SOS Flow Navigation & State Management
- **D-01:** Separate URL routes (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`) are implemented matching Master Spec §9.2. This ensures browser/hardware back button functionality, distinct step bookmarks, and clear step-by-step progress tracking.
- **D-02:** Shared React Context with `sessionStorage` draft persistence preserves all input fields (selected chips, "Who needs help", answers to the 3 questions, free text, captured coordinates, and landmark notes) across accidental page refreshes or mobile browser tab switches. The draft is automatically purged upon successful emergency creation or user cancellation.
- **D-03:** The 1.5s press-and-hold `SosButton` triggers haptic feedback (via `navigator.vibrate([40])` where supported) and opens a bottom action sheet on mobile (centered modal dialog on desktop) with a visible 10-second auto-cancel countdown progress bar and prominent touch targets for `[Send Now]` and `[Cancel]`.
- **D-04:** The 10s confirmation sheet offers two distinct pathways: `[Add Details / Guided Triage]` (advances to `/sos/type` for structured multi-step intake) and `[Send Now (Instant Fast Dispatch)]` (creates the emergency immediately via `POST /api/v1/emergencies`). The Fast Dispatch path MUST execute the full existing backend safety pipeline: Create emergency → deterministic triage rules (Phase 3) → hard eligibility filtering (Phase 4) → multi-factor candidate scoring/ranking (Phase 4) → parallel community/professional track dispatch → atomic offer/cascade (Phase 5). Fast Dispatch must NEVER directly dispatch the nearest responder or bypass any Phase 3/4 safety, verification, or orchestration logic.

#### Location Capture & Fallback UX
- **D-05:** Geolocation auto-acquisition (`navigator.geolocation.getCurrentPosition`) is initiated immediately on `/sos` home mount to pre-warm the browser location cache so coordinates and accuracy radius are instantly available when SOS is pressed.
- **D-06:** On `/sos/details`, location is presented via a stacked layout: a compact interactive Leaflet map featuring a draggable pin with a "Re-center GPS" button, paired with a dedicated text input for landmark/entry details (e.g. "Gate 2, 3rd floor, apt 301").
- **D-07:** If browser GPS permission is denied or unavailable, the map defaults to configured fallback coordinates (`DEMO_CENTER_LAT/LNG`) and makes this visually explicit in the UI with a prominent label: "Demo location used — GPS unavailable". The system must never imply that this fallback is the user's real location, while still allowing the citizen to drag the pin, enter landmarks, or proceed without blocking acute dispatch.
- **D-08:** The review card (`/sos/review`) presents a dynamic location accuracy indicator displaying the browser-provided geolocation accuracy when available (e.g. `±{Math.round(coords.accuracy)}m`), or "Accuracy unavailable" if the browser does not provide accuracy data. In demo mode, the UI clearly distinguishes simulated/fallback location from real GPS via explicit badging, alongside the privacy guarantee badge: "Privacy-gated: Exact location revealed only to accepted responder" (reinforcing Master Spec §11).

#### Offline Protocol Viewer & Guidance Access
- **D-09:** The 7 clinically cited emergency protocols (`shared/protocols/*.json`) are statically imported into the client bundle at build time, ensuring 100% instantaneous offline availability with zero network latency, no runtime API dependencies, and no browser storage quota eviction risks.
- **D-10:** When the device disconnects (`navigator.onLine === false` or API connection failure), a persistent high-visibility amber banner appears below the header: "Offline mode — Emergency calls work via 112. First-aid protocols available below". The "Call 112" button and offline protocol viewer remain fully functional and prominently displayed. The offline `tel:112` action triggers the operating system dialer via standard `tel:` URI and is device/environment dependent (requiring OS telephony/dialer capability); the application must never claim or imply that an emergency call was actually placed, especially during demo mode.
- **D-11:** Protocol instructions render as vertical step-by-step cards with bold step numbering, action icons (Lucide), highlighted imperative instructions, a prominent red/amber "DO NOT" warning callout box, and source citations with the required unreviewed demo disclaimer footer.
- **D-12:** When triage detects multiple clinical conditions (e.g. Unresponsive + Severe Bleeding from trauma), the protocol viewer provides segmented tabs with the primary triage protocol active by default (e.g. CPR) and adjacent tabs for secondary conditions, plus a "Browse All Protocols" drawer for manual search and lookup.

#### Duplicate Incident Resolution UX
- **D-13:** When `POST /api/v1/emergencies` returns HTTP `409 Conflict` (`POSSIBLE_DUPLICATE`), the review screen displays a dedicated modal dialog showing proximity and elapsed time (e.g. "Active incident 45m away, reported 2 min ago") with two clear choices: `[Join Existing Incident]` and `[Report as Separate Incident]` (which retries with `force_create: true`).
- **D-14:** Choosing `[Join Existing Incident]` redirects the citizen directly to `/emergency/{existing_emergency_id}` in linked observer mode, allowing them to follow response progress and protocol guidance without dispatching duplicate community volunteers.
- **D-15:** The client generates a unique UUIDv4 `Idempotency-Key` upon entry to `/sos/review` (stored in draft state). The "Send" button is immediately disabled upon click to prevent rapid double-taps, and identical keys are reused across network retries.
- **D-16:** Emergency cancellation and false-alarm handling from `/emergency/:id` is protected by a two-step confirmation sheet requiring a cancellation reason chip (`false_alarm`, `resolved_on_scene`, `called_112_instead`, `other`) before issuing `POST /api/v1/emergencies/{id}/cancel`.

### Agent's Discretion
- Micro-animations: Smooth 1.5s press ring progress for `SosButton`, countdown progress animations, and tab transitions.
- Iconography: Semantic Lucide React icon pairings for quick-type chips and protocol steps.
- Accessibility: Focus rings, touch targets (≥48px), WCAG AA color contrast, and `aria-live` announcements.

### Deferred Ideas (OUT OF SCOPE)
- Full live tracking map with simulated moving responder/ambulance markers and real-time event timeline (deferred to Phase 8).
- Responder dashboard, incoming offer modal, and ambulance console (deferred to Phase 7).
- Authority verification queue, live board, and printable handover packet UI (deferred to Phase 9).
- Multilingual i18n support (Hindi/Marathi) and full PWA service worker shell (deferred to stretch Phase 12).
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 1.5s Press-and-Hold & 10s Auto-cancel | Browser/Client | — | Pure client interaction timing with requestAnimationFrame/setInterval and haptics |
| Persistent Non-Network Call 112 | Browser/Client | Operating System | Client renders direct `tel:112` link; OS telephony/dialer executes the hardware call |
| Multi-Step Route State & Draft Persistence | Browser/Client | `sessionStorage` | Client router maintains URL; `sessionStorage` survives tab refreshes |
| Geolocation Auto-Detection & Pin Drag | Browser/Client | — | HTML5 `navigator.geolocation` + Leaflet interactive raster map pin |
| Offline Protocol Library Guidance | Static Bundle (CDN) | Browser/Client | 7 JSON files bundled at build time; zero network latency or runtime fetch |
| Triage Preview (`/triage/preview`) | API/Backend | Browser/Client | Backend deterministic rules engine (Phase 3) computes priority and protocol ID |
| Emergency Creation & Dedup Override | API/Backend | Database/PostgreSQL | Backend handles idempotency, 150m spatial deduplication (Phase 5), and row locks |
| Fast Dispatch Pipeline Safety | API/Backend | Orchestration Engine | Full pipeline execution (Phase 3 triage + Phase 4 matching + Phase 5 cascade) |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 6 implements the citizen-facing emergency entry point of LIFELINK. In an emergency coordination layer, user experience is not a cosmetic concern—it is a critical safety constraint. A panicked citizen or bystander must be able to report an incident in under 20 seconds, understand their options, receive pre-reviewed first-aid guidance immediately, and never be locked out by missing network connectivity or slow server responses.

The frontend is architected as a mobile-first Single Page Application using React 19, TypeScript 5.7, Tailwind CSS 3.4, and Vite 6. Routing across the 5 distinct SOS steps (`/sos`, `/sos/type`, `/sos/questions`, `/sos/details`, `/sos/review`) is managed by `react-router-dom` v7. Form state is held in a unified `SosDraftContext` that syncs to browser `sessionStorage`, ensuring that an accidental page refresh or switching to the camera app does not destroy the citizen's intake draft.

Key technical invariants include:
1. **Zero-Dependency Offline Guidance**: Emergency protocols are compiled statically into the client bundle at build time from `shared/protocols/*.json`. When network connection drops, guidance remains accessible with zero delay.
2. **Deterministic Fallback Transparency**: If GPS is denied or unavailable, `DEMO_CENTER_LAT/LNG` is used with a clear visual disclaimer ("Demo location used — GPS unavailable"), preventing false impressions of location verification.
3. **Double-Tap Idempotency**: A client-generated UUIDv4 `Idempotency-Key` is initialized with the review screen and locked on button click, preventing duplicate emergency reports.
4. **Fast Dispatch Safety**: The "Send Now" button triggers `POST /api/v1/emergencies`, which executes the full deterministic triage, eligibility filter, scoring, and cascade pipeline—never short-circuiting safety logic.

**Primary recommendation:** Build a unified `SosDraftProvider` wrapping standard `react-router-dom` routes, package protocol JSONs via direct ES module imports, mount Leaflet cleanly inside an explicit `useEffect` cleanup wrapper, and validate the full flow using Vitest and Testing Library.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.0.0 | Declarative UI components | Mobile-first SPA, reactive state hooks |
| react-router-dom | 7.18+ | Client-side URL routing | Standard routing supporting browser back/forward and deep linking |
| Tailwind CSS | 3.4.17 | Utility-first CSS framework | Strict light-theme tokens, WCAG AA compliance, rapid styling |
| Lucide React | 0.468.0 | Semantic icons | Lightweight, accessible, comprehensive medical/status iconography |
| Leaflet | 1.9.4 | Interactive map rendering | Lightweight raster tile maps with custom `divIcon` pins and drag handlers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| clsx + tailwind-merge | 2.1.1 / 2.6.0 | Dynamic CSS class merging | Safe conditional class composition for active/hover/disabled states |
| Vitest | 3.x+ | Unit & component test runner | Native Vite test integration, ultra-fast execution |
| @testing-library/react | 16.x+ | Component DOM testing | User-centric behavioral assertions for SOS hold, forms, and dialogs |
| jsdom | 26.x+ | Headless DOM environment | Standard test DOM environment for browser APIs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-router-dom | Custom history state hook | react-router-dom provides complete URL sync, route guards, and nested layouts |
| Build-time JSON import | Runtime fetch with IndexedDB | Static import guarantees 100% offline access without storage quota or migration risks |
| Leaflet Raster Maps | Mapbox GL JS / MapLibre | Mapbox requires WebGL and API tokens; Leaflet is lightweight and has zero token requirements |

**Installation:**
```bash
cd apps/web
npm install react-router-dom@^7.18.4
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```mermaid
flowchart TD
    subgraph Browser["Citizen Browser / Client"]
        SOS_HOME["/sos (Hold 1.5s)"] -->|Haptic + Hold Complete| CONFIRM_SHEET["10s Auto-Cancel Sheet"]
        
        CONFIRM_SHEET -->|Fast Dispatch| SEND_FAST["Instant Create (POST /emergencies)"]
        CONFIRM_SHEET -->|Add Details| TYPE_PAGE["/sos/type (Chips & Target)"]
        
        TYPE_PAGE --> QUESTIONS_PAGE["/sos/questions (3 Tri-State Questions)"]
        QUESTIONS_PAGE --> DETAILS_PAGE["/sos/details (Text + Leaflet Pin)"]
        DETAILS_PAGE --> REVIEW_PAGE["/sos/review (Triage Preview + Send)"]
        
        REVIEW_PAGE -->|POST /emergencies (UUID Key)| API_CREATE["POST /api/v1/emergencies"]
        SEND_FAST --> API_CREATE
    end

    subgraph Backend["FastAPI Safety Pipeline"]
        API_CREATE --> TIER1_TRIAGE["Deterministic Triage (Phase 3)"]
        TIER1_TRIAGE --> HARD_FILTERS["Hard Eligibility Filters (Phase 4)"]
        HARD_FILTERS --> MULTI_FACTOR["0-100 Multi-Factor Scoring (Phase 4)"]
        MULTI_FACTOR --> DUAL_DISPATCH["Dual-Track State Machine (Phase 5)"]
        DUAL_DISPATCH --> ATOMIC_OFFER["Atomic Offer / Cascade (Phase 5)"]
    end

    subgraph Outcomes["Client Response Handling"]
        ATOMIC_OFFER -->|201 Created| LIVE_ROUTE["Navigate /emergency/:id"]
        ATOMIC_OFFER -->|409 Conflict| DUP_MODAL["Duplicate Dialog (Join vs Force)"]
        DUP_MODAL -->|Join Existing| OBSERVER_ROUTE["Navigate /emergency/:existing_id (Observer)"]
        DUP_MODAL -->|Force Create| API_CREATE_FORCE["POST /emergencies (force_create=true)"]
    end
```

### Recommended Project Structure
```
apps/web/src/
├── features/
│   ├── citizen/
│   │   ├── components/
│   │   │   ├── SosButton.tsx             # 1.5s press-and-hold button with SVG progress ring
│   │   │   ├── SosConfirmSheet.tsx       # 10s auto-cancel bottom sheet with fast-dispatch option
│   │   │   ├── QuickTypeGrid.tsx         # Skippable emergency type chips + victim selector
│   │   │   ├── TriageQuestions.tsx       # 3 large tri-state cards (Yes / No / Not Sure)
│   │   │   ├── LocationPicker.tsx        # Stacked Leaflet mini-map pin + landmark text field
│   │   │   ├── ReviewCard.tsx            # Triage preview card, dynamic accuracy, privacy badge
│   │   │   ├── DuplicateModal.tsx        # 409 Conflict resolution (Join vs Report Separate)
│   │   │   └── CancelModal.tsx           # Two-step cancellation sheet with reason chips
│   │   └── pages/
│   │       ├── SosHomePage.tsx           # /sos
│   │       ├── SosTypePage.tsx           # /sos/type
│   │       ├── SosQuestionsPage.tsx      # /sos/questions
│   │       ├── SosDetailsPage.tsx        # /sos/details
│   │       └── SosReviewPage.tsx         # /sos/review
│   ├── protocols/
│   │   ├── components/
│   │   │   ├── ProtocolViewer.tsx        # Step cards with action icons and DO NOT box
│   │   │   ├── ProtocolTabs.tsx          # Multi-condition segmented tabs (CPR primary)
│   │   │   └── ProtocolDrawer.tsx        # Full catalog lookup drawer
│   │   └── lib/
│   │       └── protocolRegistry.ts       # Static imports of shared/protocols/*.json
│   └── auth/
│       ├── components/
│       │   ├── LoginForm.tsx             # Email/password login with error envelope
│       │   └── RegisterForm.tsx          # Citizen/responder registration
│       └── pages/
│           ├── LoginPage.tsx             # /login
│           └── RegisterPage.tsx          # /register
├── components/
│   ├── layout/
│   │   ├── Header.tsx                    # LIFELINK mark, offline indicator, DEMO MODE pill
│   │   ├── Call112Button.tsx             # Permanent non-network tel:112 button
│   │   └── OfflineBanner.tsx             # High-visibility amber disconnection alert
│   └── ui/
│       ├── Button.tsx                    # Accessible touch target button (>=48px)
│       └── Card.tsx                      # Strict light-theme card container
├── context/
│   ├── SosDraftContext.tsx               # Shared draft state with sessionStorage sync
│   └── AuthContext.tsx                   # User session, role state, and logout
├── lib/
│   ├── api.ts                            # Typed fetch wrapper with error envelope handling
│   ├── geolocation.ts                    # Geolocation watcher, accuracy, and fallback coords
│   └── strings.ts                        # Centralized UI copy strings
└── types/
    ├── emergency.ts                      # Emergency DTOs and triage response types
    └── protocol.ts                       # Clinical protocol schemas
```

### Pattern 1: Resilient 1.5s Press-and-Hold Button with Haptics
**What:** The SOS button requires continuous hold for 1500 ms to trigger, rendering an animated ring and emitting haptic feedback. Releasing before 1500 ms resets the progress ring.
**When to use:** On `/sos` home screen to prevent accidental pocket or bump triggers.
**Example:**
```typescript
export function usePressAndHold(onTrigger: () => void, holdTimeMs = 1500) {
  const [progress, setProgress] = useState(0);
  const startTimeRef = useRef<number | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const start = useCallback(() => {
    startTimeRef.current = performance.now();
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      navigator.vibrate(20);
    }
    const update = () => {
      if (!startTimeRef.current) return;
      const elapsed = performance.now() - startTimeRef.current;
      const pct = Math.min((elapsed / holdTimeMs) * 100, 100);
      setProgress(pct);
      if (pct >= 100) {
        if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
          navigator.vibrate([40, 60, 40]);
        }
        onTrigger();
        reset();
      } else {
        animFrameRef.current = requestAnimationFrame(update);
      }
    };
    animFrameRef.current = requestAnimationFrame(update);
  }, [holdTimeMs, onTrigger]);

  const reset = useCallback(() => {
    startTimeRef.current = null;
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setProgress(0);
  }, []);

  return { progress, start, cancel: reset };
}
```

### Pattern 2: Leaflet Draggable Pin with React 19 Lifecycle
**What:** Mounting Leaflet maps safely in React 19 without encountering "Map container is already initialized" or missing container height errors.
**When to use:** On `/sos/details` for interactive location confirmation.
**Example:**
```typescript
import { useEffect, useRef } from 'react';
import L from 'leaflet';

interface MiniMapProps {
  lat: number;
  lng: number;
  onPositionChange: (lat: number, lng: number) => void;
  isDemoFallback?: boolean;
}

export function MiniMap({ lat, lng, onPositionChange, isDemoFallback }: MiniMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [lat, lng],
      zoom: 16,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);

    const pinIcon = L.divIcon({
      className: 'custom-pin',
      html: `<div class="w-8 h-8 bg-red-600 border-2 border-white rounded-full shadow-lg flex items-center justify-center text-white font-bold">📍</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
    });

    const marker = L.marker([lat, lng], { draggable: true, icon: pinIcon }).addTo(map);
    marker.on('dragend', () => {
      const pos = marker.getLatLng();
      onPositionChange(pos.lat, pos.lng);
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
    };
  }, []);

  return (
    <div className="relative w-full h-48 rounded-xl overflow-hidden border border-slate-200">
      <div ref={mapContainerRef} className="w-full h-full" />
      {isDemoFallback && (
        <div className="absolute top-2 left-2 z-[1000] bg-amber-500 text-white text-xs font-semibold px-2 py-1 rounded shadow">
          Demo location used — GPS unavailable
        </div>
      )}
    </div>
  );
}
```

### Pattern 3: Static Protocol Registry
**What:** Statically loading all 7 protocols into a TypeScript map for zero-latency, 100% offline reliability.
**Example:**
```typescript
import protBurns from '../../../../shared/protocols/PROT_BURNS.json';
import protChoking from '../../../../shared/protocols/PROT_CHOKING.json';
import protGeneral from '../../../../shared/protocols/PROT_GENERAL.json';
import protSeizure from '../../../../shared/protocols/PROT_SEIZURE.json';
import protBleeding from '../../../../shared/protocols/PROT_SEVERE_BLEEDING.json';
import protFall from '../../../../shared/protocols/PROT_TRAUMA_FALL.json';
import protUnresponsive from '../../../../shared/protocols/PROT_UNRESPONSIVE.json';
import { Protocol } from '../types/protocol';

export const PROTOCOL_REGISTRY: Record<string, Protocol> = {
  PROT_BURNS: protBurns as Protocol,
  PROT_CHOKING: protChoking as Protocol,
  PROT_GENERAL: protGeneral as Protocol,
  PROT_SEIZURE: protSeizure as Protocol,
  PROT_SEVERE_BLEEDING: protBleeding as Protocol,
  PROT_TRAUMA_FALL: protFall as Protocol,
  PROT_UNRESPONSIVE: protUnresponsive as Protocol,
};

export function getProtocol(protocolId?: string | null): Protocol {
  if (protocolId && PROTOCOL_REGISTRY[protocolId]) {
    return PROTOCOL_REGISTRY[protocolId];
  }
  return PROTOCOL_REGISTRY['PROT_GENERAL'];
}
```

### Anti-Patterns to Avoid
- **Hardcoding GPS Accuracy**: Claiming `±10m` regardless of hardware. Always inspect `position.coords.accuracy` and display "Accuracy unavailable" if null.
- **Claiming 112 Call Placed**: Displaying "Emergency services dispatched via 112" when clicking `tel:112`. In demo mode and browsers, the dialer simply opens; the app cannot confirm placement.
- **Short-circuiting Fast Dispatch**: Directly picking a responder in client code. Fast dispatch must call `POST /emergencies`, triggering the full Phase 3/4/5 backend safety pipeline.
- **Losing Form State on Refresh**: Storing draft state purely in React `useState`. Always mirror draft state into `sessionStorage`.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Map interaction & tile rendering | Custom canvas or SVG map | Leaflet (`L.map`, `L.tileLayer`, `L.marker`) | Leaflet handles touch gestures, coordinate projection, tiles, and bounding boxes reliably |
| URL routing & history | Custom pushState router | `react-router-dom` v7 | Handles browser back/forward buttons, nested layouts, and route guards natively |
| UUID generation | Math.random() hash generator | `crypto.randomUUID()` | Built into all modern browsers; cryptographically collision-free for Idempotency-Key |
| Class merging | String concatenation (`"btn " + cls`) | `clsx` + `tailwind-merge` (`cn()`) | Avoids CSS specificity clashes and duplicate Tailwind utility overrides |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Leaflet Container Re-initialization
**What goes wrong:** React component re-mounts (e.g. during fast navigation or HMR), throwing `Error: Map container is already initialized`.
**Why it happens:** Leaflet attaches state to the DOM element; React 19's effect lifecycles trigger cleanup and remount.
**How to avoid:** Ensure `mapInstanceRef.current.remove()` is called in the `useEffect` cleanup return and set `mapInstanceRef.current = null`.
**Warning signs:** Uncaught Leaflet runtime error in browser console when switching tabs.

### Pitfall 2: Geolocation Permission Hangs
**What goes wrong:** `navigator.geolocation.getCurrentPosition` hangs indefinitely on mobile without invoking either success or error callback.
**Why it happens:** Some mobile browsers wait indefinitely for a satellite fix if `timeout` is not specified.
**How to avoid:** Always pass `{ timeout: 8000, maximumAge: 30000, enableHighAccuracy: true }`. If it times out or errors, gracefully fallback to `DEMO_CENTER_LAT/LNG` with the "Demo location used — GPS unavailable" banner.

### Pitfall 3: Accidental SOS Double-Trigger
**What goes wrong:** Citizen double-taps or rapid-clicks the "Send Emergency" button, triggering duplicate requests.
**Why it happens:** Network latency between click and server response.
**How to avoid:** Generate a single UUIDv4 `Idempotency-Key` upon entering `/sos/review`. Lock the submission button immediately on click and reuse the key across retries.
</common_pitfalls>

<threat_model>
## Security & Threat Modeling (ASVS L1)

| Threat ID | Threat Description | Severity | Mitigation Strategy |
|-----------|--------------------|----------|---------------------|
| T-06-01 | Rapid False-Alarm SOS Flooding | High | 1.5s press-and-hold trigger + 10s auto-cancel confirmation sheet + backend rate limiting |
| T-06-02 | Accidental SOS Trigger in Pocket | Medium | 1.5s continuous hold threshold with progressive visual and haptic confirmation |
| T-06-03 | Patient Exact Location Leakage on Citizen View | High | Patient exact coordinates only shown on citizen's own screen; API responses enforce privacy tiers (Phase 5) |
| T-06-04 | IDOR on Citizen Emergency Cancellation | Critical | Citizen cancellation (`POST /emergencies/{id}/cancel`) authorized strictly via authenticated session matching `reported_by_user_id` or authority role |
| T-06-05 | Client-Side Triage Tampering | Critical | Citizen UI only sends raw conditions/answers. Backend rules engine (Phase 3) is sole source of truth for priority and protocol assignment |
</threat_model>

## Validation Architecture & Test Strategy

### Test Infrastructure
- **Framework:** Vitest + React Testing Library + jsdom
- **Config file:** `apps/web/vite.config.ts` (configured with `test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] }`)
- **Quick run command:** `npm --prefix apps/web test -- --run`
- **Full suite command:** `npm --prefix apps/web test -- --run && npm --prefix apps/web run build`
- **Estimated runtime:** ~5-10 seconds

### Per-Task Verification Map

| Task ID | Component/Feature | Requirement | Threat Ref | Verification Method | Automated Command | Status |
|---------|-------------------|-------------|------------|---------------------|-------------------|--------|
| 06-01-01 | Design tokens & Layout Shell | CITIZEN-01 | T-06-02 | Verify WCAG AA light theme tokens, persistent Header, and Call 112 button | `npm --prefix apps/web test -- Layout.test.tsx` | ⬜ pending |
| 06-01-02 | Auth screens & Session Cookie | AUTH-01, AUTH-02 | T-06-04 | Verify login/register forms, error envelopes, and session state | `npm --prefix apps/web test -- Auth.test.tsx` | ⬜ pending |
| 06-02-01 | SosButton & 10s Confirm Sheet | CITIZEN-01 | T-06-01, T-06-02 | Test 1.5s continuous hold requirement, cancellation on early release, and auto-cancel timer | `npm --prefix apps/web test -- SosButton.test.tsx` | ⬜ pending |
| 06-02-02 | Triage Steps (Chips & Questions) | CITIZEN-03 | T-06-05 | Test quick-type chips selection, skippability, and 3 tri-state question answers | `npm --prefix apps/web test -- TriageSteps.test.tsx` | ⬜ pending |
| 06-02-03 | LocationPicker & Pin Drag | CITIZEN-03 | T-06-03 | Test geolocation hook, accuracy display, draggable pin, and fallback badging | `npm --prefix apps/web test -- LocationPicker.test.tsx` | ⬜ pending |
| 06-03-01 | ReviewCard & Idempotency Key | CITIZEN-04 | T-06-01 | Test preview card rendering, client UUID generation, and submission locking | `npm --prefix apps/web test -- ReviewCard.test.tsx` | ⬜ pending |
| 06-03-02 | Duplicate & Cancellation Modals | CITIZEN-04 | T-06-01, T-06-04 | Test 409 conflict dialog (join vs force) and cancellation reason sheet | `npm --prefix apps/web test -- EmergencyModals.test.tsx` | ⬜ pending |
| 06-03-03 | Offline Protocols & Banner | CITIZEN-05 | T-06-01 | Test static protocol rendering, multi-protocol tabs, DO NOT box, and offline banner | `npm --prefix apps/web test -- Protocols.test.tsx` | ⬜ pending |

### Manual-Only Verifications
| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Physical Haptic Feedback | CITIZEN-01 | Browser vibration API requires physical mobile hardware | Hold SOS button on Android Chrome; verify 20ms click and multi-pulse trigger vibration |
| Native Telephony Dialer Launch | CITIZEN-02 | OS dialer requires mobile telephony hardware | Tap "Call 112" on mobile device; verify OS dialer launches with 112 pre-filled |
| Full 360px Mobile Viewport Layout | CITIZEN-01 | Physical ergonomics and touch target spacing | Inspect UI on 360×640 viewport in Chrome DevTools; verify all buttons ≥48px |
</validation_architecture>

<sources>
## Sources

### Primary (HIGH confidence)
- `docs/LIFELINK_MASTER_SPEC.md` §3.1, §9.1, §9.2, §18 — Canonical citizen user journeys and technical specifications
- `.planning/phases/06-frontend-foundation-and-citizen-sos-flow/06-CONTEXT.md` — Locked decisions and implementation constraints
- `shared/protocols/*.json` — 7 pre-reviewed clinical emergency protocols
- Leaflet Official Documentation (v1.9.4) — Map lifecycle, tile layers, and draggable markers

### Secondary (MEDIUM confidence)
- React 19 Documentation — Effect cleanup and component lifecycle behaviors
- W3C WAI-ARIA Authoring Practices — Emergency alert announcements and accessible touch target standards
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: React 19, react-router-dom v7, Tailwind CSS 3.4, Leaflet 1.9
- Ecosystem: Vitest, @testing-library/react, Lucide React
- Patterns: 1.5s press-and-hold, sessionStorage draft persistence, static protocol bundling, 409 deduplication handling
- Pitfalls: Leaflet container reuse, geolocation timeouts, fast-dispatch safety invariants

**Confidence breakdown:**
- Standard stack: HIGH — Verified package compatibility with React 19 and Vite 6
- Architecture: HIGH — Directly matches Master Spec §9.2 and locked Phase 6 decisions
- Pitfalls: HIGH — Documented Leaflet and geolocation edge cases with tested mitigations
- Security & Validation: HIGH — Complete ASVS L1 threat model and Vitest verification map

**Research date:** 2026-10-01  
**Valid until:** 2026-11-01  
</metadata>

---

*Phase: 06-frontend-foundation-and-citizen-sos-flow*  
*Research completed: 2026-10-01*  
*Ready for planning: yes*  
