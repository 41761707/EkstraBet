"""Tests for optional single-family future-event prediction."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import _future_predictor
from models.pipeline.core.config import BttsPrediction
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.persistence.prediction_writer import (
    map_predictions_to_rows)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor,
    LoadedFutureModels)


def _matchup() -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=945,
        league_id=1,
        season_id=1,
        as_of_date=date(2026, 7, 24),
        match_id=None)


def _btts_config() -> FutureEventsRunConfig:
    return FutureEventsRunConfig(
        model_name="FOOTBALL_BTTS_V2",
        task_type="btts",
        model_version="2.0.0",
        artifact_dir="models/artifacts/dev/football_btts_v2",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="FootballBttsLabeler",
        trainer="LstmTrainer",
        output_columns=["p_yes", "p_no"],
        window_size=8,
        events={"btts_yes": 6, "btts_no": 172})


def _batch() -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((1, 2, 3), dtype=float),
        X_away=np.zeros((1, 2, 3), dtype=float),
        X_static=np.zeros((1, 4), dtype=float))


def test_predict_pair_returns_only_btts_when_other_configs_missing() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[0.4, 0.6]], dtype=float)
    predictor = FutureEventsPredictor(
        btts_config=_btts_config(),
        models=LoadedFutureModels(btts_model=model),
        feature_provider=lambda _matchup, _config: _batch())

    payload = predictor.predict_pair(_matchup())

    assert set(payload) == {"btts"}
    assert isinstance(payload["btts"], BttsPrediction)
    assert payload["btts"].p_yes == pytest.approx(0.6)
    assert payload["btts"].p_no == pytest.approx(0.4)
    model.predict.assert_called_once()


def test_predictor_requires_at_least_one_config() -> None:
    with pytest.raises(ValueError, match="At least one"):
        FutureEventsPredictor()


def test_mapping_supports_btts_only_payload() -> None:
    rows = map_predictions_to_rows(
        100,
        {"btts": BttsPrediction(0.7, 0.3)},
        {"btts": 11},
        {"btts_yes": 6, "btts_no": 172},
        select_finals=True)

    assert len(rows) == 2
    finals = {row.event_id for row in rows if row.is_final}
    assert finals == {6}


def test_cli_accepts_btts_config_without_result_or_goals() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "predict-pair",
        "--btts_config",
        "models/configs/training/football_btts_v2.json",
        "--home",
        "10",
        "--away",
        "945",
        "--as-of",
        "2026-07-24"
    ])

    assert args.btts_config is not None
    assert args.result_config is None
    assert args.goals_config is None


def test_future_predictor_rejects_empty_config_set() -> None:
    args = SimpleNamespace(
        result_config=None,
        btts_config=None,
        goals_config=None)
    with pytest.raises(ValueError, match="At least one"):
        _future_predictor(args)
