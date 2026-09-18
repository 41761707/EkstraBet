"""Unit tests for football table special slots repository."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories import football_table_special_slots_repository as repo


_GET_CONN = (
    "backend.repositories.football_table_special_slots_repository"
    ".get_db_connection")
_READ_SQL = (
    "backend.repositories.football_table_special_slots_repository"
    ".pd.read_sql")


def _mock_connection(mock_get_conn: MagicMock) -> None:
    """Wire get_db_connection as a context manager."""
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm


class TestFetchSpecialSlots(unittest.TestCase):
    """Mapping and SQL contract for league slot thresholds."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_maps_ekstraklasa_row(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "league_id": 1,
            "top_slots": 4,
            "bot_slots": 3
        }])

        record = repo.fetch_special_slots(1)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.league_id, 1)
        self.assertEqual(record.top_slots, 4)
        self.assertEqual(record.bot_slots, 3)
        query = mock_read_sql.call_args.args[0]
        self.assertIn("SELECT league_id, top_slots, bot_slots", query)
        self.assertIn("FROM football_table_special_slots", query)
        self.assertIn("WHERE league_id = %s", query)
        self.assertIn("LIMIT 1", query)
        self.assertEqual(mock_read_sql.call_args.kwargs["params"], (1,))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_empty_frame_returns_none(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        self.assertIsNone(repo.fetch_special_slots(1))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_negative_slots_return_none(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "league_id": 1,
            "top_slots": -1,
            "bot_slots": 3
        }])

        self.assertIsNone(repo.fetch_special_slots(1))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_zero_slots_are_valid(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "league_id": 2,
            "top_slots": 0,
            "bot_slots": 0
        }])

        record = repo.fetch_special_slots(2)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.top_slots, 0)
        self.assertEqual(record.bot_slots, 0)


if __name__ == "__main__":
    unittest.main()
