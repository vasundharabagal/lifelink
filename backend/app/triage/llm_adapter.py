"""Concrete LLM provider adapters with timeout budgets and fast retry (Spec §5.6, TRIAGE-04).

Implements multi-provider extraction (Gemini, OpenAI/Groq/Ollama, None) over httpx.
Enforces a 4.0-second total budget and at most 1 fast retry (1.5s), falling back
cleanly to Tier 1 rules on any network or parsing error without stalling SOS dispatch.
"""
import json
import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.triage.extractor import (
    BaseLLMExtractor,
    LLMExtractionPayload,
    LLMExtractionResult,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)


class NoneExtractor(BaseLLMExtractor):
    """Offline default extractor that performs no remote network calls."""

    async def extract(self, sanitized_text: str) -> LLMExtractionResult:
        return LLMExtractionResult(
            success=True,
            payload=LLMExtractionPayload(conditions=[], confidence=0.0),
            raw_response=None,
            fallback_triggered=False,
        )


class GeminiExtractor(BaseLLMExtractor):
    """Google Gemini REST API extractor enforcing 4s budget and JSON schema output."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: Optional[float] = None,
        retry_timeout_s: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout_s = timeout_s or settings.LLM_TIMEOUT_SECONDS
        self.retry_timeout_s = retry_timeout_s or settings.LLM_RETRY_TIMEOUT_SECONDS

    async def extract(self, sanitized_text: str) -> LLMExtractionResult:
        if not self.api_key:
            return LLMExtractionResult(
                success=False,
                error="Gemini API key not configured",
                fallback_triggered=True,
            )

        prompt = build_extraction_prompt(sanitized_text)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }

        # Attempt 1 (initial try) with total budget
        # Attempt 2 (fast retry) with retry timeout if timeout occurs
        for attempt, timeout in enumerate([self.timeout_s, self.retry_timeout_s]):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No candidates returned by Gemini")

                    raw_text = candidates[0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    validated_payload = LLMExtractionPayload.model_validate(parsed)
                    return LLMExtractionResult(
                        success=True,
                        payload=validated_payload,
                        raw_response=raw_text,
                        fallback_triggered=False,
                    )

                if resp.status_code < 500 and attempt == 0:
                    # Client errors (4xx) should not retry
                    return LLMExtractionResult(
                        success=False,
                        error=f"Gemini API returned {resp.status_code}: {resp.text}",
                        fallback_triggered=True,
                    )

            except (httpx.TimeoutException, httpx.NetworkError, json.JSONDecodeError, Exception) as e:
                logger.warning("Gemini extraction attempt %d failed: %s", attempt + 1, e)
                if attempt == 1:
                    # Exhausted retry budget
                    return LLMExtractionResult(
                        success=False,
                        error=str(e),
                        fallback_triggered=True,
                    )

        return LLMExtractionResult(
            success=False,
            error="Gemini extraction timed out after retry",
            fallback_triggered=True,
        )


class OpenAIExtractor(BaseLLMExtractor):
    """OpenAI-compatible REST API extractor (OpenAI, Groq, Ollama) enforcing JSON mode."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: Optional[float] = None,
        retry_timeout_s: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.model = model or settings.OPENAI_MODEL
        self.timeout_s = timeout_s or settings.LLM_TIMEOUT_SECONDS
        self.retry_timeout_s = retry_timeout_s or settings.LLM_RETRY_TIMEOUT_SECONDS

    async def extract(self, sanitized_text: str) -> LLMExtractionResult:
        if not self.api_key:
            return LLMExtractionResult(
                success=False,
                error="OpenAI API key not configured",
                fallback_triggered=True,
            )

        prompt = build_extraction_prompt(sanitized_text)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        for attempt, timeout in enumerate([self.timeout_s, self.retry_timeout_s]):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError("No choices returned by OpenAI API")

                    raw_text = choices[0]["message"]["content"]
                    parsed = json.loads(raw_text)
                    validated_payload = LLMExtractionPayload.model_validate(parsed)
                    return LLMExtractionResult(
                        success=True,
                        payload=validated_payload,
                        raw_response=raw_text,
                        fallback_triggered=False,
                    )

                if resp.status_code < 500 and attempt == 0:
                    return LLMExtractionResult(
                        success=False,
                        error=f"OpenAI API returned {resp.status_code}: {resp.text}",
                        fallback_triggered=True,
                    )

            except (httpx.TimeoutException, httpx.NetworkError, json.JSONDecodeError, Exception) as e:
                logger.warning("OpenAI extraction attempt %d failed: %s", attempt + 1, e)
                if attempt == 1:
                    return LLMExtractionResult(
                        success=False,
                        error=str(e),
                        fallback_triggered=True,
                    )

        return LLMExtractionResult(
            success=False,
            error="OpenAI extraction timed out after retry",
            fallback_triggered=True,
        )


def get_llm_extractor(provider: Optional[str] = None, is_demo: bool = False) -> BaseLLMExtractor:
    """Factory function returning configured provider adapter.
    
    Demo sessions default to NoneExtractor unless explicitly disabled to ensure
    deterministic testing without external API quota consumption (D-43).
    """
    if is_demo and settings.DEMO_DISABLE_LLM:
        return NoneExtractor()

    chosen_provider = (provider or settings.LLM_PROVIDER).strip().lower()

    if chosen_provider == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiExtractor()
        logger.info("GEMINI_API_KEY missing, falling back to NoneExtractor")
        return NoneExtractor()

    if chosen_provider == "openai":
        if settings.OPENAI_API_KEY:
            return OpenAIExtractor()
        logger.info("OPENAI_API_KEY missing, falling back to NoneExtractor")
        return NoneExtractor()

    return NoneExtractor()
