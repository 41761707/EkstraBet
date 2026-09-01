"""Shared domain errors for administrative operations."""

from __future__ import annotations


class AdminServiceError(Exception):
    """Base error for administrative operations."""


class AdminNotFoundError(AdminServiceError):
    """Raised when the target user or league does not exist."""


class AdminConflictError(AdminServiceError):
    """Raised when a unique field is already taken."""


class AdminValidationError(AdminServiceError):
    """Raised when input or a related foreign key is invalid."""


class AdminForbiddenError(AdminServiceError):
    """Raised when an administrator targets their own protected flags."""
