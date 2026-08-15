"""Tests for Garmin client authentication adapter."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock homeassistant package if not present in test environment
if "homeassistant" not in sys.modules:
    ha_mock = MagicMock()
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.core"] = ha_mock
    sys.modules["homeassistant.const"] = ha_mock
    sys.modules["homeassistant.config_entries"] = ha_mock
    sys.modules["homeassistant.helpers"] = ha_mock
    sys.modules["homeassistant.helpers.storage"] = ha_mock

    class MockConfigEntryAuthFailed(Exception):
        pass

    sys.modules["homeassistant.exceptions"] = MagicMock(
        ConfigEntryAuthFailed=MockConfigEntryAuthFailed
    )

# Mock garminconnect package if not present in test environment
if "garminconnect" not in sys.modules:
    gc_mock = MagicMock()

    class MockGarminConnectAuthenticationError(Exception):
        pass

    class MockGarminConnectConnectionError(Exception):
        pass

    gc_mock.GarminConnectAuthenticationError = MockGarminConnectAuthenticationError
    gc_mock.GarminConnectConnectionError = MockGarminConnectConnectionError
    sys.modules["garminconnect"] = gc_mock

import pytest

from custom_components.garmin_ha_ai.garmin_client import GarminClient
from homeassistant.exceptions import ConfigEntryAuthFailed


def test_login_with_tokens_success() -> None:
    """Test successful token resume."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "dG9rZW4="})
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.garth.dumps.return_value = "dG9rZW4="
            mock_garmin_cls.return_value = mock_garmin_inst

            success = await client_adapter.async_login_with_tokens()

            assert success is True
            assert client_adapter.client is mock_garmin_inst
            mock_garmin_inst.garth.loads.assert_called_once_with("dG9rZW4=")
            mock_garmin_inst.login.assert_called_once()
            mock_storage.async_save_tokens.assert_called_once_with({"tokenstore": "dG9rZW4="})

    asyncio.run(run())


def test_login_with_tokens_auth_failure() -> None:
    """Test token resume raising ConfigEntryAuthFailed on auth failure."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "invalid_token"})

        client_adapter = GarminClient(mock_hass, mock_storage)

        from garminconnect import GarminConnectAuthenticationError

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminConnectAuthenticationError("Token expired")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(ConfigEntryAuthFailed):
                await client_adapter.async_login_with_tokens()

    asyncio.run(run())


def test_login_with_credentials_success() -> None:
    """Test successful credential login."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.garth.dumps.return_value = "new_tokenstore"
            mock_garmin_cls.return_value = mock_garmin_inst

            tokens = await client_adapter.async_login_with_credentials(
                username="testuser@example.com", password="secret_password", mfa_code="123456"
            )

            assert tokens == {"tokenstore": "new_tokenstore"}
            mock_garmin_cls.assert_called_once_with(
                email="testuser@example.com", password="secret_password"
            )
            mock_garmin_inst.login.assert_called_once_with(mfa_code="123456")

    asyncio.run(run())


def test_login_with_credentials_auth_failure() -> None:
    """Test credential login failure raising ConfigEntryAuthFailed."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        from garminconnect import GarminConnectAuthenticationError

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminConnectAuthenticationError("Invalid credentials")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(ConfigEntryAuthFailed):
                await client_adapter.async_login_with_credentials(
                    username="user@example.com", password="wrongpassword"
                )

    asyncio.run(run())


def test_async_get_client() -> None:
    """Test async_get_client returns client when authenticated."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "valid"})
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_cls.return_value = mock_garmin_inst

            client = await client_adapter.async_get_client()
            assert client is mock_garmin_inst

    asyncio.run(run())
