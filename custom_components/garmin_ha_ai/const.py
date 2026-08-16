"""Constants for the Garmin HA AI integration."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN: Final[str] = "garmin_ha_ai"
DEFAULT_NAME: Final[str] = "Garmin HA AI"

PLATFORMS: Final[list[Platform]] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.TEXT,
    Platform.SELECT,
]

# Report View / Display Mode Options
REPORT_VIEW_SHORT: Final[str] = "Short Summary"
REPORT_VIEW_LONG: Final[str] = "Long Report"
REPORT_VIEW_QA: Final[str] = "Latest Q&A Answer"
REPORT_VIEW_OPTIONS: Final[list[str]] = [
    REPORT_VIEW_SHORT,
    REPORT_VIEW_LONG,
    REPORT_VIEW_QA,
]

# Configuration Keys - Garmin Credentials
CONF_GARMIN_USERNAME: Final[str] = "username"
CONF_GARMIN_PASSWORD: Final[str] = "password"
CONF_MFA_CODE: Final[str] = "mfa_code"

# Configuration Keys - AI Provider Settings
CONF_AI_PROVIDER: Final[str] = "ai_provider"
CONF_AI_API_KEY: Final[str] = "ai_api_key"
CONF_AI_MODEL: Final[str] = "ai_model"
CONF_AI_BASE_URL: Final[str] = "ai_base_url"

# Configuration Keys - Preferences & Preferences Updates
CONF_POLLING_SCHEDULE: Final[str] = "polling_schedule"
CONF_RETENTION_DAYS: Final[str] = "retention_days"
CONF_NOTIFICATION_TARGETS: Final[str] = "notification_targets"
CONF_FITNESS_GOALS: Final[str] = "fitness_goals"
CONF_COACHING_DIRECTIVES: Final[str] = "coaching_directives"

# Supported AI Providers
PROVIDER_GEMINI: Final[str] = "gemini"
PROVIDER_OPENAI: Final[str] = "openai"

# Default Configuration Values
DEFAULT_AI_PROVIDER: Final[str] = PROVIDER_GEMINI
DEFAULT_AI_MODEL_GEMINI: Final[str] = "gemini-2.5-flash"
DEFAULT_AI_MODEL_OPENAI: Final[str] = "gpt-4o"
DEFAULT_AI_BASE_URL: Final[str] = "https://api.openai.com/v1"

FALLBACK_GEMINI_MODELS: Final[list[str]] = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
]

FALLBACK_OPENAI_MODELS: Final[list[str]] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "o1",
    "o3-mini",
]

DEFAULT_RETENTION_DAYS: Final[int] = 30
MIN_RETENTION_DAYS: Final[int] = 7
MAX_RETENTION_DAYS: Final[int] = 90

DEFAULT_POLLING_TIME: Final[str] = "06:00:00"
DEFAULT_POLLING_INTERVAL_HOURS: Final[int] = 24

# Service Names
SERVICE_GENERATE_REPORT: Final[str] = "generate_report"
SERVICE_ASK_QUESTION: Final[str] = "ask_question"

# Storage Constants
STORAGE_KEY_TOKENS: Final[str] = f"{DOMAIN}_tokens.json"
STORAGE_KEY_HISTORY: Final[str] = f"{DOMAIN}_history.json"
STORAGE_VERSION: Final[int] = 1
