"""Unit tests for hockey game ratings."""

from __future__ import annotations

import unittest
from decimal import Decimal

import pandas as pd

from backend.sports.hockey.game_rating import GOAL_EVENT_ID
from backend.sports.hockey.game_rating import MAJOR_PENALTY_EVENT_ID
from backend.sports.hockey.game_rating import MINOR_PENALTY_EVENT_ID
from backend.sports.hockey.game_rating import RatingParts
from backend.sports.hockey.game_rating import SkaterCounts
from backend.sports.hockey.game_rating import attribute_events
from backend.sports.hockey.game_rating import build_match_rating
from backend.sports.hockey.game_rating import normalize
from backend.sports.hockey.game_rating import player_group
from backend.sports.hockey.game_rating import rate_goalie
from backend.sports.hockey.game_rating import rate_skater


def _counts(
    goals: int = 0,
    assists: int = 0,
    es_points: int = 0,
    empty_net_goals: int = 0,
    shots_on_goal: int = 0,
    plus_minus: int | None = 0,
    minor_penalties: int = 0,
    major_penalties: int = 0,
    blocked: int = 0,
    faceoffs_taken: int = 0,
    faceoffs_won: int = 0) -> SkaterCounts:
    """Build skater counters, with untouched stats left neutral."""
    return SkaterCounts(
        goals=goals,
        assists=assists,
        es_points=es_points,
        empty_net_goals=empty_net_goals,
        shots_on_goal=shots_on_goal,
        plus_minus=plus_minus,
        minor_penalties=minor_penalties,
        major_penalties=major_penalties,
        blocked=blocked,
        faceoffs_taken=faceoffs_taken,
        faceoffs_won=faceoffs_won)


class TestHockeySkaterRating(unittest.TestCase):
    """Cases that rate_skater can score from counters alone."""

    def _assert_score(
        self,
        parts: RatingParts,
        offense: str,
        defense: str,
        total: str) -> None:
        """Check the three sums and that goaltending stayed zero."""
        self.assertEqual(parts.offense, Decimal(offense))
        self.assertEqual(parts.defense, Decimal(defense))
        self.assertEqual(parts.total, Decimal(total))
        self.assertEqual(parts.offense + parts.defense, parts.total)
        self.assertEqual(parts.goaltending, Decimal("0.0"))

    def test_even_strength_three_points_and_plus_three_score_3_3(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=2,
            es_points=3,
            shots_on_goal=4,
            plus_minus=3))
        self._assert_score(parts, "3.3", "0.0", "3.3")
        self.assertEqual(parts.production, Decimal("3.0"))
        self.assertEqual(parts.shots, Decimal("0.3"))
        self.assertEqual(format(parts.empty_net, "f"), "0.0")
        self.assertEqual(format(parts.penalties, "f"), "0.0")
        self.assertEqual(format(parts.goals_against, "f"), "0.0")
        self.assertEqual(format(parts.blocks, "f"), "0.0")

    def test_even_strength_three_points_and_minus_one_score_1_9(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=2,
            es_points=3,
            shots_on_goal=4,
            plus_minus=-1))
        self._assert_score(parts, "3.3", "-1.4", "1.9")
        self.assertEqual(parts.production, Decimal("3.0"))
        self.assertEqual(parts.shots, Decimal("0.3"))
        self.assertEqual(parts.goals_against, Decimal("-1.4"))

    def test_quiet_defender_scores_shots_teammates_and_blocks(self) -> None:
        parts = rate_skater(_counts(
            shots_on_goal=1,
            plus_minus=2,
            blocked=4))
        self._assert_score(parts, "0.5", "0.4", "0.9")
        self.assertEqual(parts.shots, Decimal("0.1"))
        self.assertEqual(parts.teammate_goals, Decimal("0.4"))
        self.assertEqual(parts.blocks, Decimal("0.4"))

    def test_two_minors_and_minus_three_score_minus_1_4(self) -> None:
        parts = rate_skater(_counts(
            plus_minus=-3,
            minor_penalties=2))
        self._assert_score(parts, "0.0", "-1.4", "-1.4")
        self.assertEqual(parts.goals_against, Decimal("-1.1"))
        self.assertEqual(parts.penalties, Decimal("-0.3"))

    def test_one_minor_rounds_half_up(self) -> None:
        parts = rate_skater(_counts(minor_penalties=1))
        self.assertEqual(parts.penalties, Decimal("-0.2"))
        self._assert_score(parts, "0.0", "-0.2", "-0.2")

    def test_minor_plus_major_round_as_one_leaf(self) -> None:
        parts = rate_skater(_counts(
            minor_penalties=1,
            major_penalties=1))
        self.assertEqual(parts.penalties, Decimal("-0.5"))
        self._assert_score(parts, "0.0", "-0.5", "-0.5")

    def test_faceoffs_ten_of_fourteen_round_to_one_tenth(self) -> None:
        parts = rate_skater(_counts(
            faceoffs_taken=14,
            faceoffs_won=10))
        self.assertEqual(parts.faceoffs, Decimal("0.1"))
        self._assert_score(parts, "0.1", "0.0", "0.1")

    def test_missing_plus_minus_keeps_ice_at_zero(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=1,
            plus_minus=None))
        self._assert_score(parts, "1.0", "0.0", "1.0")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.teammate_goals, Decimal("0.0"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_power_play_goal_does_not_count_as_a_goal_against(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=0,
            shots_on_goal=3,
            plus_minus=0))
        self._assert_score(parts, "1.2", "0.0", "1.2")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.shots, Decimal("0.2"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_empty_net_goal_trims_the_goal(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=1,
            empty_net_goals=1,
            shots_on_goal=1,
            plus_minus=1))
        self._assert_score(parts, "0.7", "0.0", "0.7")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.empty_net, Decimal("-0.3"))

    def test_power_play_assist_stays_out_of_even_strength_ice(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=1,
            es_points=1,
            shots_on_goal=1,
            plus_minus=1))
        self._assert_score(parts, "2.0", "0.0", "2.0")
        self.assertEqual(parts.production, Decimal("2.0"))
        self.assertEqual(parts.shots, Decimal("0.0"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_each_block_scores_one_tenth(self) -> None:
        one = rate_skater(_counts(blocked=1))
        four = rate_skater(_counts(blocked=4))
        none = rate_skater(_counts(blocked=0))
        self.assertEqual(one.blocks, Decimal("0.1"))
        self.assertEqual(four.blocks, Decimal("0.4"))
        self.assertEqual(none.blocks, Decimal("0.0"))


class TestHockeyGoalieRating(unittest.TestCase):
    """rate_goalie scores saves above a season rate and nothing else."""

    def test_shutout_on_thirty_shots_scores_2_8(self) -> None:
        self.assertEqual(rate_goalie(30, 30, 0.907), 2.8)

    def test_twenty_three_saves_on_twenty_eight_shots_score_minus_2_4(
        self) -> None:
        self.assertEqual(rate_goalie(28, 23, 0.907), -2.4)

    def test_missing_shots_against_score_zero(self) -> None:
        self.assertEqual(rate_goalie(None, 30, 0.907), 0.0)

    def test_zero_shots_against_score_zero(self) -> None:
        self.assertEqual(rate_goalie(0, 0, 0.907), 0.0)

    def test_missing_saves_use_the_rounded_negative_expectation(self) -> None:
        # -0.907 * 10 = -9.07, czyli -9.1 po tym samym zaokrągleniu.
        self.assertEqual(rate_goalie(10, None, 0.907), -9.1)


HOME_TEAM_ID = 10
AWAY_TEAM_ID = 20


def _player(
    player_id: int,
    player_name: str,
    team_id: int = HOME_TEAM_ID,
    goals: int = 0,
    assists: int = 0) -> dict[str, object]:
    """Build one player row. The name column is the common name."""
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "goals": goals,
        "assists": assists
    }


def _event(
    player_id: int,
    event_id: int,
    team_id: int = HOME_TEAM_ID,
    description: str | None = None,
    pp_flag: int = 0,
    en_flag: int = 0) -> dict[str, object]:
    """Build one play-by-play row."""
    return {
        "event_id": event_id,
        "player_id": player_id,
        "team_id": team_id,
        "pp_flag": pp_flag,
        "en_flag": en_flag,
        "description": description
    }


class TestHockeyEventCredits(unittest.TestCase):
    """attribute_events reads goals, assists and penalties."""

    def test_event_ids_are_goal_minor_and_major(self) -> None:
        self.assertEqual(GOAL_EVENT_ID, 181)
        self.assertEqual(MINOR_PENALTY_EVENT_ID, 183)
        self.assertEqual(MAJOR_PENALTY_EVENT_ID, 185)

    def test_normalize_matches_a_name_without_diacritics(self) -> None:
        self.assertEqual(normalize("Stützle T."), normalize("Stutzle T."))

    def test_assist_matches_stutzle_without_diacritics(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Stützle T.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Stutzle T.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[1].empty_net_goals, 0)

    def test_power_play_goal_adds_no_even_strength_points(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Sanderson J."),
            _player(3, "Halliday S.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Sanderson J. + Halliday S., W przewadze",
                pp_flag=1,
                en_flag=0)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].empty_net_goals, 0)
        self.assertEqual(credits[2].es_points, 0)
        self.assertEqual(credits[3].es_points, 0)

    def test_empty_net_goal_credits_scorer_and_assists(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Armia J."),
            _player(3, "Haula E.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Armia J. + Haula E., Do pustej bramki",
                pp_flag=0,
                en_flag=1)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].empty_net_goals, 1)
        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[2].empty_net_goals, 0)
        self.assertEqual(credits[3].es_points, 1)
        self.assertEqual(credits[3].empty_net_goals, 0)

    def test_empty_net_still_counts_on_a_power_play_goal(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Assist A.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Assist A.",
                pp_flag=1,
                en_flag=1)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].empty_net_goals, 1)
        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[2].es_points, 0)

    def test_unmatched_and_ambiguous_assists_are_skipped(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Twin T."),
            _player(3, "Twin T."),
            _player(4, "Away A.", team_id=AWAY_TEAM_ID),
            _player(5, "Real R.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Nobody N. + Twin T. + Away A. + Real R.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[2].es_points, 0)
        self.assertEqual(credits[3].es_points, 0)
        self.assertEqual(credits[4].es_points, 0)
        self.assertEqual(credits[5].es_points, 1)

    def test_same_player_is_credited_once_per_goal(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Haula E.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Haula E. + Haula E.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[2].es_points, 1)

    def test_missing_goal_events_use_box_score_points(self) -> None:
        players = pd.DataFrame([
            _player(1, "Assist A.", assists=2),
            _player(2, "Quiet Q.", goals=1, assists=1)
        ])

        credits = attribute_events(players, pd.DataFrame())

        self.assertEqual(credits[1].es_points, 2)
        self.assertEqual(credits[1].empty_net_goals, 0)
        self.assertEqual(credits[1].minor_penalties, 0)
        self.assertEqual(credits[2].es_points, 2)
        self.assertEqual(credits[2].empty_net_goals, 0)

    def test_one_goal_event_disables_box_score_fallback(self) -> None:
        players = pd.DataFrame([
            _player(1, "Assist A.", assists=2),
            _player(2, "Scorer S.", goals=1)
        ])
        events = pd.DataFrame([
            _event(player_id=2, event_id=181, description=None),
            _event(player_id=1, event_id=183)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].minor_penalties, 1)
        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[2].empty_net_goals, 0)

    def test_penalties_are_counted_from_events_not_minutes(self) -> None:
        players = pd.DataFrame([_player(1, "Penal P.")])
        events = pd.DataFrame([
            _event(player_id=1, event_id=183),
            _event(player_id=1, event_id=183),
            _event(player_id=1, event_id=185),
            _event(player_id=1, event_id=184),
            _event(player_id=1, event_id=186),
            _event(player_id=1, event_id=187),
            _event(player_id=1, event_id=188),
            _event(player_id=1, event_id=189)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].minor_penalties, 2)
        self.assertEqual(credits[1].major_penalties, 1)
        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].empty_net_goals, 0)


def _rating_player(
    player_id: int,
    player_name: str,
    team_id: int = HOME_TEAM_ID,
    goals: int = 0,
    assists: int = 0,
    plus_minus: int | None = 0,
    sog: int = 0,
    blocked: int = 0,
    faceoff: int = 0,
    faceoff_won: int = 0,
    shots_against: int | None = None,
    shots_saved: int | None = None,
    roster_position: str | None = None,
    player_position: str | None = None) -> dict[str, object]:
    """Build one rating row. A missing roster stays missing."""
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "goals": goals,
        "assists": assists,
        "plus_minus": plus_minus,
        "sog": sog,
        "blocked": blocked,
        "faceoff": faceoff,
        "faceoff_won": faceoff_won,
        "shots_against": shots_against,
        "shots_saved": shots_saved,
        "roster_position": roster_position,
        "player_position": player_position
    }


def _rate(
    players: pd.DataFrame,
    events: pd.DataFrame | None = None,
    save_rate: float = 0.907) -> dict:
    """Rate a frame with home first and away second."""
    if events is None:
        events = pd.DataFrame()
    return build_match_rating(
        players,
        events,
        save_rate,
        HOME_TEAM_ID,
        AWAY_TEAM_ID,
        "Philadelphia Flyers",
        "Ottawa Senators")


class TestHockeyMatchRating(unittest.TestCase):
    """Position groups and the two-team rating payload."""

    def _assert_balanced(self, rating: dict) -> None:
        """Every published total is offense plus defense."""
        self.assertEqual(len(rating["teams"]), 2)
        for team in rating["teams"]:
            for player in team["players"]:
                self.assertEqual(
                    player["offense"] + player["defense"],
                    player["total"])

    def test_roster_defense_beats_a_wing_position(self) -> None:
        self.assertEqual(player_group("D", "R", None), "defense")
        players = pd.DataFrame([
            _rating_player(
                7, "Halliday S.",
                roster_position="D",
                player_position="R",
                blocked=0,
                plus_minus=0)
        ])

        rating = _rate(players)
        player = rating["teams"][0]["players"][0]

        self.assertEqual(player["group"], "defense")
        self.assertEqual(player["parts"]["blocks"], 0.0)
        self.assertEqual(player["parts"]["goaltending"], 0.0)
        self.assertEqual(rating["teams"][0]["team_id"], HOME_TEAM_ID)
        self.assertEqual(rating["teams"][1]["team_id"], AWAY_TEAM_ID)
        self.assertEqual(rating["teams"][1]["players"], [])
        self._assert_balanced(rating)

    def test_missing_roster_goalie_gets_saves_and_no_blocks(self) -> None:
        self.assertEqual(player_group(None, "G", None), "goalie")
        self.assertEqual(player_group("", "G", None), "goalie")
        players = pd.DataFrame([
            _rating_player(
                8, "Sogaard M.",
                roster_position=None,
                player_position="G",
                shots_against=30,
                shots_saved=30,
                blocked=6,
                plus_minus=None)
        ])

        rating = _rate(players)
        player = rating["teams"][0]["players"][0]

        self.assertEqual(player["group"], "goalie")
        self.assertEqual(player["offense"], 0.0)
        self.assertEqual(player["defense"], 2.8)
        self.assertEqual(player["total"], 2.8)
        self.assertEqual(player["parts"]["goaltending"], 2.8)
        self.assertEqual(player["parts"]["blocks"], 0.0)
        self._assert_balanced(rating)

    def test_shots_against_mark_a_goalie_without_a_position(self) -> None:
        self.assertEqual(player_group(None, None, 12), "goalie")
        self.assertEqual(player_group("C", "G", None), "forward")
        self.assertEqual(player_group("D", "G", 0), "defense")
        self.assertEqual(player_group("G", "D", None), "goalie")

    def test_three_point_game_scores_3_3_and_away_team_is_second(
        self) -> None:
        players = pd.DataFrame([
            _rating_player(
                1, "Konecny T.",
                goals=1,
                assists=2,
                plus_minus=3,
                sog=4,
                roster_position="C"),
            _rating_player(
                2, "Batherson D.",
                assists=1,
                plus_minus=1,
                roster_position="C"),
            _rating_player(
                3, "Sanderson J.",
                assists=1,
                plus_minus=1,
                roster_position="C"),
            _rating_player(
                4, "Other O.",
                goals=2,
                plus_minus=2,
                sog=2),
            _rating_player(9, "Stranger S.", team_id=30, goals=5)
        ])
        events = pd.DataFrame([
            _event(
                1,
                GOAL_EVENT_ID,
                description="Batherson D. + Sanderson J."),
            _event(4, GOAL_EVENT_ID, description="Konecny T."),
            _event(4, GOAL_EVENT_ID, description="Konecny T.")
        ])

        rating = _rate(players, events)
        home = rating["teams"][0]
        away = rating["teams"][1]

        self.assertEqual(home["team_id"], HOME_TEAM_ID)
        self.assertEqual(home["team_name"], "Philadelphia Flyers")
        self.assertEqual(
            [row["player_id"] for row in home["players"]],
            [1, 2, 3, 4])
        self.assertEqual(away["team_id"], AWAY_TEAM_ID)
        self.assertEqual(away["team_name"], "Ottawa Senators")
        self.assertEqual(away["players"], [])
        konecny = home["players"][0]
        self.assertEqual(konecny["group"], "forward")
        self.assertEqual(konecny["offense"], 3.3)
        self.assertEqual(konecny["defense"], 0.0)
        self.assertEqual(konecny["total"], 3.3)
        self.assertEqual(konecny["parts"]["production"], 3.0)
        self.assertEqual(konecny["parts"]["shots"], 0.3)
        self.assertEqual(konecny["parts"]["goaltending"], 0.0)
        self.assertEqual(konecny["parts"]["goals_against"], 0.0)
        self.assertEqual(konecny["parts"]["empty_net"], 0.0)
        # Asysta w es_points, więc plus/minus nie dokłada gola.
        self.assertEqual(home["players"][1]["total"], 1.0)
        self.assertEqual(
            home["players"][1]["parts"]["teammate_goals"], 0.0)
        self.assertEqual(home["players"][2]["total"], 1.0)
        self._assert_balanced(rating)

    def test_negative_counters_stay_at_zero(self) -> None:
        players = pd.DataFrame([
            _rating_player(
                1, "Wing W.",
                roster_position="LW",
                goals=-1,
                assists=-2,
                sog=-3,
                shots_against=-4)
        ])

        rating = _rate(players)
        player = rating["teams"][0]["players"][0]

        self.assertEqual(player["group"], "forward")
        self.assertEqual(player["parts"]["production"], 0.0)
        self.assertEqual(player["parts"]["shots"], 0.0)
        self.assertEqual(player["parts"]["goaltending"], 0.0)
        self.assertEqual(player["total"], 0.0)
        self._assert_balanced(rating)


if __name__ == "__main__":
    unittest.main()
