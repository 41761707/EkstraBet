"""Unit tests for the shared player profile service and slice read."""

from __future__ import annotations

import unittest
from contextlib import ExitStack
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories.player_profile_repository import (
    fetch_hockey_event_facts)
from backend.repositories.player_profile_repository import fetch_profile_slice
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.services.player_profile_service import (
    PlayerProfileNotFoundError)
from backend.services.player_profile_service import (
    PlayerProfileUnavailableError)
from backend.services.player_profile_service import (
    PlayerProfileValidationError)
from backend.services.player_profile_service import get_player_profile
from backend.services.player_profile_service import search_players
from backend.services.player_service import FOOTBALL_SPORT_ID
from backend.services.player_service import _build_hockey_summary
from backend.sports.hockey.player_profile import (
    DISALLOWED_GOAL_EVENT_ID)
from backend.sports.hockey.player_profile import GOAL_EVENT_ID
from backend.sports.hockey.player_profile import HOCKEY_GOALIE_STAT_SQL
from backend.sports.hockey.player_profile import HOCKEY_SKATER_STAT_SQL
from backend.sports.hockey.player_profile import HockeyPlayerProfileSource
from backend.sports.hockey.player_profile import INCLUDED_EVENT_IDS
from backend.sports.hockey.player_profile import MAJOR_PENALTY_EVENT_ID
from backend.sports.hockey.player_profile import MINOR_PENALTY_EVENT_ID
from backend.sports.hockey.player_profile import MISCONDUCT_EVENT_ID
from backend.sports.hockey.player_profile import (
    UNSPORTSMANLIKE_EVENT_ID)
from backend.sports.player_profile import PLAYER_SEARCH_LIMIT
from backend.sports.player_profile import SLICE_MATCH_LIMIT


_UNSUPPORTED_TABLE = "Unsupported player profile stats table"


class TestFetchProfileSliceWhitelist(unittest.TestCase):
    """Stats table names enter SQL only after the whitelist check."""

    def test_unknown_table_raises_before_connection(self) -> None:
        with patch(
                "backend.repositories.player_profile_repository"
                ".get_db_connection") as connection:
            with self.assertRaises(ValueError) as caught:
                fetch_profile_slice(
                    "not_a_stats_table",
                    "stat.goals",
                    1,
                    2,
                    None,
                    None,
                    None,
                    None,
                    10)
        self.assertEqual(str(caught.exception), _UNSUPPORTED_TABLE)
        connection.assert_not_called()

    def test_slice_query_applies_optional_filters(self) -> None:
        query, params = _capture_slice(
            "hockey_match_player_stats",
            "stat.points, stat.goals",
            player_id=5,
            sport_id=2,
            season_id=9,
            opponent_team_id=3,
            own_team_id=4,
            teammate_id=8,
            limit=1000)
        self.assertIn("FROM hockey_match_player_stats stat", query)
        self.assertIn(
            "EXISTS (SELECT 1 FROM hockey_match_player_stats mate ",
            query)
        self.assertIn("m.season = %s", query)
        self.assertIn("m.away_team = %s", query)
        self.assertIn("m.home_team = %s", query)
        self.assertIn("stat.team_id = %s", query)
        self.assertIn("mate.player_id = %s", query)
        self.assertIn("stat.points, stat.goals", query)
        self.assertIn("ORDER BY m.game_date DESC, m.id DESC", query)
        self.assertEqual(params, (5, 2, 9, 3, 3, 4, 8, 1000))
        self.assertEqual(query.count("hockey_match_player_stats"), 2)

    def test_unset_filters_stay_out_of_the_query(self) -> None:
        query, params = _capture_slice(
            "football_player_stats",
            "stat.goals",
            player_id=5,
            sport_id=1,
            season_id=None,
            opponent_team_id=None,
            own_team_id=None,
            teammate_id=None,
            limit=10)
        self.assertIn("FROM football_player_stats stat", query)
        self.assertNotIn("m.season = %s", query)
        self.assertNotIn("m.away_team = %s", query)
        self.assertNotIn("stat.team_id = %s", query)
        self.assertNotIn("EXISTS", query)
        self.assertEqual(params, (5, 1, 10))
        self.assertEqual(query.count("football_player_stats"), 1)


