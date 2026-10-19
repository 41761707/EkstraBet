"""Synthetic NHL schedule features: rest, B2B, travel and time zones."""

from __future__ import annotations

import pandas as pd
import pytest

from models.pipeline.features.hockey.schedule import (
    SCHEDULE_FEATURE_COLUMNS)
from models.pipeline.features.hockey.schedule import (
    build_schedule_features)

EAST_TEAM = 1
WEST_TEAM = 2
OTHER_TEAM = 3
NY_TO_LA_KM = 3923.607


def test_back_to_back_uses_arena_local_date() -> None:
    """Treat one Warsaw calendar day as two New York dates.

    2025-01-12 01:00 Europe/Warsaw is 19:00 EST on January 11.
    2025-01-12 18:00 Europe/Warsaw is 12:00 EST on January 12.
    """
    matches = pd.DataFrame([
        _match(2, "2025-01-12 18:00", EAST_TEAM, WEST_TEAM),
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM)])
    result = build_schedule_features(matches, _arenas())
    assert list(result["match_id"]) == [2, 1]
    assert _value(result, 1, "home_rest_days") == 0.0
    assert _value(result, 1, "home_is_b2b") == 0.0
    assert _value(result, 1, "home_games_last_4_days") == 1.0
    assert _value(result, 1, "home_series_index") == 1.0
    assert _value(result, 1, "home_travel_km") == 0.0
    assert _value(result, 2, "home_rest_days") == 1.0
    assert _value(result, 2, "home_is_b2b") == 1.0
    assert _value(result, 2, "home_is_b2b_road") == 0.0
    assert _value(result, 2, "away_is_b2b") == 1.0
    assert _value(result, 2, "away_is_b2b_road") == 1.0
    assert _value(result, 2, "home_games_last_4_days") == 2.0
    assert _value(result, 2, "home_series_index") == 2.0
    assert _value(result, 2, "away_series_index") == 2.0


def test_three_games_in_four_local_days() -> None:
    matches = pd.DataFrame([
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM),
        _match(2, "2025-01-14 01:00", EAST_TEAM, WEST_TEAM),
        _match(3, "2025-01-15 01:00", EAST_TEAM, WEST_TEAM)])
    result = build_schedule_features(matches, _arenas())
    assert _value(result, 2, "home_rest_days") == 2.0
    assert _value(result, 2, "home_is_b2b") == 0.0
    assert _value(result, 2, "home_games_last_4_days") == 2.0
    assert _value(result, 3, "home_rest_days") == 1.0
    assert _value(result, 3, "home_is_b2b") == 1.0
    assert _value(result, 3, "home_games_last_4_days") == 3.0
    assert _value(result, 3, "home_games_last_7_days") == 3.0
    assert _value(result, 3, "home_series_index") == 3.0


def test_road_trip_travel_and_timezone_shift() -> None:
    matches = pd.DataFrame([
        _match(1, "2025-01-15 01:00", EAST_TEAM, WEST_TEAM, season=1),
        _match(2, "2025-01-17 04:00", WEST_TEAM, EAST_TEAM, season=1),
        _match(3, "2025-01-18 04:00", WEST_TEAM, EAST_TEAM, season=1),
        _match(4, "2025-01-19 01:00", EAST_TEAM, WEST_TEAM, season=1)])
    result = build_schedule_features(matches, _arenas())
    assert _value(result, 2, "away_series_index") == 1.0
    assert _value(result, 2, "away_rest_days") == 2.0
    assert _value(result, 2, "away_is_b2b") == 0.0
    assert _value(result, 2, "away_travel_km") == pytest.approx(NY_TO_LA_KM)
    assert _value(result, 2, "away_tz_shift_hours") == -3.0
    assert _value(result, 2, "home_travel_km") == pytest.approx(NY_TO_LA_KM)
    assert _value(result, 2, "home_tz_shift_hours") == -3.0
    assert _value(result, 3, "away_series_index") == 2.0
    assert _value(result, 3, "away_is_b2b") == 1.0
    assert _value(result, 3, "away_is_b2b_road") == 1.0
    assert _value(result, 3, "home_is_b2b") == 1.0
    assert _value(result, 3, "home_is_b2b_road") == 0.0
    assert _value(result, 3, "away_travel_km") == 0.0
    assert _value(result, 3, "away_tz_shift_hours") == 0.0
    assert _value(result, 3, "home_series_index") == 2.0
    assert _value(result, 4, "home_tz_shift_hours") == 3.0
    assert _value(result, 4, "home_travel_km") == pytest.approx(
        NY_TO_LA_KM)
    assert _value(result, 4, "home_is_b2b") == 1.0
    assert _value(result, 4, "home_is_b2b_road") == 0.0
    assert _value(result, 4, "home_series_index") == 1.0


