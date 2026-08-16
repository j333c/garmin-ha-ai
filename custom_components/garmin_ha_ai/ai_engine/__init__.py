"""AI Engine package initializer and factory function."""
from __future__ import annotations

from typing import Any

from ..const import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MODEL_GEMINI,
    DEFAULT_AI_MODEL_OPENAI,
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
)
from .base import (
    AIEngineClientError,
    AIEngineError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
    BaseAIProvider,
)
from .gemini import GeminiProvider, async_list_gemini_models
from .openai import OpenAIProvider, async_list_openai_models
from .prompt import (
    assemble_qa_prompt,
    assemble_report_prompt,
    parse_ai_health_report,
    truncate_history_context,
)

__all__ = [
    "BaseAIProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "AIEngineError",
    "AIEngineClientError",
    "AIEngineQuotaError",
    "AIEngineTimeoutError",
    "get_ai_provider",
    "async_list_gemini_models",
    "async_list_openai_models",
    "assemble_report_prompt",
    "assemble_qa_prompt",
    "parse_ai_health_report",
    "truncate_history_context",
]


def get_ai_provider(
    provider_type: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseAIProvider:
    """Factory function to instantiate configured AI Engine Provider."""
    provider_lower = (provider_type or "").lower()
    if provider_lower == PROVIDER_GEMINI:
        selected_model = model or DEFAULT_AI_MODEL_GEMINI
        return GeminiProvider(api_key=api_key, model=selected_model, base_url=base_url, **kwargs)
    if provider_lower == PROVIDER_OPENAI:
        selected_model = model or DEFAULT_AI_MODEL_OPENAI
        selected_base_url = base_url or DEFAULT_AI_BASE_URL
        return OpenAIProvider(
            api_key=api_key, model=selected_model, base_url=selected_base_url, **kwargs
        )
    raise ValueError(f"Unsupported AI provider type: '{provider_type}'")
