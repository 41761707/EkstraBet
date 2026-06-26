"""Backward-compatible re-exports; prefer backend.config."""

from backend.config import (
    Settings,
    get_database_config,
    get_database_url,
    get_settings,
    settings)

__all__ = [
    "Settings",
    "get_database_config",
    "get_database_url",
    "get_settings",
    "settings"]
