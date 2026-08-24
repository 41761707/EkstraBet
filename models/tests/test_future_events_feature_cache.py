"""Tests for shared history reuse in future-events matchup features."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta

import pandas as pd
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.data import shared_history_context as history_context
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.data.shared_history_context import (
    build_shared_history_context)
from models.pipeline.data.shared_history_context import feature_signature
from models.pipeline.features import sequence_builder
from models.pipeline.features.ratings import compute_ratings_timeline
from models.pipeline.features.sequence_builder import (
    FutureEventsFeatureBuilder)


def _fail_db(*args, **kwargs):
    del args, kwargs
    raise AssertionError("database was queried")


def _matches(count: int = 6) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    rows = []
    for index in range(count):
        rows.append({
            "id": index + 1,
            "league": 1,
            "home_team": 10,
            "away_team": 20,
            "game_date": start + timedelta(days=index),
            "result": "1",
            "home_team_goals": 2,
            "away_team_goals": 1
        })
    return pd.DataFrame(rows)


def _future_config(**overrides) -> FutureEventsRunConfig:
    values = dict(
        model_name="test",
        task_type="result",
        artifact_dir=".",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="football_result",
        output_columns=["1", "X", "2"],
        window_size=2,
        ratings={"elo": True, "gap": True, "czech": True},
        sequence_feature_columns=["elo"],
        static_feature_columns=["elo_home", "elo_away", "league_tier"])
    values.update(overrides)
    return FutureEventsRunConfig(**values)


def _matchup(as_of: date = date(2026, 1, 8)) -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=1,
        as_of_date=as_of)


def _league_frame() -> pd.DataFrame:
    return pd.DataFrame([{"league_id": 1, "tier": 2}])


def _context_from_matches(
        matches: pd.DataFrame,
        config: FutureEventsRunConfig,
        max_as_of: date = date(2026, 1, 20)) -> SharedHistoryContext:
    timeline = compute_ratings_timeline(matches, params=config.ratings)
    key = feature_signature(config).ratings_key
    return SharedHistoryContext(
        sport_id=1,
        finished_matches=matches,
        ratings_timeline=timeline,
        league_tiers={1: 2},
        max_as_of_date=max_as_of,
        ratings_by_key={key: timeline})


def test_build_matchup_batch_uses_context_without_db(monkeypatch) -> None:
    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "compute_ratings_timeline", _fail_db)
    config = _future_config()
    context = _context_from_matches(_matches(), config)
    batch = FutureEventsFeatureBuilder().build_matchup_batch(
        _matchup(), config, context)
    assert batch.X_home.shape[0] == 1
    assert batch.X_away.shape[0] == 1
    assert batch.X_static.shape[0] == 1
    assert batch.X_static[0, -1] == 2.0


def test_shared_history_fetches_once_for_multiple_matchups(
        monkeypatch) -> None:
    matches = _matches()
    fetch_calls: list[tuple] = []
    league_calls: list[int] = []

    def fake_fetch(sport_id, date_to):
        fetch_calls.append((sport_id, date_to))
        return matches.copy()

    def fake_leagues(sport_id, league_id=None):
        del league_id
        league_calls.append(sport_id)
        return _league_frame()

    monkeypatch.setattr(
        history_context, "fetch_finished_matches", fake_fetch)
    monkeypatch.setattr(
        history_context, "fetch_league_context", fake_leagues)
    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "compute_ratings_timeline", _fail_db)

    max_as_of = date(2026, 1, 20)
    config = _future_config()
    context = build_shared_history_context(
        1, max_as_of, [config.ratings])
    builder = FutureEventsFeatureBuilder()
    builder.build_matchup_batch(
        _matchup(date(2026, 1, 5)), config, context)
    builder.build_matchup_batch(
        _matchup(date(2026, 1, 7)), config, context)

    assert fetch_calls == [(1, max_as_of)]
    assert league_calls == [1]
    assert context.ratings_by_key is not None
    assert len(context.ratings_by_key) == 1


def test_shared_history_builds_one_timeline_per_unique_ratings_key(
        monkeypatch) -> None:
    timeline_params: list[object] = []

    def fake_fetch(sport_id, date_to):
        del sport_id, date_to
        return _matches()

    def fake_leagues(sport_id, league_id=None):
        del sport_id, league_id
        return _league_frame()

    def fake_timeline(matches, teams=None, params=None):
        del matches, teams
        timeline_params.append(params)
        return _matches()

    monkeypatch.setattr(
        history_context, "fetch_finished_matches", fake_fetch)
    monkeypatch.setattr(
        history_context, "fetch_league_context", fake_leagues)
    monkeypatch.setattr(
        history_context, "compute_ratings_timeline", fake_timeline)

    duplicate = {"elo": True}
    other = {"elo": True, "gap": True}
    context = build_shared_history_context(
        1, date(2026, 1, 20), [duplicate, duplicate, other])

    assert len(timeline_params) == 2
    assert context.ratings_by_key is not None
    assert len(context.ratings_by_key) == 2


def test_build_matchup_batch_without_context_still_fetches(
        monkeypatch) -> None:
    fetch_calls: list[tuple] = []

    def fake_fetch(sport_id, date_to):
        fetch_calls.append((sport_id, date_to))
        return _matches()

    def fake_leagues(sport_id, league_id=None):
        del sport_id, league_id
        return _league_frame()

    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", fake_fetch)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", fake_leagues)

    as_of = date(2026, 1, 8)
    FutureEventsFeatureBuilder().build_matchup_batch(
        _matchup(as_of), _future_config())

    assert fetch_calls == [(1, as_of)]


def test_build_matchup_batch_rejects_as_of_after_context_max(
        monkeypatch) -> None:
    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _fail_db)
    config = _future_config()
    context = _context_from_matches(
        _matches(), config, max_as_of=date(2026, 1, 10))
    with pytest.raises(ValueError, match="as_of_date"):
        FutureEventsFeatureBuilder().build_matchup_batch(
            _matchup(date(2026, 1, 11)), config, context)


def test_build_matchup_batch_rejects_missing_ratings_key(
        monkeypatch) -> None:
    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _fail_db)
    context = SharedHistoryContext(
        sport_id=1,
        finished_matches=pd.DataFrame(),
        ratings_timeline=pd.DataFrame(),
        league_tiers={1: 2},
        max_as_of_date=date(2026, 1, 20),
        ratings_by_key={"{}": pd.DataFrame()})
    with pytest.raises(KeyError, match="ratings_key"):
        FutureEventsFeatureBuilder().build_matchup_batch(
            _matchup(), _future_config(), context)
