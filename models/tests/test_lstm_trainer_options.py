"""Tests for sequence normalization, league embedding and recency."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from models.pipeline.core.artifacts import load_league_vocab
from models.pipeline.core.artifacts import save_league_vocab
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.evaluation import candidates
from models.pipeline.prediction import future_events_predictor as predictor
from models.pipeline.training import lstm_trainer
from models.pipeline.training import poisson_trainer
from models.pipeline.training.lstm_trainer import LstmTrainer
from models.pipeline.training.lstm_trainer import build_dual_lstm_classifier
from models.pipeline.training.model_inputs import recency_sample_weights
from models.pipeline.training.model_inputs import sequence_normalization_layer
from models.pipeline.training.poisson_trainer import PoissonTrainer
from models.pipeline.training.poisson_trainer import build_poisson_model
from models.pipeline.training.poisson_trainer import poisson_nll


def _config(**overrides: object) -> FutureEventsRunConfig:
    payload: dict[str, object] = {
        "model_name": "test",
        "task_type": "result",
        "artifact_dir": ".",
        "feature_config": {},
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "football_result",
        "output_columns": ["p_home", "p_draw", "p_away"]
    }
    payload.update(overrides)
    return FutureEventsRunConfig.model_validate(payload)


def _sequences() -> np.ndarray:
    home = np.array([
        [[10.0, 1.0], [30.0, 3.0]],
        [[10.0, 1.0], [30.0, 3.0]],
        [[0.0, 100.0], [0.0, 100.0]],
        [[0.0, 100.0], [0.0, 100.0]]], dtype=np.float32)
    return np.concatenate([home, home + 5.0], axis=0)


def _normalization_layers(model: Any) -> list[Any]:
    return [
        layer for layer in model.layers
        if layer.__class__.__name__ == "Normalization"]


def _lstm_reads_normalization(model: Any, name: str) -> bool:
    history = model.get_layer(name).input._keras_history
    return history.operation.__class__.__name__ == "Normalization"


def test_network_has_normalization_only_when_the_layer_is_passed() -> None:
    pytest.importorskip("tensorflow")
    shape = (2, 2)
    plain = _config()
    layer = sequence_normalization_layer(_sequences())
    classifier = build_dual_lstm_classifier(shape, 1, 3, plain)
    poisson = build_poisson_model(shape, 1, plain)
    assert _normalization_layers(classifier) == []
    assert _normalization_layers(poisson) == []
    normalized_classifier = build_dual_lstm_classifier(
        shape, 1, 3, plain, layer)
    assert len(_normalization_layers(normalized_classifier)) == 1
    assert _lstm_reads_normalization(normalized_classifier, "home_lstm")
    assert _lstm_reads_normalization(normalized_classifier, "away_lstm")
    assert len(normalized_classifier.inputs) == 3
    other = sequence_normalization_layer(_sequences())
    normalized_poisson = build_poisson_model(shape, 1, plain, other)
    assert len(_normalization_layers(normalized_poisson)) == 1
    assert _lstm_reads_normalization(normalized_poisson, "home_lstm")
    assert _lstm_reads_normalization(normalized_poisson, "away_lstm")
    assert len(normalized_poisson.inputs) == 3


def test_normalized_model_loads_without_custom_objects(
        tmp_path: Path) -> None:
    tensorflow = pytest.importorskip("tensorflow")
    model = build_dual_lstm_classifier(
        (2, 2),
        1,
        3,
        _config(),
        sequence_normalization_layer(_sequences()))
    target = tmp_path / "model.keras"
    model.save(target)
    loaded = tensorflow.keras.models.load_model(target)
    assert len(_normalization_layers(loaded)) == 1
    home = np.zeros((2, 2, 2), dtype=np.float32)
    away = np.ones((2, 2, 2), dtype=np.float32)
    static = np.zeros((2, 1), dtype=np.float32)
    before = np.asarray(model.predict(
        [home, away, static], verbose=0))
    after = np.asarray(loaded.predict(
        [home, away, static], verbose=0))
    assert np.allclose(before, after)


class _History:
    def __init__(self) -> None:
        self.history = {"val_loss": [0.2]}


class _RecordingModel:
    def __init__(self, width: int) -> None:
        self.width = width
        self.history = _History()

    def fit(self, inputs, labels, **kwargs):
        del inputs, labels, kwargs
        return self.history

    def predict(self, inputs, verbose=0):
        del verbose
        count = len(inputs[0])
        return np.full((count, self.width), 1.0 / self.width)

    def save(self, path) -> None:
        Path(path).write_text("ok", encoding="utf-8")


class _Keras:
    class callbacks:
        class EarlyStopping:
            def __init__(self, **kwargs) -> None:
                del kwargs


def _window_payload() -> tuple[SequenceBatch, np.ndarray]:
    home = np.array([
        [[10.0, 1.0], [30.0, 3.0]],
        [[10.0, 1.0], [30.0, 3.0]],
        [[0.0, 100.0], [0.0, 100.0]],
        [[0.0, 100.0], [0.0, 100.0]]], dtype=np.float32)
    away = home + 5.0
    static = np.arange(4, dtype=np.float32).reshape(4, 1)
    dates = np.array([
        "2026-01-01",
        "2026-02-01",
        "2026-06-01",
        "2026-08-01"], dtype="datetime64[ns]")
    return SequenceBatch(home, away, static), dates


def _split_config(
        artifact_dir: Path,
        **overrides: object) -> FutureEventsRunConfig:
    payload: dict[str, object] = {
        "artifact_dir": str(artifact_dir),
        "date_to": "2026-09-01",
        "epochs": 1,
        "split": {
            "validation_from": "2026-05-01",
            "calibration_from": "2026-07-01"
        }
    }
    payload.update(overrides)
    return _config(**payload)


def test_trainers_fit_normalization_on_the_training_window_only(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, dates = _window_payload()
    seen: dict[str, Any] = {}

    def _layer(sequences: np.ndarray) -> str:
        seen["sequences"] = np.array(sequences, copy=True)
        return "norm"

    def _build(*args: object, **kwargs: object) -> _RecordingModel:
        del kwargs
        if len(args) > 2 and isinstance(args[2], int):
            seen["layer"] = args[4] if len(args) > 4 else None
            seen["vocab_size"] = args[5] if len(args) > 5 else None
            return _RecordingModel(3)
        seen["layer"] = args[3] if len(args) > 3 else None
        seen["vocab_size"] = args[4] if len(args) > 4 else None
        return _RecordingModel(2)

    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        lstm_trainer, "sequence_normalization_layer", _layer)
    monkeypatch.setattr(
        lstm_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros(4, dtype=np.int64), dates))
    monkeypatch.setattr(
        lstm_trainer, "build_dual_lstm_classifier", _build)
    LstmTrainer().train(_split_config(
        tmp_path / "lstm", normalize_sequences=True))
    # Czerwiec i sierpień są poza oknem treningowym.
    expected = np.concatenate(
        [batch.X_home[:2], batch.X_away[:2]], axis=0)
    assert np.array_equal(seen["sequences"], expected)
    assert seen["layer"] == "norm"
    assert seen["vocab_size"] is None
    assert not (tmp_path / "lstm" / "league_vocab.json").is_file()

    seen.clear()
    LstmTrainer().train(_split_config(tmp_path / "plain"))
    assert "sequences" not in seen
    assert seen["layer"] is None
    assert seen["vocab_size"] is None
    assert not (tmp_path / "plain" / "league_vocab.json").is_file()

    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros((4, 2), dtype=np.float32), dates))
    monkeypatch.setattr(poisson_trainer, "build_poisson_model", _build)
    poisson_config = _split_config(
        tmp_path / "poisson",
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        normalize_sequences=True)
    PoissonTrainer().train(poisson_config)
    assert np.array_equal(seen["sequences"], expected)
    assert seen["layer"] == "norm"
    assert seen["vocab_size"] is None
    assert not (tmp_path / "poisson" / "league_vocab.json").is_file()


def _embedding_inputs(model: Any) -> list[str]:
    return [tensor.name.split(":")[0] for tensor in model.inputs]


def _concat_width(model: Any) -> int:
    layer = next(
        item for item in model.layers
        if item.__class__.__name__ == "Concatenate")
    return int(layer.output.shape[-1])


def test_embedding_is_a_fourth_standard_input() -> None:
    pytest.importorskip("tensorflow")
    config = _config(league_embedding_dim=2, lstm_units=4, dense_units=4)
    layer = sequence_normalization_layer(_sequences())
    model = build_dual_lstm_classifier((2, 2), 1, 3, config, layer, 3)
    assert _embedding_inputs(model) == [
        "home_sequence",
        "away_sequence",
        "static_features",
        "league_index"]
    assert "int32" in str(model.inputs[3].dtype)
    embedding = model.get_layer("league_embedding").get_config()
    assert embedding["input_dim"] == 4
    assert embedding["output_dim"] == 2
    regularizer = embedding["embeddings_regularizer"]
    assert regularizer["class_name"] == "L2"
    assert regularizer["config"]["l2"] == pytest.approx(1e-3)
    flat = model.get_layer("league_embedding_flat")
    assert flat.__class__.__name__ == "Flatten"
    assert len(_normalization_layers(model)) == 1
    assert _lstm_reads_normalization(model, "home_lstm")
    assert _lstm_reads_normalization(model, "away_lstm")
    assert _concat_width(model) == 4 + 4 + 4 + 2
    poisson = build_poisson_model((2, 2), 1, config, None, 3)
    assert _embedding_inputs(poisson)[-1] == "league_index"
    assert _concat_width(poisson) == 4 + 4 + 4 + 2
    with pytest.raises(ValueError, match="league_vocab_size"):
        build_dual_lstm_classifier((2, 2), 1, 3, config)
    with pytest.raises(ValueError, match="league_vocab_size"):
        build_poisson_model((2, 2), 1, config)


def test_embedding_model_loads_without_custom_objects(
        tmp_path: Path) -> None:
    tensorflow = pytest.importorskip("tensorflow")
    model = build_dual_lstm_classifier(
        (2, 2),
        1,
        3,
        _config(league_embedding_dim=2),
        sequence_normalization_layer(_sequences()),
        3)
    target = tmp_path / "model.keras"
    model.save(target)
    loaded = tensorflow.keras.models.load_model(target)
    assert loaded.get_layer("league_embedding").get_config()["input_dim"] == 4
    home = np.zeros((2, 2, 2), dtype=np.float32)
    away = np.ones((2, 2, 2), dtype=np.float32)
    static = np.zeros((2, 1), dtype=np.float32)
    indexes = np.array([[1], [0]], dtype=np.int32)
    before = np.asarray(model.predict(
        [home, away, static, indexes], verbose=0))
    after = np.asarray(loaded.predict(
        [home, away, static, indexes], verbose=0))
    assert np.allclose(before, after)


def test_zero_embedding_dim_keeps_three_inputs() -> None:
    pytest.importorskip("tensorflow")
    model = build_dual_lstm_classifier((2, 2), 1, 3, _config(), None, 3)
    poisson = build_poisson_model((2, 2), 1, _config(), None, 3)
    assert len(model.inputs) == 3
    assert len(poisson.inputs) == 3


class _CaptureModel:
    def __init__(self, width: int) -> None:
        self.width = width
        self.train_inputs: list[np.ndarray] | None = None
        self.validation_inputs: list[np.ndarray] | None = None
        self.history = _History()

    def fit(self, inputs, labels, **kwargs):
        del labels
        self.train_inputs = inputs
        validation = kwargs.get("validation_data")
        if validation is not None:
            self.validation_inputs = validation[0]
        return self.history

    def predict(self, inputs, verbose=0):
        del inputs, verbose
        return np.full((1, self.width), 1.0 / self.width)

    def save(self, path) -> None:
        Path(path).write_text("ok", encoding="utf-8")


def _dated_batch(
        league_ids: np.ndarray) -> tuple[SequenceBatch, np.ndarray]:
    rows = len(league_ids)
    home = np.zeros((rows, 2, 1), dtype=np.float32)
    away = np.ones((rows, 2, 1), dtype=np.float32)
    static = np.arange(rows, dtype=np.float32).reshape(rows, 1)
    dates = np.array([
        "2026-01-01",
        "2026-02-01",
        "2026-06-01",
        "2026-08-01"], dtype="datetime64[ns]")
    return SequenceBatch(home, away, static, league_ids), dates


def test_trainers_save_vocabulary_from_the_training_window(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    league_ids = np.array([45, 7, 99, 3])
    batch, dates = _dated_batch(league_ids)
    captured = _CaptureModel(3)
    sizes: dict[str, object] = {}

    def _build(*args: object, **kwargs: object) -> _CaptureModel:
        del kwargs
        sizes["lstm"] = args[5]
        return captured

    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        lstm_trainer,
        "_prepare_training_data",
        lambda config: (batch, np.zeros(4, dtype=np.int64), dates))
    monkeypatch.setattr(lstm_trainer, "build_dual_lstm_classifier", _build)
    artifact_dir = tmp_path / "lstm"
    LstmTrainer().train(_split_config(
        artifact_dir, league_embedding_dim=4))
    assert load_league_vocab(artifact_dir) == [7, 45]
    assert sizes["lstm"] == 2
    assert captured.train_inputs is not None
    assert captured.validation_inputs is not None
    assert captured.train_inputs[3].reshape(-1).tolist() == [2, 1]
    assert captured.validation_inputs[3].reshape(-1).tolist() == [0]

    poisson_model = _CaptureModel(2)
    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros((4, 2), dtype=np.float32), dates))
    def _poisson_build(*args: object, **kwargs: object) -> _CaptureModel:
        del kwargs
        sizes["poisson"] = args[4]
        return poisson_model

    monkeypatch.setattr(
        poisson_trainer, "build_poisson_model", _poisson_build)
    poisson_dir = tmp_path / "poisson"
    PoissonTrainer().train(_split_config(
        poisson_dir,
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        league_embedding_dim=4))
    assert load_league_vocab(poisson_dir) == [7, 45]
    assert sizes["poisson"] == 2
    assert poisson_model.train_inputs is not None
    assert poisson_model.train_inputs[3].reshape(-1).tolist() == [2, 1]


def test_embedding_training_requires_league_ids(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, dates = _window_payload()
    monkeypatch.setattr(
        lstm_trainer,
        "_prepare_training_data",
        lambda config: (batch, np.zeros(4, dtype=np.int64), dates))
    with pytest.raises(ValueError, match="league_ids"):
        LstmTrainer().train(_split_config(
            tmp_path, league_embedding_dim=4))


def test_load_future_models_reads_vocab_only_for_an_embedding(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        predictor.artifacts, "load_keras_model_artifact", lambda path: "model")
    monkeypatch.setattr(
        predictor.artifacts, "load_scaler_artifact", lambda path: None)
    plain = predictor.load_future_models(
        _config(artifact_dir=str(tmp_path / "plain")), None, None)
    assert plain.result_league_vocab is None
    embedded_dir = tmp_path / "embedded"
    save_league_vocab(embedded_dir, [7, 45])
    loaded = predictor.load_future_models(
        _config(artifact_dir=str(embedded_dir), league_embedding_dim=4),
        None,
        None)
    assert loaded.result_league_vocab == [7, 45]
    assert loaded.btts_league_vocab is None
    with pytest.raises(FileNotFoundError, match="league_vocab"):
        predictor.load_future_models(
            _config(
                artifact_dir=str(tmp_path / "missing"),
                league_embedding_dim=4),
            None,
            None)


def test_predictor_maps_an_unknown_league_to_zero() -> None:
    captured: dict[str, np.ndarray] = {}

    class _Model:
        def predict(self, inputs, verbose=0):
            del verbose
            captured["index"] = np.asarray(inputs[3])
            return np.asarray([[0.2, 0.5, 0.3]], dtype=float)

    batch = SequenceBatch(
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 1), dtype=np.float32),
        np.array([99]))

    def _provider(matchup, config, context=None):
        del matchup, config, context
        return batch

    model = predictor.FutureEventsPredictor(
        result_config=_config(league_embedding_dim=4),
        models=predictor.LoadedFutureModels(
            result_model=_Model(),
            result_league_vocab=[1, 7]),
        feature_provider=_provider)
    model.predict_pair(MatchupInput(
        home_team_id=1,
        away_team_id=2,
        league_id=99,
        as_of_date=date(2026, 11, 1)))
    assert captured["index"].reshape(-1).tolist() == [0]


class _Scaler:
    def transform(self, values: np.ndarray) -> np.ndarray:
        return values


def test_candidate_scoring_maps_an_unknown_league_to_zero(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    save_league_vocab(tmp_path, [7, 45])
    captured: dict[str, np.ndarray] = {}

    class _Model:
        def predict(self, inputs, verbose=0):
            del verbose
            captured["index"] = np.asarray(inputs[3])
            return np.asarray([[0.2, 0.3, 0.5]], dtype=float)

    monkeypatch.setattr(
        candidates.artifacts,
        "load_keras_model_artifact",
        lambda path: _Model())
    monkeypatch.setattr(
        candidates.artifacts,
        "load_scaler_artifact",
        lambda path, required=False: _Scaler())
    batch = SequenceBatch(
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 1), dtype=np.float32),
        np.array([99]))
    candidates._predict_rows(
        _config(artifact_dir=str(tmp_path), league_embedding_dim=4),
        batch,
        np.array([0]),
        "v3")
    assert captured["index"].reshape(-1).tolist() == [0]


def test_candidate_requires_league_vocab_before_history(
        tmp_path: Path) -> None:
    directory = tmp_path / "artifact"
    directory.mkdir()
    (directory / "model.keras").write_text("x", encoding="utf-8")
    (directory / "scaler.joblib").write_text("x", encoding="utf-8")
    candidates._require_saved_model(
        directory, "v2", _config(artifact_dir=str(directory)))
    with pytest.raises(FileNotFoundError, match="v3"):
        candidates._require_saved_model(
            directory,
            "v3",
            _config(artifact_dir=str(directory), league_embedding_dim=4))


class _WeightCapture:
    def __init__(self, width: int) -> None:
        self.width = width
        self.history = _History()
        self.kwargs: dict[str, Any] = {}

    def fit(self, inputs, labels, **kwargs):
        del inputs, labels
        self.kwargs = kwargs
        return self.history

    def predict(self, inputs, verbose=0):
        del verbose
        count = len(inputs[0])
        return np.full((count, self.width), 1.0 / self.width)

    def save(self, path) -> None:
        Path(path).write_text("ok", encoding="utf-8")


def _assert_training_weights(
        kwargs: dict[str, Any],
        train_dates: np.ndarray,
        half_life: int) -> None:
    weights = np.asarray(kwargs["sample_weight"], dtype=np.float64)
    reference = np.datetime64(np.max(train_dates), "ns")
    expected = recency_sample_weights(train_dates, reference, half_life)
    assert np.allclose(weights, expected)
    assert float(np.mean(weights)) == pytest.approx(1.0)
    newest = int(np.argmax(train_dates))
    assert float(weights[newest]) == pytest.approx(float(np.max(weights)))
    assert len(kwargs["validation_data"]) == 2


def test_recency_weights_are_fit_only_on_the_training_window(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, dates = _window_payload()
    captured = _WeightCapture(3)
    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        lstm_trainer,
        "_prepare_training_data",
        lambda config: (batch, np.zeros(4, dtype=np.int64), dates))
    monkeypatch.setattr(
        lstm_trainer,
        "build_dual_lstm_classifier",
        lambda *args, **kwargs: captured)
    LstmTrainer().train(_split_config(tmp_path / "plain"))
    assert "sample_weight" not in captured.kwargs
    LstmTrainer().train(_split_config(
        tmp_path / "weighted", recency_half_life_days=365))
    # Styczeń i luty są oknem treningowym; czerwiec i sierpień nie.
    _assert_training_weights(captured.kwargs, dates[:2], 365)
    fraction = _WeightCapture(3)
    monkeypatch.setattr(
        lstm_trainer,
        "build_dual_lstm_classifier",
        lambda *args, **kwargs: fraction)
    LstmTrainer().train(_config(
        artifact_dir=str(tmp_path / "fraction"),
        epochs=1,
        recency_half_life_days=30))
    # Ułamek 0.15 zostawia trzy najstarsze mecze w treningu.
    _assert_training_weights(fraction.kwargs, dates[:3], 30)
    poisson_model = _WeightCapture(2)
    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros((4, 2), dtype=np.float32), dates))
    monkeypatch.setattr(
        poisson_trainer,
        "build_poisson_model",
        lambda *args, **kwargs: poisson_model)
    PoissonTrainer().train(_split_config(
        tmp_path / "poisson",
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        recency_half_life_days=365))
    _assert_training_weights(poisson_model.kwargs, dates[:2], 365)


def test_poisson_nll_returns_one_value_per_sample() -> None:
    tensorflow = pytest.importorskip("tensorflow")
    inputs = tensorflow.keras.Input(shape=(1,))
    outputs = tensorflow.keras.layers.Dense(2, use_bias=False)(inputs)
    model = tensorflow.keras.Model(inputs, outputs)
    weight = np.array([[0.2, -0.4]], dtype=np.float32)
    model.layers[-1].set_weights([weight])
    model.compile(optimizer="sgd", loss=poisson_nll)
    features = np.ones((2, 1), dtype=np.float32)
    targets = np.array([[0.0, 1.0], [3.0, 0.0]], dtype=np.float32)
    predicted = model.predict(features, verbose=0)
    per_sample = np.asarray(poisson_nll(
        tensorflow.constant(targets),
        tensorflow.constant(predicted)))
    assert per_sample.shape == (2,)
    plain = model.evaluate(features, targets, verbose=0)
    assert plain == pytest.approx(float(np.mean(per_sample)))
    weights = np.array([1.0, 3.0], dtype=np.float32)
    weighted = model.evaluate(
        features, targets, sample_weight=weights, verbose=0)
    # Keras dzieli przez liczbę próbek, nie przez sumę wag.
    expected = float(np.sum(per_sample * weights) / len(per_sample))
    assert weighted == pytest.approx(expected)
