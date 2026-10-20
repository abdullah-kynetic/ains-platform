"""Egnyte client exceptions. Messages never include credentials or tokens."""

from __future__ import annotations


class EgnyteError(Exception):
    """Base class for Egnyte client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class EgnyteConfigError(EgnyteError):
    """Required settings are missing or invalid."""


class EgnyteAuthError(EgnyteError):
    """401 or token-endpoint failure: bad/expired token, unknown or unapproved key."""


class EgnytePermissionError(EgnyteError):
    """403: user lacks access, token lacks scope, or the plan has no API access."""


class EgnyteNotFoundError(EgnyteError):
    """404: file or folder does not exist."""


class EgnyteRateLimitError(EgnyteError):
    """429 (or token-endpoint 409) persisted after retries, or daily quota exhausted."""


class EgnyteAPIError(EgnyteError):
    """Any other non-success response."""
