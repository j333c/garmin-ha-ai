"""Base class and exceptions for AI engine drivers."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
import logging
from typing import Any, TypeVar

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class AIEngineError(Exception):
    """Base exception for AI Engine errors."""


class AIEngineTimeoutError(AIEngineError):
    """Exception raised when AI provider request times out."""


class AIEngineQuotaError(AIEngineError):
    """Exception raised when AI provider quota or rate limit is exceeded (HTTP 429)."""


class AIEngineClientError(AIEngineError):
    """Exception raised when AI provider returns a non-retryable 4xx client error.

    Examples: 404 model not found, 400 invalid request, 401 unauthorized.
    """


class BaseAIProvider(ABC):
    """Abstract base class for pluggable AI engine drivers.

    Implementations wrap provider-specific SDKs (e.g. google-genai, OpenAI/httpx)
    and expose a uniform asynchronous generate_response interface.
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        """Initialize AI provider settings."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def async_generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        """Generate AI response string asynchronously.

        Args:
            prompt: The assembled prompt text.
            system_instruction: Optional system instruction / persona prompt.

        Returns:
            The raw text response from the language model.
        """


async def async_with_retry(
    func: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 2,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
) -> T:
    """Execute async function with exponential backoff retries for transient failures.

    Transient 5xx server errors or timeouts are retried up to max_retries times.
    Non-retryable errors (e.g. AIEngineQuotaError 429 or AIEngineClientError 404)
    are immediately re-raised via exclude_exceptions.
    """
    attempt = 0
    delay = initial_delay
    while True:
        try:
            return await func()
        except exclude_exceptions:
            # Re-raise excluded exceptions immediately without retrying
            raise
        except retry_exceptions as err:
            attempt += 1
            if attempt > max_retries:
                # Exhausted max retry attempts; re-raise original exception
                raise err
            err_msg = str(err).split("\n")[0]
            if len(err_msg) > 100:
                err_msg = err_msg[:97] + "..."
            _LOGGER.warning(
                "AI engine request transient error (attempt %d/%d), retrying in %.1fs: %s (%s)",
                attempt,
                max_retries + 1,
                delay,
                type(err).__name__,
                err_msg,
            )
            # Await asynchronous sleep before next retry attempt
            await asyncio.sleep(delay)
            delay *= backoff_factor

