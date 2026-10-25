"""Pre-match feature formulas, allowlist, and schema fingerprint."""

from __future__ import annotations

import hashlib
import inspect
import math
from datetime import datetime

import pandas as pd
import pytest

from models.pipeline.betting import features as feature_module
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import POST_MATCH_DENYLIST
from models.pipeline.betting.features import build_candidate_features
from models.pipeline.betting.features import feature_schema_fingerprint


def _row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": datetime(2026, 8, 1, 18, 0),
        "value_pct": 50.0,
        "odds": 2.0,
        "devig_probability": None}
    payload.update(overrides)
    return payload


def _features(rows: list[dict[str, object]]) -> pd.DataFrame:
    return build_candidate_features(pd.DataFrame(rows))


def _clock_distance(left: pd.Series, right: pd.Series, prefix: str) -> float:
    return math.hypot(
        left[f"{prefix}_sin"] - right[f"{prefix}_sin"],
        left[f"{prefix}_cos"] - right[f"{prefix}_cos"])


def test_even_money_probability_implied_edge_and_ev() -> None:
    kickoff = datetime(2026, 8, 1, 18, 0)
    frame = _features([_row()])
    row = frame.iloc[0]
    assert row["model_probability"] == pytest.approx(0.5)
    assert row["implied_probability"] == pytest.approx(0.5)
    assert row["edge"] == pytest.approx(0.0)
    assert row["ev"] == pytest.approx(0.0)
    assert math.isnan(row["devig_probability"])
    assert row["market_family"] == "REZULTAT"
    assert row["league_id"] == "12"
    assert row["model_id"] == "8"
    turn = 2.0 * math.pi
    weekday = kickoff.weekday()
    assert row["kickoff_weekday_sin"] == pytest.approx(
        math.sin(turn * weekday / 7.0))
    assert row["kickoff_weekday_cos"] == pytest.approx(
        math.cos(turn * weekday / 7.0))
    assert row["kickoff_hour_sin"] == pytest.approx(math.sin(turn * 18 / 24.0))
    assert row["kickoff_hour_cos"] == pytest.approx(math.cos(turn * 18 / 24.0))


def test_edge_and_ev_use_the_raw_price() -> None:
    frame = _features([_row(value_pct=60.0, odds=2.0)])
    row = frame.iloc[0]
    assert row["model_probability"] == pytest.approx(0.6)
    assert row["implied_probability"] == pytest.approx(0.5)
    assert row["edge"] == pytest.approx(0.1)
    assert row["ev"] == pytest.approx(0.2)


def test_copies_fair_probability_and_does_not_rebuild_it() -> None:
    kept = _features([_row(devig_probability=3.0 / 7.0)])
    assert kept["devig_probability"].iloc[0] == pytest.approx(3.0 / 7.0)
    mixed = _features([
        _row(event_id=1, bookmaker_id=4, odds=2.0, prediction_id=1),
        _row(event_id=2, bookmaker_id=5, odds=3.0, prediction_id=2),
        _row(event_id=3, bookmaker_id=6, odds=3.0, prediction_id=3)])
    assert mixed["devig_probability"].isna().all()
    invalid = _features([
        _row(devig_probability=1.5, prediction_id=4),
        _row(devig_probability=0.0, prediction_id=5),
        _row(devig_probability=-0.2, prediction_id=6)])
    assert invalid["devig_probability"].isna().all()
    assert len(invalid) == 3


def test_market_family_comes_from_the_event_id() -> None:
    rows = [
        _row(event_id=1, prediction_id=1),
        _row(event_id=6, prediction_id=2),
        _row(event_id=8, prediction_id=3),
        _row(event_id=173, prediction_id=4),
        _row(event_id=174, prediction_id=5),
        _row(event_id=198, prediction_id=6),
        _row(event_id=49, prediction_id=7),
        _row(event_id=999, prediction_id=8),
        _row(league_id=None, prediction_id=9)]
    frame = _features(rows)
    assert list(frame["market_family"]) == [
        "REZULTAT",
        "BTTS",
        "OU",
        "GOALS",
        "GOALS",
        "EXACT",
        None,
        None,
        "REZULTAT"]
    assert frame["league_id"].iloc[-1] is None


