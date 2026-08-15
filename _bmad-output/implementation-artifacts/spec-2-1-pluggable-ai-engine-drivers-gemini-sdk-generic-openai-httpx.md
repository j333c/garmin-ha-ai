---
title: 'Pluggable AI Engine Drivers (Gemini SDK & Generic OpenAI HTTPX)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '9d36970a429f75eb8b77d0a0cab190b07a61ccb0'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/const.py'
  - 'custom_components/garmin_ha_ai/models.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant integration needs a flexible, pluggable AI driver layer to generate daily health reports and answer Q&A queries via Google Gemini (using the `google-genai` SDK) or generic OpenAI-compatible endpoints (using `httpx`). The system must support configurable endpoints, models, 30s timeouts, exponential backoff retries, and clean exception mapping without blocking Home Assistant's main event loop.

**Approach:** Build a lightweight `ai_engine/` package featuring an abstract `BaseAIProvider` protocol, `GeminiProvider` using official `google-genai` SDK, `OpenAIProvider` using `httpx.AsyncClient` targeting `/v1/chat/completions`, custom exception hierarchy (`AIEngineError`, `AIEngineTimeoutError`, `AIEngineQuotaError`), and factory function `get_ai_provider`. Include up to 2 automatic retries with exponential backoff for 5xx and timeout errors. Add `AIHealthReport` dataclass to `models.py`.

## Boundaries & Constraints

**Always:**
- Derive provider drivers from abstract `BaseAIProvider` base class.
- Use non-blocking async network calls (`client.aio.models.generate_content` for Gemini, `httpx.AsyncClient` for OpenAI).
- Enforce 30-second default request timeout on AI API calls.
- Execute up to 2 retries with exponential backoff (1s, 2s) on API timeouts (`httpx.TimeoutException`) or HTTP 5xx server errors.
- Map low-level driver exceptions to domain exception classes (`AIEngineTimeoutError`, `AIEngineQuotaError`, `AIEngineError`).
- Sanitize logs to never output raw API keys, bearer tokens, or full prompt contents in warning/error logs.

**Ask First:**
- Modifying retry count (default: 2 retries) or default timeout duration (default: 30 seconds).

**Never:**
- Make synchronous blocking HTTP network calls in the Home Assistant main event loop.
- Import heavy LLM orchestration frameworks (LangChain, LlamaIndex, AutoGen).
- Log raw API keys or plain authorization headers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Gemini Happy Path | Valid prompt, `provider="gemini"`, valid API key | Generated response string returned | N/A |
| OpenAI Happy Path | Valid prompt, `provider="openai"`, valid key & base_url | Generated response string from `/v1/chat/completions` | N/A |
| System Prompt Included | Prompt + `system_instruction` provided | Driver formats prompt with system instruction included | N/A |
| Transient 5xx Error | AI service returns HTTP 500 / 503 | Retries up to 2 times with backoff, succeeds on retry | Logs warning retry count |
| Repeated Timeout | AI request exceeds 30s timeout across retries | Retries up to 2 times, then fails | Raises `AIEngineTimeoutError` |
| Quota / Rate Limit Error | API returns HTTP 429 quota exceeded | Immediate failure without retry | Raises `AIEngineQuotaError` |
| Invalid Provider Type | Unknown `provider_type="unsupported"` passed | Immediate validation error | Raises `ValueError` |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/models.py` -- Data models including `GarminDailyMetrics` and `AIHealthReport`.
- `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Package entry point and `get_ai_provider` factory function.
- `custom_components/garmin_ha_ai/ai_engine/base.py` -- Abstract base class `BaseAIProvider`, exceptions (`AIEngineError`, `AIEngineTimeoutError`, `AIEngineQuotaError`), and exponential backoff helper.
- `custom_components/garmin_ha_ai/ai_engine/gemini.py` -- `GeminiProvider` driver utilizing `google-genai` SDK (`genai.Client`).
- `custom_components/garmin_ha_ai/ai_engine/openai.py` -- `OpenAIProvider` driver utilizing `httpx.AsyncClient` POST to `{base_url}/chat/completions`.
- `tests/test_ai_engine.py` -- Unit tests for drivers, factory function, timeouts, retries, and error mapping.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/models.py` -- Add `AIHealthReport` dataclass with `timestamp`, `short_summary`, `full_report`, `provider_used`, and `model_used` fields.
- [x] `custom_components/garmin_ha_ai/ai_engine/base.py` -- Create `BaseAIProvider` ABC with `async_generate_response`, define custom exception hierarchy (`AIEngineError`, `AIEngineTimeoutError`, `AIEngineQuotaError`), and implement async retry decorator/helper.
- [x] `custom_components/garmin_ha_ai/ai_engine/gemini.py` -- Implement `GeminiProvider` using `google.genai.Client`, using async `client.aio.models.generate_content`, mapping SDK errors to domain exceptions.
- [x] `custom_components/garmin_ha_ai/ai_engine/openai.py` -- Implement `OpenAIProvider` using `httpx.AsyncClient` targeting `{base_url}/chat/completions`, supporting `system_instruction` message formatting, headers, 30s timeout, and exception mapping.
- [x] `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Implement `get_ai_provider(provider_type, api_key, model, base_url)` factory function instantiating the requested driver.
- [x] `tests/test_ai_engine.py` -- Write comprehensive unit tests for Gemini provider, OpenAI provider, factory, retry backoff, and exception mappings.

