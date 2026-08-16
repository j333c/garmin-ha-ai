"""Google Gemini AI Engine Provider implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ..const import DEFAULT_AI_MODEL_GEMINI, FALLBACK_GEMINI_MODELS
from .base import (
    AIEngineClientError,
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
        model: str = DEFAULT_AI_MODEL_GEMINI,
        base_url: str | None = None,
        hass: Any | None = None,
        client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Gemini provider."""
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self.hass = hass
        self._client = client

    async def async_get_client(self) -> genai.Client:
        """Return or instantiate genai.Client asynchronously off the main event loop."""
        if self._client is not None:
            return self._client

        def _init_client() -> genai.Client:
            return genai.Client(api_key=self.api_key)

        if self.hass and hasattr(self.hass, "async_add_executor_job"):
            self._client = await self.hass.async_add_executor_job(_init_client)
        else:
            self._client = await asyncio.to_thread(_init_client)
        return self._client

    async def async_list_models(self) -> list[str]:
        """Discover available content generation models from Gemini API."""
        return await async_list_gemini_models(self.api_key, hass=self.hass, client=self._client)

    async def async_generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        """Generate response asynchronously using google-genai SDK."""
        client = await self.async_get_client()

        async def _call_api() -> str:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction
                )

            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=30.0,
                )
                if not response.text:
                    raise AIEngineError("Gemini API returned empty response text")
                return response.text
            except genai_errors.APIError as err:
                code = getattr(err, "code", None) or getattr(err, "status_code", None)
                message = str(err)
                if code == 429 or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
                    raise AIEngineQuotaError(f"Gemini API quota exceeded: {message}") from err
                if code in (400, 401, 403, 404) or "NOT_FOUND" in message or "not found" in message.lower() or "no longer available" in message.lower() or "INVALID_ARGUMENT" in message:
                    raise AIEngineClientError(f"Gemini API client error ({code}): {message}") from err
                if code in (500, 502, 503, 504) or "503" in message or "500" in message:
                    raise AIEngineError(f"Gemini API server error ({code}): {message}") from err
                raise AIEngineError(f"Gemini API error: {message}") from err
            except (TimeoutError, asyncio.TimeoutError) as err:
                raise AIEngineTimeoutError("Gemini API request timed out") from err
            except Exception as err:
                if isinstance(err, (AIEngineError, AIEngineQuotaError, AIEngineTimeoutError, AIEngineClientError)):
                    raise
                raise AIEngineError(f"Unexpected error calling Gemini API: {err}") from err

        return await async_with_retry(
            _call_api,
            max_retries=2,
            initial_delay=1.0,
            retry_exceptions=(AIEngineError, TimeoutError),
            exclude_exceptions=(AIEngineQuotaError, AIEngineClientError),
        )


async def async_list_gemini_models(
    api_key: str, hass: Any | None = None, client: Any | None = None
) -> list[str]:
    """Fetch available models supporting content generation asynchronously."""
    if not api_key:
        return list(FALLBACK_GEMINI_MODELS)

    def _fetch_models_sync() -> list[str]:
        models_list = []
        try:
            active_client = client or genai.Client(api_key=api_key)
            if hasattr(active_client, "models") and hasattr(active_client.models, "list"):
                for m in active_client.models.list():
                    name = getattr(m, "name", None) or getattr(m, "model", None) or str(m)
                    if name.startswith("models/"):
                        name = name[7:]
                    if "gemini" in name.lower():
                        models_list.append(name)
        except Exception as err:
            _LOGGER.debug("Could not query Gemini models endpoint: %s", err)
        return models_list

    try:
        if hass and hasattr(hass, "async_add_executor_job"):
            discovered = await hass.async_add_executor_job(_fetch_models_sync)
        else:
            discovered = await asyncio.to_thread(_fetch_models_sync)

        if discovered:
            # Combine discovered models with fallback models preserving unique items
            combined = []
            for m in discovered:
                if m not in combined:
                    combined.append(m)
            for m in FALLBACK_GEMINI_MODELS:
                if m not in combined:
                    combined.append(m)
            return combined
    except Exception as err:
        _LOGGER.debug("Error during dynamic Gemini model discovery: %s", err)

    return list(FALLBACK_GEMINI_MODELS)

