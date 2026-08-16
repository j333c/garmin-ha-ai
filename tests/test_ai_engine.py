"""Unit tests for the AI Engine drivers package."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from custom_components.garmin_ha_ai.ai_engine import (
    AIEngineError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
    BaseAIProvider,
    GeminiProvider,
    OpenAIProvider,
    get_ai_provider,
)
from custom_components.garmin_ha_ai.ai_engine.base import async_with_retry
from custom_components.garmin_ha_ai.models import AIHealthReport


def test_ai_health_report_dataclass() -> None:
    """Test AIHealthReport dataclass instantiation and dictionary conversion."""
    report = AIHealthReport(
        timestamp="2026-08-15T12:00:00Z",
        short_summary="Great workout today! Focus on recovery tonight.",
        full_report="# Daily Health Briefing\n\nYour sleep score was 85...",
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )
    assert report.provider_used == "gemini"
    assert report.model_used == "gemini-2.0-flash"
    report_dict = report.to_dict()
    assert report_dict["short_summary"] == "Great workout today! Focus on recovery tonight."
    assert report_dict["provider_used"] == "gemini"


def test_get_ai_provider_factory() -> None:
    """Test get_ai_provider factory function instantiation and defaults."""
    gemini = get_ai_provider("gemini", api_key="test_key")
    assert isinstance(gemini, GeminiProvider)
    assert gemini.model == "gemini-2.5-flash"

    openai = get_ai_provider("openai", api_key="test_key")
    assert isinstance(openai, OpenAIProvider)
    assert openai.model == "gpt-4o"
    assert openai.base_url == "https://api.openai.com/v1"

    custom_openai = get_ai_provider(
        "openai",
        api_key="test_key",
        model="local-model",
        base_url="http://localhost:11434/v1/",
    )
    assert isinstance(custom_openai, OpenAIProvider)
    assert custom_openai.model == "local-model"
    assert custom_openai.base_url == "http://localhost:11434/v1"

    with pytest.raises(ValueError, match="Unsupported AI provider type"):
        get_ai_provider("unsupported_provider", api_key="test_key")


@pytest.mark.asyncio
async def test_gemini_provider_success() -> None:
    """Test GeminiProvider async generation happy path."""
    with patch("custom_components.garmin_ha_ai.ai_engine.gemini.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_aio_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini generated report content"

        mock_aio_models.generate_content = AsyncMock(return_value=mock_response)
        mock_client.aio.models = mock_aio_models
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="fake_key", model="gemini-2.5-flash")
        result = await provider.async_generate_response(
            prompt="Analyze my stats", system_instruction="You are a health coach"
        )

        assert result == "Gemini generated report content"
        mock_aio_models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_provider_quota_error() -> None:
    """Test GeminiProvider maps API 429 error to AIEngineQuotaError without retry."""
    with patch("custom_components.garmin_ha_ai.ai_engine.gemini.genai.Client") as mock_client_cls:
        from google.genai import errors as genai_errors

        mock_client = MagicMock()
        mock_aio_models = MagicMock()

        api_error = genai_errors.APIError(429, "RESOURCE_EXHAUSTED", None)
        mock_aio_models.generate_content = AsyncMock(side_effect=api_error)
        mock_client.aio.models = mock_aio_models
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="fake_key")
        with pytest.raises(AIEngineQuotaError):
            await provider.async_generate_response("Test prompt")

        # Quota errors fail immediately without retry
        assert mock_aio_models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_gemini_provider_503_high_demand_error() -> None:
    """Test GeminiProvider maps API 503 high demand error to AIEngineError and retries."""
    from google.genai import errors as genai_errors

    with patch("custom_components.garmin_ha_ai.ai_engine.gemini.genai.Client") as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client = MagicMock()
        mock_aio_models = MagicMock()

        api_error = genai_errors.APIError(
            503,
            "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.",
            None,
        )
        mock_aio_models.generate_content = AsyncMock(side_effect=api_error)
        mock_client.aio.models = mock_aio_models
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="fake_key")
        with pytest.raises(AIEngineError) as exc_info:
            await provider.async_generate_response("Test prompt")

        assert "503" in str(exc_info.value)
        assert "high demand" in str(exc_info.value).lower()
        # Retries: 1 initial call + 2 retries = 3 calls total
        assert mock_aio_models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_gemini_provider_404_client_error_no_retry() -> None:
    """Test GeminiProvider maps API 404 error to AIEngineClientError and fails immediately without retry."""
    from custom_components.garmin_ha_ai.ai_engine.base import AIEngineClientError
    from google.genai import errors as genai_errors

    with patch("custom_components.garmin_ha_ai.ai_engine.gemini.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_aio_models = MagicMock()

        api_error = genai_errors.APIError(
            404,
            "This model models/gemini-2.0-flash is no longer available. Please update your code.",
            None,
        )
        mock_aio_models.generate_content = AsyncMock(side_effect=api_error)
        mock_client.aio.models = mock_aio_models
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="fake_key", model="gemini-2.0-flash")
        with pytest.raises(AIEngineClientError):
            await provider.async_generate_response("Test prompt")

        # Must NOT retry on 404
        assert mock_aio_models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_async_list_gemini_models() -> None:
    """Test dynamic model discovery from Gemini API."""
    from custom_components.garmin_ha_ai.ai_engine.gemini import async_list_gemini_models

    # Case 1: Empty API key returns fallback models
    models = await async_list_gemini_models(api_key="")
    assert "gemini-2.5-flash" in models

    # Case 2: API returns model objects
    mock_model_1 = MagicMock()
    mock_model_1.name = "models/gemini-2.5-flash"
    mock_model_2 = MagicMock()
    mock_model_2.name = "models/gemini-2.5-pro"
    mock_model_other = MagicMock()
    mock_model_other.name = "models/embedding-001"

    with patch("custom_components.garmin_ha_ai.ai_engine.gemini.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model_1, mock_model_2, mock_model_other]
        mock_client_cls.return_value = mock_client

        discovered = await async_list_gemini_models(api_key="valid_key")
        assert "gemini-2.5-flash" in discovered
        assert "gemini-2.5-pro" in discovered
        assert "models/gemini-2.5-flash" not in discovered
        assert "embedding-001" not in discovered


@pytest.mark.asyncio
async def test_openai_provider_success() -> None:
    """Test OpenAIProvider async generation happy path via HTTP POST."""
    provider = OpenAIProvider(
        api_key="fake_openai_key",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "OpenAI generated coaching response"}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await provider.async_generate_response(
            prompt="My steps today: 10000", system_instruction="Be concise"
        )

        assert result == "OpenAI generated coaching response"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.openai.com/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer fake_openai_key"
        assert kwargs["json"]["messages"][0] == {"role": "system", "content": "Be concise"}
        assert kwargs["json"]["messages"][1] == {"role": "user", "content": "My steps today: 10000"}


@pytest.mark.asyncio
async def test_openai_provider_quota_error() -> None:
    """Test OpenAIProvider HTTP 429 quota error mapping."""
    provider = OpenAIProvider(api_key="fake_openai_key")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Quota exceeded"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(AIEngineQuotaError, match="quota exceeded"):
            await provider.async_generate_response("Test prompt")


@pytest.mark.asyncio
async def test_openai_provider_timeout_and_retry() -> None:
    """Test OpenAIProvider retry backoff on HTTP timeouts."""
    provider = OpenAIProvider(api_key="fake_openai_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(AIEngineTimeoutError):
                await provider.async_generate_response("Test prompt")

            # Initial call + 2 retries = 3 calls total
            assert mock_post.call_count == 3
            assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_retry_helper_success_on_retry() -> None:
    """Test async_with_retry helper succeeds on retry after initial failure."""
    calls = 0

    async def transient_func() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AIEngineError("Transient error")
        return "success"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await async_with_retry(
            transient_func, max_retries=2, retry_exceptions=(AIEngineError,)
        )
        assert result == "success"
        assert calls == 2


@pytest.mark.asyncio
async def test_async_list_openai_models_empty_key_fallback() -> None:
    """Test async_list_openai_models returns fallback models if API key is empty on default endpoint."""
    from custom_components.garmin_ha_ai.ai_engine.openai import async_list_openai_models
    from custom_components.garmin_ha_ai.const import FALLBACK_OPENAI_MODELS

    models = await async_list_openai_models(api_key="", base_url="https://api.openai.com/v1")
    assert models == list(FALLBACK_OPENAI_MODELS)


@pytest.mark.asyncio
async def test_async_list_openai_models_success() -> None:
    """Test async_list_openai_models parses and filters OpenAI models correctly."""
    from custom_components.garmin_ha_ai.ai_engine.openai import async_list_openai_models

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
            {"id": "text-embedding-3-small"},
            {"id": "tts-1"},
            {"id": "o3-mini"},
            {"id": "gpt-4.5-preview"},
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        models = await async_list_openai_models(
            api_key="valid_key", base_url="https://api.openai.com/v1"
        )

        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        assert "o3-mini" in models
        assert "gpt-4.5-preview" in models
        assert "text-embedding-3-small" not in models
        assert "tts-1" not in models
        # Verify fallback items are retained if missing
        assert "gpt-4-turbo" in models


@pytest.mark.asyncio
async def test_async_list_openai_models_custom_endpoint() -> None:
    """Test async_list_openai_models queries custom local endpoint like Ollama."""
    from custom_components.garmin_ha_ai.ai_engine.openai import async_list_openai_models

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "llama3.3:70b"},
            {"id": "mistral:latest"},
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        models = await async_list_openai_models(
            api_key="", base_url="http://localhost:11434/v1"
        )

        assert "llama3.3:70b" in models
        assert "mistral:latest" in models
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://localhost:11434/v1/models"


@pytest.mark.asyncio
async def test_async_list_openai_models_error_fallback() -> None:
    """Test async_list_openai_models returns fallback models on error or non-200 response."""
    from custom_components.garmin_ha_ai.ai_engine.openai import async_list_openai_models
    from custom_components.garmin_ha_ai.const import FALLBACK_OPENAI_MODELS

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("Connection failed")

        models = await async_list_openai_models(
            api_key="valid_key", base_url="https://api.openai.com/v1"
        )
        assert models == list(FALLBACK_OPENAI_MODELS)


@pytest.mark.asyncio
async def test_openai_provider_list_models_method() -> None:
    """Test OpenAIProvider.async_list_models delegates to async_list_openai_models."""
    provider = OpenAIProvider(api_key="fake_key", base_url="https://api.openai.com/v1")

    with patch(
        "custom_components.garmin_ha_ai.ai_engine.openai.async_list_openai_models",
        new_callable=AsyncMock,
        return_value=["discovered-model-1", "discovered-model-2"],
    ) as mock_list:
        models = await provider.async_list_models()
        assert models == ["discovered-model-1", "discovered-model-2"]
        mock_list.assert_called_once()

