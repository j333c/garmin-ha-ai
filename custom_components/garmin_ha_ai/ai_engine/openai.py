"""Generic OpenAI-compatible AI Engine Provider implementation."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .base import (
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
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI provider."""
        url = (base_url or "https://api.openai.com/v1").rstrip("/")
        super().__init__(api_key=api_key, model=model, base_url=url)
        self.timeout = timeout

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

                if response.status_code >= 500:
                    raise AIEngineError(
                        f"OpenAI API server error ({response.status_code}): {response.text}"
                    )

                response.raise_for_status()

                data = response.json()
                choices = data.get("choices")
                if not choices or not choices[0].get("message", {}).get("content"):
                    raise AIEngineError("OpenAI API response choices were empty or missing content")

                return data["choices"][0]["message"]["content"]

            except httpx.TimeoutException as err:
                raise AIEngineTimeoutError("OpenAI API request timed out") from err
            except httpx.HTTPStatusError as err:
                if err.response.status_code == 429:
                    raise AIEngineQuotaError(f"OpenAI API quota error: {err}") from err
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
            exclude_exceptions=(AIEngineQuotaError,),
        )
