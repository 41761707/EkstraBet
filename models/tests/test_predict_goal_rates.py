"""Tests for batch Poisson lambda inference without DB access."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor,
    LoadedFutureModels)


def _goals_config() -> FutureEventsRunConfig:
    return FutureEventsRunConfig(
        model_name="FOOTBALL_GOALS_POISSON_V1",
        task_type="goals_poisson",
        model_version="1.0.0",
        artifact_dir="models/artifacts/dev/football_goals_poisson_v1",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="FootballGoalsPoissonLabeler",
        trainer="PoissonTrainer",
        output_columns=["lambda_home", "lambda_away"],
        window_size=8,
        events={})


def _batch(rows: int) -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((rows, 2, 3), dtype=float),
        X_away=np.zeros((rows, 2, 3), dtype=float),
        X_static=np.zeros((rows, 4), dtype=float))


def _predictor_with_model(model: MagicMock) -> FutureEventsPredictor:
    return FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(goals_model=model),
        feature_provider=lambda _matchup, _config: _batch(1))


def test_predict_goal_rates_returns_shape_b_by_2() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray(
        [[1.2, 0.8], [1.5, 1.1], [0.9, 1.3]],
        dtype=float)
    predictor = _predictor_with_model(model)

    rates = predictor.predict_goal_rates(_batch(3))

    assert rates.shape == (3, 2)
    assert rates.dtype == float or np.issubdtype(rates.dtype, np.floating)
    np.testing.assert_allclose(rates, [[1.2, 0.8], [1.5, 1.1], [0.9, 1.3]])
    model.predict.assert_called_once()


def test_predict_goal_rates_chunks_large_batches() -> None:
    model = MagicMock()
    model.predict.side_effect = [
        np.asarray([[1.0, 0.5], [1.1, 0.6]], dtype=float),
        np.asarray([[1.2, 0.7], [1.3, 0.8]], dtype=float),
        np.asarray([[1.4, 0.9]], dtype=float)
    ]
    predictor = _predictor_with_model(model)

    rates = predictor.predict_goal_rates(_batch(5), batch_size=2)

    assert rates.shape == (5, 2)
    assert model.predict.call_count == 3
    np.testing.assert_allclose(
        rates,
        [[1.0, 0.5], [1.1, 0.6], [1.2, 0.7], [1.3, 0.8], [1.4, 0.9]])


def test_predict_goal_rates_applies_scaler() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[1.0, 1.0]], dtype=float)
    scaler = MagicMock()
    scaler.transform.return_value = np.full((1, 4), 9.0, dtype=float)
    predictor = FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(
            goals_model=model,
            goals_scaler=scaler),
        feature_provider=lambda _matchup, _config: _batch(1))

    predictor.predict_goal_rates(_batch(1))

    scaler.transform.assert_called_once()
    call_args = model.predict.call_args[0][0]
    np.testing.assert_allclose(call_args[2], np.full((1, 4), 9.0))


def test_predict_goal_rates_does_not_use_feature_provider() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[1.0, 0.5]], dtype=float)
    provider = MagicMock(side_effect=AssertionError("DB/feature provider"))
    predictor = FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(goals_model=model),
        feature_provider=provider)

    rates = predictor.predict_goal_rates(_batch(1))

    assert rates.shape == (1, 2)
    provider.assert_not_called()


def test_predict_goal_rates_clamps_negative_lambdas() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[-0.2, 1.5]], dtype=float)
    predictor = _predictor_with_model(model)

    rates = predictor.predict_goal_rates(_batch(1))

    np.testing.assert_allclose(rates, [[0.0, 1.5]])


def test_predict_goal_rates_rejects_non_finite_lambdas() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[1.0, np.nan]], dtype=float)
    predictor = _predictor_with_model(model)

    with pytest.raises(ValueError, match="non-finite"):
        predictor.predict_goal_rates(_batch(1))


def test_predict_goal_rates_requires_goals_model() -> None:
    predictor = FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(),
        feature_provider=lambda _matchup, _config: _batch(1))

    with pytest.raises(RuntimeError, match="Goals model"):
        predictor.predict_goal_rates(_batch(1))


def test_predict_goal_rates_rejects_invalid_batch_size() -> None:
    model = MagicMock()
    predictor = _predictor_with_model(model)

    with pytest.raises(ValueError, match="batch_size"):
        predictor.predict_goal_rates(_batch(1), batch_size=0)


def test_predict_goal_rates_empty_batch() -> None:
    model = MagicMock()
    predictor = _predictor_with_model(model)

    rates = predictor.predict_goal_rates(_batch(0))

    assert rates.shape == (0, 2)
    model.predict.assert_not_called()
