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
from models.pipeline.features.sequence_builder import build_team_sequence


def _matches(count: int = 9) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    rows = []
    for index in range(count):
        rows.append({
            "id": index + 1,
            "league": 1,
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
