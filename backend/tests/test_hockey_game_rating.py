"""Unit tests for hockey play-by-play credits."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.sports.hockey.game_rating import EventCredits
from backend.sports.hockey.game_rating import GOAL_EVENT_ID
from backend.sports.hockey.game_rating import attribute_events
from backend.sports.hockey.game_rating import normalize


def _player(
    player_id: int,
    player_name: str,
    team_id: int = 10,
    goals: int | None = 0,
    assists: int | None = 0,
    roster_position: str | None = None,
    player_position: str | None = None,
    shots_against: int | None = None) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "goals": goals,
        "assists": assists,
        "roster_position": roster_position,
        "player_position": player_position,
        "shots_against": shots_against
    }


def _event(
    player_id: int,
    event_id: int = 181,
    description: str | None = None,
    team_id: int = 10,
    pp_flag: int = 0,
    en_flag: int = 0) -> dict[str, object]:
    return {
        "event_id": event_id,
        "player_id": player_id,
        "team_id": team_id,
        "pp_flag": pp_flag,
        "en_flag": en_flag,
        "description": description
    }


def _credits(
    players: list[dict[str, object]],
    events: list[dict[str, object]] | None = None) -> dict[int, EventCredits]:
    if events is None:
        event_frame = pd.DataFrame()
    else:
        event_frame = pd.DataFrame(events)
    return attribute_events(pd.DataFrame(players), event_frame)


class TestNormalizePlayerName(unittest.TestCase):
    """Name keys used to match assist text to common names."""

    def test_normalize_drops_diacritics_case_and_extra_spaces(self) -> None:
        self.assertEqual(normalize("Stützle T."), normalize("Stutzle T."))
        self.assertEqual(normalize("Stutzle  T."), normalize("Stutzle T."))
        self.assertEqual(normalize("STUTZLE T."), normalize("stutzle t."))


class TestAttributeEvents(unittest.TestCase):
    """Even-strength points, empty-net goals and penalties."""

    def test_goal_event_id_is_the_scorer_event(self) -> None:
        self.assertEqual(GOAL_EVENT_ID, 181)

    def test_power_play_assists_do_not_raise_es_points(self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Sanderson J."),
                _player(3, "Halliday S.")
            ],
            [_event(
                1,
                description="Sanderson J. + Halliday S., W przewadze",
                pp_flag=1,
                en_flag=0)])

        zero = EventCredits(0, 0, 0, 0)
        self.assertEqual(credits[1], zero)
        self.assertEqual(credits[2], zero)
        self.assertEqual(credits[3], zero)

    def test_empty_net_goal_credits_scorer_and_same_team_assists(
            self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Armia J."),
                _player(3, "Haula E."),
                _player(4, "Haula E.", team_id=20)
            ],
            [_event(
                1,
                description="Armia J. + Haula E., Do pustej bramki",
                pp_flag=0,
                en_flag=1)])

        self.assertEqual(credits[1], EventCredits(1, 1, 0, 0))
        self.assertEqual(credits[2], EventCredits(1, 0, 0, 0))
        self.assertEqual(credits[3], EventCredits(1, 0, 0, 0))
        self.assertEqual(credits[4], EventCredits(0, 0, 0, 0))

    def test_power_play_empty_net_counts_only_the_empty_net(
            self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Armia J.")
            ],
            [_event(1, description="Armia J.", pp_flag=1, en_flag=1)])

        self.assertEqual(credits[1], EventCredits(0, 1, 0, 0))
        self.assertEqual(credits[2], EventCredits(0, 0, 0, 0))

    def test_diacritic_name_receives_the_assist(self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Stützle T.")
            ],
            [_event(1, description="Stutzle T.")])

        self.assertEqual(credits[2], EventCredits(1, 0, 0, 0))

    def test_unmatched_and_ambiguous_pieces_do_not_raise_es_points(
            self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Twin A."),
                _player(3, "Twin A.")
            ],
            [_event(1, description="Nobody N. + Twin A.")])

        self.assertEqual(credits[1], EventCredits(1, 0, 0, 0))
        self.assertEqual(credits[2], EventCredits(0, 0, 0, 0))
        self.assertEqual(credits[3], EventCredits(0, 0, 0, 0))

    def test_same_player_gets_one_assist_from_one_goal(self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S."),
                _player(2, "Bonk O.")
            ],
            [_event(1, description="Bonk O. + Bonk O.")])

        self.assertEqual(credits[2], EventCredits(1, 0, 0, 0))

    def test_boxscore_fallback_when_goal_events_are_missing(self) -> None:
        credits = _credits([
            _player(1, "Skater A.", assists=2),
            _player(2, "Goalie G.", assists=2, roster_position="G"),
            _player(3, "Null N.", goals=None, assists=None),
            _player(4, "Negative N.", goals=-2, assists=2),
            _player(5, "Backup G.", assists=2, player_position="G"),
            _player(6, "Shots G.", assists=2, shots_against=30)
        ])

        self.assertEqual(credits[1], EventCredits(2, 0, 0, 0))
        self.assertEqual(credits[2], EventCredits(0, 0, 0, 0))
        self.assertEqual(credits[3], EventCredits(0, 0, 0, 0))
        self.assertEqual(credits[4], EventCredits(2, 0, 0, 0))
        self.assertEqual(credits[5], EventCredits(0, 0, 0, 0))
        self.assertEqual(credits[6], EventCredits(0, 0, 0, 0))

    def test_one_goal_event_disables_fallback_for_other_players(
            self) -> None:
        credits = _credits(
            [
                _player(1, "Scorer S.", goals=5),
                _player(2, "Helper H.", assists=2)
            ],
            [_event(1, description=None)])

        self.assertEqual(credits[1], EventCredits(1, 0, 0, 0))
        self.assertEqual(credits[2], EventCredits(0, 0, 0, 0))

    def test_prop_goal_event_does_not_disable_the_fallback(self) -> None:
        credits = _credits(
            [_player(1, "Skater A.", assists=2)],
            [_event(1, event_id=196)])

        self.assertEqual(credits[1], EventCredits(2, 0, 0, 0))

    def test_penalties_count_without_goal_events(self) -> None:
        credits = _credits(
            [
                _player(1, "Skater A.", assists=2),
                _player(3, "Other O.")
            ],
            [
                _event(1, event_id=183),
                _event(1, event_id=183),
                _event(1, event_id=185),
                _event(1, event_id=186),
                _event(1, event_id=189),
                _event(3, event_id=184),
                _event(3, event_id=187),
                _event(3, event_id=188)
            ])

        self.assertEqual(credits[1], EventCredits(2, 0, 2, 1))
        self.assertEqual(credits[3], EventCredits(0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
