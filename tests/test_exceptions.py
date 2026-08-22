"""Tests for centralized exception taxonomy and translation consistency."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.garmin_ha_ai.const import (
    CONF_POLLING_INTERVAL,
    CONF_POLLING_MODE,
    DEFAULT_POLLING_INTERVAL_HOURS,
    POLLING_MODE_DAILY,
    POLLING_MODE_INTERVAL,
)
from custom_components.garmin_ha_ai.coordinator import calculate_coordinator_interval
from custom_components.garmin_ha_ai.exceptions import (
    AIEngineAuthError,
    AIEngineClientError,
    AIEngineConnectionError,
    AIEngineError,
    AIEngineModelNotFoundError,
    AIEngineQuotaError,
    AIEngineTimeoutError,
    GarminAIError,
    GarminAuthError,
    GarminConnectionError,
    GarminDataParsingError,
    GarminError,
    GarminMfaRequired,
    GarminRateLimitError,
    GarminSessionExpiredError,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError


def test_exception_taxonomy_hierarchy():
    """Test inheritance structure of centralized exceptions."""
    # Base check
    assert issubclass(GarminAIError, HomeAssistantError)

    # Garmin error hierarchy
    assert issubclass(GarminError, GarminAIError)
    assert issubclass(GarminAuthError, GarminError)
    assert issubclass(GarminAuthError, ConfigEntryAuthFailed)
    assert issubclass(GarminMfaRequired, GarminError)
    assert issubclass(GarminRateLimitError, GarminError)
    assert issubclass(GarminConnectionError, GarminError)
    assert issubclass(GarminDataParsingError, GarminError)
    assert issubclass(GarminSessionExpiredError, GarminAuthError)

    # AI engine hierarchy
    assert issubclass(AIEngineError, GarminAIError)
    assert issubclass(AIEngineAuthError, AIEngineError)
    assert issubclass(AIEngineQuotaError, AIEngineError)
    assert issubclass(AIEngineTimeoutError, AIEngineError)
    assert issubclass(AIEngineModelNotFoundError, AIEngineError)
    assert issubclass(AIEngineClientError, AIEngineError)
    assert issubclass(AIEngineConnectionError, AIEngineError)


def test_translation_files_integrity_and_matching_keys():
    """Verify that strings.json, en.json, and de.json have identical key structures."""
    comp_dir = Path(__file__).parent.parent / "custom_components" / "garmin_ha_ai"
    strings_file = comp_dir / "strings.json"
    en_file = comp_dir / "translations" / "en.json"
    de_file = comp_dir / "translations" / "de.json"

    assert strings_file.exists()
    assert en_file.exists()
    assert de_file.exists()

    strings_data = json.loads(strings_file.read_text(encoding="utf-8"))
    en_data = json.loads(en_file.read_text(encoding="utf-8"))
    de_data = json.loads(de_file.read_text(encoding="utf-8"))

    def extract_keys(d: dict, prefix: str = "") -> set[str]:
        keys = set()
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(extract_keys(v, full))
            else:
                keys.add(full)
        return keys

    strings_keys = extract_keys(strings_data)
    en_keys = extract_keys(en_data)
    de_keys = extract_keys(de_data)

    assert strings_keys == en_keys
    assert strings_keys == de_keys


def test_calculate_coordinator_interval_modes():
    """Test polling interval calculation for daily vs interval modes."""
    class FakeEntry:
        def __init__(self, options=None, data=None):
            self.options = options or {}
            self.data = data or {}

    # Default daily mode
    entry_daily = FakeEntry(options={CONF_POLLING_MODE: POLLING_MODE_DAILY})
    delta_daily = calculate_coordinator_interval(entry_daily)
    assert delta_daily.total_seconds() == 24 * 3600

    # Interval mode: 6 hours
    entry_int6 = FakeEntry(options={CONF_POLLING_MODE: POLLING_MODE_INTERVAL, CONF_POLLING_INTERVAL: 6})
    delta_int6 = calculate_coordinator_interval(entry_int6)
    assert delta_int6.total_seconds() == 6 * 3600

    # Interval mode: 3 hours string
    entry_int3 = FakeEntry(options={CONF_POLLING_MODE: POLLING_MODE_INTERVAL, CONF_POLLING_INTERVAL: "3"})
    delta_int3 = calculate_coordinator_interval(entry_int3)
    assert delta_int3.total_seconds() == 3 * 3600
