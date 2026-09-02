"""Unit tests for season dictionary repository SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.repositories import season_repository


_GET_CONN = "backend.repositories.season_repository.get_db_connection"

_SEASON_ROW = {"id": 13, "years": "2026/27"}


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        rows: list[dict[str, object]] | None = None) -> MagicMock:
    """Return mocked cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows if rows is not None else []
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return cursor


class TestFetchAllSeasons(unittest.TestCase):
    """Season dropdown must list newest years first."""

    @patch(_GET_CONN)
    def test_selects_seasons_ordered_newest_first(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(mock_get_conn, rows=[_SEASON_ROW])
        seasons = season_repository.fetch_all_seasons()
        self.assertEqual(seasons, [_SEASON_ROW])
        query = cursor.execute.call_args.args[0]
        self.assertIn("FROM seasons", query)
        self.assertIn("ORDER BY years DESC, id DESC", query)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(season_repository.fetch_all_seasons(), [])


if __name__ == "__main__":
    unittest.main()
