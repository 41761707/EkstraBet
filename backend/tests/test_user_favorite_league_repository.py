"""Unit tests for user favorite league repository SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError

from backend.repositories import user_favorite_league_repository as repo


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        rows: list[dict[str, object]] | None = None,
        rowcount: int = 1) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows if rows is not None else []
    cursor.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


_GET_CONN = (
    "backend.repositories.user_favorite_league_repository"
    ".get_db_connection")


class TestFetchFavoriteLeagueIds(unittest.TestCase):
    """SELECT must return sorted IDs and always close the cursor."""

    @patch(_GET_CONN)
    def test_query_filters_user_and_orders_by_league_id(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            rows=[{"league_id": 1}, {"league_id": 4}])
        ids = repo.fetch_favorite_league_ids(7)
        self.assertEqual(ids, [1, 4])
        query, params = cursor.execute.call_args.args
        self.assertIn("SELECT league_id", query)
        self.assertIn("FROM user_favorite_leagues", query)
        self.assertIn("WHERE user_id = %s", query)
        self.assertIn("ORDER BY league_id", query)
        self.assertEqual(params, (7,))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(repo.fetch_favorite_league_ids(7), [])

    @patch(_GET_CONN)
    def test_db_error_closes_cursor_and_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("connection lost")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.fetch_favorite_league_ids(7)
        self.assertIs(ctx.exception, error)
        cursor.close.assert_called_once()


class TestAddFavoriteLeague(unittest.TestCase):
    """INSERT must be parameterized, idempotent and committed."""

    @patch(_GET_CONN)
    def test_inserts_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        repo.add_favorite_league(7, 4)
        query, params = cursor.execute.call_args.args
        self.assertIn("INSERT INTO user_favorite_leagues", query)
        self.assertIn("VALUES (%s, %s)", query)
        self.assertIn("ON DUPLICATE KEY UPDATE", query)
        self.assertEqual(params, (7, 4))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_db_error_does_not_commit_and_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("deadlock")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.add_favorite_league(7, 4)
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


class TestRemoveFavoriteLeague(unittest.TestCase):
    """DELETE must be parameterized, idempotent and committed."""

    @patch(_GET_CONN)
    def test_deletes_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=1)
        repo.remove_favorite_league(7, 4)
        query, params = cursor.execute.call_args.args
        self.assertIn("DELETE FROM user_favorite_leagues", query)
        self.assertIn("WHERE user_id = %s AND league_id = %s", query)
        self.assertEqual(params, (7, 4))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_missing_row_still_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=0)
        repo.remove_favorite_league(7, 4)
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_db_error_does_not_commit_and_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("lock wait timeout")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.remove_favorite_league(7, 4)
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
