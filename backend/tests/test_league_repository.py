"""Unit tests for admin league repository SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.repositories import league_repository


_GET_CONN = "backend.repositories.league_repository.get_db_connection"

_ADMIN_LEAGUE_ROW = {
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
    "has_player_stats": 0
}


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
        rowcount: int = 1,
        lastrowid: int = 48) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.fetchall.return_value = rows if rows is not None else []
    cursor.rowcount = rowcount
    cursor.lastrowid = lastrowid
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


class TestFetchAllLeagues(unittest.TestCase):
    """Admin list must include inactive leagues and joined labels."""

    @patch(_GET_CONN)
    def test_selects_all_leagues_without_active_filter(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, rows=[_ADMIN_LEAGUE_ROW])
        leagues = league_repository.fetch_all_leagues()
        self.assertEqual(leagues, [_ADMIN_LEAGUE_ROW])
        query = cursor.execute.call_args.args[0]
        self.assertIn("FROM leagues l", query)
        self.assertIn("LEFT JOIN countries c", query)
        self.assertIn("LEFT JOIN sports s", query)
        self.assertIn("ORDER BY l.country, l.name", query)
        self.assertNotIn("l.active =", query)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(league_repository.fetch_all_leagues(), [])


class TestCreateLeague(unittest.TestCase):
    """INSERT must commit and surface foreign-key violations."""

    @patch(_GET_CONN)
    def test_inserts_commits_and_returns_joined_row(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            rows=[_ADMIN_LEAGUE_ROW],
            lastrowid=48)
        created = league_repository.create_league(
            "Test League", 1, 1, 13, 1, False, True)
        self.assertEqual(created, _ADMIN_LEAGUE_ROW)
        insert_query, insert_params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO leagues", insert_query)
        self.assertEqual(insert_params, ("Test League", 1, 1, 13, 1, 0, 1))
        select_query, select_params = cursor.execute.call_args_list[1].args
        self.assertIn("FROM leagues l", select_query)
        self.assertIn("WHERE l.id = %s", select_query)
        self.assertEqual(select_params, (48,))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_inserts_null_season_and_tier(
            self,
            mock_get_conn: MagicMock) -> None:
        nullable_row = dict(_ADMIN_LEAGUE_ROW)
        nullable_row["current_season_id"] = None
        nullable_row["tier"] = None
        _conn, cursor = _mock_connection(
            mock_get_conn,
            rows=[nullable_row],
            lastrowid=48)
        created = league_repository.create_league("Test League", 1, 1)
        self.assertEqual(created, nullable_row)
        _insert_query, insert_params = cursor.execute.call_args_list[0].args
        self.assertEqual(
            insert_params, ("Test League", 1, 1, None, None, 0, 1))

    @patch(_GET_CONN)
    def test_invalid_foreign_key_integrity_error_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = IntegrityError(
            "Cannot add or update a child row: a foreign key "
            "constraint fails",
            1452)
        cursor.execute.side_effect = error
        with self.assertRaises(IntegrityError) as ctx:
            league_repository.create_league(
                "Test League", 999, 1, 13, 1)
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


class TestSetLeagueActive(unittest.TestCase):
    """Toggle active must commit and skip missing leagues."""

    @patch(_GET_CONN)
    def test_updates_commits_and_returns_row(
            self,
            mock_get_conn: MagicMock) -> None:
        inactive = dict(_ADMIN_LEAGUE_ROW)
        inactive["active"] = 0
        conn, cursor = _mock_connection(
            mock_get_conn, rows=[inactive], rowcount=1)
        updated = league_repository.set_league_active(48, False)
        self.assertEqual(updated, inactive)
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE leagues", query)
        self.assertIn("SET active = %s", query)
        self.assertIn("WHERE id = %s", query)
        self.assertEqual(params, (0, 48))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_noop_update_on_existing_league_still_returns_row(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, rows=[_ADMIN_LEAGUE_ROW], rowcount=0)
        updated = league_repository.set_league_active(48, True)
        self.assertEqual(updated, _ADMIN_LEAGUE_ROW)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_missing_league_returns_none_after_select(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, rows=[], rowcount=0)
        result = league_repository.set_league_active(999, False)
        self.assertIsNone(result)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)


if __name__ == "__main__":
    unittest.main()
