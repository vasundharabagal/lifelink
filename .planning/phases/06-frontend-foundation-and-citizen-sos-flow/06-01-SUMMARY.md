---
plan: "06-01"
phase: "06"
status: "complete"
completed_at: "2026-10-01T07:04:00Z"
tests_passed: 13
tests_failed: 0
self_check: "PASSED"
key-files:
  created:
    - apps/web/src/test/setup.ts
    - apps/web/src/lib/strings.ts
    - apps/web/src/lib/api.ts
    - apps/web/src/context/AuthContext.tsx
    - apps/web/src/components/ui/Button.tsx
    - apps/web/src/components/ui/Card.tsx
    - apps/web/src/components/layout/Call112Button.tsx
    - apps/web/src/components/layout/OfflineBanner.tsx
    - apps/web/src/components/layout/Header.tsx
    - apps/web/src/features/auth/pages/LoginPage.tsx
    - apps/web/src/features/auth/pages/RegisterPage.tsx
    - apps/web/src/test/Layout.test.tsx
    - apps/web/src/test/Auth.test.tsx
  modified:
    - apps/web/package.json
    - apps/web/vite.config.ts
    - apps/web/src/index.css
    - apps/web/src/main.tsx
    - apps/web/src/App.tsx
---

# Plan 06-01 Execution Summary

## What was built

### Task 1 — Vitest test infrastructure
- Installed `react-router-dom@^7.18.4`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`
- Added `"test": "vitest run"` and `"test:watch": "vitest"` scripts to `package.json`
- Configured Vitest in `vite.config.ts` with `environment: 'jsdom'`, `globals: true`, `setupFiles`, and `css: false` (prevents Leaflet/Tailwind CSS import hangs)
- Created `src/test/setup.ts` with `@testing-library/jest-dom` import, `window.matchMedia` mock, `navigator.geolocation` mock, and `navigator.vibrate` mock

### Task 2 — Design system, UI primitives, strings
- Updated `index.css`: strict `color-scheme: light`, WCAG focus ring utility, `.touch-target` min 48×48px, Leaflet container override
- Moved `'leaflet/dist/leaflet.css'` import to `main.tsx` (browser-only entry point) to avoid Vitest jsdom hang
- Created `src/lib/strings.ts`: all safety-critical copywriting constants (`CALL_112_LABEL`, `CALL_112_SUBTITLE`, `GPS_FALLBACK_BADGE`, `ACCURACY_UNAVAILABLE`, etc.)
- Created `src/components/ui/Button.tsx`: min-h-[48px] min-w-[48px], variants (primary/emergency/secondary/ghost), loading spinner, WCAG focus ring
- Created `src/components/ui/Card.tsx`: bg-white, rounded-2xl, slate border, shadow-sm

### Task 3 — Header, Call112Button, OfflineBanner
- Created `Call112Button.tsx`: fixed-bottom `<a href="tel:112">` with min-h-[52px] bg-red-600, device-dialer disclaimer subtitle ("Works offline"), focus ring. **Never claims call was placed.**
- Created `OfflineBanner.tsx`: listens to `online`/`offline` window events, amber sticky banner with WifiOff icon, `role="alert"` + `aria-live="assertive"`
- Created `Header.tsx`: sticky top-0, LIFELINK red brand, DEMO MODE amber pill when demo session detected, auth status/logout link

### Task 4 — API client, AuthContext, login/register, routing
- Created `src/lib/api.ts`: typed `api.get/post/patch/delete` with `credentials: "include"`, FastAPI error envelope parsing, `ApiError` class
- Created `src/context/AuthContext.tsx`: `User` interface (id/email/full_name/role/is_active), session fetch on mount via `GET /api/v1/auth/me`, `login()`/`register()`/`logout()` with error propagation
- Created `LoginPage.tsx`: email+password form, error alert banner, quick-fill buttons for demo credentials (citizen.maya@demo, asha.nurse@demo)
- Created `RegisterPage.tsx`: name+email+password+role selector, POST /api/v1/auth/register
- Updated `App.tsx`: `BrowserRouter` + `AuthProvider` wrapper, routes for `/`, `/login`, `/register`, `/sos/*`, persistent `Call112Button`, `Header`, `OfflineBanner`

## Test results

```
Test Files  2 passed (2)
Tests  13 passed (13)
Duration  14.20s
```

- `Layout.test.tsx` — 9 tests: Call112Button href, label, subtitle, id; OfflineBanner online/offline toggle; Header brand text and DEMO pill
- `Auth.test.tsx` — 4 tests: form renders, login submission, demo quick-fill, error banner

## Notable deviations

- `css: false` added to Vitest config to prevent Vitest/jsdom hang when Tailwind or Leaflet CSS @import is encountered during module graph traversal
- `leaflet/dist/leaflet.css` import moved from `index.css` to `main.tsx` (browser-only entry) — tests don't import `main.tsx`

## Self-Check: PASSED

All 13 tests pass. All 4 tasks committed individually. SUMMARY.md ready for orchestrator.
