"""Unit tests for user preferences repository SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError

from backend.repositories import user_preferences_repository as repo

_FULL_ROW = {"theme": "dark", "team_name_display": "full"}
_GET_CONN = (
    "backend.repositories.user_preferences_repository"
    ".get_db_connection")


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


class TestFetchPreferences(unittest.TestCase):
    """SELECT must filter by user_id and always close the cursor."""

    @patch(_GET_CONN)
    def test_query_filters_user_and_returns_full_document(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn, row=_FULL_ROW)
        document = repo.fetch_preferences(7)
        self.assertEqual(document, {
            "theme": "dark",
            "team_name_display": "full"
        })
        query, params = cursor.execute.call_args.args
        self.assertIn("SELECT theme, team_name_display", query)
        self.assertIn("FROM user_preferences", query)
        self.assertIn("WHERE user_id = %s", query)
        self.assertEqual(params, (7,))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_missing_row_returns_none(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row=None)
        self.assertIsNone(repo.fetch_preferences(7))

    @patch(_GET_CONN)
    def test_db_error_closes_cursor_and_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("connection lost")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.fetch_preferences(7)
        self.assertIs(ctx.exception, error)
        cursor.close.assert_called_once()


class TestUpsertPreferences(unittest.TestCase):
    """INSERT patches provided columns and preserves omitted ones."""

    def _assert_upsert_sql(self, query: str) -> None:
        self.assertIn("INSERT INTO user_preferences", query)
        self.assertIn("theme, team_name_display", query)
        self.assertIn("COALESCE(%s, 'system')", query)
        self.assertIn("COALESCE(%s, 'full')", query)
        self.assertIn("ON DUPLICATE KEY UPDATE", query)
        self.assertIn("theme = COALESCE(%s, theme)", query)
        self.assertIn(
            "team_name_display = COALESCE(%s, team_name_display)",
            query)

    @patch(_GET_CONN)
    def test_upserts_theme_only_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, row=_FULL_ROW)
        document = repo.upsert_preferences(7, theme="dark")
        self.assertEqual(document, {
            "theme": "dark",
            "team_name_display": "full"
        })
        insert_query, insert_params = cursor.execute.call_args_list[0].args
        self._assert_upsert_sql(insert_query)
        self.assertEqual(insert_params, (7, "dark", None, "dark", None))
        select_query, select_params = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT theme, team_name_display", select_query)
        self.assertEqual(select_params, (7,))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_upserts_team_name_display_only(
            self,
            mock_get_conn: MagicMock) -> None:
        stored = {"theme": "light", "team_name_display": "shortcut"}
        _conn, cursor = _mock_connection(mock_get_conn, row=stored)
        document = repo.upsert_preferences(
            7,
            team_name_display="shortcut")
        self.assertEqual(document, stored)
        _query, insert_params = cursor.execute.call_args_list[0].args
        self.assertEqual(
            insert_params,
            (7, None, "shortcut", None, "shortcut"))

    @patch(_GET_CONN)
    def test_upserts_both_fields(
            self,
            mock_get_conn: MagicMock) -> None:
        stored = {"theme": "light", "team_name_display": "shortcut"}
        _conn, cursor = _mock_connection(mock_get_conn, row=stored)
        document = repo.upsert_preferences(
            7,
            theme="light",
            team_name_display="shortcut")
        self.assertEqual(document, stored)
        _query, insert_params = cursor.execute.call_args_list[0].args
        self.assertEqual(
            insert_params,
            (7, "light", "shortcut", "light", "shortcut"))

    @patch(_GET_CONN)
    def test_db_error_does_not_commit_and_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("deadlock")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.upsert_preferences(7, theme="light")
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
