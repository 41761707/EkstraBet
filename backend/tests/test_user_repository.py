"""Unit tests for user repository first-login queries."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.repositories import user_repository


_ADMIN_USER_ROW = {
    "id": 8,
    "uuid": "11111111-1111-1111-1111-111111111111",
    "username": "alice",
    "display_name": "Alice",
    "is_active": 1,
    "is_admin": 0,
    "first_login": 1,
    "created_at": None,
    "updated_at": None
}

_GET_CONN = "backend.repositories.user_repository.get_db_connection"


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
        rowcount: int = 1) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.fetchall.return_value = rows if rows is not None else []
    cursor.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


class TestFetchUserColumns(unittest.TestCase):
    """SELECT must include first_login and is_admin for auth flags."""

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

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_fetch_user_by_id_selects_is_admin(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"id": 1, "is_admin": 1})
        row = user_repository.fetch_user_by_id(1)
        self.assertIsNotNone(row)
        self.assertEqual(row["is_admin"], 1)
        query = cursor.execute.call_args.args[0]
        self.assertIn("is_admin", query)


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
    """UPDATE must clear first_login and persist username, hash and nickname."""

    @patch("backend.repositories.user_repository.get_db_connection")
    def test_happy_path_updates_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=1)
        user_repository.update_user_credentials_after_first_login(
            7, "new_name", "hashed", "Nick")
        query, params = cursor.execute.call_args.args
        self.assertIn("UPDATE users", query)
        self.assertIn("username = %s", query)
        self.assertIn("password_hash = %s", query)
        self.assertIn("display_name = %s", query)
        self.assertIn("first_login = 0", query)
        self.assertIn("WHERE id = %s AND first_login = 1", query)
        self.assertEqual(params, ("new_name", "hashed", "Nick", 7))
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
                7, "new_name", "hashed", "Nick")
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
                7, "alice", "hashed", "Nick")
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        # IntegrityError przed commit — rollback przy close połączenia
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()


class TestFetchAllUsers(unittest.TestCase):
    """Admin list must omit password_hash and order by username."""

    @patch(_GET_CONN)
    def test_select_omits_password_hash_and_returns_rows(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, rows=[_ADMIN_USER_ROW])
        users = user_repository.fetch_all_users()
        self.assertEqual(users, [_ADMIN_USER_ROW])
        query = cursor.execute.call_args.args[0]
        self.assertIn("FROM users", query)
        self.assertIn("ORDER BY username, id", query)
        self.assertNotIn("password_hash", query)
        self.assertNotIn("password_hash", users[0])
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(user_repository.fetch_all_users(), [])


class TestCreateUser(unittest.TestCase):
    """INSERT must persist flags, commit and hide the password hash."""

    @patch(_GET_CONN)
    def test_inserts_commits_and_returns_row_without_hash(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=_ADMIN_USER_ROW)
        created = user_repository.create_user(
            "11111111-1111-1111-1111-111111111111",
            "alice",
            "hashed-secret",
            "Alice",
            is_admin=False)
        self.assertEqual(created, _ADMIN_USER_ROW)
        self.assertNotIn("password_hash", created)
        insert_query, insert_params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO users", insert_query)
        self.assertIn("password_hash", insert_query)
        self.assertEqual(
            insert_params,
            (
                "11111111-1111-1111-1111-111111111111",
                "alice",
                "hashed-secret",
                "Alice",
                0,
                1,
                1))
        select_query = cursor.execute.call_args_list[1].args[0]
        self.assertNotIn("password_hash", select_query)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_duplicate_username_integrity_error_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = IntegrityError(
            "Duplicate entry 'alice' for key 'username_UNIQUE'",
            1062)
        cursor.execute.side_effect = error
        with self.assertRaises(IntegrityError) as ctx:
            user_repository.create_user(
                "11111111-1111-1111-1111-111111111111",
                "alice",
                "hashed-secret",
                "Alice")
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


class TestSetUserActive(unittest.TestCase):
    """Toggle is_active must commit and skip missing users."""

    @patch(_GET_CONN)
    def test_updates_commits_and_returns_row_without_hash(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=_ADMIN_USER_ROW, rowcount=1)
        updated = user_repository.set_user_active(
            "11111111-1111-1111-1111-111111111111", False)
        self.assertEqual(updated, _ADMIN_USER_ROW)
        self.assertNotIn("password_hash", updated)
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE users", query)
        self.assertIn("is_active = %s", query)
        self.assertIn("WHERE uuid = %s", query)
        self.assertEqual(
            params, (0, "11111111-1111-1111-1111-111111111111"))
        select_query = cursor.execute.call_args_list[1].args[0]
        self.assertNotIn("password_hash", select_query)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_noop_update_on_existing_uuid_still_returns_row(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=_ADMIN_USER_ROW, rowcount=0)
        updated = user_repository.set_user_active(
            "11111111-1111-1111-1111-111111111111", True)
        self.assertEqual(updated, _ADMIN_USER_ROW)
        self.assertNotIn("password_hash", updated)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_missing_user_returns_none_after_select(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=None, rowcount=0)
        result = user_repository.set_user_active(
            "missing-uuid", False)
        self.assertIsNone(result)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)


class TestSetUserAdmin(unittest.TestCase):
    """Toggle is_admin must commit and skip missing users."""

    @patch(_GET_CONN)
    def test_updates_commits_and_returns_row_without_hash(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=_ADMIN_USER_ROW, rowcount=1)
        updated = user_repository.set_user_admin(
            "11111111-1111-1111-1111-111111111111", True)
        self.assertEqual(updated, _ADMIN_USER_ROW)
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE users", query)
        self.assertIn("is_admin = %s", query)
        self.assertEqual(
            params, (1, "11111111-1111-1111-1111-111111111111"))
        conn.commit.assert_called_once()
        self.assertEqual(cursor.close.call_count, 2)

    @patch(_GET_CONN)
    def test_missing_user_returns_none_after_select(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=None, rowcount=0)
        result = user_repository.set_user_admin("missing-uuid", True)
        self.assertIsNone(result)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        self.assertEqual(cursor.close.call_count, 2)


if __name__ == "__main__":
    unittest.main()
