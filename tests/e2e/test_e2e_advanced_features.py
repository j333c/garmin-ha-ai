"""End-to-End Advanced Features & Multi-Account Lifecycle Tests."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant
from custom_components.garmin_ha_ai import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.garmin_ha_ai.button import (
    GarminAIAskQuestionButton,
    GarminAIGenerateReportButton,
    async_setup_entry as button_setup_entry,
)
from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_GARMIN_USERNAME,
    CONF_NOTIFICATION_TARGETS,
    CONF_RETENTION_DAYS,
    DEFAULT_AI_MODEL_GEMINI,
    DOMAIN,
    PROVIDER_GEMINI,
    REPORT_VIEW_LONG,
    REPORT_VIEW_OPTIONS,
    REPORT_VIEW_QA,
    REPORT_VIEW_SHORT,
    SERVICE_ASK_QUESTION,
    SERVICE_GENERATE_REPORT,
)
from custom_components.garmin_ha_ai.frontend import (
    FRONTEND_DIR,
    FRONTEND_FILE_PATH,
    FRONTEND_URL,
    FRONTEND_URL_BASE,
    _DEFAULT_VERSION,
    async_setup_frontend,
)
from custom_components.garmin_ha_ai.models import GarminDailyMetrics
from custom_components.garmin_ha_ai.select import (
    GarminAIReportDisplayModeSelectEntity,
    async_setup_entry as select_setup_entry,
)
from custom_components.garmin_ha_ai.sensor import async_setup_entry as sensor_setup_entry
from custom_components.garmin_ha_ai.text import (
    GarminAIQuestionTextEntity,
    async_setup_entry as text_setup_entry,
)


@pytest.mark.asyncio
async def test_e2e_multi_account_concurrent_lifecycle(hass: HomeAssistant) -> None:
    """Test full E2E lifecycle with two concurrent Garmin user accounts maintaining complete data and entity isolation."""
    # Step 1: Initialize component and services
    assert await async_setup(hass, {}) is True
    assert DOMAIN in hass.data

    # Setup 2 config entries
    entry_alice = MagicMock()
    entry_alice.entry_id = "alice_entry_001"
    entry_alice.title = "Garmin (alice@runner.com)"
    entry_alice.data = {
        CONF_GARMIN_USERNAME: "alice@runner.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "alice-api-key-123",
        CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
    }
    entry_alice.options = {
        CONF_RETENTION_DAYS: 30,
        CONF_FITNESS_GOALS: "Marathon prep: 70km/week, sleep score > 85",
        CONF_COACHING_DIRECTIVES: "Performance focus, high precision",
        CONF_NOTIFICATION_TARGETS: "notify.alice_phone",
    }
    entry_alice.add_update_listener = MagicMock(return_value=MagicMock())
    entry_alice.async_on_unload = MagicMock()

    entry_bob = MagicMock()
    entry_bob.entry_id = "bob_entry_002"
    entry_bob.title = "Garmin (bob@wellness.com)"
    entry_bob.data = {
        CONF_GARMIN_USERNAME: "bob@wellness.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "bob-api-key-456",
        CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
    }
    entry_bob.options = {
        CONF_RETENTION_DAYS: 14,
        CONF_FITNESS_GOALS: "Stress reduction and 8,000 steps daily",
        CONF_COACHING_DIRECTIVES: "Calm, encouraging, holistic",
        CONF_NOTIFICATION_TARGETS: "persistent_notification",
    }
    entry_bob.add_update_listener = MagicMock(return_value=MagicMock())
    entry_bob.async_on_unload = MagicMock()

    # Track registered entities per entry
    alice_entities = []
    bob_entities = []

    def mock_add_alice_entities(entities):
        alice_entities.extend(entities)

    def mock_add_bob_entities(entities):
        bob_entities.extend(entities)

    hass.config_entries = MagicMock()

    async def mock_forward_setups(entry, platforms):
        add_fn = mock_add_alice_entities if entry.entry_id == "alice_entry_001" else mock_add_bob_entities
        for platform in platforms:
            plat_str = str(platform)
            if plat_str == "sensor" or plat_str.endswith("sensor"):
                await sensor_setup_entry(hass, entry, add_fn)
            elif plat_str == "button" or plat_str.endswith("button"):
                await button_setup_entry(hass, entry, add_fn)
            elif plat_str == "text" or plat_str.endswith("text"):
                await text_setup_entry(hass, entry, add_fn)
            elif plat_str == "select" or plat_str.endswith("select"):
                await select_setup_entry(hass, entry, add_fn)
        return True

    hass.config_entries.async_forward_entry_setups = AsyncMock(side_effect=mock_forward_setups)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    # Mock metrics for Alice and Bob
    alice_metrics = GarminDailyMetrics(
        date="2026-08-22",
        steps=18500,
        distance_km=15.4,
        total_calories=3100,
        resting_hr=48,
        sleep_score=94,
        avg_stress=15,
        body_battery_min=30,
        body_battery_max=98,
        weight_kg=61.5,
        hrv_status="BALANCED",
        activities=[{"name": "15km Long Run", "duration_min": 72, "calories": 920}],
    )

    bob_metrics = GarminDailyMetrics(
        date="2026-08-22",
        steps=8200,
        distance_km=6.1,
        total_calories=2100,
        resting_hr=64,
        sleep_score=76,
        avg_stress=28,
        body_battery_min=18,
        body_battery_max=82,
        weight_kg=84.0,
        hrv_status="BALANCED",
        activities=[{"name": "Evening Walk", "duration_min": 35, "calories": 180}],
    )

    # In-memory storage mock partitioned by entry_id
    storage_backends: dict[str, dict] = {}

    def create_mock_store(hass, version, key, private=False):
        store = MagicMock()
        store.key = key
        store.async_load = AsyncMock(side_effect=lambda: storage_backends.get(key, {}))

        async def _save(data):
            storage_backends[key] = data

        store.async_save = AsyncMock(side_effect=_save)
        return store

    # Step 2: Setup both accounts concurrently
    with patch("custom_components.garmin_ha_ai.storage.Store", side_effect=create_mock_store):
        with patch(
            "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_fetch_daily_metrics",
            side_effect=[alice_metrics, bob_metrics],
        ):
            alice_setup = await async_setup_entry(hass, entry_alice)
            bob_setup = await async_setup_entry(hass, entry_bob)

            assert alice_setup is True
            assert bob_setup is True

    # Step 3: Verify isolation in hass.data
    assert "alice_entry_001" in hass.data[DOMAIN]
    assert "bob_entry_002" in hass.data[DOMAIN]

    alice_coordinator = hass.data[DOMAIN]["alice_entry_001"]["coordinator"]
    bob_coordinator = hass.data[DOMAIN]["bob_entry_002"]["coordinator"]

    assert alice_coordinator.data.steps == 18500
    assert bob_coordinator.data.steps == 8200

    # Step 4: Verify entity instances & distinct unique IDs
    assert len(alice_entities) == 16
    assert len(bob_entities) == 16

    alice_unique_ids = {e.unique_id for e in alice_entities if getattr(e, "unique_id", None)}
    bob_unique_ids = {e.unique_id for e in bob_entities if getattr(e, "unique_id", None)}

    # Ensure completely disjoint sets of unique IDs
    assert alice_unique_ids.isdisjoint(bob_unique_ids)

    # Step 5: Test interactive text, select, and button on Alice
    alice_text = next(e for e in alice_entities if isinstance(e, GarminAIQuestionTextEntity))
    alice_select = next(e for e in alice_entities if isinstance(e, GarminAIReportDisplayModeSelectEntity))
    alice_report_btn = next(e for e in alice_entities if isinstance(e, GarminAIGenerateReportButton))
    alice_ask_btn = next(e for e in alice_entities if isinstance(e, GarminAIAskQuestionButton))

    # Test text entity value change
    await alice_text.async_set_value("What is my average pace and recovery recommendation?")
    assert alice_coordinator.question_input == "What is my average pace and recovery recommendation?"

    # Test select entity view mode change
    assert alice_select.current_option == REPORT_VIEW_SHORT
    await alice_select.async_select_option(REPORT_VIEW_LONG)
    assert alice_coordinator.report_display_mode == REPORT_VIEW_LONG
    assert alice_select.current_option == REPORT_VIEW_LONG

    # Test button entity async_press triggering coordinator report generation
    with patch.object(alice_coordinator, "async_generate_report", new_callable=AsyncMock) as mock_gen:
        await alice_report_btn.async_press()
        mock_gen.assert_called_once()

    with patch.object(alice_coordinator, "async_ask_question", new_callable=AsyncMock) as mock_ask:
        await alice_ask_btn.async_press()
        mock_ask.assert_called_once_with()

    # Step 6: Verify teardown of Alice leaves Bob intact
    alice_unloaded = await async_unload_entry(hass, entry_alice)
    assert alice_unloaded is True
    assert "alice_entry_001" not in hass.data[DOMAIN]
    assert "bob_entry_002" in hass.data[DOMAIN]

    # Clean unload of Bob
    bob_unloaded = await async_unload_entry(hass, entry_bob)
    assert bob_unloaded is True
    assert "bob_entry_002" not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_e2e_baseline_analytics_prompt_integration(hass: HomeAssistant) -> None:
    """Test full E2E pipeline for 7-day baseline analytics computation and prompt injection."""
    await async_setup(hass, {})

    entry = MagicMock()
    entry.entry_id = "analytics_e2e_entry"
    entry.title = "Garmin (pro@athlete.com)"
    entry.data = {
        CONF_GARMIN_USERNAME: "pro@athlete.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "analytics-key",
        CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
    }
    entry.options = {
        CONF_RETENTION_DAYS: 30,
        CONF_FITNESS_GOALS: "10,000 steps daily, sleep target 85",
        CONF_COACHING_DIRECTIVES: "Data-driven and direct",
    }
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()

    # Pre-populate 7 days of historical metrics
    history_records = {}
    for i in range(7):
        day_date = f"2026-08-{10+i:02d}"
        history_records[day_date] = {
            "date": day_date,
            "steps": 10000 + i * 500,
            "sleep_score": 80 + i,
            "resting_hr": 54 - (i % 2),
            "avg_stress": 22 - (i % 3),
            "total_calories": 2500 + i * 50,
            "hrv_status": "BALANCED",
            "activities": [
                {
                    "name": f"Interval Training Day {i+1}",
                    "duration_min": 45,
                    "calories": 480,
                    "avg_hr": 152,
                    "max_hr": 174,
                }
            ],
        }

    current_metrics = GarminDailyMetrics(
        date="2026-08-17",
        steps=14500,
        distance_km=12.0,
        total_calories=2950,
        resting_hr=50,
        sleep_score=89,
        avg_stress=18,
        body_battery_min=25,
        body_battery_max=95,
        weight_kg=70.0,
        hrv_status="BALANCED",
        activities=[{"name": "Progression Run", "duration_min": 55, "calories": 610}],
    )

    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_fetch_daily_metrics",
        new_callable=AsyncMock,
        return_value=current_metrics,
    ), patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_load_history",
        new_callable=AsyncMock,
        return_value=history_records,
    ), patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_save_daily_metrics",
        new_callable=AsyncMock,
    ):
        assert await async_setup_entry(hass, entry) is True

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

        captured_prompts = []

        async def mock_generate(prompt: str) -> str:
            captured_prompts.append(prompt)
            return "<summary>Peak fitness with 14,500 steps and sleep score of 89.</summary>\n\n# Detailed Analysis\nGreat week."

        with patch(
            "custom_components.garmin_ha_ai.ai_engine.gemini.GeminiProvider.async_generate_response",
            side_effect=mock_generate,
        ):
            await coordinator.async_generate_report()

            # Verify prompt contains Block 2 baseline analytics details
            assert len(captured_prompts) == 1
            prompt_text = captured_prompts[0]

            assert "### BLOCK 2: HISTORICAL TRENDS (7-DAY CONTEXT)" in prompt_text
            assert "Sleep Score Baseline: 7-day Avg = 83.0" in prompt_text
            assert "Resting Heart Rate Baseline: 7-day Avg = 53.6 bpm" in prompt_text
            assert "Stable & Balanced" in prompt_text
            assert "7-Day Training Volume: 7 activities" in prompt_text

            # Verify coordinator latest_report updated
            assert coordinator.latest_report is not None
            assert "14,500 steps" in coordinator.latest_report.short_summary


@pytest.mark.asyncio
async def test_e2e_frontend_custom_card_registration_lifecycle(hass: HomeAssistant) -> None:
    """Test E2E frontend custom card registration and static asset serving in Home Assistant."""
    import custom_components.garmin_ha_ai.frontend as frontend_mod

    frontend_mod._FRONTEND_REGISTERED = False

    with patch("homeassistant.components.frontend.add_extra_js_url") as mock_add_js:
        await async_setup_frontend(hass)

        # Verify static path registration
        hass.http.async_register_static_paths.assert_called_once()
        reg_paths = hass.http.async_register_static_paths.call_args[0][0]
        assert len(reg_paths) == 2

        # Verify JS resource registration
        mock_add_js.assert_called_once_with(hass, f"{FRONTEND_URL}?v={_DEFAULT_VERSION}")

        # Idempotency check
        await async_setup_frontend(hass)
        assert mock_add_js.call_count == 1
