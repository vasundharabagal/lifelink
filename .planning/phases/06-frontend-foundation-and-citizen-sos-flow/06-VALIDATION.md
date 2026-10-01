---
phase: 6
slug: 06-frontend-foundation-and-citizen-sos-flow
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.x + React Testing Library + jsdom |
| **Config file** | `apps/web/vite.config.ts` |
| **Quick run command** | `npm --prefix apps/web test -- --run` |
| **Full suite command** | `npm --prefix apps/web test -- --run && npm --prefix apps/web run build` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm --prefix apps/web test -- --run`
- **After every plan wave:** Run `npm --prefix apps/web test -- --run && npm --prefix apps/web run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CITIZEN-01, CITIZEN-02 | T-06-02 | Persistent Header, Call 112 button with `tel:112`, and light-theme tokens | unit/component | `npm --prefix apps/web test -- Layout.test.tsx` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | AUTH-01, AUTH-02 | T-06-04 | Session auth client, login/register forms, cookie credentials, error envelope | unit/component | `npm --prefix apps/web test -- Auth.test.tsx` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | CITIZEN-01 | T-06-01, T-06-02 | 1.5s press-and-hold trigger, early release abort, 10s auto-cancel countdown | component | `npm --prefix apps/web test -- SosButton.test.tsx` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | CITIZEN-03 | T-06-05 | Quick-type chips, skippability, 3 tri-state questions, victim selector | component | `npm --prefix apps/web test -- TriageSteps.test.tsx` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | CITIZEN-03 | T-06-03 | GPS auto-capture, dynamic accuracy display, draggable pin, explicit fallback badging | component | `npm --prefix apps/web test -- LocationPicker.test.tsx` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | CITIZEN-04 | T-06-01 | Triage preview card, client UUIDv4 idempotency key, double-tap prevention | component | `npm --prefix apps/web test -- ReviewCard.test.tsx` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 3 | CITIZEN-04 | T-06-01, T-06-04 | 409 duplicate dialog (join vs force) and 2-step cancellation modal | component | `npm --prefix apps/web test -- EmergencyModals.test.tsx` | ❌ W0 | ⬜ pending |
| 06-03-03 | 03 | 3 | CITIZEN-05 | T-06-01 | Static build-time protocols, multi-protocol tabs, DO NOT box, offline banner | component | `npm --prefix apps/web test -- Protocols.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/web/package.json` — install `react-router-dom`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
- [ ] `apps/web/vite.config.ts` — configure Vitest with `environment: 'jsdom'`
- [ ] `apps/web/src/test/setup.ts` — setup file for `@testing-library/jest-dom` and mocks (navigator.geolocation, navigator.vibrate)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Physical Haptic Vibration | CITIZEN-01 | Physical vibration motor required | Hold SOS button on Android phone; verify haptic click and pulse |
| Native Telephony Dialer Launch | CITIZEN-02 | Physical dialer application required | Tap "Call 112" on phone; verify dialer opens with 112 pre-dialed |
| Real 360px Viewport Ergonomics | CITIZEN-01 | Human touch ergonomics | Test SOS workflow on 360px screen; confirm all buttons ≥48px |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-01
