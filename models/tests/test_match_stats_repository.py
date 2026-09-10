"""Tests for match stats repository SQL helpers and xG normalization."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from models.pipeline.core.config import FeatureConfig
from models.pipeline.core.config import ModelRunConfig
from models.pipeline.data import match_stats_repository as stats_repo
from models.pipeline.data.match_stats_repository import (
    _normalize_zero_xg_as_missing,
    _xg_filter)
from models.pipeline.data.match_stats_repository import fetch_match_stats
from models.pipeline.data.match_stats_repository import fetch_matches_by_ids
from models.pipeline.data.match_stats_repository import fetch_matches_by_season
from models.pipeline.data.match_stats_repository import fetch_training_matches
from models.pipeline.data.ml_league_filter import MAX_ML_LEAGUE_TIER
from models.pipeline.data.ml_league_filter import ml_eligible_league_sql


def test_xg_filter_none_by_default() -> None:
    assert _xg_filter() is None
    assert _xg_filter(False, False) is None


def test_xg_filter_require_positive() -> None:
    clause = _xg_filter(require_positive_xg=True)
    assert clause is not None
    assert "home_team_xg > 0" in clause
    assert "away_team_xg > 0" in clause


def test_xg_filter_exclude_positive() -> None:
    clause = _xg_filter(exclude_positive_xg=True)
    assert clause is not None
    assert clause.startswith("NOT (")
    assert "home_team_xg > 0" in clause


def test_xg_filter_rejects_both_flags() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        _xg_filter(require_positive_xg=True, exclude_positive_xg=True)


def test_normalize_zero_xg_as_missing() -> None:
    frame = pd.DataFrame({
        "home_team_xg": [1.2, 0.0, None],
        "away_team_xg": [0.8, 0.0, 1.1]
    })
    normalized = _normalize_zero_xg_as_missing(frame)
    assert normalized.loc[0, "home_team_xg"] == 1.2
    assert pd.isna(normalized.loc[1, "home_team_xg"])
    assert pd.isna(normalized.loc[1, "away_team_xg"])
    assert pd.isna(normalized.loc[2, "home_team_xg"])


def test_feature_config_rejects_both_xg_flags() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        FeatureConfig(require_positive_xg=True, exclude_positive_xg=True)


def _training_config() -> ModelRunConfig:
    return ModelRunConfig(
        model_name="test_model",
        sport_id=1,
        task_type="classification",
        artifact_dir="artifacts/test",
        feature_config=FeatureConfig(),
        feature_builder="PlayedBetterFeatureBuilder",
        labeler="PlayedBetterLabeler",
        output_columns=["home", "draw", "away"])


def _capture_read_sql(
        monkeypatch: pytest.MonkeyPatch,
        frame: pd.DataFrame | None = None) -> dict[str, object]:
    captured: dict[str, object] = {}
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False

    def fake_read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame() if frame is None else frame.copy()

    monkeypatch.setattr(stats_repo, "get_db_connection", lambda: context)
    monkeypatch.setattr(stats_repo.pd, "read_sql", fake_read_sql)
    return captured


def _assert_ml_tier_sql(query: str) -> None:
    assert "INNER JOIN leagues l ON l.id = m.league" in query
    assert ml_eligible_league_sql() in query
    assert f"l.tier <= {MAX_ML_LEAGUE_TIER}" in query
    # Championship (tier=2) musi przejść — nie zawężamy do pierwszej ligi
    assert "tier = 1" not in query


def test_fetch_training_matches_joins_leagues_and_filters_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_training_matches(_training_config())
    _assert_ml_tier_sql(str(captured["query"]))
    assert captured["params"] == (1,)


def test_fetch_matches_by_season_joins_leagues_and_filters_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_matches_by_season(1, 10)
    _assert_ml_tier_sql(str(captured["query"]))
    assert captured["params"] == (1, 10)


def test_fetch_matches_by_ids_joins_leagues_and_filters_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_matches_by_ids([7, 8])
    _assert_ml_tier_sql(str(captured["query"]))
    assert captured["params"] == (7, 8)


def test_fetch_match_stats_joins_leagues(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(
        monkeypatch,
        pd.DataFrame({
            "id": [1],
            "league": [2],
            "sport_id": [1],
            "home_team_xg": [1.2],
            "away_team_xg": [0.8],
            "tier": [2]
        }))
    frame = fetch_match_stats(1)
    query = str(captured["query"])
    assert "INNER JOIN leagues l ON l.id = m.league" in query
    assert "l.tier" in query
    # predykat w WHERE ukryłby puchar jako pusty wynik / Match not found
    assert ml_eligible_league_sql() not in query
    assert "tier" not in frame.columns
    assert list(frame["id"]) == [1]


def test_fetch_match_stats_rejects_ineligible_league_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_read_sql(
        monkeypatch,
        pd.DataFrame({
            "id": [1],
            "league": [42],
            "sport_id": [1],
            "home_team_xg": [1.2],
            "away_team_xg": [0.8],
            "tier": [100]
        }))
    with pytest.raises(
            ValueError,
            match="League tier 100 exceeds ML cutoff 5"):
        fetch_match_stats(1)


def test_fetch_match_stats_rejects_null_league_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_read_sql(
        monkeypatch,
        pd.DataFrame({
            "id": [1],
            "league": [7],
            "sport_id": [1],
            "home_team_xg": [1.2],
            "away_team_xg": [0.8],
            "tier": [None]
        }))
    with pytest.raises(
            ValueError,
            match=r"League tier None is not eligible for ML \(cutoff 5\)"):
        fetch_match_stats(1)
