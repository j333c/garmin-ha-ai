"""Tests for storage helper module."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

# Mock homeassistant package if not present in test environment
if "homeassistant" not in sys.modules:
    ha_mock = MagicMock()
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.core"] = ha_mock
    sys.modules["homeassistant.const"] = ha_mock
    sys.modules["homeassistant.config_entries"] = ha_mock
    sys.modules["homeassistant.helpers"] = ha_mock
    sys.modules["homeassistant.helpers.storage"] = ha_mock

    class MockStore:
        def __init__(self, hass, version, key):
            self.hass = hass
            self.version = version
            self.key = key
            self.async_load = MagicMock()
            self.async_save = MagicMock()

    sys.modules["homeassistant.helpers.storage"].Store = MockStore

import pytest

from custom_components.garmin_ha_ai.storage import GarminStorage


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture for mock HomeAssistant instance."""
    return MagicMock()


def test_load_tokens_clean_install(mock_hass: MagicMock) -> None:
    """Test loading tokens on clean install returns empty dict."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        storage._token_store.async_load = AsyncMock(return_value=None)

        result = await storage.async_load_tokens()
        assert result == {}
        storage._token_store.async_load.assert_called_once()

    asyncio.run(run())


def test_save_and_load_tokens(mock_hass: MagicMock) -> None:
    """Test saving and loading OAuth tokens."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        stored_data: dict | None = None

        async def mock_save(data: dict) -> None:
            nonlocal stored_data
            stored_data = data

        async def mock_load() -> dict | None:
            return stored_data

        storage._token_store.async_save = AsyncMock(side_effect=mock_save)
        storage._token_store.async_load = AsyncMock(side_effect=mock_load)

        tokens = {"token": "sample_oauth_token", "refresh_token": "sample_refresh"}
        await storage.async_save_tokens(tokens)
        assert stored_data == tokens

        loaded = await storage.async_load_tokens()
        assert loaded == tokens

    asyncio.run(run())


def test_load_history_clean_install(mock_hass: MagicMock) -> None:
    """Test loading history on clean install returns empty dict."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        storage._history_store.async_load = AsyncMock(return_value=None)

        result = await storage.async_load_history()
        assert result == {}
        storage._history_store.async_load.assert_called_once()

    asyncio.run(run())


def test_save_and_load_history(mock_hass: MagicMock) -> None:
    """Test saving and loading metric history."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        stored_data: dict | None = None

        async def mock_save(data: dict) -> None:
            nonlocal stored_data
            stored_data = data

        async def mock_load() -> dict | None:
            return stored_data

        storage._history_store.async_save = AsyncMock(side_effect=mock_save)
        storage._history_store.async_load = AsyncMock(side_effect=mock_load)

        history = {"2026-08-15": {"steps": 10000, "sleep_score": 85}}
        await storage.async_save_history(history)
        assert stored_data == history

        loaded = await storage.async_load_history()
        assert loaded == history

    asyncio.run(run())


def test_concurrent_read_write(mock_hass: MagicMock) -> None:
    """Test concurrent read/write operations execute safely under lock."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        stored_tokens = {}

        async def mock_save(data: dict) -> None:
            await asyncio.sleep(0.01)
            stored_tokens.update(data)

        async def mock_load() -> dict:
            await asyncio.sleep(0.01)
            return dict(stored_tokens)

        storage._token_store.async_save = AsyncMock(side_effect=mock_save)
        storage._token_store.async_load = AsyncMock(side_effect=mock_load)

        async def writer(val: int) -> None:
            await storage.async_save_tokens({"key": val})

        async def reader() -> dict:
            return await storage.async_load_tokens()

        results = await asyncio.gather(writer(1), reader(), writer(2), reader())
        assert isinstance(results[1], dict)
        assert isinstance(results[3], dict)

    asyncio.run(run())


def test_prune_history(mock_hass: MagicMock) -> None:
    """Test history pruning removes entries older than retention_days."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        history_data = {
            "2020-01-01": {"steps": 5000},
            "2026-08-15": {"steps": 12000},
        }

        async def mock_save(data: dict) -> None:
            history_data.clear()
            history_data.update(data)

        async def mock_load() -> dict:
            return history_data

        storage._history_store.async_save = AsyncMock(side_effect=mock_save)
        storage._history_store.async_load = AsyncMock(side_effect=mock_load)

        await storage.async_prune_history(retention_days=30)
        assert "2020-01-01" not in history_data
        assert "2026-08-15" in history_data

    asyncio.run(run())


