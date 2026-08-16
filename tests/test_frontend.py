"""Tests for Garmin HA AI frontend custom cards registration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.garmin_ha_ai.frontend import (
    FRONTEND_DIR,
    FRONTEND_FILE_PATH,
    FRONTEND_URL,
    FRONTEND_URL_BASE,
    FRONTEND_URL_VERSIONED,
    async_setup_frontend,
)


async def test_frontend_js_file_exists_and_contains_custom_cards():
    """Verify that garmin-ha-ai-cards.js file exists and contains custom card definitions."""
    assert FRONTEND_FILE_PATH.exists()
    content = FRONTEND_FILE_PATH.read_text(encoding="utf-8")

    # Check custom element definitions
    assert "garmin-ha-ai-qa-card" in content
    assert "garmin-ha-ai-report-card" in content
    assert "garmin-ha-ai-overview-card" in content

    # Check window.customCards card picker registration
    assert "window.customCards" in content
    assert "Garmin AI Coach Q&A" in content
    assert "Garmin AI Health Report" in content
    assert "Garmin AI Health Overview" in content

    # Check error banner UI definitions
    assert "garmin-error-banner" in content
    assert "garmin-error-text" in content
    assert "garmin-error-close" in content

    # Check safe linear markdown parsing (no catastrophic backtracking regex)
    assert "renderMarkdown" in content
    assert "ulMatch" in content
    assert "olMatch" in content


async def test_async_setup_frontend_registers_static_path_and_extra_js(hass):
    """Verify that async_setup_frontend properly registers static paths and extra js URL."""
    # Reset registration flag for isolated test
    import custom_components.garmin_ha_ai.frontend as frontend_mod
    frontend_mod._FRONTEND_REGISTERED = False

    with patch("homeassistant.components.frontend.add_extra_js_url") as mock_add_js:
        await async_setup_frontend(hass)

        # Check static path was registered
        hass.http.async_register_static_paths.assert_called_once()
        call_args = hass.http.async_register_static_paths.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].url_path == FRONTEND_URL_BASE
        assert call_args[0].path == str(FRONTEND_DIR)

        # Check extra js url was added
        mock_add_js.assert_called_once_with(hass, FRONTEND_URL_VERSIONED)


async def test_async_setup_frontend_idempotent(hass):
    """Verify that async_setup_frontend is idempotent and does not re-register if already done."""
    import custom_components.garmin_ha_ai.frontend as frontend_mod
    frontend_mod._FRONTEND_REGISTERED = False

    with patch("homeassistant.components.frontend.add_extra_js_url") as mock_add_js:
        await async_setup_frontend(hass)
        assert mock_add_js.call_count == 1

        # Second invocation should be a no-op
        await async_setup_frontend(hass)
        assert mock_add_js.call_count == 1


async def test_async_setup_frontend_fallback_register_static_path(hass):
    """Verify fallback to register_static_path if async_register_static_paths is unavailable."""
    import custom_components.garmin_ha_ai.frontend as frontend_mod
    frontend_mod._FRONTEND_REGISTERED = False

    # Remove async_register_static_paths to test fallback
    delattr(hass.http, "async_register_static_paths")

    with patch("homeassistant.components.frontend.add_extra_js_url") as mock_add_js:
        await async_setup_frontend(hass)
        hass.http.register_static_path.assert_called_once_with(
            FRONTEND_URL_BASE,
            str(FRONTEND_DIR),
            cache_headers=False,
        )
        mock_add_js.assert_called_once_with(hass, FRONTEND_URL_VERSIONED)


async def test_async_setup_frontend_handles_exceptions_gracefully(hass):
    """Verify that exceptions in HTTP or frontend registration do not crash setup."""
    import custom_components.garmin_ha_ai.frontend as frontend_mod
    frontend_mod._FRONTEND_REGISTERED = False

    hass.http.async_register_static_paths.side_effect = Exception("HTTP server error")

    with patch("homeassistant.components.frontend.add_extra_js_url", side_effect=Exception("Frontend error")):
        # Should not raise exception
        await async_setup_frontend(hass)
