"""End-to-End lifecycle tests for Garmin HA AI integration."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant
from custom_components.garmin_ha_ai import (
    async_reload_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_GARMIN_PASSWORD,
    CONF_GARMIN_USERNAME,
    CONF_MFA_CODE,
    CONF_NOTIFICATION_TARGETS,
    CONF_RETENTION_DAYS,
    DEFAULT_AI_MODEL_GEMINI,
    DOMAIN,
    PLATFORMS,
    PROVIDER_GEMINI,
    SERVICE_ASK_QUESTION,
    SERVICE_GENERATE_REPORT,
)
from custom_components.garmin_ha_ai.models import GarminDailyMetrics
from custom_components.garmin_ha_ai.sensor import async_setup_entry as sensor_setup_entry
from custom_components.garmin_ha_ai.storage import GarminStorage


@pytest.mark.asyncio
async def test_e2e_full_integration_pipeline_lifecycle(hass: HomeAssistant) -> None:
    """Test full E2E flow: config flow -> setup -> polling -> sensors -> report -> Q&A -> options -> unload."""
    # -----------------------------------------------------------------------
    # Step 1: Initialize component and services
    # -----------------------------------------------------------------------
    assert await async_setup(hass, {}) is True
    assert DOMAIN in hass.data
    assert hass.services.has_service(DOMAIN, SERVICE_GENERATE_REPORT)
    assert hass.services.has_service(DOMAIN, SERVICE_ASK_QUESTION)

    # -----------------------------------------------------------------------
    # Step 2: Simulate Config Flow UI setup with Garmin MFA
    # -----------------------------------------------------------------------
    from custom_components.garmin_ha_ai.config_flow import GarminHaAiConfigFlow

    flow = GarminHaAiConfigFlow()
    flow.hass = hass

    from custom_components.garmin_ha_ai.garmin_client import GarminMfaRequired

    # User enters credentials & AI provider config -> Garmin raises MFA Required
    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_login_with_credentials",
        side_effect=GarminMfaRequired("MFA code required"),
    ):
        user_result = await flow.async_step_user(
            {
                CONF_GARMIN_USERNAME: "athlete@example.com",
                CONF_GARMIN_PASSWORD: "secret-garmin-pw",
                CONF_AI_PROVIDER: PROVIDER_GEMINI,
                CONF_AI_API_KEY: "test-gemini-key-12345",
                CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
            }
        )

        assert user_result["type"] == "form"
        assert user_result["step_id"] == "mfa"

    # User enters MFA code -> successfully authenticated
    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
    ) as mock_login_mfa:
        mock_login_mfa.return_value = {"tokenstore": "token-123"}

        mfa_result = await flow.async_step_mfa({CONF_MFA_CODE: "654321"})

        assert mfa_result["type"] == "create_entry"
        assert mfa_result["title"] == "Garmin (athlete@example.com)"
        entry_data = mfa_result["data"]
        # Passwords must never be stored in entry data
        assert CONF_GARMIN_PASSWORD not in entry_data
        assert entry_data[CONF_GARMIN_USERNAME] == "athlete@example.com"
        assert entry_data[CONF_AI_PROVIDER] == PROVIDER_GEMINI

    # -----------------------------------------------------------------------
    # Step 3: Set up Config Entry into Home Assistant
    # -----------------------------------------------------------------------
    config_entry = MagicMock()
    config_entry.entry_id = "e2e_test_entry"
    config_entry.data = entry_data
    config_entry.options = {
        CONF_RETENTION_DAYS: 30,
        CONF_FITNESS_GOALS: "Sub-4 marathon & optimal recovery",
        CONF_COACHING_DIRECTIVES: "Encouraging and precise",
        CONF_NOTIFICATION_TARGETS: "notify.mobile_app_phone,persistent_notification",
    }
    config_entry.add_update_listener = MagicMock(return_value=MagicMock())
    config_entry.async_on_unload = MagicMock()

    # Track sensor entities registered
    registered_entities = []

    def mock_add_entities(entities):
        registered_entities.extend(entities)

    hass.config_entries = MagicMock()
    async def mock_forward_setups(entry, platforms):
        for platform in platforms:
            if str(platform) == "sensor" or str(platform).endswith("sensor"):
                await sensor_setup_entry(hass, entry, mock_add_entities)
            elif str(platform) == "button" or str(platform).endswith("button"):
                from custom_components.garmin_ha_ai.button import (
                    async_setup_entry as button_setup_entry,
                )
                await button_setup_entry(hass, entry, mock_add_entities)
            elif str(platform) == "text" or str(platform).endswith("text"):
                from custom_components.garmin_ha_ai.text import (
                    async_setup_entry as text_setup_entry,
                )
                await text_setup_entry(hass, entry, mock_add_entities)
            elif str(platform) == "select" or str(platform).endswith("select"):
                from custom_components.garmin_ha_ai.select import (
                    async_setup_entry as select_setup_entry,
                )
                await select_setup_entry(hass, entry, mock_add_entities)
        return True

    hass.config_entries.async_forward_entry_setups = AsyncMock(
        side_effect=mock_forward_setups
    )
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock(return_value=True)

    # Register notification mock services into hass.services
    notifications_sent = []
    def mock_mobile_notify(call):
        notifications_sent.append({"target": "notify.mobile_app_phone", "data": call.data})
    def mock_persistent_notify(call):
        notifications_sent.append({"target": "persistent_notification.create", "data": call.data})

    hass.services.async_register("notify", "mobile_app_phone", mock_mobile_notify)
    hass.services.async_register("persistent_notification", "create", mock_persistent_notify)

    # Mock daily metrics from Garmin Cloud
    mock_metrics = GarminDailyMetrics(
        date="2026-08-16",
        steps=14250,
        distance_km=11.2,
        total_calories=2850,
        resting_hr=52,
        sleep_score=91,
        avg_stress=19,
        body_battery_min=24,
        body_battery_max=96,
        weight_kg=72.5,
        activities=[{"name": "Morning Tempo Run", "duration_min": 50, "calories": 620}],
    )

    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_fetch_daily_metrics",
        new_callable=AsyncMock,
        return_value=mock_metrics,
    ), patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_save_daily_metrics",
        new_callable=AsyncMock,
    ) as mock_save_history:
        setup_success = await async_setup_entry(hass, config_entry)
        assert setup_success is True

        # Verify entry registry in hass.data
        entry_store = hass.data[DOMAIN][config_entry.entry_id]
        coordinator = entry_store["coordinator"]
        storage = entry_store["storage"]

        assert coordinator.data == mock_metrics
        mock_save_history.assert_called_once_with(mock_metrics.to_dict())

        # Verify 11 sensor entities + 2 button entities + 1 text + 1 select = 15 total
        assert len(registered_entities) == 15
        sensor_entities = [e for e in registered_entities if getattr(e, "entity_description", None) or "Sensor" in e.__class__.__name__]
        assert len(sensor_entities) == 11
        
        # Verify steps sensor
        steps_sensor = next(e for e in registered_entities if getattr(e, "entity_description", None) and e.entity_description.key == "steps")
        assert steps_sensor.native_value == 14250
        assert steps_sensor.extra_state_attributes["distance_km"] == 11.2

        # Verify sleep sensor
        sleep_sensor = next(e for e in registered_entities if getattr(e, "entity_description", None) and e.entity_description.key == "sleep_score")
        assert sleep_sensor.native_value == 91

    # -----------------------------------------------------------------------
    # Step 4: Execute Service: garmin_ha_ai.generate_report
    # -----------------------------------------------------------------------
    llm_report_response = (
        "<summary>Peak recovery with sleep score of 91. Excellent tempo run performance.</summary>\n\n"
        "### Daily Coaching Summary\n\n"
        "Your resting heart rate dropped to 52 bpm with a strong Body Battery recharge of 96. "
        "Training load from today's 50-minute tempo run is well absorbed."
    )

    with patch(
        "custom_components.garmin_ha_ai.ai_engine.gemini.GeminiProvider.async_generate_response",
        new_callable=AsyncMock,
        return_value=llm_report_response,
    ), patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_load_history",
        new_callable=AsyncMock,
        return_value=[{"date": "2026-08-15", "sleep_score": 85, "steps": 10000}],
    ):
        # Call generate_report service
        await coordinator.async_generate_report()

        assert coordinator.latest_report is not None
        assert coordinator.latest_report.short_summary == "Peak recovery with sleep score of 91. Excellent tempo run performance."
        assert coordinator.latest_report.provider_used == PROVIDER_GEMINI
        assert coordinator.latest_report.model_used == DEFAULT_AI_MODEL_GEMINI

        # Find report sensors
        short_report_sensor = next(e for e in registered_entities if e.__class__.__name__ == "GarminAIHealthReportShortSensor")
        long_report_sensor = next(e for e in registered_entities if e.__class__.__name__ == "GarminAIHealthReportLongSensor")

        assert short_report_sensor.native_value == "Peak recovery with sleep score of 91. Excellent tempo run performance."
        assert long_report_sensor.native_value == "Report generated (2026-08-16)"
        assert long_report_sensor.extra_state_attributes["full_report"] == llm_report_response

        # Verify notifications were dispatched to targets
        assert len(notifications_sent) == 2
        assert any(n["target"] == "notify.mobile_app_phone" for n in notifications_sent)
        assert any(n["target"] == "persistent_notification.create" for n in notifications_sent)

    # -----------------------------------------------------------------------
    # Step 5: Execute Service: garmin_ha_ai.ask_question
    # -----------------------------------------------------------------------
    llm_qa_response = "Over the past 7 days, your sleep score averaged 88, showing a consistent upward trend."

    with patch(
        "custom_components.garmin_ha_ai.ai_engine.gemini.GeminiProvider.async_generate_response",
        new_callable=AsyncMock,
        return_value=llm_qa_response,
    ), patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_load_history",
        new_callable=AsyncMock,
        return_value={
            "2026-08-14": {"date": "2026-08-14", "sleep_score": 88, "steps": 12000},
            "2026-08-15": {"date": "2026-08-15", "sleep_score": 85, "steps": 10000},
            "2026-08-16": {"date": "2026-08-16", "sleep_score": 91, "steps": 14250},
        },
    ):
        # Register custom state recorder for response_entity
        target_entity_states = {}
        hass.states = MagicMock()
        def mock_set_state(entity_id, state, attributes=None):
            target_entity_states[entity_id] = {"state": state, "attributes": attributes or {}}
        hass.states.async_set = MagicMock(side_effect=mock_set_state)

        # Trigger service call
        qa_data = {
            "question": "How has my sleep progressed over the last few days?",
            "days_history": 7,
            "response_entity": "sensor.qa_display",
        }

        result = await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            service_data=qa_data,
            return_response=True,
        )

        # Verify Q&A return response payload
        assert result["question"] == "How has my sleep progressed over the last few days?"
        assert result["answer"] == llm_qa_response
        assert result["context_days"] == 3

        # Verify sensor.garmin_ai_last_answer updated
        last_answer_sensor = next(e for e in registered_entities if e.__class__.__name__ == "GarminAILastAnswerSensor")
        assert last_answer_sensor.native_value == llm_qa_response
        assert last_answer_sensor.extra_state_attributes["question"] == "How has my sleep progressed over the last few days?"

        # Verify response_entity state set
        assert "sensor.qa_display" in target_entity_states
        assert target_entity_states["sensor.qa_display"]["state"] == llm_qa_response

    # -----------------------------------------------------------------------
    # Step 6: Options Flow Update & History Prune
    # -----------------------------------------------------------------------
    config_entry.options = {
        CONF_RETENTION_DAYS: 60,
        CONF_FITNESS_GOALS: "Maintain 10k steps daily",
    }

    with patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_prune_history",
        new_callable=AsyncMock,
    ) as mock_prune:
        await async_reload_entry(hass, config_entry)
        mock_prune.assert_called_once_with(60)
        hass.config_entries.async_reload.assert_called_once_with("e2e_test_entry")

    # -----------------------------------------------------------------------
    # Step 7: Clean Unload & Teardown
    # -----------------------------------------------------------------------
    unload_result = await async_unload_entry(hass, config_entry)
    assert unload_result is True
    assert config_entry.entry_id not in hass.data[DOMAIN]
