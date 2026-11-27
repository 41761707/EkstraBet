"""Training and prediction feature paths for football context."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.config import FootballContextParams
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.data.shared_history_context import feature_signature
from models.pipeline.features import sequence_builder
from models.pipeline.features.ratings import compute_ratings_timeline
from models.pipeline.features.sequence_builder import (
    FutureEventsFeatureBuilder)


_START = datetime(2025, 8, 1)
_NEWCOMER_MATCH_ID = 18
_FATIGUE_MATCH_ID = 22

# Liga, sezon, dzień, gospodarz, gość, gole, xG.
# Jeden mecz na dzień: obie ścieżki obcinają wtedy tę samą dobę.
_FIXTURES = [
    (1, 10, 0, 1, 2, 2, 0, 0.0, 0.0),
    (1, 10, 1, 3, 4, 1, 1, 1.1, 0.4),
    (1, 10, 2, 1, 3, 1, 0, 0.8, 0.2),
    (1, 10, 3, 2, 4, 0, 1, 0.3, 0.9),
    (1, 10, 4, 4, 1, 0, 2, 0.4, 1.5),
    (1, 10, 5, 3, 2, 1, 2, 0.7, 1.2),
    (2, 20, 6, 6, 7, 3, 1, 1.8, 0.6),
    (2, 20, 7, 8, 6, 0, 0, 0.5, 0.5),
    (2, 20, 8, 7, 8, 2, 1, 1.4, 0.9),
    (2, 20, 9, 6, 8, 1, 0, 0.9, 0.2),
    (2, 20, 10, 7, 6, 1, 1, 0.8, 0.8),
    (2, 20, 11, 8, 7, 2, 0, 1.3, 0.4),
    (1, 11, 12, 1, 2, 1, 1, 0.6, 0.6),
    (1, 11, 13, 3, 5, 2, 0, 1.5, 0.3),
    (1, 11, 14, 2, 3, 0, 0, 0.2, 0.2),
    (1, 11, 15, 5, 1, 1, 3, 0.4, 1.7),
    (1, 11, 16, 1, 3, 2, 1, 0.0, 0.0),
    (1, 11, 17, 2, 5, 1, 0, 1.0, 0.3),
    (1, 11, 18, 4, 2, 0, 1, 0.2, 0.8),
    (1, 11, 19, 5, 4, 2, 2, 1.1, 1.1),
    (2, 21, 20, 1, 6, 2, 1, 1.4, 0.7),
    (1, 11, 23, 1, 4, 1, 0, 0.9, 0.4)
]

_SEQUENCE_COLUMNS = [
    "goals_for",
    "xg_for_masked",
    "xg_available",
    "opponent_elo_before",
    "clean_sheet",
    "failed_to_score",
    "is_home"
]

_CONTEXT_COLUMNS = [
    "league_ctx_home_goals",
    "league_ctx_away_goals",
    "league_ctx_btts_pct",
    "league_ctx_over_25_pct",
    "league_ctx_draw_pct",
    "league_ctx_season_matches",
    "home_ctx_clean_sheet_pct",
    "home_ctx_failed_to_score_pct",
    "home_ctx_draw_pct",
    "home_ctx_matches_played",
    "home_ctx_is_newcomer",
    "home_ctx_rank_pct",
    "home_ctx_points_per_game",
    "home_ctx_matches_last_14d",
    "away_ctx_clean_sheet_pct",
    "away_ctx_failed_to_score_pct",
    "away_ctx_draw_pct",
    "away_ctx_matches_played",
    "away_ctx_is_newcomer",
    "away_ctx_rank_pct",
    "away_ctx_points_per_game",
    "away_ctx_matches_last_14d"
]

_STATIC_COLUMNS = [
    "elo_diff",
    "abs_elo_diff",
    "league_avg_goals",
    "home_rest_days",
    "league_tier",
    *_CONTEXT_COLUMNS
]


def _result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "1"
    if away_goals > home_goals:
        return "2"
    return "X"


def _history() -> pd.DataFrame:
    """Return two leagues and two seasons, one match per day."""
    rows = []
    for index, fixture in enumerate(_FIXTURES):
        (
            league_id,
            season_id,
            day,
            home_id,
            away_id,
            home_goals,
            away_goals,
            home_xg,
            away_xg) = fixture
        rows.append({
            "id": index + 1,
            "league": league_id,
            "season": season_id,
            "home_team": home_id,
            "away_team": away_id,
            "game_date": _START + timedelta(days=day),
            "result": _result(home_goals, away_goals),
            "home_team_goals": home_goals,
            "away_team_goals": away_goals,
            "home_team_xg": home_xg,
            "away_team_xg": away_xg
        })
    return pd.DataFrame(rows)


def _config(
        *,
        context: bool,
        static_columns: list[str] | None = None) -> FutureEventsRunConfig:
    values: dict[str, object] = dict(
        model_name="test",
        task_type="result",
        artifact_dir=".",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="football_result",
        output_columns=["1", "X", "2"],
        window_size=2,
        ratings={"elo": True, "gap": True, "czech": True},
        sequence_feature_columns=list(_SEQUENCE_COLUMNS))
    if context:
        values["static_feature_columns"] = list(_STATIC_COLUMNS)
        values["context_params"] = {}
    else:
        values["static_feature_columns"] = static_columns or [
            "elo_home",
            "elo_away",
            "league_tier"]
        values["sequence_feature_columns"] = ["elo"]
    return FutureEventsRunConfig(**values)


def _leagues(
        sport_id: int,
        league_id: int | None = None) -> pd.DataFrame:
    assert sport_id == 1
    frame = pd.DataFrame([
        {"league_id": 1, "tier": 1},
        {"league_id": 2, "tier": 3}
    ])
    if league_id is None:
        return frame
    selected = frame.loc[frame["league_id"] == league_id]
    return selected.reset_index(drop=True)


def _finished_before(
        frame: pd.DataFrame,
        sport_id: int,
        date_to: date | datetime) -> pd.DataFrame:
    assert sport_id == 1
    dates = pd.to_datetime(frame["game_date"])
    return frame.loc[dates < pd.Timestamp(date_to)].copy()


def _patch_reads(monkeypatch: pytest.MonkeyPatch, frame: pd.DataFrame) -> None:
    monkeypatch.setattr(
        sequence_builder, "fetch_league_context", _leagues)
    monkeypatch.setattr(
        sequence_builder,
        "fetch_finished_matches",
        lambda sport_id, date_to: _finished_before(
            frame, sport_id, date_to))


def _block_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("database was queried")

    monkeypatch.setattr(sequence_builder, "fetch_league_context", fail)
    monkeypatch.setattr(sequence_builder, "fetch_finished_matches", fail)
    monkeypatch.setattr(
        sequence_builder, "compute_ratings_timeline", fail)


def _matchup_for(frame: pd.DataFrame, match_id: int) -> MatchupInput:
    row = frame.loc[frame["id"] == match_id].iloc[0]
    return MatchupInput(
        home_team_id=int(row["home_team"]),
        away_team_id=int(row["away_team"]),
        league_id=int(row["league"]),
        season_id=int(row["season"]),
        as_of_date=pd.Timestamp(row["game_date"]).date(),
        match_id=int(row["id"]))


def _shared(
        frame: pd.DataFrame,
        config: FutureEventsRunConfig) -> SharedHistoryContext:
    timeline = compute_ratings_timeline(frame, params=config.ratings)
    key = feature_signature(config).ratings_key
    return SharedHistoryContext(
        sport_id=1,
        finished_matches=frame,
        ratings_timeline=timeline,
        league_tiers={1: 1, 2: 3},
        max_as_of_date=date(2025, 12, 31),
        ratings_by_key={key: timeline})


def _position(match_ids: np.ndarray, match_id: int) -> int:
    found = np.flatnonzero(np.asarray(match_ids) == match_id)
    assert found.size == 1
    return int(found[0])


def _assert_same_row(trained, predicted, position: int) -> None:
    assert predicted.league_ids is not None
    assert trained.league_ids is not None
    np.testing.assert_allclose(
        predicted.X_static[0], trained.X_static[position])
    np.testing.assert_allclose(
        predicted.X_home[0], trained.X_home[position])
    np.testing.assert_allclose(
        predicted.X_away[0], trained.X_away[position])
    assert int(predicted.league_ids[0]) == int(trained.league_ids[position])


def test_training_and_matchup_features_match(monkeypatch) -> None:
    frame = _history()
    config = _config(context=True)
    _patch_reads(monkeypatch, frame)
    builder = FutureEventsFeatureBuilder()
    payload = builder.build_training_batch(frame, config)
    batch = payload["batch"]
    assert batch.league_ids is not None
    assert np.array_equal(batch.league_ids, payload["league_ids"])
    static = batch.X_static
    columns = list(_STATIC_COLUMNS)
    newcomer_at = _position(payload["match_ids"], _NEWCOMER_MATCH_ID)
    fatigue_at = _position(payload["match_ids"], _FATIGUE_MATCH_ID)
    assert static[newcomer_at, columns.index("away_ctx_is_newcomer")] == 1.0
    assert static[newcomer_at, columns.index("home_ctx_is_newcomer")] == 0.0
    assert static[
        fatigue_at, columns.index("home_ctx_matches_last_14d")] > 0.0
    for position, match_id in enumerate(payload["match_ids"]):
        matchup = _matchup_for(frame, int(match_id))
        predicted = builder.build_matchup_batch(matchup, config)
        _assert_same_row(batch, predicted, position)
    context = _shared(frame, config)
    _block_reads(monkeypatch)
    for position, match_id in enumerate(payload["match_ids"]):
        matchup = _matchup_for(frame, int(match_id))
        predicted = builder.build_matchup_batch(matchup, config, context)
        _assert_same_row(batch, predicted, position)


def test_shared_context_caches_state_by_day_and_params(monkeypatch) -> None:
    frame = _history()
    config = _config(context=True)
    context = _shared(frame, config)
    _block_reads(monkeypatch)
    calls: list[tuple[date, int]] = []
    real = sequence_builder.build_context_state

    def spy(timeline, as_of, params):
        calls.append((as_of, params.fatigue_days))
        return real(timeline, as_of, params)

    monkeypatch.setattr(sequence_builder, "build_context_state", spy)
    builder = FutureEventsFeatureBuilder()
    first = _matchup_for(frame, _NEWCOMER_MATCH_ID)
    later = _matchup_for(frame, _FATIGUE_MATCH_ID)
    builder.build_matchup_batch(first, config, context)
    builder.build_matchup_batch(first, config, context)
    builder.build_matchup_batch(later, config, context)
    shorter = config.model_copy(update={
        "context_params": FootballContextParams(fatigue_days=7)})
    builder.build_matchup_batch(first, shorter, context)
    assert calls == [
        (first.as_of_date, 14),
        (later.as_of_date, 14),
        (first.as_of_date, 7)
    ]


def test_v2_config_does_not_build_context_state(monkeypatch) -> None:
    frame = _history()
    config = _config(context=False)
    _patch_reads(monkeypatch, frame)

    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("context state was built")

    monkeypatch.setattr(sequence_builder, "FootballContextState", fail)
    monkeypatch.setattr(sequence_builder, "build_context_state", fail)
    builder = FutureEventsFeatureBuilder()
    payload = builder.build_training_batch(frame, config)
    batch = payload["batch"]
    assert batch.league_ids is not None
    assert np.array_equal(batch.league_ids, payload["league_ids"])
    matchup = _matchup_for(frame, _FATIGUE_MATCH_ID)
    predicted = builder.build_matchup_batch(matchup, config)
    assert predicted.league_ids is not None
    assert predicted.league_ids.tolist() == [int(matchup.league_id)]
    shared = _shared(frame, config)
    _block_reads(monkeypatch)
    cached = builder.build_matchup_batch(matchup, config, shared)
    assert cached.league_ids is not None
    assert shared.context_states == {}


def test_context_matchup_requires_season_id(monkeypatch) -> None:
    frame = _history()
    config = _config(context=True)
    _patch_reads(monkeypatch, frame)
    matchup = _matchup_for(frame, _FATIGUE_MATCH_ID)
    missing = matchup.model_copy(update={"season_id": None})
    with pytest.raises(ValueError, match="season_id"):
        FutureEventsFeatureBuilder().build_matchup_batch(missing, config)
