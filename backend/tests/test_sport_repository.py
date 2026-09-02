"""Unit tests for sport dictionary repository SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.repositories import sport_repository


_GET_CONN = "backend.repositories.sport_repository.get_db_connection"

_SPORT_ROW = {"id": 1, "name": "Piłka nożna"}


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


class TestFetchAllSports(unittest.TestCase):
    """Sport dropdown must list id and name."""

    @patch(_GET_CONN)
    def test_selects_sports_ordered_by_name(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(mock_get_conn, rows=[_SPORT_ROW])
        sports = sport_repository.fetch_all_sports()
        self.assertEqual(sports, [_SPORT_ROW])
        query = cursor.execute.call_args.args[0]
        self.assertIn("FROM sports", query)
        self.assertIn("ORDER BY name, id", query)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(sport_repository.fetch_all_sports(), [])


if __name__ == "__main__":
    unittest.main()
