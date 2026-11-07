"""Unit tests for the football table zones repository."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
from mysql.connector.errors import ProgrammingError
from pandas.errors import DatabaseError as PandasDatabaseError

from backend.repositories import football_table_zones_repository as repo


_GET_CONN = (
    "backend.repositories.football_table_zones_repository"
    ".get_db_connection")
_READ_SQL = (
    "backend.repositories.football_table_zones_repository"
    ".pd.read_sql")
_MISSING_TABLE = (
    "1146 (42S02): Table 'ekstrabet.football_table_zones' "
    "doesn't exist")


def _mock_connection(mock_get_conn: MagicMock) -> None:
    """Wire get_db_connection as a context manager."""
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm


def _two_zone_frame() -> pd.DataFrame:
    """One cup place and one relegation place on a two-team table."""
    return pd.DataFrame([{
        "position_from": 1,
        "position_to": 1,
        "zone_kind": "champions_league",
        "band": "top",
        "stage": "qualification",
        "target_league_id": 42,
        "target_league_name": "Liga Mistrzów",
        "sort_order": 1
    }, {
        "position_from": 2,
        "position_to": 2,
        "zone_kind": "relegation",
        "band": "bot",
        "stage": None,
        "target_league_id": float("nan"),
        "target_league_name": None,
        "sort_order": 2
    }])


class TestFetchTableZones(unittest.TestCase):
    """Mapping, rejection and a missing zones table."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_maps_two_rows_with_labels(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = _two_zone_frame()

        zone_set = repo.fetch_table_zones(1, 13, 2)

        self.assertIsNotNone(zone_set)
        assert zone_set is not None
        self.assertEqual(zone_set.top_slots, 1)
        self.assertEqual(zone_set.bot_slots, 1)
        self.assertEqual(len(zone_set.zones), 2)
        cup, drop = zone_set.zones
        self.assertEqual(cup.zone_kind, "champions_league")
        self.assertEqual(cup.band, "top")
        self.assertEqual(cup.stage, "qualification")
        self.assertEqual(cup.target_league_id, 42)
        self.assertEqual(cup.target_league_name, "Liga Mistrzów")
        self.assertEqual(cup.sort_order, 1)
        self.assertEqual(
            cup.label,
            "Awans – Liga Mistrzów (Kwalifikacje)")
        self.assertEqual(drop.zone_kind, "relegation")
        self.assertIsNone(drop.stage)
        self.assertIsNone(drop.target_league_id)
        self.assertIsNone(drop.target_league_name)
        self.assertEqual(drop.label, "Spadek")
        query = mock_read_sql.call_args.args[0]
        self.assertIn("FROM football_table_zones", query)
        self.assertIn("LEFT JOIN leagues", query)
        self.assertIn(
            "target_league.id = zones.target_league_id",
            query)
        self.assertIn(
            "ORDER BY zones.sort_order, zones.position_from",
            query)
        self.assertEqual(
            mock_read_sql.call_args.kwargs["params"],
            (1, 13))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_empty_frame_returns_zero_slots(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        with self.assertNoLogs(repo.logger, level="WARNING"):
            zone_set = repo.fetch_table_zones(1, 13, 18)

        self.assertIsNotNone(zone_set)
        assert zone_set is not None
        self.assertEqual(zone_set.zones, ())
        self.assertEqual(zone_set.top_slots, 0)
        self.assertEqual(zone_set.bot_slots, 0)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_rejected_frame_returns_none(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        # Dziura na miejscu 2: agregacja odmawia prefiksu.
        mock_read_sql.return_value = pd.DataFrame([{
            "position_from": 1,
            "position_to": 1,
            "zone_kind": "champions_league",
            "band": "top",
            "stage": "qualification",
            "target_league_id": 42,
            "target_league_name": "Liga Mistrzów",
            "sort_order": 1
        }, {
            "position_from": 3,
            "position_to": 3,
            "zone_kind": "europa_league",
            "band": "top",
            "stage": "qualification",
            "target_league_id": 43,
            "target_league_name": "Liga Europy",
            "sort_order": 2
        }])

        with self.assertLogs(repo.logger, level="WARNING") as captured:
            zone_set = repo.fetch_table_zones(8, 13, 3)

        self.assertIsNone(zone_set)
        text = "\n".join(captured.output)
        self.assertIn("league_id=8", text)
        self.assertIn("season_id=13", text)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_missing_table_returns_none(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = PandasDatabaseError(
            f"Execution failed on sql: {_MISSING_TABLE}")

        with self.assertLogs(repo.logger, level="WARNING") as captured:
            zone_set = repo.fetch_table_zones(1, 13, 18)

        self.assertIsNone(zone_set)
        text = "\n".join(captured.output)
        self.assertIn("league_id=1", text)
        self.assertIn("season_id=13", text)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_driver_missing_table_returns_none(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = ProgrammingError(
            msg="Table 'ekstrabet.football_table_zones' doesn't exist",
            errno=1146,
            sqlstate="42S02")

        with self.assertLogs(repo.logger, level="WARNING"):
            self.assertIsNone(repo.fetch_table_zones(1, 13, 18))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_other_database_error_propagates(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = PandasDatabaseError(
            "Execution failed on sql: deadlock")

        with self.assertNoLogs(repo.logger, level="WARNING"):
            with self.assertRaises(PandasDatabaseError):
                repo.fetch_table_zones(1, 13, 18)


if __name__ == "__main__":
    unittest.main()
