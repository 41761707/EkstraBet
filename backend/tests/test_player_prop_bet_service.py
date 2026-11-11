"""Unit tests for player-prop recommendation mapping."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.services.player_prop_bet_service import (
    get_player_prop_recommendations)


_SEARCH = (
    "backend.services.player_prop_bet_service"
    ".player_prop_bet_repository.search_player_prop_recommendations")
_RECENT = (
    "backend.services.player_prop_bet_service"
    ".player_prop_bet_repository.fetch_recent_player_stats")
_MATCH = (
    "backend.services.player_prop_bet_service"
    ".player_prop_bet_repository.fetch_match_player_stats")

_GAME_DATE = datetime(2026, 11, 5, 18, 0, 0)
_EVENT_NAME = "Powyżej X strzałów na bramkę (zawodnik)"


def _page_row(**overrides: object) -> dict[str, object]:
    """Return one repository row. ``expected_value`` is a decoy."""
    row: dict[str, object] = {
        "line_id": 10,
        "player_id": 7,
        "player_name": "Player A",
        "line": 2.5,
        "match_id": 100,
        "league_id": 45,
        "league_name": "NHL",
        "season_id": 8,
        "game_date": _GAME_DATE,
        "home_team_id": 1,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": 2,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "event_id": 190,
        "event_name": _EVENT_NAME,
        "odds": 2.0,
        "probability": 20.0,
        "expected_value": 1.57,
        "bookmaker_id": 1,
        "bookmaker_name": "Superbet",
        "model_id": 13,
        "model_name": "HOCKEY_PLAYER_PROPS_V1",
        "settlement_status": "lost"}
    row.update(overrides)
    return row


def _history_frame() -> pd.DataFrame:
    """Newest first: 4, then 3, then 1. Oldest-first points are 1, 3, 4."""
    return pd.DataFrame([
        {
            "player_id": 7,
            "anchor_match_id": 100,
            "match_id": 90,
            "game_date": datetime(2026, 11, 4, 18, 0, 0),
            "stat_value": 4,
            "stat_column": "sog"},
        {
            "player_id": 7,
            "anchor_match_id": 100,
            "match_id": 80,
            "game_date": datetime(2026, 11, 3, 18, 0, 0),
            "stat_value": 3,
            "stat_column": "sog"},
        {
            "player_id": 7,
            "anchor_match_id": 100,
            "match_id": 70,
            "game_date": datetime(2026, 11, 2, 18, 0, 0),
            "stat_value": 1,
            "stat_column": "sog"}])


def _match_stats_frame() -> pd.DataFrame:
    """Settlement sog for the recommended match. It is not history."""
    return pd.DataFrame([{
        "player_id": 7,
        "match_id": 100,
        "sog": 3,
        "points": None,
        "assists": None,
        "goals": None}])


def _wire(
        mock_search: MagicMock,
        mock_recent: MagicMock,
        mock_match: MagicMock,
        rows: list[dict[str, object]],
        total: int,
        history: pd.DataFrame | None = None,
        stats: pd.DataFrame | None = None) -> None:
    """Point the three repository reads at in-memory frames."""
    mock_search.return_value = (pd.DataFrame(rows), total)
    if history is None:
        mock_recent.return_value = pd.DataFrame()
    else:
        mock_recent.return_value = history
    if stats is None:
        mock_match.return_value = pd.DataFrame()
    else:
        mock_match.return_value = stats


class TestPlayerPropBetService(unittest.TestCase):
    """EV, history order and settlement come from Python, not SQL text."""

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_rejects_history_window_outside_catalog(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        with self.assertRaises(ValueError) as caught:
            get_player_prop_recommendations(history_window=7)
        self.assertEqual(
            str(caught.exception), "history_window must be 5 or 10")
        mock_search.assert_not_called()
        mock_recent.assert_not_called()
        mock_match.assert_not_called()

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_ev_uses_probability_and_odds_not_expected_value(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        _wire(mock_search, mock_recent, mock_match, [_page_row()], 1)

        payload = get_player_prop_recommendations(apply_tax=True)
        row = payload["recommendations"][0]
        taxed = 0.2 * 2.0 * (1 - BETTING_TAX_RATE) - 1

        self.assertAlmostEqual(row["ev"], -0.6)
        self.assertAlmostEqual(row["ev_after_tax"], taxed)
        self.assertNotEqual(row["ev"], 1.57)
        self.assertNotIn("expected_value", row)
        self.assertAlmostEqual(row["probability"], 0.2)
        self.assertAlmostEqual(row["probability_pct"], 20.0)
        self.assertEqual(
            row["event_name"],
            "Powyżej 2.5 strzałów na bramkę (zawodnik)")
        self.assertEqual(
            mock_search.call_args.kwargs["tax_rate"], BETTING_TAX_RATE)
        self.assertTrue(mock_search.call_args.kwargs["apply_tax"])
        self.assertNotIn("history_window", mock_search.call_args.kwargs)

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_history_is_oldest_first_and_skips_settlement_stat(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        _wire(
            mock_search,
            mock_recent,
            mock_match,
            [_page_row()],
            1,
            history=_history_frame(),
            stats=_match_stats_frame())

        payload = get_player_prop_recommendations(history_window=10)
        history = payload["recommendations"][0]["history"]

        self.assertEqual(history["window"], 10)
        self.assertEqual(history["played"], 3)
        self.assertEqual(history["hits"], 2)
        self.assertEqual(
            history["points"],
            [{"value": 1}, {"value": 3}, {"value": 4}])
        anchors = mock_recent.call_args.args[0]
        self.assertEqual(
            anchors, [(7, 100, _GAME_DATE, "sog")])
        self.assertEqual(mock_recent.call_args.args[1], 10)

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_settlement_follows_match_stat_not_sql_column(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        pending = _page_row(
            line_id=11,
            player_id=8,
            match_id=101,
            player_name="Player B",
            settlement_status="won")
        _wire(
            mock_search,
            mock_recent,
            mock_match,
            [_page_row(), pending],
            2,
            history=_history_frame(),
            stats=_match_stats_frame())

        payload = get_player_prop_recommendations()
        won = payload["recommendations"][0]
        missing = payload["recommendations"][1]

        self.assertEqual(won["settlement_status"], "won")
        self.assertEqual(
            won["history"]["points"],
            [{"value": 1}, {"value": 3}, {"value": 4}])
        self.assertEqual(missing["settlement_status"], "pending")
        self.assertEqual(missing["history"]["played"], 0)
        self.assertEqual(missing["history"]["hits"], 0)
        self.assertEqual(missing["history"]["points"], [])
        self.assertIsNone(payload["filters_applied"]["tax_rate"])

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_filters_applied_uses_isoformat_and_window(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        _wire(mock_search, mock_recent, mock_match, [], 0)
        match_date = date(2026, 11, 5)
        date_from = date(2026, 11, 1)
        date_to = date(2026, 11, 6)

        payload = get_player_prop_recommendations(
            league_ids=[45],
            match_date=match_date,
            date_from=date_from,
            date_to=date_to,
            apply_tax=True,
            history_window=5)
        applied = payload["filters_applied"]

        self.assertEqual(payload["recommendations"], [])
        self.assertEqual(payload["total_count"], 0)
        self.assertEqual(applied["match_date"], "2026-11-05")
        self.assertEqual(applied["date_from"], "2026-11-01")
        self.assertEqual(applied["date_to"], "2026-11-06")
        self.assertEqual(applied["history_window"], 5)
        self.assertIsInstance(applied["history_window"], int)
        self.assertEqual(applied["league_ids"], [45])
        self.assertEqual(applied["tax_rate"], BETTING_TAX_RATE)
        self.assertEqual(mock_recent.call_args.args, ([], 5))
        self.assertEqual(mock_match.call_args.args, ([],))

    @patch(_MATCH)
    @patch(_RECENT)
    @patch(_SEARCH)
    def test_duplicate_line_and_model_keeps_first_row(
            self,
            mock_search: MagicMock,
            mock_recent: MagicMock,
            mock_match: MagicMock) -> None:
        first = _page_row(player_name="Player A")
        second = _page_row(player_name="Player B", player_id=9)
        _wire(
            mock_search,
            mock_recent,
            mock_match,
            [first, second],
            2,
            stats=_match_stats_frame())

        payload = get_player_prop_recommendations()

        self.assertEqual(payload["total_count"], 2)
        self.assertEqual(len(payload["recommendations"]), 1)
        self.assertEqual(
            payload["recommendations"][0]["player_name"], "Player A")
        self.assertEqual(len(mock_recent.call_args.args[0]), 1)
