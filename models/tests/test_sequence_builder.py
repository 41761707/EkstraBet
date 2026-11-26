"""Tests for leakage-safe football sequence construction."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.features import sequence_builder
from models.pipeline.features.ratings import compute_ratings_timeline
from models.pipeline.features.sequence_builder import FutureEventsFeatureBuilder
from models.pipeline.features.sequence_builder import _perspective_row
from models.pipeline.features.sequence_builder import build_team_sequence


def _matches(count: int = 9) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    rows = []
    for index in range(count):
        rows.append({
            "id": index + 1,
            "league": 1,
            "season": 15,
            "home_team": 10 if index % 2 == 0 else 20 + index,
            "away_team": 20 + index if index % 2 == 0 else 10,
            "game_date": start + timedelta(days=index),
            "result": "1",
            "home_team_goals": 2,
            "away_team_goals": 1,
            "home_team_xg": None if index == 3 else 1.4,
            "away_team_xg": 0.8
        })
    return pd.DataFrame(rows)


def _perspective_match(**overrides: object) -> pd.Series:
    row: dict[str, object] = {
        "home_team": 10,
        "away_team": 20,
        "result": "1",
        "home_team_goals": 2.0,
        "away_team_goals": 1.0,
        "home_team_xg": 1.4,
        "away_team_xg": 0.8
    }
    row.update(overrides)
    return pd.Series(row)


def test_perspective_row_masks_zero_xg_with_goals() -> None:
    row = _perspective_match(home_team_xg=0.0, away_team_xg=0.0)
    home = _perspective_row(row, 10)
    away = _perspective_row(row, 20)
    assert home["xg_for"] == 0.0
    assert home["xg_against"] == 0.0
    assert home["xg_for_masked"] == 2.0
    assert home["xg_against_masked"] == 1.0
    assert home["xg_available"] == 0.0
    assert away["xg_for"] == 0.0
    assert away["xg_against"] == 0.0
    assert away["xg_for_masked"] == 1.0
    assert away["xg_against_masked"] == 2.0
    assert away["xg_available"] == 0.0


def test_perspective_row_keeps_positive_xg() -> None:
    row = _perspective_match()
    home = _perspective_row(row, 10)
    away = _perspective_row(row, 20)
    assert home["xg_for"] == 1.4
    assert home["xg_against"] == 0.8
    assert home["xg_for_masked"] == 1.4
    assert home["xg_against_masked"] == 0.8
    assert home["xg_available"] == 1.0
    assert away["xg_for_masked"] == 0.8
    assert away["xg_against_masked"] == 1.4
    assert away["xg_for"] == 0.8
    assert away["xg_against"] == 1.4
    assert away["xg_available"] == 1.0


def test_perspective_row_masks_a_one_sided_xg_gap() -> None:
    row = _perspective_match(away_team_xg=0.0)
    home = _perspective_row(row, 10)
    assert home["xg_for"] == 1.4
    assert home["xg_against"] == 0.0
    assert home["xg_for_masked"] == 1.4
    assert home["xg_against_masked"] == 1.0
    assert home["xg_available"] == 0.0


def test_perspective_row_masks_missing_xg_with_goals() -> None:
    row = _perspective_match(home_team_xg=None, away_team_xg=None)
    home = _perspective_row(row, 10)
    assert np.isnan(home["xg_for"])
    assert np.isnan(home["xg_against"])
    assert home["xg_for_masked"] == 2.0
    assert home["xg_against_masked"] == 1.0
    assert home["xg_available"] == 0.0


def test_perspective_row_reads_opponent_elo_for_both_sides() -> None:
    row = _perspective_match(home_elo=1610.0, away_elo=1420.0)
    home = _perspective_row(row, 10)
    away = _perspective_row(row, 20)
    assert home["elo"] == 1610.0
    assert away["elo"] == 1420.0
    assert home["opponent_elo_before"] == away["elo"]
    assert away["opponent_elo_before"] == home["elo"]


def test_perspective_row_flags_clean_sheet_and_failed_to_score() -> None:
    row = _perspective_match(home_team_goals=2.0, away_team_goals=0.0)
    home = _perspective_row(row, 10)
    away = _perspective_row(row, 20)
    assert home["clean_sheet"] == 1.0
    assert home["failed_to_score"] == 0.0
    assert away["clean_sheet"] == 0.0
    assert away["failed_to_score"] == 1.0


def test_perspective_row_defaults_missing_opponent_elo() -> None:
    row = _perspective_match()
    home = _perspective_row(row, 10)
    away = _perspective_row(row, 20)
    assert home["opponent_elo_before"] == 1500.0
    assert away["opponent_elo_before"] == 1500.0
    assert home["elo"] == 1500.0
    assert away["elo"] == 1500.0


def test_build_team_sequence_uses_strictly_earlier_matches() -> None:
    matches = _matches()
    sequence = build_team_sequence(
        matches,
        team_id=10,
        as_of_date=datetime(2026, 1, 9),
        window=8,
        feature_cols=["goals_for", "goals_against", "is_home"])
    assert sequence is not None
    assert sequence.shape == (8, 3)
    assert sequence[-1].tolist() == [1.0, 2.0, 0.0]


def test_build_team_sequence_returns_none_for_short_history() -> None:
    sequence = build_team_sequence(
        _matches(7),
        team_id=10,
        as_of_date=datetime(2027, 1, 1),
        window=8)
    assert sequence is None


def test_build_team_sequence_imputes_optional_stats() -> None:
    sequence = build_team_sequence(
        _matches(),
        team_id=10,
        as_of_date=datetime(2026, 1, 9),
        window=8,
        feature_cols=["xg_for", "xg_against"])
    assert sequence is not None
    assert np.isfinite(sequence).all()


def test_ratings_are_recorded_before_each_match() -> None:
    matches = _matches(2)
    matches.loc[1, "game_date"] = matches.loc[0, "game_date"]
    timeline = compute_ratings_timeline(matches)
    assert timeline.loc[0, "home_elo"] == 1500.0
    assert timeline.loc[1, "away_elo"] == 1500.0
    assert timeline.loc[0, "home_elo_post"] > 1500.0


def _future_config() -> FutureEventsRunConfig:
    return FutureEventsRunConfig(
        model_name="test",
        task_type="result",
        artifact_dir=".",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="football_result",
        output_columns=["1", "X", "2"],
        window_size=2,
        sequence_feature_columns=["elo"],
        static_feature_columns=[
            "elo_home",
            "elo_away",
            "home_czech_win_pct",
            "league_avg_goals",
            "h2h_home_wins",
            "home_rest_days",
            "league_tier"
        ])


def test_training_batch_uses_chronological_state_without_public_scans(
        monkeypatch) -> None:
    matches = _matches(12)
    matches["home_team"] = 10
    matches["away_team"] = 20
    timeline = compute_ratings_timeline(matches)
    timeline["home_elo"] = np.arange(len(timeline), dtype=float) + 1100.0
    timeline["away_elo"] = np.arange(len(timeline), dtype=float) + 1200.0
    timeline["home_elo_post"] = 9999.0
    timeline["away_elo_post"] = 9999.0
    context_calls = 0

    def fail_full_scan(*args, **kwargs):
        del args, kwargs
        raise AssertionError("training used a full-scan public builder")

    def fake_context(sport_id):
        nonlocal context_calls
        assert sport_id == 1
        context_calls += 1
        return pd.DataFrame([{"league_id": 1, "tier": 3}])

    monkeypatch.setattr(
        sequence_builder, "compute_ratings_timeline",
        lambda *args, **kwargs: timeline)
    monkeypatch.setattr(
        sequence_builder, "build_team_sequence", fail_full_scan)
    monkeypatch.setattr(
        sequence_builder, "build_matchup_static", fail_full_scan)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", fake_context)

    result = FutureEventsFeatureBuilder().build_training_batch(
        matches, _future_config())
    batch = result["batch"]

    assert batch.X_home.shape == (10, 2, 1)
    assert batch.X_static[:, 0].tolist() == list(
        np.arange(10, dtype=float) + 1102.0)
    assert batch.X_static[:, 1].tolist() == list(
        np.arange(10, dtype=float) + 1202.0)
    assert batch.X_static[:, -1].tolist() == [3.0] * 10
    assert context_calls == 1
    labels = result["labels"]
    assert len(result["match_ids"]) == len(labels)
    assert len(result["league_ids"]) == len(labels)
    assert len(result["season_ids"]) == len(labels)
    assert len(result["home_goals"]) == len(labels)
    assert len(result["away_goals"]) == len(labels)
    assert result["dates"].shape[0] == len(labels)
    assert result["match_ids"].tolist() == list(range(3, 13))
    assert result["league_ids"].tolist() == [1] * 10
    assert result["season_ids"].tolist() == [15] * 10
    assert result["home_goals"].tolist() == [2] * 10
    assert result["away_goals"].tolist() == [1] * 10