def test_drops_invalid_probability_and_price() -> None:
    frame = pd.DataFrame([
        _row(prediction_id=1, value_pct=40.0),
        _row(prediction_id=2, odds=1.0),
        _row(prediction_id=3, odds=0.5),
        _row(prediction_id=4, value_pct=100.1),
        _row(prediction_id=5, value_pct=-0.1),
        _row(prediction_id=6, value_pct=float("nan")),
        _row(prediction_id=7, odds=float("inf")),
        _row(prediction_id=8, value_pct=0.0, odds=1.01),
        _row(prediction_id=9, value_pct=100.0, odds=1.5)])
    result = build_candidate_features(frame)
    assert list(result.index) == [0, 7, 8]
    assert result["model_probability"].iloc[1] == pytest.approx(0.0)
    assert result["model_probability"].iloc[2] == pytest.approx(1.0)


def test_extreme_odds_stay_finite() -> None:
    tiny = _features([_row(value_pct=0.0, odds=1.0000001)]).iloc[0]
    huge = _features([_row(value_pct=100.0, odds=1_000_000.0)]).iloc[0]
    for row in (tiny, huge):
        assert math.isfinite(row["implied_probability"])
        assert math.isfinite(row["edge"])
        assert math.isfinite(row["ev"])
    assert tiny["ev"] == pytest.approx(-1.0)
    assert huge["implied_probability"] == pytest.approx(1e-6)
    assert huge["ev"] == pytest.approx(1_000_000.0 - 1.0)


def test_missing_kickoff_leaves_the_clock_empty() -> None:
    frame = _features([
        _row(kickoff=None),
        _row(kickoff="not-a-date", prediction_id=11)])
    for name in (
            "kickoff_weekday_sin",
            "kickoff_weekday_cos",
            "kickoff_hour_sin",
            "kickoff_hour_cos"):
        assert frame[name].isna().all()
    assert frame["model_probability"].iloc[0] == pytest.approx(0.5)


def test_weekday_and_hour_wrap_around() -> None:
    monday = _features([_row(kickoff=datetime(2026, 8, 3, 0, 0))]).iloc[0]
    sunday = _features([_row(kickoff=datetime(2026, 8, 2, 0, 0))]).iloc[0]
    wednesday = _features([_row(kickoff=datetime(2026, 8, 5, 12, 0))]).iloc[0]
    hour_zero = _features([_row(kickoff=datetime(2026, 8, 3, 0, 0))]).iloc[0]
    hour_23 = _features([_row(kickoff=datetime(2026, 8, 3, 23, 0))]).iloc[0]
    assert _clock_distance(sunday, monday, "kickoff_weekday") < (
        _clock_distance(wednesday, monday, "kickoff_weekday"))
    assert _clock_distance(hour_23, hour_zero, "kickoff_hour") < (
        _clock_distance(wednesday, hour_zero, "kickoff_hour"))


def test_kickoff_minutes_sit_between_the_hours() -> None:
    early = _clock_row(18, 0)
    middle = _clock_row(18, 30)
    late = _clock_row(19, 0)
    to_early = _clock_distance(middle, early, "kickoff_hour")
    to_late = _clock_distance(middle, late, "kickoff_hour")
    assert to_early == pytest.approx(to_late)
    assert to_early < _clock_distance(early, late, "kickoff_hour")
    midnight = _clock_row(0, 0)
    half_past_eleven = _clock_row(23, 30)
    eleven = _clock_row(23, 0)
    assert _clock_distance(half_past_eleven, midnight, "kickoff_hour") < (
        _clock_distance(eleven, midnight, "kickoff_hour"))


