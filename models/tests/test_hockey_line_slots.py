"""Line slots from position and line, with as-of slot ice time."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd
import pytest

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.line_slots import LineSlotResolver
from models.pipeline.features.hockey.line_slots import SlotToiConfig


def test_line_and_position_name_the_slot() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 60, start),
        _player(2, 11, "D", 1, 60, start),
        _player(3, 12, "LW", 4, 60, start),
        _player(4, 13, "C", 4, 1200, start),
        _player(5, 14, "RW", 4, 30, start),
        _player(6, 15, "G", 1, 3600, start)])
    assigned = LineSlotResolver().assign(rows)
    slots = dict(zip(assigned["player_id"], assigned["slot"]))
    assert slots[10] == "F1"
    assert slots[11] == "D1"
    assert slots[12] == "F4"
    assert slots[13] == "F4"
    assert slots[14] == "F4"
    assert slots[15] == "G"


def test_labeled_line_beats_time_on_ice() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 30, start),
        _player(1, 11, "C", 4, 2000, start)])
    assigned = LineSlotResolver().assign(rows)
    slots = dict(zip(assigned["player_id"], assigned["slot"]))
    assert slots[10] == "F1"
    assert slots[11] == "F4"


def test_missing_line_is_filled_by_toi_rank() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 600, start),
        _player(1, 11, "LW", 1, 600, start),
        _player(1, 20, "C", None, 1500, start),
        _player(1, 21, "RW", None, 400, start)])
    assigned = LineSlotResolver().assign(rows)
    slots = dict(zip(assigned["player_id"], assigned["slot"]))
    assert slots[10] == "F1"
    assert slots[11] == "F1"
    assert slots[20] == "F1"
    assert slots[21] == "F2"


def test_fourth_line_defence_label_is_not_rewritten() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rows = pd.DataFrame([
        _player(1, 10, "D", 4, 700, start)])
    assigned = LineSlotResolver().assign(rows)
    assert assigned.loc[0, "slot"] == "D1"
    assert assigned.loc[0, "slot"] != "F4"


def test_slot_toi_is_as_of_and_resets_to_last_season_mean() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    later = start + timedelta(days=2)
    nxt = start + timedelta(days=10)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 600, start, season=1),
        _player(2, 10, "C", 1, 600, later, season=1),
        _player(3, 10, "C", 1, 600, nxt, season=2)])
    resolver = LineSlotResolver(_minutes_config(20.0))
    toi = resolver.build_slot_toi(resolver.assign(rows))
    by_match = toi.set_index("match_id")["slot_toi_minutes"]
    assert by_match.loc[1] == pytest.approx(20.0)
    assert by_match.loc[2] == pytest.approx(17.5)
    # Średnia obserwacji sezonu 1 to 10 min, nie EWMA 17.5.
    assert by_match.loc[3] == pytest.approx(10.0)


def test_same_night_does_not_leak_into_slot_toi() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    nxt = start + timedelta(days=1)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 600, start, team_id=1),
        _player(2, 20, "C", 1, 1800, start, team_id=2),
        _player(3, 10, "C", 1, 600, nxt, team_id=1),
        _player(4, 20, "C", 1, 1800, nxt, team_id=2)])
    resolver = LineSlotResolver(_minutes_config(20.0))
    toi = resolver.build_slot_toi(resolver.assign(rows))
    opening = toi.loc[toi["match_id"].isin([1, 2]), "slot_toi_minutes"]
    assert list(opening) == pytest.approx([20.0, 20.0])
    follow = toi.set_index("match_id")["slot_toi_minutes"]
    assert follow.loc[3] == pytest.approx(17.5)
    assert follow.loc[4] == pytest.approx(22.5)


def test_flat_early_season_moves_slot_toi_less() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rows = pd.DataFrame([
        _player(1, 10, "C", 1, 600, start),
        _player(2, 10, "C", 1, 600, start + timedelta(days=1))])
    boosted = _second_game_minutes(rows, EarlySeasonConfig())
    flat = _second_game_minutes(
        rows, EarlySeasonConfig(boost=1.0))
    assert flat == pytest.approx(19.0)
    assert boosted == pytest.approx(17.5)
    assert boosted < flat


def _second_game_minutes(
        rows: pd.DataFrame,
        early_season: EarlySeasonConfig) -> float:
    config = _minutes_config(20.0, early_season)
    resolver = LineSlotResolver(config)
    toi = resolver.build_slot_toi(resolver.assign(rows))
    return float(toi.loc[toi["match_id"] == 2, "slot_toi_minutes"].iloc[0])


def _minutes_config(
        f1_minutes: float,
        early_season: EarlySeasonConfig | None = None) -> SlotToiConfig:
    return SlotToiConfig(
        initial_minutes={"F1": f1_minutes},
        early_season=early_season or EarlySeasonConfig())


def _player(
        match_id: int,
        player_id: int,
        position: str,
        line: int | None,
        toi_seconds: int,
        game_date: datetime,
        season: int = 1,
        team_id: int = 7) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "position": position,
        "line": line,
        "toi_seconds": toi_seconds,
        "game_date": game_date,
        "season": season
    }