class TestHockeyProfileSlice(unittest.TestCase):
    """Hockey slice picks stat columns from the player position."""

    @patch(
        "backend.repositories.player_profile_repository.fetch_profile_slice")
    @patch(
        "backend.repositories.player_profile_repository.fetch_player",
        return_value={"position": "G"})
    def test_goalie_uses_goalie_columns(
            self,
            _fetch_player: MagicMock,
            fetch_slice: MagicMock) -> None:
        fetch_slice.return_value = pd.DataFrame()
        frame = HockeyPlayerProfileSource().fetch_slice(
            15,
            7,
            None,
            None,
            None,
            1000)
        self.assertTrue(frame.empty)
        fetch_slice.assert_called_once_with(
            "hockey_match_player_stats",
            HOCKEY_GOALIE_STAT_SQL,
            15,
            2,
            7,
            None,
            None,
            None,
            1000)

    @patch(
        "backend.repositories.player_profile_repository.fetch_profile_slice")
    @patch(
        "backend.repositories.player_profile_repository.fetch_player",
        return_value={"position": "C"})
    def test_skater_uses_skater_columns(
            self,
            _fetch_player: MagicMock,
            fetch_slice: MagicMock) -> None:
        fetch_slice.return_value = pd.DataFrame()
        HockeyPlayerProfileSource().fetch_slice(
            15,
            None,
            3,
            4,
            8,
            50)
        fetch_slice.assert_called_once_with(
            "hockey_match_player_stats",
            HOCKEY_SKATER_STAT_SQL,
            15,
            2,
            None,
            3,
            4,
            8,
            50)


class TestFetchHockeyEventFacts(unittest.TestCase):
    """Hockey event facts stay on the player, the matches and six ids."""

    def test_empty_match_list_skips_sql(self) -> None:
        with patch(
                "backend.repositories.player_profile_repository"
                ".get_db_connection") as connection:
            frame = fetch_hockey_event_facts(15, [])
        connection.assert_not_called()
        self.assertTrue(frame.empty)
        self.assertEqual(
            list(frame.columns),
            ["match_id", "event_id", "period", "pp_flag", "en_flag"])

    def test_query_keeps_included_event_ids(self) -> None:
        query, params = _capture_event_facts(15, [10, 11])
        self.assertIn("FROM hockey_match_events hme", query)
        self.assertIn("hme.player_id = %s", query)
        self.assertIn("hme.match_id IN (%s, %s)", query)
        self.assertIn(
            "hme.event_id IN (%s, %s, %s, %s, %s, %s)",
            query)
        for column in (
                "match_id",
                "event_id",
                "period",
                "pp_flag",
                "en_flag"):
            self.assertIn(f"hme.{column}", query)
        self.assertNotIn("description", query)
        self.assertNotIn(188, params)
        self.assertEqual(params, (15, 10, 11, *INCLUDED_EVENT_IDS))

    def test_source_returns_frame_for_empty_matches(self) -> None:
        with patch(
                "backend.repositories.player_profile_repository"
                ".get_db_connection") as connection:
            frame = HockeyPlayerProfileSource().fetch_event_facts(15, [])
        connection.assert_not_called()
        self.assertIsNotNone(frame)
        self.assertTrue(frame.empty)


def _capture_slice(
        stats_table: str,
        stat_select_sql: str,
        player_id: int,
        sport_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None,
        limit: int) -> tuple[str, tuple[object, ...]]:
    with patch(
            "backend.repositories.player_profile_repository"
            ".get_db_connection") as connection, patch(
            "backend.repositories.player_profile_repository.pd.read_sql"
            ) as read_sql:
        connection.return_value.__enter__.return_value = object()
        read_sql.return_value = pd.DataFrame()
        fetch_profile_slice(
            stats_table,
            stat_select_sql,
            player_id,
            sport_id,
            season_id,
            opponent_team_id,
            own_team_id,
            teammate_id,
            limit)
    query = read_sql.call_args[0][0]
    params = read_sql.call_args[1]["params"]
    return query, params


def _capture_event_facts(
        player_id: int,
        match_ids: list[int]) -> tuple[str, tuple[object, ...]]:
    with patch(
            "backend.repositories.player_profile_repository"
            ".get_db_connection") as connection, patch(
            "backend.repositories.player_profile_repository.pd.read_sql"
            ) as read_sql:
        connection.return_value.__enter__.return_value = object()
        read_sql.return_value = pd.DataFrame()
        fetch_hockey_event_facts(player_id, match_ids)
    query = read_sql.call_args[0][0]
    params = read_sql.call_args[1]["params"]
    return query, params


_REPO = "backend.repositories.player_profile_repository"
_ZERO_EVENTS = {
    "goals": 0,
    "power_play_goals": 0,
    "empty_net_goals": 0,
    "goals_period_1": 0,
    "goals_period_2": 0,
    "goals_period_3": 0,
    "goals_overtime": 0,
    "shootout_goals": 0,
    "minor_penalties": 0,
    "major_penalties": 0,
    "misconduct_penalties": 0,
    "unsportsmanlike_penalties": 0,
    "disallowed_goals": 0}


class TestPlayerProfileService(unittest.TestCase):
    """Envelope checks run before the hockey slice is read."""

    def test_unknown_player_skips_the_slice(self) -> None:
        with _repo(None) as mocks:
            with self.assertRaises(PlayerProfileNotFoundError):
                get_player_profile(15, None, None, None, None)
        mocks["slice"].assert_not_called()
        mocks["events"].assert_not_called()

    def test_football_player_skips_the_slice(self) -> None:
        player = _person(sport_id=FOOTBALL_SPORT_ID, position="FW")
        with _repo(player) as mocks:
            with self.assertRaises(PlayerProfileUnavailableError):
                get_player_profile(15, None, None, None, None)
        mocks["slice"].assert_not_called()
        mocks["events"].assert_not_called()

    def test_same_teammate_is_rejected_before_the_slice(self) -> None:
        with _repo(_person()) as mocks:
            with self.assertRaises(PlayerProfileValidationError) as caught:
                get_player_profile(15, None, None, None, 15)
        self.assertEqual(
            caught.exception.message,
            "teammate_id must differ from player_id")
        mocks["slice"].assert_not_called()

    def test_same_club_as_opponent_is_rejected(self) -> None:
        with _repo(_person()) as mocks:
            with self.assertRaises(PlayerProfileValidationError) as caught:
                get_player_profile(15, None, 4, 4, None)
        self.assertEqual(
            caught.exception.message,
            "opponent_team_id must differ from own_team_id")
        mocks["slice"].assert_not_called()

    def test_unknown_season_is_rejected(self) -> None:
        with _repo(_person(), season_ok=False) as mocks:
            with self.assertRaises(PlayerProfileValidationError) as caught:
                get_player_profile(15, 99, None, None, None)
        self.assertEqual(caught.exception.message, "Unknown season")
        mocks["slice"].assert_not_called()

    def test_unknown_team_is_rejected(self) -> None:
        with _repo(_person(), team_ok=False) as mocks:
            with self.assertRaises(PlayerProfileValidationError) as caught:
                get_player_profile(15, None, 3, None, None)
        self.assertEqual(caught.exception.message, "Unknown team")
        mocks["slice"].assert_not_called()

    def test_teammate_from_another_sport_or_missing_is_rejected(
            self) -> None:
        cases = (
            ("other sport", _person(20, FOOTBALL_SPORT_ID, "FW")),
            ("missing", None))
        for label, teammate in cases:
            with self.subTest(label=label):
                profile = _person()
                with _repo(
                        profile,
                        players=[profile, teammate]) as mocks:
                    with self.assertRaises(
                            PlayerProfileValidationError) as caught:
                        get_player_profile(15, None, None, None, 20)
                self.assertEqual(
                    caught.exception.message,
                    "Unknown teammate")
                mocks["slice"].assert_not_called()

    def test_empty_slice_returns_zeros(self) -> None:
        cases = (
            ("C", "skater", False),
            ("G", "goalie", True))
        for position, role, is_goalie in cases:
            with self.subTest(position=position):
                player = _person(position=position)
                with _repo(player) as mocks:
                    result = get_player_profile(
                        15, None, None, None, None)
                body = result["body"]
                self.assertEqual(result["match_count"], 0)
                self.assertFalse(result["truncated"])
                self.assertEqual(result["sport_id"], 2)
                self.assertEqual(body["sport_id"], 2)
                self.assertEqual(body["player_role"], role)
                self.assertEqual(body["matches"], [])
                self.assertEqual(body["summary"]["is_goalie"], is_goalie)
                self.assertEqual(body["summary"]["average_toi"], "0:00")
                self.assertEqual(body["event_split"], _ZERO_EVENTS)
                stat_sql = (
                    HOCKEY_GOALIE_STAT_SQL
                    if is_goalie
                    else HOCKEY_SKATER_STAT_SQL)
                self.assertEqual(mocks["slice"].call_args[0][1], stat_sql)
                mocks["events"].assert_called_once_with(15, [])

    def test_two_skater_matches_sum_like_the_box_score(self) -> None:
        profile = _person()
        mate = _person(20, HOCKEY_SPORT_ID, "C", "Leon Draisaitl")
        frame = pd.DataFrame([
            _skater_row(
                10,
                goals=1,
                points=1,
                assists=0,
                plus_minus=1,
                penalty_minutes=2,
                sog=4,
                toi="20:00"),
            _skater_row(
                11,
                goals=2,
                points=3,
                assists=1,
                plus_minus=-1,
                penalty_minutes=0,
                sog=2,
                toi="10:30")])
        with _repo(
                profile,
                frame=frame,
                players=[profile, mate]) as mocks:
            result = get_player_profile(15, 7, 3, 4, 20)
        body = result["body"]
        expected = _build_hockey_summary(pd.DataFrame([
            {
                "points": 1,
                "goals": 1,
                "assists": 0,
                "plus_minus": 1,
                "penalty_minutes": 2,
                "sog": 4,
                "toi_minutes": 20.0},
            {
                "points": 3,
                "goals": 2,
                "assists": 1,
                "plus_minus": -1,
                "penalty_minutes": 0,
                "sog": 2,
                "toi_minutes": 10.5}]), False)
        self.assertEqual(body["summary"], expected)
        self.assertEqual(body["summary"]["goals"], 3)
        self.assertEqual(body["summary"]["points"], 4)
        self.assertEqual(body["sport_id"], 2)
        self.assertEqual(body["player_role"], "skater")
        self.assertEqual(result["match_count"], 2)
        self.assertFalse(result["truncated"])
        self.assertEqual(result["player_name"], "Connor McDavid")
        self.assertEqual(result["filters"], {
            "player_id": 15,
            "season_id": 7,
            "opponent_team_id": 3,
            "own_team_id": 4,
            "teammate_id": 20})
        self.assertEqual(mocks["slice"].call_args[0], (
            "hockey_match_player_stats",
            HOCKEY_SKATER_STAT_SQL,
            15,
            HOCKEY_SPORT_ID,
            7,
            3,
            4,
            20,
            SLICE_MATCH_LIMIT))
        first = body["matches"][0]
        self.assertEqual(first["match_id"], 10)
        self.assertEqual(first["game_date"], "2024-01-02")
        self.assertEqual(first["venue"], "home")
        self.assertEqual(first["goals"], 1)
        self.assertEqual(first["toi"], "20:00")
        self.assertEqual(first["toi_minutes"], 20.0)
        self.assertEqual(first["power_play_goals"], 0)
        self.assertEqual(first["empty_net_goals"], 0)
        self.assertEqual(body["matches"][1]["toi_minutes"], 10.5)

    def test_goalie_role_uses_goalie_summary(self) -> None:
        frame = pd.DataFrame([_goalie_row(10)])
        with _repo(_person(position="G"), frame=frame):
            result = get_player_profile(15, None, None, None, None)
        body = result["body"]
        self.assertEqual(body["player_role"], "goalie")
        self.assertTrue(body["summary"]["is_goalie"])
        self.assertEqual(body["summary"]["shots_against"], 30.0)
        match = body["matches"][0]
        self.assertIsNone(match["goals"])
        self.assertEqual(match["shots_against"], 30)
        self.assertEqual(match["saves_acc"], 90.0)
        self.assertEqual(match["toi_minutes"], 60.0)

    def test_event_facts_fill_the_split_and_the_match(self) -> None:
        events = pd.DataFrame([
            _event(10, GOAL_EVENT_ID, 1, pp_flag=1, en_flag=0),
            _event(10, GOAL_EVENT_ID, 4, pp_flag=0, en_flag=1),
            _event(10, MINOR_PENALTY_EVENT_ID, 2),
            _event(10, MAJOR_PENALTY_EVENT_ID, 2),
            _event(10, MISCONDUCT_EVENT_ID, 2),
            _event(10, UNSPORTSMANLIKE_EVENT_ID, 2),
            _event(10, DISALLOWED_GOAL_EVENT_ID, 3)])
        with _repo(
                _person(),
                frame=pd.DataFrame([_skater_row(10, goals=2, points=2)]),
                events=events) as mocks:
            result = get_player_profile(15, None, None, None, None)
        split = result["body"]["event_split"]
        self.assertEqual(split["goals"], 2)
        self.assertEqual(split["power_play_goals"], 1)
        self.assertEqual(split["empty_net_goals"], 1)
        self.assertEqual(split["goals_period_1"], 1)
        self.assertEqual(split["goals_overtime"], 1)
        self.assertEqual(split["minor_penalties"], 1)
        self.assertEqual(split["major_penalties"], 1)
        self.assertEqual(split["misconduct_penalties"], 1)
        self.assertEqual(split["unsportsmanlike_penalties"], 1)
        self.assertEqual(split["disallowed_goals"], 1)
        self.assertEqual(split["goals_period_2"], 0)
        self.assertEqual(split["shootout_goals"], 0)
        match = result["body"]["matches"][0]
        self.assertEqual(match["power_play_goals"], 1)
        self.assertEqual(match["empty_net_goals"], 1)
        mocks["events"].assert_called_once_with(15, [10])

    def test_goal_with_both_flags_counts_once(self) -> None:
        events = pd.DataFrame([
            _event(10, GOAL_EVENT_ID, 2, pp_flag=1, en_flag=1),
            _event(10, GOAL_EVENT_ID, 3, pp_flag=2, en_flag=2)])
        with _repo(
                _person(),
                frame=pd.DataFrame([_skater_row(10)]),
                events=events):
            result = get_player_profile(15, None, None, None, None)
        split = result["body"]["event_split"]
        self.assertEqual(split["goals"], 2)
        self.assertEqual(split["power_play_goals"], 1)
        self.assertEqual(split["empty_net_goals"], 1)
        self.assertEqual(split["goals_period_2"], 1)
        self.assertEqual(split["goals_period_3"], 1)
        match = result["body"]["matches"][0]
        self.assertEqual(match["power_play_goals"], 1)
        self.assertEqual(match["empty_net_goals"], 1)

    def test_null_box_score_becomes_zero(self) -> None:
        row = _skater_row(
            10,
            goals=None,
            points=None,
            assists=None,
            plus_minus=None,
            penalty_minutes=None,
            sog=None,
            toi=None)
        row["home_goals"] = None
        row["away_goals"] = None
        row["result"] = None
        row["opponent_shortcut"] = None
        with _repo(_person(), frame=pd.DataFrame([row])):
            result = get_player_profile(15, None, None, None, None)
        match = result["body"]["matches"][0]
        self.assertEqual(match["goals"], 0)
        self.assertEqual(match["points"], 0)
        self.assertEqual(match["toi"], "0:00")
        self.assertEqual(match["toi_minutes"], 0.0)
        self.assertIsNone(match["home_goals"])
        self.assertIsNone(match["result"])
        self.assertEqual(match["opponent_shortcut"], "")
        self.assertEqual(result["body"]["summary"]["goals"], 0)
        self.assertEqual(result["body"]["summary"]["average_toi"], "0:00")

    def test_full_limit_marks_the_slice_truncated(self) -> None:
        frame = pd.DataFrame([
            _skater_row(match_id)
            for match_id in range(1, SLICE_MATCH_LIMIT + 1)])
        with _repo(_person(), frame=frame) as mocks:
            result = get_player_profile(15, None, None, None, None)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["match_count"], SLICE_MATCH_LIMIT)
        self.assertEqual(
            mocks["slice"].call_args[0][-1],
            SLICE_MATCH_LIMIT)

    def test_short_search_is_rejected(self) -> None:
        for term in (" a ", None, "", " "):
            with self.subTest(term=term):
                with patch(f"{_REPO}.fetch_player_search") as search:
                    with self.assertRaises(
                            PlayerProfileValidationError) as caught:
                        search_players(HOCKEY_SPORT_ID, term)
                self.assertEqual(
                    caught.exception.message,
                    "Search must contain at least 2 characters")
                search.assert_not_called()

    def test_search_outside_the_registry_is_unavailable(self) -> None:
        with patch(f"{_REPO}.fetch_player_search") as search:
            with self.assertRaises(PlayerProfileUnavailableError):
                search_players(FOOTBALL_SPORT_ID, "abc")
        search.assert_not_called()

    def test_search_returns_hits_for_hockey(self) -> None:
        hits = [{
            "player_id": 8,
            "player_name": "Leon Draisaitl",
            "position": "C",
            "current_team_name": "Oilers"}]
        with patch(
                f"{_REPO}.fetch_player_search",
                return_value=hits) as search:
            result = search_players(HOCKEY_SPORT_ID, "  DR ")
        search.assert_called_once_with(
            HOCKEY_SPORT_ID,
            "DR",
            PLAYER_SEARCH_LIMIT)
        self.assertEqual(result["players"], hits)
        self.assertEqual(result["total_count"], 1)


def _person(
        player_id: int = 15,
        sport_id: int = HOCKEY_SPORT_ID,
        position: str | None = "C",
        player_name: str = "Connor McDavid") -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "position": position,
        "sport_id": sport_id}


def _skater_row(
        match_id: int,
        goals: int | None = 0,
        points: int | None = 0,
        assists: int | None = 0,
        plus_minus: int | None = 0,
        penalty_minutes: int | None = 0,
        sog: int | None = 0,
        toi: str | None = "10:00") -> dict[str, object]:
    return {
        "match_id": match_id,
        "game_date": "2024-01-02",
        "season_id": 7,
        "season_years": "2024/2025",
        "own_team_id": 4,
        "own_team_name": "Oilers",
        "opponent_team_id": 3,
        "opponent_name": "Flames",
        "opponent_shortcut": "CGY",
        "venue": "home",
        "home_goals": 3,
        "away_goals": 1,
        "result": "H",
        "points": points,
        "goals": goals,
        "assists": assists,
        "plus_minus": plus_minus,
        "penalty_minutes": penalty_minutes,
        "sog": sog,
        "toi": toi}


def _goalie_row(match_id: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "game_date": "2024-01-02",
        "season_id": 7,
        "season_years": "2024/2025",
        "own_team_id": 4,
        "own_team_name": "Oilers",
        "opponent_team_id": 3,
        "opponent_name": "Flames",
        "opponent_shortcut": "CGY",
        "venue": "away",
        "home_goals": 2,
        "away_goals": 1,
        "result": "A",
        "toi": "60:00",
        "shots_against": 30,
        "shots_saved": 27,
        "saves_acc": 90}


