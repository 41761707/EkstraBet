"""Unit tests for favorite league domain rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services.favorite_league_service import (
    LeagueNotAvailableError,
    add_favorite_league,
    get_favorite_league_ids,
    remove_favorite_league)


_USER = {
    "id": 7,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice"
}

_GET_SUMMARY = (
    "backend.services.favorite_league_service.league_service"
    ".get_league_summary")
_FETCH_IDS = (
    "backend.services.favorite_league_service.repository"
    ".fetch_favorite_league_ids")
_ADD = (
    "backend.services.favorite_league_service.repository"
    ".add_favorite_league")
_REMOVE = (
    "backend.services.favorite_league_service.repository"
    ".remove_favorite_league")


class TestGetFavoriteLeagueIds(unittest.TestCase):
    """Read uses only the internal users.id."""

    @patch(_FETCH_IDS, return_value=[1, 4])
    def test_reads_ids_by_internal_user_id(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(get_favorite_league_ids(_USER), [1, 4])
        mock_fetch.assert_called_once_with(7)


class TestAddFavoriteLeague(unittest.TestCase):
    """Insert requires an existing, active league."""

    @patch(_ADD)
    @patch(_GET_SUMMARY, return_value={"id": 4, "active": True})
    def test_adds_active_league(
            self,
            mock_summary: MagicMock,
            mock_add: MagicMock) -> None:
        add_favorite_league(_USER, 4)
        mock_summary.assert_called_once_with(4)
        mock_add.assert_called_once_with(7, 4)

    @patch(_ADD)
    @patch(_GET_SUMMARY, return_value={"id": 4, "active": False})
    def test_rejects_inactive_league(
            self,
            mock_summary: MagicMock,
            mock_add: MagicMock) -> None:
        with self.assertRaises(LeagueNotAvailableError) as ctx:
            add_favorite_league(_USER, 4)
        self.assertEqual(str(ctx.exception), "League not available")
        mock_summary.assert_called_once_with(4)
        mock_add.assert_not_called()

    @patch(_ADD)
    @patch(_GET_SUMMARY, return_value=None)
    def test_rejects_missing_league(
            self,
            mock_summary: MagicMock,
            mock_add: MagicMock) -> None:
        with self.assertRaises(LeagueNotAvailableError) as ctx:
            add_favorite_league(_USER, 999)
        self.assertEqual(str(ctx.exception), "League not available")
        mock_summary.assert_called_once_with(999)
        mock_add.assert_not_called()


class TestRemoveFavoriteLeague(unittest.TestCase):
    """Delete stays safe for missing rows and deactivated leagues."""

    @patch(_REMOVE)
    @patch(_GET_SUMMARY)
    def test_removes_without_checking_league_availability(
            self,
            mock_summary: MagicMock,
            mock_remove: MagicMock) -> None:
        remove_favorite_league(_USER, 4)
        mock_remove.assert_called_once_with(7, 4)
        mock_summary.assert_not_called()

    @patch(_REMOVE)
    def test_historical_inactive_relation_still_succeeds(
            self,
            mock_remove: MagicMock) -> None:
        # relacja może przetrwać active=0; DELETE i tak ma się udać
        remove_favorite_league(_USER, 8)
        mock_remove.assert_called_once_with(7, 8)


if __name__ == "__main__":
    unittest.main()
