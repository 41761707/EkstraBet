"""Tests for season NHL power play and penalty kill totals."""

from __future__ import annotations

from backend.services.hockey_special_teams_service import (
    accumulate_special_teams,
    power_play_chances_from_penalties,
    power_play_opportunities)


def test_accuracy_recovers_chances_when_fouls_disagree() -> None:
    chances = power_play_opportunities(1, 33.33, 9)
    assert chances == 3


def test_two_goals_on_one_power_play_count_as_one_chance() -> None:
    chances = power_play_opportunities(2, 200.0, 9)
    assert chances == 1


def test_zero_accuracy_uses_opponent_fouls() -> None:
    assert power_play_opportunities(2, 0.0, 5) == 5
    assert power_play_opportunities(0, 0.0, 4) == 4
    assert power_play_opportunities(0, None, 4) == 4


def _match(
        home_goals: int,
        home_accuracy: float | None,
        away_fouls: int,
        away_goals: int,
        away_accuracy: float | None,
        home_fouls: int,
        home_id: int = 1,
        away_id: int = 2,
        home_name: str = "Alpha",
        away_name: str = "Bravo") -> dict:
    return {
        "home_team_id": home_id,
        "home_team_name": home_name,
        "home_team_shortcut": home_name[:3].upper(),
        "away_team_id": away_id,
        "away_team_name": away_name,
        "away_team_shortcut": away_name[:3].upper(),
        "home_pp_goals": home_goals,
        "away_pp_goals": away_goals,
        "home_pp_accuracy": home_accuracy,
        "away_pp_accuracy": away_accuracy,
        "home_fouls": home_fouls,
        "away_fouls": away_fouls
    }


def test_season_totals_are_not_an_average_of_match_percents() -> None:
    rows = accumulate_special_teams([
        _match(1, 50.0, 9, 0, 0.0, 4),
        _match(1, 100.0, 1, 0, 0.0, 2)
    ])
    alpha = rows[0]
    bravo = rows[1]
    assert alpha["team_name"] == "Alpha"
    assert alpha["pp_goals"] == 2
    assert alpha["pp_opportunities"] == 3
    assert alpha["pp_pct"] == 66.7
    assert alpha["pk_kills"] == 6
    assert alpha["pk_opportunities"] == 6
    assert alpha["pk_pct"] == 100.0
    assert alpha["hitchcock"] == 166.7
    assert alpha["matches_played"] == 2
    assert bravo["pp_goals"] == 0
    assert bravo["pp_opportunities"] == 6
    assert bravo["pp_pct"] == 0.0
    assert bravo["pk_kills"] == 1
    assert bravo["pk_opportunities"] == 3
    assert bravo["pk_pct"] == 33.3
    assert bravo["hitchcock"] == 33.3


def test_missing_chances_leave_rates_empty() -> None:
    rows = accumulate_special_teams([
        _match(0, None, 0, 0, None, 0, home_name="Empty", away_name="Also")
    ])
    assert rows[0]["pp_pct"] is None
    assert rows[0]["pk_pct"] is None
    assert rows[0]["hitchcock"] is None
    assert rows[1]["hitchcock"] is None


def test_higher_hitchcock_wins_and_name_ignores_case() -> None:
    rows = accumulate_special_teams([
        _match(
            1, 50.0, 4, 0, 0.0, 4,
            home_id=10, away_id=11,
            home_name="Zulu", away_name="Bravo"),
        _match(
            1, 50.0, 4, 0, 0.0, 4,
            home_id=12, away_id=13,
            home_name="alpha", away_name="Mike"),
        _match(
            1, 50.0, 4, 0, 0.0, 4,
            home_id=14, away_id=15,
            home_name="Alpha", away_name="Charlie")
    ])
    leaders = [
        row["team_name"]
        for row in rows
        if row["hitchcock"] == 150.0]
    assert leaders == ["alpha", "Alpha", "Zulu"]


def test_empty_sample_stays_empty() -> None:
    assert accumulate_special_teams([]) == []


def _penalty(
        team_id: int,
        event_id: int,
        description: str,
        period: int,
        event_time: str) -> dict:
    return {
        "team_id": team_id,
        "event_id": event_id,
        "description": description,
        "period": period,
        "event_time": event_time
    }


def test_coincidental_whistle_keeps_only_the_surplus() -> None:
    penalties = [
        _penalty(1, 183, "Niesportowe zachowanie", 2, "14:54"),
        _penalty(2, 183, "Niesportowe zachowanie", 2, "14:54"),
        _penalty(2, 183, "Atak kijem trzymanym oburącz", 2, "14:54"),
        _penalty(1, 185, "Walka na pięści", 3, "06:08"),
        _penalty(2, 185, "Walka na pięści", 3, "06:08")
    ]
    home_chances, away_chances = power_play_chances_from_penalties(
        penalties, 1, 2)
    assert home_chances == 1
    assert away_chances == 0


def test_one_sided_unsportsmanlike_minor_is_a_power_play() -> None:
    penalties = [
        _penalty(2, 183, "Niesportowe zachowanie", 1, "11:26")]
    home_chances, away_chances = power_play_chances_from_penalties(
        penalties, 1, 2)
    assert home_chances == 1
    assert away_chances == 0


def test_misconduct_and_final_horn_do_not_open_a_power_play() -> None:
    horn = _penalty(2, 183, "Spowodowanie upadku przeciwnika", 3, "19:59")
    misconduct = _penalty(2, 189, "Niesportowe zachowanie", 3, "09:51")
    carried = _penalty(2, 183, "Zahaczanie", 2, "20:00")
    overtime = _penalty(2, 183, "Zahaczanie", 3, "20:00")
    closed = power_play_chances_from_penalties(
        [horn, misconduct], 1, 2)
    assert closed == (0, 0)
    assert power_play_chances_from_penalties([carried], 1, 2) == (1, 0)
    overtime_chances = power_play_chances_from_penalties(
        [overtime], 1, 2, went_to_extra_time=True)
    assert overtime_chances == (1, 0)


def _anaheim_boston_penalties() -> list[dict]:
    boston = [
        _penalty(2, 183, "Spowodowanie upadku przeciwnika", 1, "01:14"),
        _penalty(2, 183, "Spowodowanie upadku przeciwnika", 2, "09:24"),
        _penalty(2, 183, "Nadmierna ostrość w grze", 2, "19:00"),
        _penalty(2, 183, "Atak łokciem", 2, "19:00"),
        _penalty(2, 183, "Zahaczanie", 3, "11:19"),
        _penalty(2, 183, "Spowodowanie upadku przeciwnika", 3, "19:59")
    ]
    anaheim = [
        _penalty(1, 183, "Trzymanie przeciwnika", 2, "01:34"),
        _penalty(1, 183, "Przeszkadzanie", 3, "02:22"),
        _penalty(1, 183, "Zahaczanie", 3, "07:34"),
        _penalty(1, 183, "Przeszkadzanie", 3, "17:43")
    ]
    return anaheim + boston


def _anaheim_boston_match() -> dict:
    return _match(
        0, 0.0, 6, 3, 75.0, 4,
        home_id=1, away_id=2,
        home_name="Anaheim Ducks", away_name="Boston Bruins")


def test_final_horn_penalty_is_dropped_from_the_kill_count() -> None:
    """The 19:59 trip is the horn, so it is not a penalty kill."""
    match = _anaheim_boston_match()
    match["penalties"] = _anaheim_boston_penalties()
    match["went_to_extra_time"] = False
    counted = {
        row["team_name"]: row
        for row in accumulate_special_teams([match])}
    boston = counted["Boston Bruins"]
    anaheim = counted["Anaheim Ducks"]
    assert boston["pp_opportunities"] == 4
    assert boston["pk_opportunities"] == 5
    assert boston["pk_kills"] == 5
    assert anaheim["pp_opportunities"] == 5


def test_short_penalty_list_still_beats_the_foul_column() -> None:
    match = _anaheim_boston_match()
    match["penalties"] = _anaheim_boston_penalties()[:-1]
    match["went_to_extra_time"] = False
    counted = {
        row["team_name"]: row
        for row in accumulate_special_teams([match])}
    assert counted["Boston Bruins"]["pk_opportunities"] == 5


def test_halfway_kill_percent_rounds_the_way_nhl_prints_it() -> None:
    penalties = []
    for index in range(32):
        clock = f"{index // 60:02d}:{index % 60:02d}"
        penalties.append(_penalty(1, 183, "Zahaczanie", 1, clock))
    match = _match(
        0, 0.0, 0, 6, 0.0, 32,
        home_id=1, away_id=2,
        home_name="Boston Bruins", away_name="Opponent")
    match["penalties"] = penalties
    match["went_to_extra_time"] = False
    counted = {
        row["team_name"]: row
        for row in accumulate_special_teams([match])}
    assert counted["Boston Bruins"]["pk_kills"] == 26
    assert counted["Boston Bruins"]["pk_opportunities"] == 32
    assert counted["Boston Bruins"]["pk_pct"] == 81.3


def test_empty_penalty_list_keeps_the_foul_fallback() -> None:
    match = _anaheim_boston_match()
    match["penalties"] = []
    match["went_to_extra_time"] = False
    counted = {
        row["team_name"]: row
        for row in accumulate_special_teams([match])}
    assert counted["Boston Bruins"]["pk_opportunities"] == 6
