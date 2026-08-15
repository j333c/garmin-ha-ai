"""Storage helper for Garmin HA AI integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    LOGGER,
    STORAGE_KEY_HISTORY,
    STORAGE_KEY_TOKENS,
    STORAGE_VERSION,
)


class GarminStorage:
    """Manages local storage for OAuth tokens and metric history snapshots."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage helper with HA Store instances and locks."""
        self._token_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TOKENS
        )
        self._history_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_HISTORY
        )
        self._token_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()

    async def async_load_tokens(self) -> dict[str, Any]:
        """Load OAuth tokens from local storage.

        Returns empty dict if storage file does not exist.
        """
        async with self._token_lock:
            try:
                data = await self._token_store.async_load()
                return data if data is not None else {}
            except Exception as err:
                LOGGER.warning("Error loading Garmin OAuth tokens from storage: %s", err)
                return {}

    async def async_save_tokens(self, tokens: dict[str, Any]) -> None:
        """Save OAuth tokens to local storage."""
        async with self._token_lock:
            await self._token_store.async_save(tokens)

    async def async_load_history(self) -> dict[str, Any]:
        """Load daily metric history snapshots from local storage.

        Returns empty dict if storage file does not exist.
        """
        async with self._history_lock:
            try:
                data = await self._history_store.async_load()
                return data if data is not None else {}
            except Exception as err:
                LOGGER.warning("Error loading Garmin metric history from storage: %s", err)
                return {}

    async def async_save_history(self, history: dict[str, Any]) -> None:
        """Save daily metric history snapshots to local storage."""
        async with self._history_lock:
            await self._history_store.async_save(history)

    async def async_prune_history(self, retention_days: int) -> None:
        """Prune metric history entries older than retention_days."""
        from datetime import datetime, timedelta, timezone

        async with self._history_lock:
            history = await self._history_store.async_load()
            if not history or not isinstance(history, dict):
                return

            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=retention_days)
            ).strftime("%Y-%m-%d")
            pruned_history = {
                date_str: metrics
                for date_str, metrics in history.items()
                if date_str >= cutoff
            }
            if len(pruned_history) != len(history):
                await self._history_store.async_save(pruned_history)