def test_series_index_resets_when_season_changes() -> None:
    matches = pd.DataFrame([
        _match(1, "2025-04-15 01:00", EAST_TEAM, WEST_TEAM, season=1),
        _match(2, "2025-04-16 01:00", EAST_TEAM, WEST_TEAM, season=1),
        _match(3, "2025-10-08 01:00", EAST_TEAM, WEST_TEAM, season=2)])
    result = build_schedule_features(matches, _arenas())
    assert _value(result, 2, "home_series_index") == 2.0
    assert _value(result, 3, "home_series_index") == 1.0


def test_postponed_match_does_not_count_as_history() -> None:
    matches = pd.DataFrame([
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM, result="1"),
        _match(2, "2025-01-13 01:00", EAST_TEAM, WEST_TEAM, result="0"),
        _match(3, "2025-01-15 01:00", EAST_TEAM, WEST_TEAM, result="1")])
    result = build_schedule_features(matches, _arenas())
    assert _value(result, 3, "home_rest_days") == 3.0
    assert _value(result, 3, "home_is_b2b") == 0.0
    assert _value(result, 3, "home_games_last_4_days") == 2.0
    assert _value(result, 3, "home_series_index") == 2.0


def test_later_match_does_not_change_earlier_features() -> None:
    early = pd.DataFrame([
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM),
        _match(2, "2025-01-14 01:00", EAST_TEAM, WEST_TEAM)])
    later = pd.concat([
        early,
        pd.DataFrame([
            _match(3, "2025-01-15 01:00", EAST_TEAM, WEST_TEAM)])],
        ignore_index=True)
    baseline = build_schedule_features(early, _arenas())
    expanded = build_schedule_features(later, _arenas())
    kept = expanded.loc[expanded["match_id"].isin([1, 2])]
    kept = kept.reset_index(drop=True)
    pd.testing.assert_frame_equal(baseline, kept)


def test_feature_diffs_are_home_minus_away() -> None:
    matches = pd.DataFrame([
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM),
        _match(2, "2025-01-13 01:00", EAST_TEAM, OTHER_TEAM)])
    result = build_schedule_features(matches, _arenas())
    assert _value(result, 2, "home_rest_days") == 1.0
    assert _value(result, 2, "away_rest_days") == 0.0
    assert _value(result, 2, "rest_days_diff") == 1.0
    assert _value(result, 2, "is_b2b_diff") == 1.0


def test_empty_matches_keep_the_column_contract() -> None:
    result = build_schedule_features(
        pd.DataFrame(columns=_MATCH_COLUMNS),
        _arenas())
    assert list(result.columns) == ["match_id", *SCHEDULE_FEATURE_COLUMNS]
    assert result.empty


def test_missing_match_column_raises() -> None:
    with pytest.raises(KeyError, match="game_date"):
        build_schedule_features(
            pd.DataFrame({"match_id": [1]}),
            _arenas())


def test_missing_arena_keeps_zero_travel(
        caplog: pytest.LogCaptureFixture) -> None:
    matches = pd.DataFrame([
        _match(1, "2025-01-12 01:00", EAST_TEAM, WEST_TEAM),
        _match(2, "2025-01-13 01:00", EAST_TEAM, WEST_TEAM)])
    with caplog.at_level("WARNING"):
        result = build_schedule_features(matches, _arenas().iloc[0:0])
    assert _value(result, 2, "home_travel_km") == 0.0
    assert _value(result, 2, "home_tz_shift_hours") == 0.0
    assert "team_id=1" in caplog.text


_MATCH_COLUMNS = [
    "match_id",
    "home_team",
    "away_team",
    "game_date"]


def _arenas() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "team_id": EAST_TEAM,
            "latitude": 40.0,
            "longitude": -74.0,
            "timezone": "America/New_York"},
        {
            "team_id": WEST_TEAM,
            "latitude": 34.0,
            "longitude": -118.0,
            "timezone": "America/Los_Angeles"},
        {
            "team_id": OTHER_TEAM,
            "latitude": 41.0,
            "longitude": -87.0,
            "timezone": "America/Chicago"}])


def _match(
        match_id: int,
        game_date: str,
        home_team: int,
        away_team: int,
        season: int | None = None,
        result: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "game_date": game_date}
    if season is not None:
        row["season"] = season
    if result is not None:
        row["result"] = result
    return row


def _value(frame: pd.DataFrame, match_id: int, column: str) -> float:
    matched = frame.loc[frame["match_id"] == match_id, column]
    assert len(matched) == 1
    return float(matched.iloc[0])
