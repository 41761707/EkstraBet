"""Tests for shared history reuse in future-events matchup features."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.data import shared_history_context as history_context
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.data.shared_history_context import (
    build_shared_history_context)
from models.pipeline.data.shared_history_context import feature_signature
from models.pipeline.features import sequence_builder
from models.pipeline.features.ratings import compute_ratings_timeline
from models.pipeline.features.sequence_builder import (
    FutureEventsFeatureBuilder)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
from models.pipeline.prediction.future_events_predictor import (
    LoadedFutureModels)


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


def _dummy_batch() -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((1, 2, 3), dtype=float),
        X_away=np.zeros((1, 2, 3), dtype=float),
        X_static=np.zeros((1, 4), dtype=float))


def _mock_models() -> LoadedFutureModels:
    result = MagicMock()
    result.predict.return_value = np.asarray([[0.5, 0.3, 0.2]], dtype=float)
    btts = MagicMock()
    btts.predict.return_value = np.asarray([[0.4, 0.6]], dtype=float)
    goals = MagicMock()
    goals.predict.return_value = np.asarray([[1.2, 0.8]], dtype=float)
    return LoadedFutureModels(
        result_model=result,
        btts_model=btts,
        goals_model=goals)


def _three_family_predictor(
        provider=None,
        result_overrides: dict | None = None,
        btts_overrides: dict | None = None,
        goals_overrides: dict | None = None) -> FutureEventsPredictor:
    result_config = _future_config(**(result_overrides or {}))
    btts_config = _future_config(
        task_type="btts",
        output_columns=["p_yes", "p_no"],
        **(btts_overrides or {}))
    goals_config = _future_config(
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        **(goals_overrides or {}))
    return FutureEventsPredictor(
        result_config=result_config,
        btts_config=btts_config,
        goals_config=goals_config,
        models=_mock_models(),
        feature_provider=provider)


def _two_matchups() -> list[MatchupInput]:
    return [
        _matchup(date(2026, 1, 16)),
        MatchupInput(
            home_team_id=10,
            away_team_id=20,
            league_id=1,
            as_of_date=date(2026, 1, 18))]


def _home_tensor(model, index: int) -> np.ndarray:
    return model.predict.call_args_list[index].args[0][0]


def _assert_family_tensor_sharing(
        predictor: FutureEventsPredictor,
        matchup_count: int,
        *,
        share_btts: bool,
        share_goals: bool) -> None:
    # te same obiekty numpy = reuse SequenceBatch; is not = osobny tensor
    models = predictor.models
    for index in range(matchup_count):
        result_home = _home_tensor(models.result_model, index)
        btts_home = _home_tensor(models.btts_model, index)
        goals_home = _home_tensor(models.goals_model, index)
        if share_btts:
            assert result_home is btts_home
        else:
            assert result_home is not btts_home
        if share_goals:
            assert result_home is goals_home
        else:
            assert result_home is not goals_home


def _patch_shared_history(
        monkeypatch,
        matches: pd.DataFrame) -> dict[str, list]:
    """Count history fetches and fail if the matchup builder hits DB."""
    counts: dict[str, list] = {
        "fetch": [],
        "league": [],
        "timeline": [],
        "build": []}

    def fake_fetch(sport_id, date_to):
        counts["fetch"].append((sport_id, date_to))
        return matches.copy()

    def fake_leagues(sport_id, league_id=None):
        del league_id
        counts["league"].append(sport_id)
        return _league_frame()

    def fake_timeline(finished, teams=None, params=None):
        counts["timeline"].append(params)
        return compute_ratings_timeline(
            finished, teams=teams, params=params)

    original_build = FutureEventsFeatureBuilder.build_matchup_batch

    def spy_build(self, matchup, config, context=None):
        counts["build"].append((
            matchup.as_of_date, feature_signature(config)))
        return original_build(self, matchup, config, context)

    monkeypatch.setattr(
        history_context, "fetch_finished_matches", fake_fetch)
    monkeypatch.setattr(
        history_context, "fetch_league_context", fake_leagues)
    monkeypatch.setattr(
        history_context, "compute_ratings_timeline", fake_timeline)
    monkeypatch.setattr(
        sequence_builder, "fetch_finished_matches", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _fail_db)
    monkeypatch.setattr(
        sequence_builder, "compute_ratings_timeline", _fail_db)
    monkeypatch.setattr(
        FutureEventsFeatureBuilder, "build_matchup_batch", spy_build)
    return counts


def _predict_batch_with_shared_history(
        monkeypatch,
        *,
        result_overrides: dict | None = None,
        btts_overrides: dict | None = None,
        goals_overrides: dict | None = None
        ) -> tuple[FutureEventsPredictor, dict[str, list], date]:
    matches = _matches(20)
    counts = _patch_shared_history(monkeypatch, matches)
    matchups = _two_matchups()
    max_as_of = date(2026, 1, 20)
    predictor = _three_family_predictor(
        result_overrides=result_overrides,
        btts_overrides=btts_overrides,
        goals_overrides=goals_overrides)
    rating_sets = [
        config.ratings
        for config in (
            predictor.result_config,
            predictor.btts_config,
            predictor.goals_config)
        if config is not None]
    context = build_shared_history_context(1, max_as_of, rating_sets)
    predictor.predict_batch(matchups, context=context)
    return predictor, counts, max_as_of


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

    # sort_keys: ta sama treść ratingów, inna kolejność kluczy
    reordered = {"gap": True, "elo": True}
    canonical = {"elo": True, "gap": True}
    other = {"elo": True}
    context = build_shared_history_context(
        1, date(2026, 1, 20), [reordered, canonical, other])

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


def test_feature_signature_stable() -> None:
    first = feature_signature(_future_config())
    second = feature_signature(_future_config())
    assert first == second
    assert hash(first) == hash(second)
    btts = feature_signature(_future_config(
        task_type="btts",
        output_columns=["p_yes", "p_no"]))
    assert first == btts
    assert first != feature_signature(_future_config(window_size=12))
    assert first != feature_signature(
        _future_config(ratings={"elo": True, "gap": True}))
    assert first != feature_signature(
        _future_config(sequence_feature_columns=["elo", "btts"]))
    assert first != feature_signature(
        _future_config(static_feature_columns=["elo_home", "elo_away"]))
    # ratings_key z sort_keys: kolejność kluczy w dict bez znaczenia
    gap_then_elo = feature_signature(
        _future_config(ratings={"gap": True, "elo": True}))
    elo_then_gap = feature_signature(
        _future_config(ratings={"elo": True, "gap": True}))
    assert gap_then_elo.ratings_key == elo_then_gap.ratings_key
    assert gap_then_elo == elo_then_gap
    # kolejność kolumn ma znaczenie dla tensora
    elo_then_btts = feature_signature(_future_config(
        sequence_feature_columns=["elo", "btts"]))
    btts_then_elo = feature_signature(_future_config(
        sequence_feature_columns=["btts", "elo"]))
    assert elo_then_btts != btts_then_elo
    assert first != feature_signature(
        _future_config(feature_builder="OtherFeatureBuilder"))


def test_identical_signatures_reuse_sequence_batch() -> None:
    calls: list[str] = []

    def provider(matchup, config, context=None):
        del matchup, context
        calls.append(config.task_type)
        return _dummy_batch()

    cache: dict = {}
    predictor = _three_family_predictor(provider)
    payload = predictor.predict_pair(_matchup(), feature_cache=cache)

    assert set(payload) == {"result", "btts", "goals_poisson"}
    assert calls == ["result"]
    assert len(cache) == 1
    _assert_family_tensor_sharing(
        predictor, 1, share_btts=True, share_goals=True)


def test_divergent_signatures_build_separate_batches() -> None:
    calls: list[tuple[str, int]] = []

    def provider(matchup, config, context=None):
        del matchup, context
        calls.append((config.task_type, config.window_size))
        return _dummy_batch()

    cache: dict = {}
    predictor = _three_family_predictor(
        provider, goals_overrides={"window_size": 12})
    predictor.predict_pair(_matchup(), feature_cache=cache)

    assert calls == [("result", 2), ("goals_poisson", 12)]
    assert len(cache) == 2
    _assert_family_tensor_sharing(
        predictor, 1, share_btts=True, share_goals=False)


def test_divergent_columns_build_separate_batches() -> None:
    calls: list[tuple[str, ...]] = []

    def provider(matchup, config, context=None):
        del matchup, context
        calls.append(tuple(config.sequence_feature_columns))
        return _dummy_batch()

    cache: dict = {}
    predictor = _three_family_predictor(
        provider,
        btts_overrides={"sequence_feature_columns": ["elo", "btts"]})
    predictor.predict_pair(_matchup(), feature_cache=cache)

    assert len(calls) == 2
    assert ("elo",) in calls
    assert ("elo", "btts") in calls
    assert len(cache) == 2
    _assert_family_tensor_sharing(
        predictor, 1, share_btts=False, share_goals=True)


def test_divergent_ratings_build_separate_batches() -> None:
    calls: list[str] = []

    def provider(matchup, config, context=None):
        del matchup, context
        calls.append(config.task_type)
        return _dummy_batch()

    cache: dict = {}
    predictor = _three_family_predictor(
        provider,
        goals_overrides={"ratings": {"elo": True, "gap": True}})
    predictor.predict_pair(_matchup(), feature_cache=cache)

    assert calls == ["result", "goals_poisson"]
    assert len(cache) == 2
    _assert_family_tensor_sharing(
        predictor, 1, share_btts=True, share_goals=False)


def test_predict_batch_reuses_cache_across_matchups() -> None:
    built: list[SequenceBatch] = []

    def provider(matchup, config, context=None):
        del matchup, config, context
        batch = _dummy_batch()
        built.append(batch)
        return batch

    matchup = _matchup()
    predictor = _three_family_predictor(provider)
    results = predictor.predict_batch([matchup, matchup])

    assert len(results) == 2
    assert len(built) == 1


def test_predict_batch_progress_callback_is_sequential() -> None:
    seen: list[tuple[int, int, int]] = []

    def progress(
            index: int, total: int, matchup: MatchupInput) -> None:
        seen.append((index, total, matchup.home_team_id))

    first = _matchup()
    second = MatchupInput(
        home_team_id=11,
        away_team_id=21,
        league_id=1,
        as_of_date=date(2026, 1, 8))
    predictor = _three_family_predictor(
        lambda _matchup, _config, context=None: _dummy_batch())
    results = predictor.predict_batch(
        [first, second], progress=progress)
    assert len(results) == 2
    assert seen == [(1, 2, 10), (2, 2, 11)]


def test_builder_type_error_is_not_retried_without_context(
        monkeypatch) -> None:
    calls: list[object] = []

    def boom(self, matchup, config, context=None):
        del self, matchup, config
        calls.append(context)
        raise TypeError("cannot reshape array of size 0")

    monkeypatch.setattr(
        FutureEventsFeatureBuilder, "build_matchup_batch", boom)
    config = _future_config()
    context = _context_from_matches(_matches(), config)
    result_model = MagicMock()
    result_model.predict.return_value = np.asarray(
        [[0.5, 0.3, 0.2]], dtype=float)
    predictor = FutureEventsPredictor(
        result_config=config,
        models=LoadedFutureModels(result_model=result_model))
    with pytest.raises(TypeError, match="reshape"):
        predictor.predict_pair(_matchup(), context=context)
    assert calls == [context]


def test_predict_pair_forwards_shared_history_context() -> None:
    seen: list[object] = []

    def provider(matchup, config, context=None):
        del matchup, config
        seen.append(context)
        return _dummy_batch()

    config = _future_config()
    context = _context_from_matches(_matches(), config)
    result_model = MagicMock()
    result_model.predict.return_value = np.asarray(
        [[0.5, 0.3, 0.2]], dtype=float)
    predictor = FutureEventsPredictor(
        result_config=config,
        models=LoadedFutureModels(result_model=result_model),
        feature_provider=provider)
    predictor.predict_pair(_matchup(), context=context)
    assert seen == [context]


def test_predict_batch_builds_history_once(monkeypatch) -> None:
    predictor, counts, max_as_of = _predict_batch_with_shared_history(
        monkeypatch)
    assert counts["fetch"] == [(1, max_as_of)]
    assert counts["league"] == [1]
    assert len(counts["timeline"]) == 1
    assert len(counts["build"]) == 2
    _assert_family_tensor_sharing(
        predictor, 2, share_btts=True, share_goals=True)


@pytest.mark.parametrize(
    ("btts_overrides", "goals_overrides", "builds", "timelines",
     "share_btts", "share_goals"),
    [
        ({}, {"window_size": 12}, 4, 1, True, False),
        (
            {"sequence_feature_columns": ["elo", "btts"]},
            {},
            4,
            1,
            False,
            True),
        (
            {},
            {"ratings": {"elo": True, "gap": True}},
            4,
            2,
            True,
            False),
        (
            {"window_size": 8},
            {"window_size": 12},
            6,
            1,
            False,
            False)
    ])
def test_predict_batch_count_matrix(
        monkeypatch,
        btts_overrides: dict,
        goals_overrides: dict,
        builds: int,
        timelines: int,
        share_btts: bool,
        share_goals: bool) -> None:
    predictor, counts, max_as_of = _predict_batch_with_shared_history(
        monkeypatch,
        btts_overrides=btts_overrides,
        goals_overrides=goals_overrides)
    assert counts["fetch"] == [(1, max_as_of)]
    assert counts["league"] == [1]
    assert len(counts["timeline"]) == timelines
    assert len(counts["build"]) == builds
    unique_keys = {item[1] for item in counts["build"]}
    assert len(counts["build"]) == 2 * len(unique_keys)
    _assert_family_tensor_sharing(
        predictor, 2, share_btts=share_btts, share_goals=share_goals)


def test_predict_batch_divergent_signatures_keep_separate_tensors(
        monkeypatch) -> None:
    predictor, counts, max_as_of = _predict_batch_with_shared_history(
        monkeypatch, goals_overrides={"window_size": 12})
    assert counts["fetch"] == [(1, max_as_of)]
    assert len(counts["build"]) == 4
    cache_batches = [
        _home_tensor(predictor.models.result_model, 0),
        _home_tensor(predictor.models.goals_model, 0)]
    assert cache_batches[0] is not cache_batches[1]
    assert cache_batches[0].shape != cache_batches[1].shape
    _assert_family_tensor_sharing(
        predictor, 2, share_btts=True, share_goals=False)
