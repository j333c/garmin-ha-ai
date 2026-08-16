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
    """Exception raised when AI provider quota or rate limit is exceeded."""


class AIEngineClientError(AIEngineError):
    """Exception raised when AI provider returns a non-retryable 4xx client error (e.g. 404 model not found, 400 invalid request)."""


class BaseAIProvider(ABC):
    """Abstract base class for pluggable AI engine drivers."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        """Initialize AI provider settings."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def async_generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        """Generate AI response string asynchronously."""


async def async_with_retry(
    func: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 2,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
) -> T:
    """Execute async function with exponential backoff retries for transient failures."""
    attempt = 0
    delay = initial_delay
    while True:
        try:
            return await func()
        except exclude_exceptions:
            raise
        except retry_exceptions as err:
            attempt += 1
            if attempt > max_retries:
                raise err
            _LOGGER.warning(
                "AI engine request transient error (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                max_retries + 1,
                delay,
                type(err).__name__,
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor
