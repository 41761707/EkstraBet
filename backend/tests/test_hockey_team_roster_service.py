"""Tests for the current NHL team roster grouping and season stats."""

from __future__ import annotations

import pandas as pd
import pytest

from api.schemas.hockey_team_roster import HockeyTeamRosterResponse
from backend.services.hockey_team_roster_service import (
    HockeyRosterUnavailableError)
from backend.services.hockey_team_roster_service import (
    build_hockey_team_roster)
from backend.services.hockey_team_roster_service import get_hockey_team_roster

TEAM_ID = 870


def test_empty_roster_lines_use_last_match_slots() -> None:
    roster = _roster_frame([
        _roster(player_id=1, common_name="Center A.", player_position="C"),
        _roster(player_id=2, common_name="Wing L.", player_position="LW"),
        _roster(player_id=3, common_name="Wing R.", player_position="RW"),
        _roster(player_id=4, common_name="Defence D.", player_position="D"),
        _roster(player_id=5, common_name="Goalie G.", player_position="G"),
        _roster(player_id=6, common_name="Scratch S.", player_position="C")])
    last_match = _match_frame([
        _match(player_id=1, position="C", line=1, number=19),
        _match(player_id=2, position="LW", line=1, number=17),
        _match(player_id=3, position="RW", line=1, number=86),
        _match(player_id=4, position="D", line=1, number=8),
        _match(player_id=5, position="G", line=1, number=90)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Columbus Blue Jackets", roster, last_match, _empty_stats())

    assert _ids(payload, "F1") == [2, 1, 3]
    assert _ids(payload, "D1") == [4]
    assert _ids(payload, "G") == [5]
    assert _ids(payload, "F2") == [6]
    assert "outside" not in _group_ids(payload)
    promoted = _players(payload, "F2")[0]
    assert promoted["in_last_lineup"] is False
    assert promoted["line"] == 2
    HockeyTeamRosterResponse.model_validate(payload)


def test_roster_line_overrides_the_last_match_slot() -> None:
    roster = _roster_frame([
        _roster(
            player_id=1,
            common_name="Center A.",
            player_position="C",
            roster_line=1)])
    last_match = _match_frame([
        _match(player_id=1, position="C", line=4, number=19)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, _empty_stats())

    assert _ids(payload, "F1") == [1]
    assert "F4" not in _group_ids(payload)
    assert _players(payload, "F1")[0]["line"] == 1
    assert _players(payload, "F1")[0]["number"] == 19


def test_roster_line_places_a_player_missing_from_the_last_match() -> None:
    roster = _roster_frame([
        _roster(
            player_id=1,
            common_name="Scratch S.",
            roster_position="C",
            roster_line=1),
        _roster(
            player_id=2,
            common_name="No Line N.",
            player_position="LW")])
    payload = build_hockey_team_roster(
        TEAM_ID,
        "Jackets",
        roster,
        _match_frame([]),
        _empty_stats())

    assert _ids(payload, "F1") == [2, 1]
    placed = _players(payload, "F1")[0]
    assert placed["player_id"] == 2
    assert placed["line"] == 1
    assert placed["in_last_lineup"] is False
    assert "outside" not in _group_ids(payload)


def test_injured_player_leaves_the_line_and_keeps_the_badge() -> None:
    roster = _roster_frame([
        _roster(
            player_id=1,
            common_name="Center A.",
            player_position="C",
            is_injured=1,
            injury_status="IR",
            injury_note="Upper body")])
    last_match = _match_frame([
        _match(player_id=1, position="C", line=1, number=19)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, _empty_stats())

    assert _group_ids(payload) == ["injured"]
    injured = _players(payload, "injured")[0]
    assert injured["is_injured"] is True
    assert injured["injury_status"] == "IR"
    assert injured["injury_note"] == "Upper body"
    assert injured["line"] == 1
    assert payload["injured_players"] == 1
    assert payload["forwards"][0]["player_id"] == 1


def test_season_stats_cover_skaters_and_goalies() -> None:
    roster = _roster_frame([
        _roster(player_id=1, common_name="Center A.", player_position="C"),
        _roster(player_id=5, common_name="Goalie G.", player_position="G")])
    last_match = _match_frame([
        _match(player_id=1, position="C", line=1, number=19),
        _match(player_id=5, position="G", line=1, number=90)])
    stats = pd.DataFrame([
        _stat(1, goals=1, assists=1, points=2, sog=3, toi="20:00"),
        _stat(1, goals=0, assists=2, points=2, sog=4, toi="10:00"),
        _stat(
            5,
            toi="60:00",
            shots_against=20,
            shots_saved=18),
        _stat(
            5,
            toi="30:00",
            shots_against=10,
            shots_saved=9)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, stats)

    skater = _players(payload, "F1")[0]
    assert skater["games_played"] == 2
    assert skater["goals"] == 1
    assert skater["assists"] == 3
    assert skater["points"] == 4
    assert skater["shots_on_goal"] == 7
    assert skater["average_toi"] == "15:00"
    assert skater["save_percentage"] is None
    assert skater["goals_against_average"] is None

    goalie = _players(payload, "G")[0]
    assert goalie["games_played"] == 2
    assert goalie["average_toi"] == "45:00"
    assert goalie["save_percentage"] == 90.0
    assert goalie["goals_against_average"] == 2.0


def test_open_forward_seat_takes_the_fourth_line_before_a_scratch() -> None:
    roster = _roster_frame([
        _roster(player_id=11, common_name="Left L.", player_position="LW"),
        _roster(player_id=12, common_name="Center C.", player_position="C"),
        _roster(player_id=13, common_name="Right R.", player_position="RW"),
        _roster(player_id=21, common_name="Left Two", player_position="LW"),
        _roster(player_id=22, common_name="Center Two", player_position="C"),
        _roster(player_id=41, common_name="Fourth F.", player_position="RW"),
        _roster(player_id=51, common_name="Scratch S.", player_position="C")])
    last_match = _match_frame([
        _match(player_id=11, position="LW", line=1, number=11),
        _match(player_id=12, position="C", line=1, number=12),
        _match(player_id=13, position="RW", line=1, number=13),
        _match(player_id=21, position="LW", line=2, number=21),
        _match(player_id=22, position="C", line=2, number=22),
        _match(player_id=41, position="RW", line=4, number=41)])
    stats = pd.DataFrame([
        _stat(41, toi="14:00"),
        _stat(51, toi="20:00")])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, stats)

    assert _ids(payload, "F1") == [11, 12, 13]
    assert _ids(payload, "F2") == [21, 22, 41]
    assert _players(payload, "F2")[2]["line"] == 2
    assert _ids(payload, "F3") == [51]
    assert _players(payload, "F3")[0]["line"] == 3
    assert "F4" not in _group_ids(payload)
    assert "outside" not in _group_ids(payload)


def test_full_top_lines_keep_the_fourth_line_and_scratches() -> None:
    rows: list[dict] = []
    matches: list[dict] = []
    for line in (1, 2, 3):
        for index, position in enumerate(("LW", "C", "RW")):
            player_id = line * 10 + index
            rows.append(_roster(
                player_id=player_id,
                common_name=f"F{line}{position}",
                player_position=position))
            matches.append(_match(
                player_id=player_id,
                position=position,
                line=line,
                number=player_id))
    rows.append(_roster(
        player_id=40,
        common_name="Fourth F.",
        player_position="C"))
    matches.append(_match(
        player_id=40, position="C", line=4, number=40))
    rows.append(_roster(
        player_id=50,
        common_name="Scratch S.",
        player_position="LW"))

    payload = build_hockey_team_roster(
        TEAM_ID,
        "Jackets",
        _roster_frame(rows),
        _match_frame(matches),
        _empty_stats())

    assert len(_players(payload, "F1")) == 3
    assert len(_players(payload, "F2")) == 3
    assert len(_players(payload, "F3")) == 3
    assert _ids(payload, "F4") == [40]
    assert _ids(payload, "outside") == [50]


def test_short_defense_pair_fills_from_a_healthy_scratch() -> None:
    roster = _roster_frame([
        _roster(player_id=4, common_name="Defence D.", player_position="D"),
        _roster(player_id=7, common_name="Extra D.", player_position="D")])
    last_match = _match_frame([
        _match(player_id=4, position="D", line=1, number=8)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, _empty_stats())

    assert _ids(payload, "D1") == [4, 7]
    assert _players(payload, "D1")[1]["line"] == 1
    assert "outside" not in _group_ids(payload)


def test_injured_forward_does_not_fill_an_open_seat() -> None:
    roster = _roster_frame([
        _roster(player_id=1, common_name="Center A.", player_position="C"),
        _roster(player_id=2, common_name="Wing L.", player_position="LW"),
        _roster(
            player_id=3,
            common_name="Hurt H.",
            player_position="RW",
            is_injured=1,
            injury_note="Upper body")])
    last_match = _match_frame([
        _match(player_id=1, position="C", line=1, number=19),
        _match(player_id=2, position="LW", line=1, number=17),
        _match(player_id=3, position="RW", line=1, number=86)])

    payload = build_hockey_team_roster(
        TEAM_ID, "Jackets", roster, last_match, _empty_stats())

    assert _ids(payload, "F1") == [2, 1]
    assert _ids(payload, "injured") == [3]
    assert len(_players(payload, "F1")) == 2


def test_missing_team_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.services.hockey_team_roster_service"
        ".team_repository.fetch_team_by_id",
        lambda team_id: pd.DataFrame())

    assert get_hockey_team_roster(99999) is None


def test_non_hockey_team_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.services.hockey_team_roster_service"
        ".team_repository.fetch_team_by_id",
        lambda team_id: pd.DataFrame([{
            "name": "Legia",
            "sport_id": 1}]))

    with pytest.raises(HockeyRosterUnavailableError):
        get_hockey_team_roster(1)


def _ids(payload: dict, group_id: str) -> list[int]:
    return [player["player_id"] for player in _players(payload, group_id)]


def _players(payload: dict, group_id: str) -> list[dict]:
    for group in payload["groups"]:
        if group["group_id"] == group_id:
            return group["players"]
    raise AssertionError(f"Missing group {group_id}")


def _group_ids(payload: dict) -> list[str]:
    return [group["group_id"] for group in payload["groups"]]


def _roster_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _match_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[
            "match_id",
            "player_id",
            "team_id",
            "position",
            "line",
            "number",
            "toi"])
    return pd.DataFrame(rows)


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "player_id",
        "goals",
        "assists",
        "points",
        "sog",
        "toi",
        "shots_against",
        "shots_saved"])