def _clock_row(hour: int, minute: int) -> pd.Series:
    kickoff = datetime(2026, 8, 3, hour, minute)
    return _features([_row(kickoff=kickoff)]).iloc[0]


def test_missing_pair_is_dropped_and_valid_index_remains() -> None:
    frame = pd.DataFrame([
        _row(prediction_id=1),
        _row(prediction_id=2, odds=None),
        _row(prediction_id=3, value_pct=None)])
    frame.index = [5, 6, 7]
    result = build_candidate_features(frame)
    assert list(result.index) == [5]


def test_output_columns_are_the_allowlist() -> None:
    frame = _features([_row()])
    assert list(frame.columns) == list(FEATURE_COLUMNS)
    assert set(FEATURE_COLUMNS).isdisjoint(POST_MATCH_DENYLIST)
    empty = build_candidate_features(pd.DataFrame([_row(odds=1.0)]))
    assert list(empty.columns) == list(FEATURE_COLUMNS)
    assert empty.empty


def test_post_match_columns_do_not_change_features() -> None:
    clean = _row()
    dirty = _row(
        result="1",
        outcome=1,
        home_team_goals=3,
        away_team_goals=1,
        home_team_xg=1.4,
        away_team_xg=0.2,
        final_assessment="HOME_PLAYED_BETTER",
        label=1)
    clean_features = _features([clean])
    dirty_features = _features([dirty])
    assert list(dirty_features.columns) == list(FEATURE_COLUMNS)
    assert dirty_features.equals(clean_features)
    for name in dirty_features.columns:
        lowered = name.lower()
        assert "goal" not in lowered
        assert "outcome" not in lowered
        assert "result" not in lowered
        assert "assessment" not in lowered


def test_fingerprint_hashes_sorted_names_as_utf8_lines() -> None:
    digest = hashlib.sha256("a\nb".encode("utf-8")).hexdigest()
    assert feature_schema_fingerprint(["b", "a"]) == digest
    assert feature_schema_fingerprint(("a", "b")) == digest
    assert feature_schema_fingerprint(["a", "b"]) == digest
    again = feature_schema_fingerprint(list(FEATURE_COLUMNS))
    reversed_columns = tuple(reversed(FEATURE_COLUMNS))
    assert again == feature_schema_fingerprint(reversed_columns)
    assert len(again) == 64
    assert again == again.lower()


def test_fingerprint_changes_when_the_schema_changes() -> None:
    base = feature_schema_fingerprint(FEATURE_COLUMNS)
    extra = feature_schema_fingerprint([*FEATURE_COLUMNS, "season_id"])
    assert base != extra


def test_fingerprint_rejects_bad_names() -> None:
    with pytest.raises(ValueError, match="sequence of names"):
        feature_schema_fingerprint("model_probability")
    with pytest.raises(ValueError, match="non-empty"):
        feature_schema_fingerprint(["edge", " "])
    with pytest.raises(ValueError, match="unique"):
        feature_schema_fingerprint(["edge", "edge"])
    with pytest.raises(ValueError, match="newlines"):
        feature_schema_fingerprint(["edge\nodds"])


def test_missing_or_duplicate_columns_raise() -> None:
    frame = pd.DataFrame([_row()]).drop(columns=["kickoff"])
    with pytest.raises(ValueError, match="kickoff"):
        build_candidate_features(frame)
    duplicated = pd.DataFrame([_row()])
    duplicated["odds"] = duplicated["odds"]
    mirrored = pd.concat([duplicated, duplicated[["odds"]]], axis=1)
    with pytest.raises(ValueError, match="unique"):
        build_candidate_features(mirrored)


def test_module_does_not_touch_the_database_or_settlement() -> None:
    source = inspect.getsource(feature_module)
    assert "get_db_connection" not in source
    assert "read_sql" not in source
    assert "execute(" not in source
    assert "outcome_evaluator" not in source
    assert "evaluate_football_outcome" not in source
