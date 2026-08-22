"""Tests for multi-account and multi-member profile isolation."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.garmin_ha_ai.const import (
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_GARMIN_USERNAME,
    DOMAIN,
)
from custom_components.garmin_ha_ai.coordinator import GarminDataUpdateCoordinator
from custom_components.garmin_ha_ai.helpers import get_device_info
from custom_components.garmin_ha_ai.models import GarminDailyMetrics
from custom_components.garmin_ha_ai.storage import GarminStorage


def test_storage_multi_account_isolation():
    """Verify that multiple GarminStorage instances with different entry_ids maintain isolated files."""
    async def run():
        mock_hass = MagicMock()

        # Simulated separate Store instances per entry
        saved_stores: dict[str, dict] = {}

        def create_mock_store(hass, version, key, private=False):
            store = MagicMock()
            store.key = key
            store.async_load = AsyncMock(side_effect=lambda: saved_stores.get(key, {}))
            async def _save(data):
                saved_stores[key] = data
            store.async_save = AsyncMock(side_effect=_save)
            return store

        with patch("custom_components.garmin_ha_ai.storage.Store", side_effect=create_mock_store):
            storage_user1 = GarminStorage(mock_hass, entry_id="user_alpha")
            storage_user2 = GarminStorage(mock_hass, entry_id="user_beta")

            # Save distinct tokens for each user
            await storage_user1.async_save_tokens({"tokenstore": "token_alpha_123"})
            await storage_user2.async_save_tokens({"tokenstore": "token_beta_456"})

            # Save distinct daily metrics for each user
            await storage_user1.async_save_daily_metrics({"date": "2026-08-16", "steps": 12000})
            await storage_user2.async_save_daily_metrics({"date": "2026-08-16", "steps": 6000})

            # Load and verify complete isolation
            tokens1 = await storage_user1.async_load_tokens()
            tokens2 = await storage_user2.async_load_tokens()
            assert tokens1.get("tokenstore") == "token_alpha_123"
            assert tokens2.get("tokenstore") == "token_beta_456"

            history1 = await storage_user1.async_load_history()
            history2 = await storage_user2.async_load_history()
            assert history1["2026-08-16"]["steps"] == 12000
            assert history2["2026-08-16"]["steps"] == 6000

    asyncio.run(run())


def test_get_device_info_multi_account_naming():
    """Test device naming and unique identification per user account."""
    entry_alice = MagicMock(
        entry_id="alice_entry_123",
        title="Garmin (alice@example.com)",
        data={CONF_GARMIN_USERNAME: "alice@example.com"},
    )
    entry_bob = MagicMock(
        entry_id="bob_entry_456",
        title="Garmin (bob@example.com)",
        data={CONF_GARMIN_USERNAME: "bob@example.com"},
    )

    device_alice = get_device_info(entry_alice)
    device_bob = get_device_info(entry_bob)

    assert (DOMAIN, "alice_entry_123") in device_alice["identifiers"]
    assert (DOMAIN, "bob_entry_456") in device_bob["identifiers"]
    assert "alice@example.com" in device_alice["name"]
    assert "bob@example.com" in device_bob["name"]
    assert device_alice["name"] != device_bob["name"]
