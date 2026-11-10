"""Domain errors for the shared player profile."""

from __future__ import annotations


class PlayerProfileNotFoundError(Exception):
    """Raised when no player exists for the given id."""


class PlayerProfileUnavailableError(Exception):
    """Raised when the sport has no profile source."""


class PlayerProfileValidationError(Exception):
    """Raised when a profile filter is rejected."""

    def __init__(self, message: str) -> None:
        """Store the English message returned to the client."""
        self.message = message
        super().__init__(message)
