"""Unit tests for user preferences domain rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services.user_preferences_service import (
    EmptyPreferencesPatchError,
    InvalidTeamNameDisplayError,
    InvalidThemeError,
    get_preferences,
    update_preferences)

_USER = {
    "id": 7,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice"
}
_DOCUMENT = {"theme": "dark", "team_name_display": "full"}
_FETCH = (
    "backend.services.user_preferences_service.repository"
    ".fetch_preferences")
_UPSERT = (
    "backend.services.user_preferences_service.repository"
    ".upsert_preferences")


class TestGetPreferences(unittest.TestCase):
    """Read uses only the internal users.id."""

    @patch(_FETCH, return_value=_DOCUMENT)
    def test_reads_by_internal_user_id(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(get_preferences(_USER), _DOCUMENT)
        mock_fetch.assert_called_once_with(7)

    @patch(_FETCH, return_value=None)
    def test_missing_row_returns_none(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertIsNone(get_preferences(_USER))
        mock_fetch.assert_called_once_with(7)


class TestUpdatePreferences(unittest.TestCase):
    """Write allowlists fields and never uses the public uuid."""

    @patch(_UPSERT, return_value=_DOCUMENT)
    def test_upserts_allowlisted_theme(
            self,
            mock_upsert: MagicMock) -> None:
        for theme in ("system", "dark", "light"):
            mock_upsert.reset_mock()
            stored = {"theme": theme, "team_name_display": "full"}
            mock_upsert.return_value = stored
            self.assertEqual(
                update_preferences(_USER, theme=theme),
                stored)
            mock_upsert.assert_called_once_with(
                7,
                theme=theme,
                team_name_display=None)

    @patch(_UPSERT, return_value=_DOCUMENT)
    def test_upserts_allowlisted_team_name_display(
            self,
            mock_upsert: MagicMock) -> None:
        for preference in ("full", "shortcut"):
            mock_upsert.reset_mock()
            stored = {"theme": "dark", "team_name_display": preference}
            mock_upsert.return_value = stored
            self.assertEqual(
                update_preferences(_USER, team_name_display=preference),
                stored)
            mock_upsert.assert_called_once_with(
                7,
                theme=None,
                team_name_display=preference)

    @patch(_UPSERT, return_value=_DOCUMENT)
    def test_upserts_both_fields_in_one_call(
            self,
            mock_upsert: MagicMock) -> None:
        stored = {"theme": "light", "team_name_display": "shortcut"}
        mock_upsert.return_value = stored
        self.assertEqual(
            update_preferences(
                _USER,
                theme="light",
                team_name_display="shortcut"),
            stored)
        mock_upsert.assert_called_once_with(
            7,
            theme="light",
            team_name_display="shortcut")

    @patch(_UPSERT)
    def test_rejects_unknown_theme(
            self,
            mock_upsert: MagicMock) -> None:
        with self.assertRaises(InvalidThemeError) as ctx:
            update_preferences(_USER, theme="sepia")
        self.assertEqual(str(ctx.exception), "Invalid theme")
        mock_upsert.assert_not_called()

    @patch(_UPSERT)
    def test_rejects_unknown_team_name_display(
            self,
            mock_upsert: MagicMock) -> None:
        with self.assertRaises(InvalidTeamNameDisplayError) as ctx:
            update_preferences(_USER, team_name_display="abbrev")
        self.assertEqual(str(ctx.exception), "Invalid team_name_display")
        mock_upsert.assert_not_called()

    @patch(_UPSERT)
    def test_rejects_empty_patch(
            self,
            mock_upsert: MagicMock) -> None:
        with self.assertRaises(EmptyPreferencesPatchError) as ctx:
            update_preferences(_USER)
        self.assertEqual(
            str(ctx.exception),
            "At least one preference field is required")
        mock_upsert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
