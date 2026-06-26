"""Tests for backend.database."""

from __future__ import annotations
import os
import unittest
from unittest.mock import MagicMock, patch
from backend.config import get_settings
from backend.database import (
    ConnectionManager,
    DatabaseConnectionError,
    db_connect,
    test_connection)


class TestConnectionManager(unittest.TestCase):
    """Unit tests for the database connection manager."""
    required_env = {
        "DB_PASSWORD": "test-db-password",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only"
    }
    def tearDown(self) -> None:
        get_settings.cache_clear()

    @patch("backend.database.mysql.connector.connect")
    def test_connect_uses_config_from_settings(
        self,
        mock_connect: MagicMock) -> None:
        mock_connect.return_value = MagicMock(is_connected=lambda: True)
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            conn = ConnectionManager.connect()
            mock_connect.assert_called_once()
            call_kwargs = mock_connect.call_args.kwargs
            self.assertEqual(call_kwargs["host"], "localhost")
            self.assertEqual(call_kwargs["password"], "test-db-password")
            self.assertTrue(conn.is_connected())

    @patch("backend.database.mysql.connector.connect")
    def test_db_connect_is_alias_for_connection_manager(
        self,
        mock_connect: MagicMock) -> None:
        mock_connect.return_value = MagicMock(is_connected=lambda: True)
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            db_connect()
            mock_connect.assert_called_once()

    @patch(
        "backend.database.ConnectionManager.connect",
        side_effect=DatabaseConnectionError("Failed to connect"))
    def test_test_connection_returns_false_on_failure(
        self,
        _mock_connect: MagicMock) -> None:
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            self.assertFalse(test_connection())

    @patch("backend.database.mysql.connector.connect")
    def test_session_closes_connection(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            with ConnectionManager.session():
                pass
            mock_conn.close.assert_called_once()


class TestDatabaseIntegration(unittest.TestCase):
    """Optional integration test against a real database."""

    required_env = {
        "DB_PASSWORD": "test-db-password",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
    }
    def tearDown(self) -> None:
        get_settings.cache_clear()
        
    def test_live_connection_when_db_password_is_configured(self) -> None:
        db_password = os.getenv("DB_PASSWORD")
        if not db_password:
            self.skipTest("DB_PASSWORD is not configured")
        get_settings.cache_clear()
        self.assertTrue(test_connection())


if __name__ == "__main__":
    unittest.main()
