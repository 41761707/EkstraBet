"""Unit tests for the knockout bracket service. No database."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories import knockout_repository
from backend.services.knockout_bracket_service import get_league_bracket
from backend.services.knockout_profiles import CHAMPIONS_LEAGUE_ID
from backend.services.knockout_profiles import PENDING_OPPONENT_LABEL
from backend.services.knockout_ties import DECIDED_EXTRA_TIME
from backend.services.knockout_ties import DECIDED_OVERTIME
from backend.services.knockout_ties import FOOTBALL_SPORT_ID
from backend.services.knockout_ties import HOCKEY_SPORT_ID


_EXISTS = (
    "backend.services.knockout_bracket_service"
    ".league_repository.league_exists")
_FETCH = (
    "backend.services.knockout_bracket_service"
    ".knockout_repository.fetch_knockout_matches")
_COUNT = (
    "backend.services.knockout_bracket_service"
    ".knockout_repository.count_unplayed_league_matches")
_STANDINGS = (
    "backend.services.knockout_bracket_service.get_league_standings")
_SEASON_ID = 12
_Loaded = tuple[
    dict[str, object] | None,
    MagicMock,
    MagicMock,
    MagicMock]


def _row(
        match_id: int,
        round_number: int,
        home_team_id: int | None,
        away_team_id: int | None,
        home_goals: int | None,
        away_goals: int | None,
        result: str,
        game_date: datetime,
        sport_id: int = FOOTBALL_SPORT_ID,
        home_extra_time_goals: int | None = None,
        away_extra_time_goals: int | None = None,
        ot_winner: int | None = None,
        so_winner: int | None = None) -> dict[str, object]:
    """One knockout row, using the repository column names."""
    return {
        "match_id": match_id,
        "sport_id": sport_id,
        "round_number": round_number,
        "game_date": game_date,
        "result": result,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_team_name": f"Team {home_team_id}",
        "away_team_name": f"Team {away_team_id}",
        "home_team_shortcut": f"T{home_team_id}",
        "away_team_shortcut": f"T{away_team_id}",
        "home_extra_time_goals": home_extra_time_goals,
        "away_extra_time_goals": away_extra_time_goals,
        "home_penalty_goals": None,
        "away_penalty_goals": None,
        "ot_winner": ot_winner,
        "so_winner": so_winner}


def _column_ties(bracket: dict[str, object]) -> list[dict[str, object]]:
    """Ties drawn in columns. The third-place tie is not among them."""
    found: list[dict[str, object]] = []
    columns = bracket["columns"]
    assert isinstance(columns, list)
    for column in columns:
        found.extend(column["ties"])
    return found


def _tie(
        bracket: dict[str, object],
        tie_id: str) -> dict[str, object]:
    """The drawn tie with this id, including third place."""
    for tie in _column_ties(bracket):
        if tie["tie_id"] == tie_id:
            return tie
    third = bracket["third_place"]
    if isinstance(third, dict) and third["tie_id"] == tie_id:
        return third
    raise AssertionError(f"Missing tie {tie_id}")


class TestGetLeagueBracket(unittest.TestCase):
    """The service composes a frame into the bracket dictionary."""

    def _read(
            self,
            frame: pd.DataFrame,
            league_id: int = 47,
            exists: bool = True,
            unplayed: int = 0,
            standings: dict[str, object] | None = None) -> _Loaded:
        """Call the service with the database replaced by this frame."""
        with patch(_EXISTS, return_value=exists), \
                patch(_FETCH, return_value=frame) as fetch, \
                patch(_COUNT, return_value=unplayed) as count, \
                patch(_STANDINGS, return_value=standings) as table:
            payload = get_league_bracket(league_id, _SEASON_ID)
        return payload, fetch, count, table

    def test_missing_league_returns_none(self) -> None:
        payload, fetch, count, table = self._read(
            pd.DataFrame(),
            exists=False)
        self.assertIsNone(payload)
        fetch.assert_not_called()
        count.assert_not_called()
        table.assert_not_called()

    def test_season_without_knockout_rounds_is_empty(self) -> None:
        payload, _fetch, _count, table = self._read(pd.DataFrame())
        assert payload is not None
        self.assertEqual(payload["league_id"], 47)
        self.assertEqual(payload["season_id"], _SEASON_ID)
        self.assertEqual(payload["brackets"], [])
        self.assertEqual(payload["consumed_round_numbers"], [])
        table.assert_not_called()

    def test_hidden_round_is_left_out_of_consumed_rounds(self) -> None:
        frame = pd.DataFrame([
            _row(1, 971, 1, 2, 1, 0, "1", datetime(2026, 7, 1)),
            _row(2, 971, 2, 1, 1, 0, "1", datetime(2026, 7, 8)),
            _row(3, 971, 3, 4, 2, 0, "1", datetime(2026, 7, 2)),
            _row(
                4, 970, 1, 3, 0, 0, "X", datetime(2026, 7, 20),
                home_extra_time_goals=1,
                away_extra_time_goals=0),
            _row(5, 969, 2, 4, 1, 0, "1", datetime(2026, 7, 19)),
            _row(6, 1005, 10, 11, 1, 0, "1", datetime(2026, 5, 1)),
            _row(7, 1006, 11, 10, 0, 1, "2", datetime(2026, 5, 8)),
            _row(8, 444, 7, 8, 1, 0, "1", datetime(2026, 6, 1)),
            _row(9, 970, None, 3, 1, 0, "1", datetime(2026, 7, 20))])
        payload, _fetch, _count, _table = self._read(frame)
        assert payload is not None
        self.assertEqual(payload["consumed_round_numbers"], [969, 970, 971])
        self.assertEqual(len(payload["brackets"]), 1)
        bracket = payload["brackets"][0]
        self.assertEqual(bracket["bracket_id"], "cup")
        self.assertEqual(bracket["title"], "Drabinka")
        self.assertEqual(
            [column["depth"] for column in bracket["columns"]],
            [2, 1])
        drawn = _column_ties(bracket)
        self.assertEqual(
            [tie["tie_id"] for tie in drawn],
            ["cup-2-1-2", "cup-2-3-4", "cup-1-1-3"])
        semi = _tie(bracket, "cup-2-1-2")
        final = _tie(bracket, "cup-1-1-3")
        other = _tie(bracket, "cup-2-3-4")
        third = bracket["third_place"]
        assert isinstance(third, dict)
        self.assertEqual(semi["aggregate"], [1, 1])
        self.assertIsNone(semi["series_wins"])
        self.assertEqual(semi["advanced_team_id"], 1)
        self.assertEqual(semi["teams"][0]["name"], "Team 1")
        self.assertEqual(semi["teams"][0]["shortcut"], "T1")
        self.assertEqual(
            [match["match_id"] for match in semi["matches"]],
            [1, 2])
        self.assertTrue(semi["on_champion_path"])
        self.assertFalse(other["on_champion_path"])
        self.assertEqual(final["feeder_tie_ids"], ["cup-2-1-2", "cup-2-3-4"])
        self.assertEqual(final["advanced_team_id"], 1)
        self.assertTrue(final["on_champion_path"])
        played = final["matches"][0]
        self.assertEqual(played["decided_by"], DECIDED_EXTRA_TIME)
        self.assertEqual(played["home_goals"], 0)
        self.assertEqual(played["home_extra_time_goals"], 1)
        self.assertEqual(played["away_extra_time_goals"], 0)
        self.assertTrue(played["is_played"])
        self.assertNotIn("score_winner_team_id", final)
        self.assertEqual(third["tie_id"], "cup-third-2-4")
        self.assertFalse(third["on_champion_path"])
        self.assertNotIn(third["tie_id"], [tie["tie_id"] for tie in drawn])

    def test_bye_card_uses_the_name_from_a_later_match(self) -> None:
        frame = pd.DataFrame([
            _row(1, 972, 1, 2, 1, 0, "1", datetime(2026, 7, 1)),
            _row(2, 970, 1, 3, 2, 0, "1", datetime(2026, 7, 10))])
        payload, _fetch, _count, _table = self._read(frame)
        assert payload is not None
        bracket = payload["brackets"][0]
        bye = _tie(bracket, "bye-cup-4-3")
        self.assertTrue(bye["is_bye"])
        self.assertEqual(bye["matches"], [])
        self.assertIsNone(bye["aggregate"])
        self.assertIsNone(bye["series_wins"])
        self.assertEqual(bye["teams"], [{
            "team_id": 3,
            "name": "Team 3",
            "shortcut": "T3"}])
        depths = [column["depth"] for column in bracket["columns"]]
        self.assertEqual(depths, [4, 1])
        self.assertEqual(
            payload["consumed_round_numbers"],
            [970, 972])

    def test_hockey_overtime_column_reaches_the_card(self) -> None:
        frame = pd.DataFrame([
            _row(
                1, 950, 1, 2, 3, 3, "X", datetime(2026, 5, 1),
                sport_id=HOCKEY_SPORT_ID,
                ot_winner=1),
            _row(
                2, 960, 1, 3, 4, 2, "1", datetime(2026, 6, 1),
                sport_id=HOCKEY_SPORT_ID)])
        payload, _fetch, _count, _table = self._read(
            frame,
            league_id=45)
        assert payload is not None
        bracket = payload["brackets"][0]
        semi = _tie(bracket, "cup-2-1-2")
        self.assertEqual(semi["series_wins"], [1, 0])
        self.assertIsNone(semi["aggregate"])
        self.assertEqual(semi["advanced_team_id"], 1)
        self.assertEqual(
            semi["matches"][0]["decided_by"],
            DECIDED_OVERTIME)
        self.assertEqual(semi["matches"][0]["home_goals"], 3)

    def test_profile_reads_standings_only_when_league_phase_is_complete(
            self) -> None:
        frame = pd.DataFrame([
            _row(1, 974, 20, 21, 2, 0, "1", datetime(2026, 3, 1))])
        rows = [
            {
                "team_id": team_id,
                "position": team_id,
                "team_name": f"Seed {team_id}"}
            for team_id in range(1, 9)]
        rows.append({
            "team_id": 20,
            "position": 20,
            "team_name": "Table Twenty"})
        payload, _fetch, _count, table = self._read(
            frame,
            league_id=CHAMPIONS_LEAGUE_ID,
            unplayed=0,
            standings={"standings": rows})
        assert payload is not None
        table.assert_called_once_with(
            CHAMPIONS_LEAGUE_ID,
            _SEASON_ID,
            "overall")
        self.assertEqual(payload["consumed_round_numbers"], [974])
        bracket = payload["brackets"][0]
        self.assertEqual(
            [column["depth"] for column in bracket["columns"]],
            [16, 8])
        placeholders = bracket["columns"][1]["ties"]
        self.assertEqual(len(placeholders), 8)
        self.assertEqual(
            [tie["tie_id"] for tie in placeholders],
            [f"cup-8-{team_id}-pending" for team_id in range(1, 9)])
        first = placeholders[0]
        self.assertEqual(
            first["pending_opponent_label"],
            PENDING_OPPONENT_LABEL)
        self.assertEqual(first["feeder_tie_ids"], [])
        self.assertEqual(first["seed_position"], 1)
        self.assertFalse(first["on_champion_path"])
        self.assertEqual(first["teams"], [{
            "team_id": 1,
            "name": "Seed 1",
            "shortcut": None}])
        played = _tie(bracket, "cup-16-20-21")
        self.assertEqual(played["teams"][0]["name"], "Team 20")
        self.assertEqual(played["feeder_tie_ids"], [])

        hidden, _fetch, _count, blocked = self._read(
            frame,
            league_id=CHAMPIONS_LEAGUE_ID,
            unplayed=4,
            standings={"standings": rows})
        assert hidden is not None
        blocked.assert_not_called()
        self.assertEqual(hidden["brackets"], [])
        self.assertEqual(hidden["consumed_round_numbers"], [])


def _connection(mock_get_conn: MagicMock) -> None:
    """Make get_db_connection a context manager that yields a mock."""
    connection = MagicMock()
    manager = MagicMock()
    manager.__enter__.return_value = connection
    manager.__exit__.return_value = False
    mock_get_conn.return_value = manager


class TestKnockoutRepositoryQuery(unittest.TestCase):
    """The reads stay one select each and do not build the tree."""

    @patch("backend.repositories.knockout_repository.pd.read_sql")
    @patch("backend.repositories.knockout_repository.get_db_connection")
    def test_fetch_reads_overtime_columns(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()
        knockout_repository.fetch_knockout_matches(47, _SEASON_ID)
        query = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertEqual(params, (47, _SEASON_ID, 900))
        self.assertIn("m.round >= %s", query)
        self.assertIn("football_special_round_add", query)
        self.assertIn("home_team_goals_post_ot", query)
        self.assertIn("home_team_pen_score", query)
        self.assertIn("hockey_matches_add", query)
        self.assertIn("hma.OTwinner AS ot_winner", query)
        self.assertIn("hma.SOwinner AS so_winner", query)
        self.assertNotIn("GROUP BY", query)

    @patch("backend.repositories.knockout_repository.pd.read_sql")
    @patch("backend.repositories.knockout_repository.get_db_connection")
    def test_count_ignores_knockout_rounds(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{"total": 3}])
        total = knockout_repository.count_unplayed_league_matches(
            42,
            _SEASON_ID)
        query = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertEqual(total, 3)
        self.assertEqual(params, (42, _SEASON_ID, 900))
        self.assertIn("round < %s", query)
        self.assertIn("result = '0'", query)
        self.assertIn("result IS NULL", query)


if __name__ == "__main__":
    unittest.main()
