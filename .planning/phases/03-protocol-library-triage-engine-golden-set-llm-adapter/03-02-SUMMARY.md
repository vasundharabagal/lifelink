# Phase 3 Plan 02 Summary: Tier 2 LLM Extractor, XML Injection Defense, and Triage Preview API

**Executed:** 2026-10-01  
**Status:** Completed  
**Requirements Covered:** `TRIAGE-04`  
**Tests:** 6 passed in `test_llm_adapter.py` (75 passed across entire backend suite)  

---

## 1. Overview of Work Completed

Plan 03-02 implemented the optional Tier 2 LLM extractor with XML prompt containment, provider adapters, the escalate-only safety invariant, and the citizen preview endpoint:

1. **Config Settings (`TRIAGE-04`, D-41, D-42, D-43)**:
   - Added `LLM_PROVIDER` (default `"none"`), `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `LLM_TIMEOUT_SECONDS` (4.0s), `LLM_RETRY_TIMEOUT_SECONDS` (1.5s), and `DEMO_DISABLE_LLM` (True).

2. **Base Extractor & Prompt Containment Framing (`TRIAGE-04`, D-45, D-46, D-47)**:
   - Built `backend/app/triage/extractor.py`:
     - `LLMExtractionPayload`: Pydantic schema with `extra="forbid"` restricted to `ConditionCode` and `EmergencyType`.
     - `build_extraction_prompt`: Frames untrusted citizen text inside `<untrusted_emergency_description>` XML tags with explicit system instructions to treat content as data, forbid obeying instructions/role overrides, and output strictly closed-enum JSON without markdown or prose.
     - `BaseLLMExtractor`: Abstract async interface.

3. **Pluggable Provider Adapters (`TRIAGE-04`, D-41, D-42)**:
   - Built `backend/app/triage/llm_adapter.py`:
     - `NoneExtractor`: Offline default, returns empty payload with 0 latency.
     - `GeminiExtractor`: REST client to Google Gemini API using `httpx.AsyncClient` with `responseMimeType: "application/json"`.
     - `OpenAIExtractor`: REST client to OpenAI-compatible endpoints (`/chat/completions`) supporting OpenAI, Groq, and local Ollama.
     - Budget enforcement: 4.0-second total timeout with at most 1 fast retry (1.5s) on timeout or HTTP 5xx. Gracefully returns `fallback_triggered=True` on any network or parsing error.
     - `get_llm_extractor`: Factory returning provider based on config or `NoneExtractor` in demo mode.

4. **Unified Triage Service & Escalate-Only Invariant (`TRIAGE-04`, D-44)**:
   - Built `backend/app/triage/service.py`:
     - Runs Tier 1 rules engine as baseline authority.
     - Programmatic union: merges LLM condition tokens with Tier 1 observed conditions.
     - Deterministic re-evaluation: re-runs rules engine over merged conditions.
     - Escalate-only safety check: verifies priority rank is equal or higher urgency than Tier 1; clamps any anomaly to Tier 1; retains all red flags and ambulance requirements.
     - On LLM failure or timeout: logs `TRIAGE_LLM_FALLBACK` audit event and falls back to Tier 1 rules seamlessly.

5. **Triage Preview Endpoint & Rate Limiting (Spec §8.2, §8.8)**:
   - Added `check_triage_preview_rate_limit` in `backend/app/services/rate_limiter.py` (20 calls per user per 10 minutes).
   - Built `POST /api/v1/triage/preview` in `backend/app/api/v1/triage.py` for citizen preview without persisting emergency incidents.
   - Registered `triage_router` in `backend/app/api/v1/__init__.py`.

---

## 2. Verification Results

- `pytest backend/tests/test_llm_adapter.py -v`: 6 passed in 0.88s.
- `pytest backend/tests/test_clock.py -k test_no_direct_datetime_now -v`: 1 passed (0 direct datetime.now calls).
- `pytest backend/tests/ -q`: 75 passed.

---

## 3. Key Artifacts Produced

- `backend/app/core/config.py` (added LLM settings)
- `backend/app/triage/extractor.py`
- `backend/app/triage/llm_adapter.py`
- `backend/app/triage/service.py`
- `backend/app/services/rate_limiter.py` (added `check_triage_preview_rate_limit`)
- `backend/app/api/v1/triage.py`
- `backend/app/api/v1/__init__.py`
- `backend/tests/test_llm_adapter.py`