def test_save_daily_metrics(mock_hass: MagicMock) -> None:
    """Test saving single daily metric snapshot via async_save_daily_metrics."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        stored_data: dict = {}

        async def mock_save(data: dict) -> None:
            nonlocal stored_data
            stored_data = data

        async def mock_load() -> dict | None:
            return stored_data

        storage._history_store.async_save = AsyncMock(side_effect=mock_save)
        storage._history_store.async_load = AsyncMock(side_effect=mock_load)

        metric_snapshot = {"date": "2026-08-16", "steps": 10500, "sleep_score": 90}
        await storage.async_save_daily_metrics(metric_snapshot)
        assert stored_data.get("2026-08-16") == metric_snapshot

    asyncio.run(run())


def test_storage_token_store_private_flag(mock_hass: MagicMock) -> None:
    """Test that token Store is created with private=True for secure file permissions."""
    storage = GarminStorage(mock_hass)
    assert getattr(storage._token_store, "private", None) is True


def test_save_daily_metrics_empty_or_invalid(mock_hass: MagicMock) -> None:
    """Test that empty snapshots or snapshots missing 'date' are rejected without saving."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        storage._history_store.async_save = AsyncMock()
        storage._history_store.async_load = AsyncMock(return_value={})

        # 1. Empty dict
        await storage.async_save_daily_metrics({})
        storage._history_store.async_save.assert_not_called()

        # 2. None
        await storage.async_save_daily_metrics(None)
        storage._history_store.async_save.assert_not_called()

        # 3. Missing date key
        await storage.async_save_daily_metrics({"steps": 5000})
        storage._history_store.async_save.assert_not_called()

    asyncio.run(run())


def test_save_and_prune_history_atomic(mock_hass: MagicMock) -> None:
    """Test async_save_and_prune_history adds new entry and prunes in a single disk write."""

    async def run() -> None:
        storage = GarminStorage(mock_hass)
        history_data = {
            "2020-01-01": {"date": "2020-01-01", "steps": 3000},
            "2026-08-15": {"date": "2026-08-15", "steps": 10000},
        }

        async def mock_save(data: dict) -> None:
            history_data.clear()
            history_data.update(data)

        async def mock_load() -> dict:
            return history_data

        storage._history_store.async_save = AsyncMock(side_effect=mock_save)
        storage._history_store.async_load = AsyncMock(side_effect=mock_load)

        new_snapshot = {"date": "2026-08-16", "steps": 12500}
        await storage.async_save_and_prune_history(new_snapshot, retention_days=30)

        # Single save call performed
        storage._history_store.async_save.assert_called_once()
        # Old entry pruned
        assert "2020-01-01" not in history_data
        # Existing recent entry retained
        assert "2026-08-15" in history_data
        # New entry saved
        assert history_data["2026-08-16"] == new_snapshot

    asyncio.run(run())


def test_legacy_token_migration_removes_legacy_store(mock_hass: MagicMock) -> None:
    """Test that loading from legacy store migrates tokens and removes the legacy store."""

    async def run() -> None:
        storage = GarminStorage(mock_hass, entry_id="entry_456")
        storage._token_store.async_load = AsyncMock(return_value=None)
        storage._token_store.async_save = AsyncMock()
        storage._legacy_token_store.async_load = AsyncMock(return_value={"token": "legacy_token"})
        storage._legacy_token_store.async_remove = AsyncMock()

        tokens = await storage.async_load_tokens()
        assert tokens == {"token": "legacy_token"}
        storage._token_store.async_save.assert_called_once_with({"token": "legacy_token"})
        storage._legacy_token_store.async_remove.assert_called_once()

    asyncio.run(run())


def test_legacy_history_migration_removes_legacy_store(mock_hass: MagicMock) -> None:
    """Test that loading from legacy history store migrates data and removes the legacy store."""

    async def run() -> None:
        storage = GarminStorage(mock_hass, entry_id="entry_456")
        storage._history_store.async_load = AsyncMock(return_value=None)
        storage._history_store.async_save = AsyncMock()
        storage._legacy_history_store.async_load = AsyncMock(return_value={"2026-08-15": {"steps": 10000}})
        storage._legacy_history_store.async_remove = AsyncMock()

        history = await storage.async_load_history()
        assert history == {"2026-08-15": {"steps": 10000}}
        storage._history_store.async_save.assert_called_once_with({"2026-08-15": {"steps": 10000}})
        storage._legacy_history_store.async_remove.assert_called_once()

    asyncio.run(run())


