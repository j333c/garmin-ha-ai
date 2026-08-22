"""Storage helper for Garmin HA AI integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
import homeassistant.util.dt as dt_util

from .const import (
    LOGGER,
    STORAGE_KEY_HISTORY,
    STORAGE_KEY_TOKENS,
    STORAGE_VERSION,
)


class GarminStorage:
    """Manages local storage for OAuth tokens and metric history snapshots.

    Uses Home Assistant's built-in Store helper (homeassistant.helpers.storage.Store)
    to perform atomic, safe JSON reads/writes in the .storage directory.
    Employs asyncio locks to prevent race conditions during concurrent coordinator access.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage helper with HA Store instances and locks."""
        # Separate storage stores for sensitive OAuth tokens and metrics history
        self._token_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TOKENS
        )
        self._history_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_HISTORY
        )
        # Concurrency locks guaranteeing single-writer consistency
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

    async def async_save_daily_metrics(self, metrics_dict: dict[str, Any]) -> None:
        """Save a single day's metric snapshot into history storage."""
        if not metrics_dict or "date" not in metrics_dict:
            return

        async with self._history_lock:
            try:
                data = await self._history_store.async_load()
                history = data if isinstance(data, dict) else {}
                # Index snapshot dictionary by ISO date string (YYYY-MM-DD)
                history[metrics_dict["date"]] = metrics_dict
                await self._history_store.async_save(history)
            except Exception as err:
                LOGGER.warning("Error saving daily metrics snapshot to storage: %s", err)

    async def async_prune_history(self, retention_days: int) -> None:
        """Prune metric history entries older than retention_days.

        Calculates date cutoff string and removes older entries to keep storage compact.
        """
        async with self._history_lock:
            history = await self._history_store.async_load()
            if not history or not isinstance(history, dict):
                return

            days = int(retention_days) if retention_days else 30
            cutoff = None
            try:
                now = dt_util.now()
                if isinstance(getattr(now, "year", None), int) and hasattr(now, "date"):
                    cutoff = (now.date() - timedelta(days=days)).strftime("%Y-%m-%d")
            except Exception:
                pass

            if not cutoff or not isinstance(cutoff, str):
                cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Filter snapshots retaining only dates on or after the cutoff date
            pruned_history = {
                date_str: metrics
                for date_str, metrics in history.items()
                if isinstance(date_str, str) and date_str >= cutoff
            }
            # Only perform disk write if entries were actually pruned
            if len(pruned_history) != len(history):
                await self._history_store.async_save(pruned_history)



