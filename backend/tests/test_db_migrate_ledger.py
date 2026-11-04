"""Tests for the migration connection and the advisory lock."""

from __future__ import annotations

import os
import unittest
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.db_migrate.connection import open_migration_connection
from backend.db_migrate.errors import MigrationError
from backend.db_migrate.ledger import acquire_lock


_APP_CONFIG = {
    "host": "localhost",
    "user": "ekstrabet_api",
    "password": "api-secret",
    "database": "ekstrabet",
    "port": 3306,
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci"
}


class _LockCursor:
    """Returns a single GET_LOCK result."""

    def __init__(self, result: object) -> None:
        self.statements: list[str] = []
        self.params: list[Any] = []
        self._result = result

    def execute(
            self,
            statement: str,
            params: tuple[Any, ...] | None = None) -> None:
        self.statements.append(statement)
        self.params.append(params)

    def fetchone(self) -> tuple[object, ...]:
        return (self._result,)


class TestOpenMigrationConnection(unittest.TestCase):
    """DDL account overrides the connection, not application settings."""

    @patch("backend.db_migrate.connection.mysql.connector.connect")
    @patch(
        "backend.db_migrate.connection.get_database_config",
        return_value=_APP_CONFIG)
    def test_migrate_user_overrides_connect_only(
            self,
            _mock_config: MagicMock,
            mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        env = {
            "DB_MIGRATE_USER": "ekstrabet_migrate",
            "DB_MIGRATE_PASSWORD": "migrate-secret"
        }
        with patch.dict(os.environ, env, clear=False):
            open_migration_connection()
        kwargs = mock_connect.call_args.kwargs
        self.assertEqual(kwargs["user"], "ekstrabet_migrate")
        self.assertEqual(kwargs["password"], "migrate-secret")
        self.assertEqual(kwargs["host"], "localhost")
        self.assertEqual(kwargs["database"], "ekstrabet")
        self.assertEqual(_APP_CONFIG["user"], "ekstrabet_api")
        self.assertEqual(_APP_CONFIG["password"], "api-secret")
        session_sql = mock_conn.cursor.return_value.execute.call_args.args[0]
        self.assertIn("time_zone", session_sql)

    @patch("backend.db_migrate.connection.mysql.connector.connect")
    @patch(
        "backend.db_migrate.connection.get_database_config",
        return_value=_APP_CONFIG)
    def test_empty_migrate_password_skips_connect(
            self,
            _mock_config: MagicMock,
            mock_connect: MagicMock) -> None:
        env = {
            "DB_MIGRATE_USER": "ekstrabet_migrate",
            "DB_MIGRATE_PASSWORD": ""
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(MigrationError) as caught:
                open_migration_connection()
        self.assertEqual(
            str(caught.exception),
            "DB_MIGRATE_PASSWORD is required when DB_MIGRATE_USER is set")
        self.assertNotIn("api-secret", str(caught.exception))
        mock_connect.assert_not_called()


class TestAcquireLock(unittest.TestCase):
    """GET_LOCK must return 1."""

    def test_zero_result_raises(self) -> None:
        cursor = _LockCursor(0)
        with self.assertRaises(MigrationError) as caught:
            acquire_lock(cursor)
        self.assertEqual(
            str(caught.exception),
            "Could not acquire migration lock")
        self.assertIn("GET_LOCK", cursor.statements[0])
        self.assertEqual(cursor.params[0], ("ekstrabet_db_migrate", 30))


if __name__ == "__main__":
    unittest.main()