def _event(
        match_id: int,
        event_id: int,
        period: int,
        pp_flag: int = 0,
        en_flag: int = 0) -> dict[str, int]:
    return {
        "match_id": match_id,
        "event_id": event_id,
        "period": period,
        "pp_flag": pp_flag,
        "en_flag": en_flag}


@contextmanager
def _repo(
        player: dict[str, object] | None,
        frame: pd.DataFrame | None = None,
        events: pd.DataFrame | None = None,
        season_ok: bool = True,
        team_ok: bool = True,
        players: list[dict[str, object] | None] | None = None
        ) -> Iterator[dict[str, MagicMock]]:
    """Patch profile reads. The slice reloads the player for position."""
    sequence: list[dict[str, object] | None]
    if players is None:
        sequence = [player]
    else:
        sequence = list(players)
    if player is not None:
        sequence.append(player)
    with ExitStack() as stack:
        player_mock = stack.enter_context(patch(
            f"{_REPO}.fetch_player",
            side_effect=sequence))
        slice_mock = stack.enter_context(patch(
            f"{_REPO}.fetch_profile_slice"))
        events_mock = stack.enter_context(patch(
            f"{_REPO}.fetch_hockey_event_facts"))
        stack.enter_context(patch(
            f"{_REPO}.season_exists",
            return_value=season_ok))
        stack.enter_context(patch(
            f"{_REPO}.team_exists",
            return_value=team_ok))
        slice_mock.return_value = (
            frame if frame is not None else pd.DataFrame())
        events_mock.return_value = (
            events if events is not None else pd.DataFrame())
        yield {
            "player": player_mock,
            "slice": slice_mock,
            "events": events_mock}
