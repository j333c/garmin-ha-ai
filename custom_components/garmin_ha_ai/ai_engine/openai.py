"""Generic OpenAI-compatible AI Engine Provider implementation."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

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

# Disallowed hosts to prevent Server-Side Request Forgery (SSRF) against cloud instance metadata services
DISALLOWED_HOSTS = frozenset({
    "169.254.169.254",
    "metadata.google.internal",
    "instance-data",
})


def validate_base_url(base_url: str | None) -> str:
    """Validate and normalize base_url, allowing http/https (local & remote) while blocking cloud metadata endpoints.

    Protects Home Assistant against SSRF vulnerabilities by validating URI schemes and
    rejecting cloud link-local metadata endpoints.
    """
    url = (base_url or "https://api.openai.com/v1").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise AIEngineClientError(
            f"Invalid base_url scheme '{parsed.scheme}'. Must be 'http' or 'https'."
        )
    hostname = (parsed.hostname or "").lower()
    if hostname in DISALLOWED_HOSTS:
        raise AIEngineClientError(
            f"Access to cloud metadata service '{hostname}' is prohibited."
        )
    return url


class OpenAIProvider(BaseAIProvider):
    """Generic OpenAI-compatible AI Engine Provider using httpx async client.

    Supports official OpenAI endpoints as well as compatible self-hosted / local
    inference servers (e.g. Ollama, LM Studio, vLLM, LocalAI, OpenRouter).
    """

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
        url = validate_base_url(base_url)
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

            # Build standard OpenAI messages array with optional system instruction
            messages: list[dict[str, str]] = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
            }

            try:
                # Perform asynchronous HTTP POST request
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)

                # HTTP 429 Quota / Rate limit
                if response.status_code == 429:
                    raise AIEngineQuotaError(
                        f"OpenAI API rate limit / quota exceeded (429): {response.text}"
                    )

                # Non-retryable 4xx client errors (400 bad request, 401 invalid key, 404 model not found)
                if response.status_code in (400, 401, 403, 404):
                    raise AIEngineClientError(
                        f"OpenAI API client error ({response.status_code}): {response.text}"
                    )

                # 5xx server errors
                if response.status_code >= 500:
                    raise AIEngineError(
                        f"OpenAI API server error ({response.status_code}): {response.text}"
                    )

                response.raise_for_status()

                # Parse JSON response payload and extract text content
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

        # Wrap in exponential backoff retry loop
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
    try:
        url = validate_base_url(base_url)
    except AIEngineClientError:
        return list(FALLBACK_OPENAI_MODELS)

    # If default official endpoint and no API key, return fallback immediately
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


