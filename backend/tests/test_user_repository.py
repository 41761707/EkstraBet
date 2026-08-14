"""Unit tests for user repository first-login queries."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.repositories import user_repository


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        rowcount: int = 1) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


class TestFetchUserColumns(unittest.TestCase):
    """SELECT must include first_login for auth to see the flag."""

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_fetch_user_by_id_selects_first_login(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"id": 1, "first_login": 1})
        row = user_repository.fetch_user_by_id(1)
        self.assertIsNotNone(row)
        self.assertEqual(row["first_login"], 1)
        query = cursor.execute.call_args.args[0]
        self.assertIn("first_login", query)
        self.assertIn("FROM users", query)


class TestIsUsernameTaken(unittest.TestCase):
    """Username uniqueness must ignore the current user."""

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_returns_true_when_another_user_has_username(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row={"1": 1})
        taken = user_repository.is_username_taken("alice", exclude_user_id=4)
        self.assertTrue(taken)

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_returns_false_when_username_free_for_others(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row=None)
        taken = user_repository.is_username_taken("alice", exclude_user_id=4)
        self.assertFalse(taken)

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_query_excludes_current_user_id(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn, row=None)
        user_repository.is_username_taken("alice", exclude_user_id=4)
        query, params = cursor.execute.call_args.args
        self.assertIn("id <> %s", query)
        self.assertEqual(params, ("alice", 4))


class TestUpdateUserCredentialsAfterFirstLogin(unittest.TestCase):
    """UPDATE must clear first_login and persist username plus hash."""

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_happy_path_updates_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=1)
        user_repository.update_user_credentials_after_first_login(
            7, "new_name", "hashed")
        query, params = cursor.execute.call_args.args
        self.assertIn("UPDATE users", query)
        self.assertIn("username = %s", query)
        self.assertIn("password_hash = %s", query)
        self.assertIn("first_login = 0", query)
        self.assertIn("WHERE id = %s AND first_login = 1", query)
        self.assertEqual(params, ("new_name", "hashed", 7))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_rowcount_zero_raises_and_rolls_back(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=0)
        with self.assertRaises(ValueError) as ctx:
            user_repository.update_user_credentials_after_first_login(
                7, "new_name", "hashed")
        self.assertIn("already completed", str(ctx.exception))
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        cursor.close.assert_called_once()

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_unique_username_integrity_error_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=1)
        error = IntegrityError(
            "Duplicate entry 'alice' for key 'username_UNIQUE'",
            1062)
        cursor.execute.side_effect = error
        with self.assertRaises(IntegrityError) as ctx:
            user_repository.update_user_credentials_after_first_login(
                7, "alice", "hashed")
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        # IntegrityError przed commit — rollback przy close połączenia
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