def _roster(
        player_id: int,
        common_name: str,
        player_position: str | None = None,
        roster_position: str | None = None,
        roster_line: int | None = None,
        is_injured: int = 0,
        injury_status: str | None = None,
        injury_note: str | None = None) -> dict:
    return {
        "player_id": player_id,
        "first_name": common_name.split(" ")[0],
        "last_name": "Player",
        "common_name": common_name,
        "country_name": "Canada",
        "roster_position": roster_position,
        "player_position": player_position,
        "roster_line": roster_line,
        "roster_number": None,
        "is_injured": is_injured,
        "injury_status": injury_status,
        "injury_note": injury_note
    }


def _match(
        player_id: int,
        position: str,
        line: int,
        number: int) -> dict:
    return {
        "match_id": 10,
        "player_id": player_id,
        "team_id": TEAM_ID,
        "position": position,
        "line": line,
        "number": number,
        "toi": "18:00"
    }


def _stat(
        player_id: int,
        goals: int = 0,
        assists: int = 0,
        points: int = 0,
        sog: int = 0,
        toi: str = "0:00",
        shots_against: int = 0,
        shots_saved: int = 0) -> dict:
    return {
        "player_id": player_id,
        "goals": goals,
        "assists": assists,
        "points": points,
        "sog": sog,
        "toi": toi,
        "shots_against": shots_against,
        "shots_saved": shots_saved
    }
