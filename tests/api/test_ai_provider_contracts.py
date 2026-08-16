"""Automated API and Contract Tests for AI Providers and Prompt Assembly."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.garmin_ha_ai.ai_engine.base import (
    AIEngineError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
)
from custom_components.garmin_ha_ai.ai_engine.gemini import GeminiProvider
from custom_components.garmin_ha_ai.ai_engine.openai import OpenAIProvider
from custom_components.garmin_ha_ai.ai_engine.prompt import (
    assemble_qa_prompt,
    assemble_report_prompt,
    parse_ai_health_report,
)
from custom_components.garmin_ha_ai.models import GarminDailyMetrics


# ---------------------------------------------------------------------------
# Gemini Provider API Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gemini_provider_api_contract_success() -> None:
    """Validate Gemini API request payload structure and successful response parsing."""
    mock_response = MagicMock()
    mock_response.text = (
        "<summary>Excellent recovery and sleep.</summary>\n\n"
        "### Daily Briefing\nYour metrics are optimal."
    )

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="valid-test-key", model="gemini-2.0-flash")

        result = await provider.async_generate_response(
            prompt="Analyze my sleep and stress",
            system_instruction="You are a health coach.",
        )

        assert result == mock_response.text
        mock_client.aio.models.generate_content.assert_called_once()
        call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.0-flash"
        assert call_kwargs["contents"] == "Analyze my sleep and stress"
        assert call_kwargs["config"].system_instruction == "You are a health coach."


@pytest.mark.asyncio
async def test_gemini_provider_quota_error_contract() -> None:
    """Validate Gemini API translates 429 / resource exhausted into AIEngineQuotaError."""
    from google.genai.errors import APIError

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=APIError(code=429, message="Resource exhausted: rate limit exceeded")
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(AIEngineQuotaError) as exc_info:
            await provider.async_generate_response(prompt="Test prompt")

        assert "quota exceeded" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_msg",
    [
        (400, "Invalid argument: Bad prompt format"),
        (401, "API key expired or invalid"),
        (403, "Forbidden: Permission denied for model"),
        (404, "Model not found"),
        (500, "Internal Gemini server error"),
        (503, "Gemini service temporarily unavailable"),
    ],
)
async def test_gemini_provider_api_error_codes(status_code: int, error_msg: str) -> None:
    """Validate Gemini API error propagation wraps non-quota errors into AIEngineError without delay."""
    from google.genai.errors import APIError

    with patch("google.genai.Client") as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=APIError(code=status_code, message=error_msg)
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(AIEngineError) as exc_info:
            await provider.async_generate_response(prompt="Test prompt")

        assert error_msg in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_provider_timeout_contract() -> None:
    """Validate Gemini API driver handles timeout wrapping into AIEngineTimeoutError."""
    with patch("google.genai.Client") as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(AIEngineTimeoutError):
            await provider.async_generate_response(prompt="Slow prompt")


# ---------------------------------------------------------------------------
# OpenAI Provider API Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_provider_api_contract_success() -> None:
    """Validate OpenAI API JSON schema payload structure and response choices extraction."""
    expected_markdown = (
        "<summary>Rest day recommended.</summary>\n\n"
        "### Recovery Analysis\nHRV is lower than normal."
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1723800000,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": expected_markdown},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        provider = OpenAIProvider(
            api_key="sk-test-openai-key",
            model="gpt-4o",
            base_url="https://custom-ai.local/v1",
        )

        result = await provider.async_generate_response(
            prompt="Analyze my daily strain",
            system_instruction="You are an athletic trainer.",
        )

        assert result == expected_markdown
        mock_client.post.assert_called_once()
        post_args, post_kwargs = mock_client.post.call_args
        assert post_args[0] == "https://custom-ai.local/v1/chat/completions"
        assert post_kwargs["headers"]["Authorization"] == "Bearer sk-test-openai-key"

        payload = post_kwargs["json"]
        assert payload["model"] == "gpt-4o"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0] == {
            "role": "system",
            "content": "You are an athletic trainer.",
        }
        assert payload["messages"][1] == {
            "role": "user",
            "content": "Analyze my daily strain",
        }


@pytest.mark.asyncio
async def test_openai_provider_quota_error_contract() -> None:
    """Validate OpenAI API 429 rate limit raises AIEngineQuotaError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="sk-test-key", model="gpt-4o")

        with pytest.raises(AIEngineQuotaError):
            await provider.async_generate_response(prompt="Test prompt")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 500, 502, 503],
)
async def test_openai_provider_api_http_error_codes(status_code: int) -> None:
    """Validate OpenAI API client wraps non-quota errors into AIEngineError."""
    import httpx

    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = f"HTTP {status_code} Error"
    if status_code < 500:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code} Error", request=MagicMock(), response=mock_resp
        )

    with patch("httpx.AsyncClient") as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="sk-test-key", model="gpt-4o")

        with pytest.raises(AIEngineError):
            await provider.async_generate_response(prompt="Test prompt")


