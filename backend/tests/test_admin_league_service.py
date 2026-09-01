"""Unit tests for administrative league domain rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.services import admin_league_service as service
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError


_REPO_LEAGUE_ROW = {
    "id": 48,
    "name": "Test League",
    "country_id": 1,
    "country_name": "Polska",
    "country_emoji": "🇵🇱",
    "sport_id": 1,
    "sport_name": "Piłka nożna",
    "active": 1,
    "last_update": None,
    "current_season_id": 13,
    "tier": 1,
    "has_player_stats": 0}

_COUNTRY_ROWS = [{"id": 1, "name": "Polska"}]
_SPORT_ROWS = [{"id": 1, "name": "Piłka nożna"}]
_SEASON_ROWS = [{"id": 13, "years": "2026/27"}]

_FETCH_ALL = (
    "backend.services.admin_league_service.league_repository"
    ".fetch_all_leagues")
_CREATE = (
    "backend.services.admin_league_service.league_repository.create_league")
_SET_ACTIVE = (
    "backend.services.admin_league_service.league_repository"
    ".set_league_active")
_FETCH_COUNTRIES = (
    "backend.services.admin_league_service.country_repository"
    ".fetch_all_countries")
_FETCH_SPORTS = (
    "backend.services.admin_league_service.sport_repository.fetch_all_sports")
_FETCH_SEASONS = (
    "backend.services.admin_league_service.season_repository"
    ".fetch_all_seasons")


def _patch_dictionaries(
        mock_countries: MagicMock,
        mock_sports: MagicMock,
        mock_seasons: MagicMock | None = None) -> None:
    mock_countries.return_value = list(_COUNTRY_ROWS)
    mock_sports.return_value = list(_SPORT_ROWS)
    if mock_seasons is not None:
        mock_seasons.return_value = list(_SEASON_ROWS)


class TestListLeagues(unittest.TestCase):
    """List maps numeric flags to bool and keeps joined labels."""

    @patch(_FETCH_ALL, return_value=[_REPO_LEAGUE_ROW])
    def test_maps_flags_and_foreign_labels(
            self,
            mock_fetch: MagicMock) -> None:
        leagues = service.list_leagues()
        self.assertEqual(len(leagues), 1)
        league = leagues[0]
        self.assertEqual(league["id"], 48)
        self.assertEqual(league["name"], "Test League")
        self.assertEqual(league["country_id"], 1)
        self.assertEqual(league["country_name"], "Polska")
        self.assertEqual(league["country_emoji"], "🇵🇱")
        self.assertEqual(league["sport_id"], 1)
        self.assertTrue(league["active"])
        self.assertFalse(league["has_player_stats"])
        self.assertEqual(league["current_season_id"], 13)
        self.assertEqual(league["tier"], 1)
        self.assertIsNone(league["last_update"])
        mock_fetch.assert_called_once_with()

    @patch(_FETCH_ALL, return_value=[])
    def test_empty_list(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(service.list_leagues(), [])
        mock_fetch.assert_called_once_with()

    @patch(
        _FETCH_ALL,
        return_value=[{
            **_REPO_LEAGUE_ROW,
            "name": None,
            "active": 0,
            "has_player_stats": 1,
            "current_season_id": None,
            "tier": None}])
    def test_maps_inactive_and_nullable_fields(
            self,
            _mock_fetch: MagicMock) -> None:
        league = service.list_leagues()[0]
        self.assertIsNone(league["name"])
        self.assertFalse(league["active"])
        self.assertTrue(league["has_player_stats"])
        self.assertIsNone(league["current_season_id"])
        self.assertIsNone(league["tier"])


class TestCreateLeague(unittest.TestCase):
    """Create checks dictionary FKs, then inserts an active league."""

    @patch(_CREATE, return_value=_REPO_LEAGUE_ROW)
    @patch(_FETCH_SEASONS)
    @patch(_FETCH_SPORTS)
    @patch(_FETCH_COUNTRIES)
    def test_happy_path_inserts_active_league(
            self,
            mock_countries: MagicMock,
            mock_sports: MagicMock,
            mock_seasons: MagicMock,
            mock_create: MagicMock) -> None:
        _patch_dictionaries(mock_countries, mock_sports, mock_seasons)
        created = service.create_league(
            "  Test League  ",
            1,
            1,
            13,
            1,
            False)
        mock_create.assert_called_once_with(
            "Test League",
            1,
            1,
            13,
            1,
            False,
            active=True)
        self.assertEqual(created["id"], 48)
        self.assertTrue(created["active"])
        self.assertFalse(created["has_player_stats"])

    @patch(_CREATE, return_value=_REPO_LEAGUE_ROW)
    @patch(_FETCH_SEASONS)
    @patch(_FETCH_SPORTS)
    @patch(_FETCH_COUNTRIES)
    def test_optional_season_skips_season_lookup(
            self,
            mock_countries: MagicMock,
            mock_sports: MagicMock,
            mock_seasons: MagicMock,
            mock_create: MagicMock) -> None:
        _patch_dictionaries(mock_countries, mock_sports)
        service.create_league("Test League", 1, 1)
        mock_seasons.assert_not_called()
        mock_create.assert_called_once_with(
            "Test League",
            1,
            1,
            None,
            None,
            False,
            active=True)

    @patch(_CREATE)
    @patch(_FETCH_SPORTS)
    @patch(_FETCH_COUNTRIES, return_value=[])
    def test_unknown_country_does_not_write(
            self,
            _mock_countries: MagicMock,
            mock_sports: MagicMock,
            mock_create: MagicMock) -> None:
        mock_sports.return_value = list(_SPORT_ROWS)
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("Test League", 999, 1, 13, 1)
        self.assertEqual(str(ctx.exception), "Country not found")
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_FETCH_SPORTS, return_value=[])
    @patch(_FETCH_COUNTRIES)
    def test_unknown_sport_does_not_write(
            self,
            mock_countries: MagicMock,
            _mock_sports: MagicMock,
            mock_create: MagicMock) -> None:
        mock_countries.return_value = list(_COUNTRY_ROWS)
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("Test League", 1, 999, 13, 1)
        self.assertEqual(str(ctx.exception), "Sport not found")
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_FETCH_SEASONS, return_value=[])
    @patch(_FETCH_SPORTS)
    @patch(_FETCH_COUNTRIES)
    def test_unknown_season_does_not_write(
            self,
            mock_countries: MagicMock,
            mock_sports: MagicMock,
            _mock_seasons: MagicMock,
            mock_create: MagicMock) -> None:
        _patch_dictionaries(mock_countries, mock_sports)
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("Test League", 1, 1, 999, 1)
        self.assertEqual(str(ctx.exception), "Season not found")
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_FETCH_SEASONS)
    @patch(_FETCH_SPORTS)
    @patch(_FETCH_COUNTRIES)
    def test_foreign_key_integrity_error_is_safety_net(
            self,
            mock_countries: MagicMock,
            mock_sports: MagicMock,
            mock_seasons: MagicMock,
            mock_create: MagicMock) -> None:
        _patch_dictionaries(mock_countries, mock_sports, mock_seasons)
        mock_create.side_effect = IntegrityError(
            "Cannot add or update a child row: a foreign key "
            "constraint fails",
            1452)
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("Test League", 1, 1, 13, 1)
        self.assertEqual(
            str(ctx.exception),
            "Invalid country, sport or season")

    @patch(_CREATE)
    def test_empty_name_does_not_write(
            self,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("   ", 1, 1)
        self.assertEqual(str(ctx.exception), "League name is required")
        mock_create.assert_not_called()

    @patch(_CREATE)
    def test_name_too_long_does_not_write(
            self,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_league("A" * 46, 1, 1)
        self.assertIn("at most", str(ctx.exception))
        mock_create.assert_not_called()


class TestSetLeagueActive(unittest.TestCase):
    """Toggle active maps the row or raises when missing."""

    @patch(_SET_ACTIVE)
    def test_happy_path_maps_dto(
            self,
            mock_set: MagicMock) -> None:
        inactive = dict(_REPO_LEAGUE_ROW)
        inactive["active"] = 0
        mock_set.return_value = inactive
        updated = service.set_league_active(48, False)
        mock_set.assert_called_once_with(48, False)
        self.assertFalse(updated["active"])
        self.assertEqual(updated["id"], 48)

    @patch(_SET_ACTIVE, return_value=None)
    def test_missing_league_raises_not_found(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminNotFoundError) as ctx:
            service.set_league_active(999, False)
        self.assertEqual(str(ctx.exception), "League not found")
        mock_set.assert_called_once_with(999, False)


class TestDictionaryLists(unittest.TestCase):
    """Dropdown helpers pass repository rows through."""

    @patch(
        _FETCH_COUNTRIES,
        return_value=[{"id": 1, "name": "Polska"}])
    def test_list_countries(
            self,
            mock_fetch: MagicMock) -> None:
        countries = service.list_countries()
        self.assertEqual(countries, [{"id": 1, "name": "Polska"}])
        mock_fetch.assert_called_once_with()

    @patch(
        _FETCH_SPORTS,
        return_value=[{"id": 1, "name": "Piłka nożna"}])
    def test_list_sports(
            self,
            mock_fetch: MagicMock) -> None:
        sports = service.list_sports()
        self.assertEqual(sports, [{"id": 1, "name": "Piłka nożna"}])
        mock_fetch.assert_called_once_with()

    @patch(
        _FETCH_SEASONS,
        return_value=[{"id": 13, "years": "2026/27"}])
    def test_list_seasons(
            self,
            mock_fetch: MagicMock) -> None:
        seasons = service.list_seasons()
        self.assertEqual(seasons, [{"id": 13, "years": "2026/27"}])
        self.assertNotIn("name", seasons[0])
        mock_fetch.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
