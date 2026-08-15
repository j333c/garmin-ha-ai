"""Google Gemini AI Engine Provider implementation."""
from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .base import (
    AIEngineError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
    BaseAIProvider,
    async_with_retry,
)

_LOGGER = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Engine Provider using official google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Gemini provider."""
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._client = genai.Client(api_key=api_key)

    async def async_generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        """Generate response asynchronously using google-genai SDK."""

        async def _call_api() -> str:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction
                )

            try:
                response = await self._client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise AIEngineError("Gemini API returned empty response text")
                return response.text
            except genai_errors.APIError as err:
                code = getattr(err, "code", None) or getattr(err, "status_code", None)
                message = str(err)
                if code == 429 or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
                    raise AIEngineQuotaError(f"Gemini API quota exceeded: {message}") from err
                if code in (500, 502, 503, 504) or "503" in message or "500" in message:
                    raise AIEngineError(f"Gemini API server error ({code}): {message}") from err
                raise AIEngineError(f"Gemini API error: {message}") from err
            except TimeoutError as err:
                raise AIEngineTimeoutError("Gemini API request timed out") from err
            except Exception as err:
                if isinstance(err, (AIEngineError, AIEngineQuotaError, AIEngineTimeoutError)):
                    raise
                raise AIEngineError(f"Unexpected error calling Gemini API: {err}") from err

        return await async_with_retry(
            _call_api,
            max_retries=2,
            initial_delay=1.0,
            retry_exceptions=(AIEngineError, TimeoutError),
            exclude_exceptions=(AIEngineQuotaError,),
        )
