"""Tests for backend.database."""

from __future__ import annotations
import os
import unittest
from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from backend.config import get_settings
from backend.database import (
    ConnectionManager,
    DatabaseConnectionError,
    db_connect,
    test_connection)
from backend.timezone import WARSAW_TIME_ZONE


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
            self.assertNotIn("time_zone", call_kwargs)
            self.assertTrue(conn.is_connected())

    @patch("backend.database.mysql.connector.connect")
    def test_connect_sets_warsaw_session_time_zone(
        self,
        mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            ConnectionManager.connect()
        sql, params = mock_cursor.execute.call_args.args
        self.assertIn("time_zone", sql)
        self.assertRegex(params[0], r"^[+-]\d{2}:\d{2}$")
        mock_cursor.close.assert_called_once()

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

    def test_session_now_matches_warsaw_game_date(self) -> None:
        db_password = os.getenv("DB_PASSWORD")
        if not db_password:
            self.skipTest("DB_PASSWORD is not configured")
        get_settings.cache_clear()
        warsaw = ZoneInfo(WARSAW_TIME_ZONE)
        warsaw_offset = datetime.now(warsaw).utcoffset()
        if warsaw_offset is None:
            self.fail("Europe/Warsaw UTC offset is unavailable")
        expected_offset_minutes = int(warsaw_offset.total_seconds() // 60)
        warsaw_now = datetime.now(warsaw).replace(tzinfo=None)
        future_kickoff = warsaw_now + timedelta(hours=1)
        past_kickoff = warsaw_now - timedelta(hours=1)
        with ConnectionManager.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), NOW())")
                offset_row = cursor.fetchone()
                cursor.execute(
                    "SELECT NOW() < %s, NOW() >= %s",
                    (future_kickoff, past_kickoff))
                compare_row = cursor.fetchone()
            finally:
                cursor.close()
        self.assertIsNotNone(offset_row)
        self.assertIsNotNone(compare_row)
        self.assertEqual(offset_row[0], expected_offset_minutes)
        self.assertTrue(compare_row[0])
        self.assertTrue(compare_row[1])


if __name__ == "__main__":
    unittest.main()
