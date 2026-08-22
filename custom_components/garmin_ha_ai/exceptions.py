"""Centralized exception taxonomy for Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError


class GarminAIError(HomeAssistantError):
    """Base exception for all Garmin HA AI integration errors."""


# =========================================================================
# Garmin Connect API Exceptions
# =========================================================================

class GarminError(GarminAIError):
    """Base exception for Garmin Connect API interactions."""


class GarminAuthError(GarminError, ConfigEntryAuthFailed):
    """Exception raised when Garmin Connect authentication fails permanently."""


class GarminMfaRequired(GarminError):
    """Exception raised when Garmin Connect requires MFA verification passcode."""


GarminConnectMfaRequired = GarminMfaRequired


class GarminRateLimitError(GarminError):
    """Exception raised when Garmin Connect rate-limits requests (HTTP 429)."""


class GarminConnectionError(GarminError):
    """Exception raised when network communication with Garmin servers fails."""


class GarminDataParsingError(GarminError):
    """Exception raised when Garmin API payload structure cannot be parsed."""


class GarminSessionExpiredError(GarminAuthError):
    """Exception raised when stored OAuth session tokens have expired."""


# =========================================================================
# AI Engine Exceptions
# =========================================================================

class AIEngineError(GarminAIError):
    """Base exception for AI provider engine errors."""


class AIEngineAuthError(AIEngineError):
    """Exception raised when AI provider authentication or API key fails (HTTP 401/403)."""


class AIEngineQuotaError(AIEngineError):
    """Exception raised when AI provider API quota or rate limits are exhausted (HTTP 429)."""


class AIEngineTimeoutError(AIEngineError):
    """Exception raised when an AI generation request exceeds the configured timeout."""


class AIEngineModelNotFoundError(AIEngineError):
    """Exception raised when the requested AI model is not found or unsupported (HTTP 404)."""


class AIEngineClientError(AIEngineError):
    """Exception raised for non-transient AI client errors (HTTP 400 Bad Request, invalid payload)."""


class AIEngineConnectionError(AIEngineError):
    """Exception raised when network connection to the AI provider endpoint fails."""
