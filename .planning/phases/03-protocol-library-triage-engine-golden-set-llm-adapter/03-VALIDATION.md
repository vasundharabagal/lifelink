---
phase: 3
slug: protocol-library-triage-engine-golden-set-llm-adapter
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio against PostgreSQL |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_triage_rules.py` |
| **Full suite command** | `pytest backend/tests/` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test suite for the modified module
- **After every plan wave:** Run full test suite (`pytest backend/tests/`)
- **Before `/gsd-verify-work`:** Full suite must be green (including golden evaluation gate)
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TRIAGE-01 | — | All 7 protocols valid JSON with clinical citations & unreviewed disclaimer | unit | `pytest backend/tests/test_triage_rules.py -k test_protocols_valid` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TRIAGE-02 | T-03-02 | Deterministic classification of priority, ambulance, and required skills | unit | `pytest backend/tests/test_triage_rules.py -k test_rules_classification` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TRIAGE-03 | T-03-02 | Precedence hierarchy selects primary protocol and escalates red-flags to P1 | unit | `pytest backend/tests/test_triage_rules.py -k test_precedence_and_red_flags` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | TRIAGE-03 | T-03-02 | Low confidence (<0.5) or empty input fails safe up to P2 PROT_GENERAL | unit | `pytest backend/tests/test_triage_rules.py -k test_fail_safe_escalation` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | TRIAGE-04 | T-03-04 | Input sanitizer clamps to 500 chars and scrubs PII/control characters | unit | `pytest backend/tests/test_llm_adapter.py -k test_input_sanitizer` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | TRIAGE-04 | T-03-01 | XML containment framing and closed-enum validation against prompt injection | unit | `pytest backend/tests/test_llm_adapter.py -k test_prompt_injection_defense` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | TRIAGE-04 | T-03-03 | 4.0s timeout with fast retry triggers TRIAGE_LLM_FALLBACK cleanly | unit | `pytest backend/tests/test_llm_adapter.py -k test_llm_timeout_fallback` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | TRIAGE-04 | T-03-01 | Programmatic union enforces escalate-only invariant (AI cannot de-escalate) | unit | `pytest backend/tests/test_llm_adapter.py -k test_escalate_only_invariant` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | TRIAGE-05 | — | Standalone CLI runner evaluates golden triage dataset with summary metrics | integration | `python -m app.triage.eval` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | TRIAGE-05 | T-03-02 | Automated Pytest gate asserts 0 unsafe downgrades on golden dataset | integration | `pytest backend/tests/test_triage_eval.py -k test_zero_unsafe_downgrades` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | TRIAGE-05 | T-03-02 | Automated Pytest gate asserts red-flag recall >= 0.95 on golden dataset | integration | `pytest backend/tests/test_triage_eval.py -k test_red_flag_recall_threshold` | ❌ W0 | ⬜ pending |
| 03-03-04 | 03 | 3 | TRIAGE-05 | — | Technical documentation docs/AI_EVAL.md accurately summarizes metrics | manual | `test -f docs/AI_EVAL.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_triage_rules.py` — protocol loading, input sanitization, condition precedence, and rules engine classification
- [ ] `backend/tests/test_llm_adapter.py` — multi-provider extraction, timeout handling, injection containment, and escalate-only invariant
- [ ] `backend/tests/test_triage_eval.py` — CI gate asserting zero unsafe downgrades and >=0.95 red flag recall on golden dataset
- [ ] `backend/tests/golden/golden_triage.jsonl` — 45-case balanced golden triage evaluation dataset

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI evaluation methodology and judge reproduction guide | TRIAGE-05 | Documentation review | Inspect `docs/AI_EVAL.md` for clarity, confusion matrix presentation, and reproduction commands |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-01
