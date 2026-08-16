"""Generic OpenAI-compatible AI Engine Provider implementation."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..const import FALLBACK_OPENAI_MODELS
from .base import (
    AIEngineClientError,
    AIEngineError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
    BaseAIProvider,
    async_with_retry,
)

_LOGGER = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """Generic OpenAI-compatible AI Engine Provider using httpx async client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        timeout: float = 30.0,
        hass: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI provider."""
        url = (base_url or "https://api.openai.com/v1").rstrip("/")
        super().__init__(api_key=api_key, model=model, base_url=url)
        self.timeout = timeout
        self.hass = hass

    async def async_list_models(self) -> list[str]:
        """Discover available models from OpenAI or compatible endpoint."""
        return await async_list_openai_models(
            api_key=self.api_key,
            base_url=self.base_url,
            hass=self.hass,
            timeout=min(self.timeout, 10.0),
        )

    async def async_generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        """Generate response asynchronously via HTTP POST to chat/completions endpoint."""

        async def _call_api() -> str:
            endpoint = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages: list[dict[str, str]] = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)

                if response.status_code == 429:
                    raise AIEngineQuotaError(
                        f"OpenAI API rate limit / quota exceeded (429): {response.text}"
                    )

                if response.status_code in (400, 401, 403, 404):
                    raise AIEngineClientError(
                        f"OpenAI API client error ({response.status_code}): {response.text}"
                    )

                if response.status_code >= 500:
                    raise AIEngineError(
                        f"OpenAI API server error ({response.status_code}): {response.text}"
                    )

                response.raise_for_status()

                data = response.json()
                choices = data.get("choices")
                first_choice = choices[0] if (choices and isinstance(choices, list)) else {}
                msg_content = (first_choice.get("message") or {}).get("content")
                if not msg_content:
                    raise AIEngineError("OpenAI API response choices were empty or missing content")

                return msg_content

            except httpx.TimeoutException as err:
                raise AIEngineTimeoutError("OpenAI API request timed out") from err
            except httpx.HTTPStatusError as err:
                if err.response.status_code == 429:
                    raise AIEngineQuotaError(f"OpenAI API quota error: {err}") from err
                if err.response.status_code in (400, 401, 403, 404):
                    raise AIEngineClientError(f"OpenAI API client error: {err}") from err
                raise AIEngineError(f"OpenAI API HTTP error: {err}") from err
            except httpx.RequestError as err:
                raise AIEngineError(f"OpenAI API network request error: {err}") from err
            except (KeyError, ValueError) as err:
                raise AIEngineError(f"Failed to parse OpenAI API JSON response: {err}") from err

        return await async_with_retry(
            _call_api,
            max_retries=2,
            initial_delay=1.0,
            retry_exceptions=(AIEngineError, AIEngineTimeoutError),
            exclude_exceptions=(AIEngineQuotaError, AIEngineClientError),
        )


async def async_list_openai_models(
    api_key: str,
    base_url: str | None = None,
    hass: Any | None = None,
    timeout: float = 10.0,
) -> list[str]:
    """Fetch available models from OpenAI or OpenAI-compatible endpoint asynchronously."""
    url = (base_url or "https://api.openai.com/v1").rstrip("/")

    # If default endpoint and no API key, return fallback immediately
    if not api_key and "api.openai.com" in url:
        return list(FALLBACK_OPENAI_MODELS)

    endpoint = f"{url}/models"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(endpoint, headers=headers)
            if response.status_code != 200:
                _LOGGER.debug(
                    "Failed to fetch OpenAI models (%s): %s",
                    response.status_code,
                    response.text,
                )
                return list(FALLBACK_OPENAI_MODELS)

            payload = response.json()
            data = payload.get("data")
            if not isinstance(data, list):
                return list(FALLBACK_OPENAI_MODELS)

            discovered: list[str] = []
            is_official_openai = "api.openai.com" in url

            # Common non-chat model keywords to exclude when querying official OpenAI API
            exclude_keywords = (
                "embedding",
                "tts",
                "whisper",
                "dall-e",
                "moderation",
                "babbage",
                "davinci",
                "canary",
                "audio",
                "realtime",
                "transcription",
                "translation",
            )

            for item in data:
                if isinstance(item, dict):
                    model_id = item.get("id")
                    if model_id and isinstance(model_id, str):
                        m_lower = model_id.lower()
                        if is_official_openai:
                            # Filter out non-chat / non-completion models on OpenAI
                            if any(k in m_lower for k in exclude_keywords):
                                continue
                        if model_id not in discovered:
                            discovered.append(model_id)

            if discovered:
                # Merge discovered models with fallback models avoiding duplicates
                combined: list[str] = list(discovered)
                for fb in FALLBACK_OPENAI_MODELS:
                    if fb not in combined:
                        combined.append(fb)
                return combined

    except Exception as err:
        _LOGGER.debug("Error during dynamic OpenAI model discovery: %s", err)

    return list(FALLBACK_OPENAI_MODELS)