@pytest.mark.asyncio
async def test_openai_provider_empty_choices_error() -> None:
    """Validate OpenAI API client raises AIEngineError on empty choices array."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": []}

    with patch("httpx.AsyncClient") as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="sk-test-key", model="gpt-4o")

        with pytest.raises(AIEngineError) as exc_info:
            await provider.async_generate_response(prompt="Test prompt")

        assert "empty or missing content" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5-Block Prompt Assembler & Parser Contract Tests
# ---------------------------------------------------------------------------


def test_5_block_report_prompt_structure_contract() -> None:
    """Validate 5-Block prompt contract adheres to specification format."""
    current = GarminDailyMetrics(
        date="2026-08-16",
        steps=10500,
        distance_km=7.8,
        total_calories=2450,
        resting_hr=58,
        sleep_score=88,
        avg_stress=24,
        body_battery_min=20,
        body_battery_max=95,
        weight_kg=75.0,
        activities=[
            {"activity_type": "running", "duration_min": 45, "calories": 480}
        ],
    )

    history = [
        {"date": "2026-08-15", "sleep_score": 82, "steps": 9200, "avg_stress": 26},
        {"date": "2026-08-14", "sleep_score": 79, "steps": 8100, "avg_stress": 30},
    ]

    prompt = assemble_report_prompt(
        current_metrics=current,
        history=history,
        user_goals="Marathon training sub-3:30",
        coaching_directives="Focus on pacing and sleep quality",
    )

    # 1. Current metrics block
    assert "### BLOCK 1: CURRENT DAY METRICS" in prompt
    assert "- Steps: 10500" in prompt
    assert "- Distance: 7.8 km" in prompt
    assert "- Total Calories: 2450 kcal" in prompt
    assert "- Sleep Score: 88" in prompt
    assert "- Body Battery (Min/Max): 20 / 95" in prompt
    assert "running: 45 min, 480 kcal" in prompt

    # 2. Historical context block
    assert "### BLOCK 2: HISTORICAL TRENDS (7-DAY CONTEXT)" in prompt
    assert "[2026-08-15] Steps: 9200 | Sleep Score: 82" in prompt

    # 3. Fitness goals block
    assert "### BLOCK 3: USER GOALS & PROFILE" in prompt
    assert "Marathon training sub-3:30" in prompt

    # 4. Coaching directives block
    assert "### BLOCK 4: PERSONA & COACHING DIRECTIVES" in prompt
    assert "Focus on pacing and sleep quality" in prompt

    # 5. Output format requirements block
    assert "### BLOCK 5: STRUCTURAL OUTPUT FORMATTING RULES" in prompt
    assert "<summary>...</summary>" in prompt


def test_qa_prompt_assembly_contract() -> None:
    """Validate interactive Q&A prompt assembly with multi-day history grounding."""
    history = [
        {"date": "2026-08-16", "sleep_score": 85, "steps": 10000},
        {"date": "2026-08-15", "sleep_score": 80, "steps": 9000},
    ]

    prompt = assemble_qa_prompt(
        question="Why was my stress higher two days ago?",
        history=history,
        user_goals="Keep stress below 25",
        coaching_directives="Be empathetic and direct",
    )

    assert "### USER QUESTION" in prompt
    assert "Why was my stress higher two days ago?" in prompt
    assert "### HISTORICAL METRICS CONTEXT" in prompt
    assert "[2026-08-16] Steps: 10000 | Sleep Score: 85" in prompt
    assert "Keep stress below 25" in prompt
    assert "Be empathetic and direct" in prompt


def test_parse_ai_health_report_contract() -> None:
    """Validate parser extracts short summary and separates full markdown report."""
    raw_llm_output = (
        "<summary>Solid sleep and active recovery day.</summary>\n\n"
        "# Daily Coaching Report\n"
        "Your HRV was balanced and readiness is high."
    )

    report = parse_ai_health_report(
        raw_llm_output,
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )

    assert report.short_summary == "Solid sleep and active recovery day."
    assert report.full_report == raw_llm_output
    assert report.provider_used == "gemini"
    assert report.model_used == "gemini-2.0-flash"
    assert report.timestamp is not None