**Acceptance Criteria:**
- Given a `GeminiProvider` instance with valid API key, when calling `async_generate_response`, it asynchronously invokes Gemini API via `google-genai` SDK and returns the response string.
- Given an `OpenAIProvider` instance with valid API key and Base URL, when calling `async_generate_response`, it sends a JSON POST request to `{base_url}/chat/completions` using `httpx.AsyncClient` with bearer token auth and returns the choice content string.
- Given transient HTTP 5xx or connection timeout errors, the provider driver retries up to 2 times with exponential backoff before failing with `AIEngineTimeoutError` or `AIEngineError`.
- Given HTTP 429 quota error, the provider raises `AIEngineQuotaError` immediately without retrying.

## Spec Change Log

*No changes yet.*

## Design Notes

The AI engine uses an asynchronous abstract strategy pattern.
For Gemini (`google-genai` SDK):
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
response = await client.aio.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None,
)
return response.text
```
For OpenAI (`httpx.AsyncClient`):
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    response = await client.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
    )
```

## Verification

**Commands:**
- `PYTHONPATH=. pytest tests/test_ai_engine.py` -- expected: 100% pass on all AI engine driver unit tests.
- `PYTHONPATH=. pytest` -- expected: 100% pass on all integration tests (existing 22 tests + new tests).

## Suggested Review Order

**AI Driver Core & Factory**

- Driver factory instantiating Gemini or OpenAI provider instances with default options
  [`__init__.py:26`](../../custom_components/garmin_ha_ai/ai_engine/__init__.py#L26)

- Abstract base class, domain exceptions, and async exponential backoff retry helper
  [`base.py:22`](../../custom_components/garmin_ha_ai/ai_engine/base.py#L22)

**Provider Drivers**

- Google Gemini SDK driver utilizing `google-genai` async content generation and error mapping
  [`gemini.py:22`](../../custom_components/garmin_ha_ai/ai_engine/gemini.py#L22)

- Generic OpenAI driver utilizing `httpx.AsyncClient` targeting `/v1/chat/completions` with 30s timeout
  [`openai.py:20`](../../custom_components/garmin_ha_ai/ai_engine/openai.py#L20)

**Data Models & Supporting Tests**

- `AIHealthReport` dataclass representing AI health summaries and raw report payload
  [`models.py:29`](../../custom_components/garmin_ha_ai/models.py#L29)

- Comprehensive unit test suite validating drivers, retries, quota exceptions, and factory function
  [`test_ai_engine.py:1`](../../tests/test_ai_engine.py#L1)

