"""Unit tests for the football point adjustments repository."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
from mysql.connector.errors import ProgrammingError
from pandas.errors import DatabaseError as PandasDatabaseError

from backend.repositories import (
    football_point_adjustments_repository as repo)


_GET_CONN = (
    "backend.repositories.football_point_adjustments_repository"
    ".get_db_connection")
_READ_SQL = (
    "backend.repositories.football_point_adjustments_repository"
    ".pd.read_sql")
_MISSING_TABLE = (
    "1146 (42S02): Table 'ekstrabet.football_point_adjustments' "
    "doesn't exist")


def _mock_connection(mock_get_conn: MagicMock) -> None:
    """Wire get_db_connection as a context manager."""
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm


def _southampton_frame() -> pd.DataFrame:
    """Two Southampton rows, higher id first, so order is by id."""
    return pd.DataFrame([{
        "id": 20,
        "team_id": 73,
        "points_delta": 6,
        "reason": "Odwołanie"
    }, {
        "id": 11,
        "team_id": 73,
        "points_delta": -10,
        "reason": "Decyzja związku"
    }])


class TestFetchPointAdjustments(unittest.TestCase):
    """Summed deltas, joined reasons and a missing adjustments table."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_sums_two_rows_in_id_order(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = _southampton_frame()

        adjustments = repo.fetch_point_adjustments(8, 13)

        self.assertEqual(list(adjustments), [73])
        summed = adjustments[73]
        self.assertIsInstance(summed, repo.PointAdjustment)
        self.assertEqual(summed.team_id, 73)
        self.assertEqual(summed.points_delta, -4)
        self.assertEqual(
            summed.reason,
            "Decyzja związku; Odwołanie")
        query = mock_read_sql.call_args.args[0]
        self.assertIn("FROM football_point_adjustments", query)
        self.assertIn("ORDER BY adjustments.id", query)
        self.assertEqual(
            mock_read_sql.call_args.kwargs["params"],
            (8, 13))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_empty_frame_returns_empty_dict(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        with self.assertNoLogs(repo.logger, level="WARNING"):
            adjustments = repo.fetch_point_adjustments(8, 13)

        self.assertEqual(adjustments, {})

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_missing_table_returns_empty_dict(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = PandasDatabaseError(
            f"Execution failed on sql: {_MISSING_TABLE}")

        with self.assertLogs(repo.logger, level="WARNING") as captured:
            adjustments = repo.fetch_point_adjustments(8, 13)

        self.assertEqual(adjustments, {})
        text = "\n".join(captured.output)
        self.assertIn("league_id=8", text)
        self.assertIn("season_id=13", text)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_driver_missing_table_returns_empty_dict(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = ProgrammingError(
            msg=(
                "Table 'ekstrabet.football_point_adjustments' "
                "doesn't exist"),
            errno=1146,
            sqlstate="42S02")

        with self.assertLogs(repo.logger, level="WARNING"):
            self.assertEqual(repo.fetch_point_adjustments(8, 13), {})

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
                repo.fetch_point_adjustments(8, 13)


if __name__ == "__main__":
    unittest.main()
