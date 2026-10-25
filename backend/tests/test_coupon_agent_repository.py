"""SELECT contract and settleable filter for coupon-agent candidates."""

from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.repositories import coupon_agent_repository as repository
from backend.repositories.coupon_agent_repository import (
    CANDIDATE_COLUMNS,
    MAX_CANDIDATES,
    fetch_candidates)


_NOW = datetime(2026, 10, 25, 12, 0)
_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "TRUNCATE")


def _raw_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": 10,
        "event_id": 1,
        "model_id": 4,
        "bookmaker_id": 2,
        "odds": 2.0,
        "probability_pct": 55.0,
        "kickoff": datetime(2026, 10, 26, 18, 0),
        "league_id": 7,
        "league_tier": 1,
        "event_name": "Zwycięstwo gospodarza",
        "event_family": "REZULTAT"}
    row.update(overrides)
    return row


def _sql(query: str) -> str:
    return " ".join(query.split())


class TestFetchCandidatesQuery(unittest.TestCase):
    """The read is one future-window SELECT with the best price."""

    def _capture(
            self,
            horizon_days: int = 7) -> tuple[str, tuple[object, ...]]:
        captured: dict[str, object] = {}

        def _read_sql(
                query: str,
                params: tuple[object, ...]) -> pd.DataFrame:
            captured["query"] = query
            captured["params"] = params
            return pd.DataFrame(columns=list(repository._SQL_COLUMNS))

        with patch.object(repository, "_read_sql", side_effect=_read_sql):
            frame = fetch_candidates(_NOW, horizon_days=horizon_days)
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), list(CANDIDATE_COLUMNS))
        return str(captured["query"]), tuple(captured["params"])

    def test_window_is_half_open_from_now(self) -> None:
        query, params = self._capture(horizon_days=3)
        text = _sql(query)
        self.assertIn("mk.game_date >= %s", text)
        self.assertIn("mk.game_date < %s", text)
        self.assertNotIn("CAST(mk.game_date AS DATE)", text)
        self.assertEqual(
            params,
            (_NOW, _NOW + timedelta(days=3), repository.FOOTBALL_SPORT_ID))

    def test_joins_published_prediction_to_best_odds(self) -> None:
        query, _params = self._capture()
        text = _sql(query)
        self.assertIn("FROM final_predictions fp", text)
        self.assertIn("INNER JOIN predictions p", text)
        self.assertIn("ON p.id = fp.predictions_id", text)
        self.assertIn("ON bo.match_id = p.match_id", text)
        self.assertIn("AND bo.event_id = p.event_id", text)
        self.assertIn("WHERE o.odds > 1", text)
        self.assertIn("INNER JOIN events e", text)
        window = text.split("ROW_NUMBER() OVER (", 1)[1]
        window = window.split(") AS rn", 1)[0]
        self.assertIn("PARTITION BY o.match_id, o.event", window)
        self.assertIn("ORDER BY o.odds DESC, o.id ASC", window)
        self.assertIn("WHERE ranked.rn = 1", text)

    def test_window_is_football_only(self) -> None:
        query, params = self._capture()
        text = _sql(query)
        self.assertIn("mk.sport_id = %s", text)
        self.assertNotIn("sport_id = 1", text)
        self.assertNotIn("sport_id = 2", text)
        self.assertEqual(params[-1], repository.FOOTBALL_SPORT_ID)
        self.assertEqual(repository.FOOTBALL_SPORT_ID, 1)

    def test_query_is_select_only(self) -> None:
        query, _params = self._capture()
        text = _sql(query).upper()
        source = inspect.getsource(repository).upper()
        self.assertIn("WITH WINDOW_MATCHES", text)
        self.assertNotIn(";", text)
        for word in _WRITE_WORDS:
            self.assertNotIn(word, text)
            self.assertNotIn(word, source)

    def test_read_uses_the_shared_connection(self) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        with patch(
                "backend.repositories.coupon_agent_repository."
                "get_db_connection",
                return_value=mock_cm), patch(
                "backend.repositories.coupon_agent_repository.pd.read_sql",
                return_value=pd.DataFrame(
                    columns=list(repository._SQL_COLUMNS))) as mock_read:
            fetch_candidates(_NOW)
        mock_read.assert_called_once()
        self.assertIs(mock_read.call_args.args[1], mock_conn)
        self.assertEqual(
            mock_read.call_args.kwargs["params"],
            (_NOW, _NOW + timedelta(days=7), repository.FOOTBALL_SPORT_ID))


