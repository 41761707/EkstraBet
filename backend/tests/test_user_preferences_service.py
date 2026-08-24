"""Unit tests for user preferences domain rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services.user_preferences_service import (
    InvalidThemeError,
    get_preferences,
    update_theme)


_USER = {
    "id": 7,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice"
}

_FETCH = (
    "backend.services.user_preferences_service.repository"
    ".fetch_preferences")
_UPSERT = (
    "backend.services.user_preferences_service.repository"
    ".upsert_theme")


class TestGetPreferences(unittest.TestCase):
    """Read uses only the internal users.id."""

    @patch(_FETCH, return_value={"theme": "light"})
    def test_reads_by_internal_user_id(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(get_preferences(_USER), {"theme": "light"})
        mock_fetch.assert_called_once_with(7)

    @patch(_FETCH, return_value=None)
    def test_missing_row_returns_none(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertIsNone(get_preferences(_USER))
        mock_fetch.assert_called_once_with(7)


class TestUpdateTheme(unittest.TestCase):
    """Write allowlists theme and never uses the public uuid."""

    @patch(_UPSERT, return_value={"theme": "dark"})
    def test_upserts_allowlisted_theme(
            self,
            mock_upsert: MagicMock) -> None:
        for theme in ("system", "dark", "light"):
            mock_upsert.reset_mock()
            mock_upsert.return_value = {"theme": theme}
            self.assertEqual(update_theme(_USER, theme), {"theme": theme})
            mock_upsert.assert_called_once_with(7, theme)

    @patch(_UPSERT)
    def test_rejects_unknown_theme(
            self,
            mock_upsert: MagicMock) -> None:
        with self.assertRaises(InvalidThemeError) as ctx:
            update_theme(_USER, "sepia")
        self.assertEqual(str(ctx.exception), "Invalid theme")
        mock_upsert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