class TestFetchCandidatesRows(unittest.TestCase):
    """Python keeps only settleable prices inside (0, 1)."""

    def _fetch(self, rows: list[dict[str, object]]) -> pd.DataFrame:
        frame = pd.DataFrame(rows)

        def _read_sql(
                _query: str,
                _params: tuple[object, ...]) -> pd.DataFrame:
            return frame

        with patch.object(repository, "_read_sql", side_effect=_read_sql):
            return fetch_candidates(_NOW)

    def test_converts_probability_and_edge_without_devig(self) -> None:
        frame = self._fetch([_raw_row()])
        self.assertEqual(len(frame), 1)
        row = frame.iloc[0]
        self.assertEqual(int(row["match_id"]), 10)
        self.assertEqual(int(row["event_id"]), 1)
        self.assertEqual(int(row["model_id"]), 4)
        self.assertEqual(int(row["bookmaker_id"]), 2)
        self.assertAlmostEqual(float(row["odds"]), 2.0)
        self.assertAlmostEqual(float(row["model_probability"]), 0.55)
        self.assertAlmostEqual(float(row["implied_probability"]), 0.5)
        self.assertAlmostEqual(float(row["value_edge_pp"]), 5.0)
        self.assertEqual(int(row["league_id"]), 7)
        self.assertEqual(int(row["league_tier"]), 1)
        self.assertEqual(row["event_family"], "REZULTAT")
        self.assertNotIn("event_name", frame.columns)
        self.assertNotIn("probability_pct", frame.columns)

    def test_drops_unsettleable_events(self) -> None:
        frame = self._fetch([
            _raw_row(match_id=1, event_id=1),
            _raw_row(
                match_id=2,
                event_id=173,
                event_name="Dokładna liczba goli"),
            _raw_row(
                match_id=3,
                event_id=181,
                event_name="Strzelec bramki"),
            _raw_row(
                match_id=4,
                event_id=236,
                event_name="Powyżej 5.5 gola (OT/SO)"),
            _raw_row(
                match_id=5,
                event_id=33,
                event_name="Powyżej 8.5 rożnych",
                event_family="CORNERS")])
        self.assertEqual(
            [int(match_id) for match_id in frame["match_id"].tolist()],
            [1, 5])
        for event_id, name in (
                (1, "Zwycięstwo gospodarza"),
                (33, "Powyżej 8.5 rożnych")):
            self.assertTrue(
                repository.is_settleable_event(event_id, name))
        self.assertFalse(
            repository.is_settleable_event(173, "Dokładna liczba goli"))

    def test_drops_probability_outside_open_unit_interval(self) -> None:
        frame = self._fetch([
            _raw_row(match_id=1, probability_pct=0.0),
            _raw_row(match_id=2, probability_pct=100.0),
            _raw_row(match_id=3, probability_pct=None),
            _raw_row(match_id=4, odds=1.0),
            _raw_row(match_id=5, probability_pct=40.0, odds=3.5)])
        self.assertEqual(list(frame["match_id"]), [5])
        self.assertAlmostEqual(
            float(frame["model_probability"].iloc[0]), 0.4)
        self.assertAlmostEqual(
            float(frame["implied_probability"].iloc[0]), 1.0 / 3.5)

    def test_keeps_null_league_tier_and_family(self) -> None:
        frame = self._fetch([
            _raw_row(league_id=None, league_tier=None, event_family=None)])
        self.assertIsNone(frame["league_id"].iloc[0])
        self.assertIsNone(frame["league_tier"].iloc[0])
        self.assertIsNone(frame["event_family"].iloc[0])

    def test_limit_keeps_earliest_settleable_kickoffs(self) -> None:
        rows = []
        for index in range(MAX_CANDIDATES + 1):
            rows.append(_raw_row(
                match_id=index + 1,
                kickoff=_NOW + timedelta(hours=index + 1)))
        rows.append(_raw_row(
            match_id=9000,
            event_id=173,
            event_name="Dokładna liczba goli",
            kickoff=_NOW + timedelta(minutes=1)))
        frame = self._fetch(rows)
        self.assertEqual(len(frame), MAX_CANDIDATES)
        self.assertEqual(int(frame["match_id"].iloc[0]), 1)
        self.assertEqual(
            int(frame["match_id"].iloc[-1]), MAX_CANDIDATES)
        self.assertNotIn(9000, set(frame["match_id"].tolist()))
        self.assertNotIn(
            MAX_CANDIDATES + 1, set(frame["match_id"].tolist()))

    def test_rejects_a_non_positive_horizon(self) -> None:
        with self.assertRaises(ValueError):
            fetch_candidates(_NOW, horizon_days=0)


if __name__ == "__main__":
    unittest.main()
