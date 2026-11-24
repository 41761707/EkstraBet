"""Frozen-test probabilities for one saved football model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from models.pipeline.core import artifacts
from models.pipeline.core.artifacts import ARTIFACT_KERAS_MODEL_NAME
from models.pipeline.core.artifacts import ARTIFACT_SCALER_NAME
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import get_feature_builder
from models.pipeline.data.match_history_repository import (
    fetch_finished_matches)
from models.pipeline.prediction.score_matrix import derive_goal_markets
from models.pipeline.prediction.score_matrix import score_matrix_from_lambdas


FAMILY_RESULT = "result"
FAMILY_BTTS = "btts"
FAMILY_OVER_25 = "over_25"
CANDIDATE_ROLES = frozenset({"champion", "control", "challenger"})

_TASK_FAMILY = {
    "result": FAMILY_RESULT,
    "btts": FAMILY_BTTS,
    "goals_poisson": FAMILY_OVER_25}


@dataclass(frozen=True)
class EvaluationFrame:
    """Matches and outcomes shared by every probability column."""

    match_ids: np.ndarray
    league_ids: np.ndarray
    season_ids: np.ndarray
    dates: np.ndarray
    home_goals: np.ndarray
    away_goals: np.ndarray


@dataclass(frozen=True)
class CandidateOutput:
    """One model's probabilities on its own match rows."""

    label: str
    role: str
    frame: EvaluationFrame
    families: dict[str, np.ndarray]
    result_finals: np.ndarray | None
    expected_goals: np.ndarray | None


def family_of_task(task_type: str) -> str:
    """Return the report family produced by a future-event task."""
    if task_type not in _TASK_FAMILY:
        raise ValueError(f"Task {task_type!r} has no evaluation family")
    return _TASK_FAMILY[task_type]


def load_candidate_output(
        label: str,
        role: str,
        config_path: Path,
        test_from: date,
        test_to: date) -> CandidateOutput:
    """Score one saved model on matches in ``[test_from, test_to)``.

    ``test_to`` is exclusive because finished-match history uses
    ``game_date < date_to``. Features still come only from earlier
    matches. A missing artifact names ``label`` and is reported
    before any database read.
    """
    if role not in CANDIDATE_ROLES:
        raise ValueError(f"Unknown candidate role {role!r}")
    if test_from >= test_to:
        raise ValueError("test_from must be before test_to")
    loaded = load_model_config(config_path)
    if not isinstance(loaded, FutureEventsRunConfig):
        raise ValueError(
            f"Candidate {label} config is not a future-event model")
    config = loaded.model_copy(update={"date_to": test_to})
    _require_saved_model(config.artifact_dir, label)
    payload = _training_payload(config)
    positions = _test_positions(payload.get("dates"), test_from, label)
    batch = _require_batch(payload, positions)
    values = _predict_rows(config, batch, positions, label)
    families, finals, expected = _families_from_task(
        config.task_type, values, config.max_goals, label)
    return CandidateOutput(
        label=label,
        role=role,
        frame=_slice_frame(payload, positions),
        families=families,
        result_finals=finals,
        expected_goals=expected)


def align_outputs(
        outputs: Sequence[CandidateOutput]) -> list[CandidateOutput]:
    """Keep the shared matches in the first candidate's order."""
    if isinstance(outputs, (str, bytes)) or not isinstance(outputs, Sequence):
        raise ValueError("outputs must be a sequence of candidates")
    rows = list(outputs)
    if not rows:
        raise ValueError("outputs must contain at least one candidate")
    indexes = [_match_index(item) for item in rows]
    shared = set(indexes[0])
    for index in indexes[1:]:
        shared &= set(index)
    if not shared:
        raise ValueError("candidates have no matches in common")
    # Kolejność pierwszego kandydata, żeby wiersze dało się porównać.
    order = [match_id for match_id in indexes[0] if match_id in shared]
    return [
        _slice_candidate(item, order, index)
        for item, index in zip(rows, indexes)]


def _families_from_task(
        task_type: str,
        values: np.ndarray,
        max_goals: int,
        label: str) -> tuple[
            dict[str, np.ndarray], np.ndarray | None, np.ndarray | None]:
    """Map a raw ``model.predict`` array onto report families."""
    family = family_of_task(task_type)
    if family == FAMILY_RESULT:
        matrix = _class_matrix(values, 3, label)
        return (
            {FAMILY_RESULT: matrix},
            np.argmax(matrix, axis=1).astype(int),
            None)
    if family == FAMILY_BTTS:
        matrix = _class_matrix(values, 2, label)
        return ({FAMILY_BTTS: matrix[:, 1]}, None, None)
    over, expected = _over_and_expected(values, max_goals, label)
    return ({FAMILY_OVER_25: over}, None, expected)


def _require_saved_model(artifact_dir: Path, label: str) -> None:
    """Reject a candidate before history is loaded."""
    # Literówka w spec nie powinna otwierać bazy ani budować cech.
    directory = Path(artifact_dir)
    model_file = directory / ARTIFACT_KERAS_MODEL_NAME
    scaler_file = directory / ARTIFACT_SCALER_NAME
    if model_file.is_file() and scaler_file.is_file():
        return
    raise FileNotFoundError(
        f"Candidate {label} is missing an artifact in {directory}")


def _training_payload(config: FutureEventsRunConfig) -> dict[str, object]:
    matches = fetch_finished_matches(config.sport_id, config.date_to)
    if matches.empty:
        raise ValueError("No finished matches available for evaluation")
    builder = get_feature_builder(config.feature_builder)
    method = getattr(builder, "build_training_batch", None)
    if method is None:
        raise TypeError(
            f"{type(builder).__name__} must implement build_training_batch")
    payload = method(matches, config)
    if not isinstance(payload, dict):
        raise TypeError("Feature builder must return a training payload")
    return payload


def _test_positions(
        dates: object,
        test_from: date,
        label: str) -> np.ndarray:
    if dates is None:
        raise ValueError("Training payload is missing dates")
    stamps = np.asarray(dates, dtype="datetime64[ns]")
    if stamps.ndim != 1:
        raise ValueError("Training dates must be one-dimensional")
    positions = np.flatnonzero(stamps >= np.datetime64(test_from))
    if positions.size == 0:
        raise ValueError(
            f"Candidate {label} has no matches on or after {test_from}")
    return positions


def _require_batch(
        payload: dict[str, object],
        positions: np.ndarray) -> SequenceBatch:
    batch = payload.get("batch")
    if not isinstance(batch, SequenceBatch):
        raise TypeError("Feature builder did not return SequenceBatch")
    if batch.X_home.shape[0] <= int(positions.max()):
        raise ValueError("Training batch is shorter than the date mask")
    return batch


def _predict_rows(
        config: FutureEventsRunConfig,
        batch: SequenceBatch,
        positions: np.ndarray,
        label: str) -> np.ndarray:
    try:
        scaler = artifacts.load_scaler_artifact(
            config.artifact_dir, required=True)
        model = artifacts.load_keras_model_artifact(config.artifact_dir)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Candidate {label} is missing an artifact: {exc}") from exc
    if scaler is None:
        raise FileNotFoundError(
            f"Candidate {label} is missing a scaler artifact")
    window = SequenceBatch(
        X_home=batch.X_home[positions],
        X_away=batch.X_away[positions],
        X_static=scaler.transform(batch.X_static[positions]))
    values = model.predict(
        [window.X_home, window.X_away, window.X_static],
        verbose=0)
    return np.asarray(values, dtype=float)


def _slice_frame(
        payload: dict[str, object],
        positions: np.ndarray) -> EvaluationFrame:
    return EvaluationFrame(
        match_ids=_payload_column(payload, "match_ids", positions),
        league_ids=_payload_column(payload, "league_ids", positions),
        season_ids=_payload_column(payload, "season_ids", positions),
        dates=_payload_column(payload, "dates", positions),
        home_goals=_payload_column(payload, "home_goals", positions),
        away_goals=_payload_column(payload, "away_goals", positions))


def _payload_column(
        payload: dict[str, object],
        name: str,
        positions: np.ndarray) -> np.ndarray:
    if name not in payload:
        raise ValueError(f"Training payload is missing {name}")
    values = np.asarray(payload[name])
    if len(values) <= int(positions.max()):
        raise ValueError(f"Training payload {name} is shorter than the batch")
    return values[positions]


def _class_matrix(
        values: np.ndarray,
        classes: int,
        label: str) -> np.ndarray:
    """Return row-normalized class probabilities."""
    # Ten sam clip co przy zapisie predykcji, żeby raport liczył ten sam wektor.
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    if matrix.ndim != 2 or matrix.shape != (matrix.shape[0], classes):
        raise ValueError(
            f"Candidate {label} must output shape (n, {classes})")
    if matrix.shape[0] == 0:
        raise ValueError(f"Candidate {label} returned no matches")
    if not np.isfinite(matrix).all():
        raise ValueError(
            f"Candidate {label} returned non-finite probabilities")
    clipped = np.clip(matrix, 0.0, None)
    totals = clipped.sum(axis=1, keepdims=True)
    if np.any(totals <= 0.0):
        raise ValueError(
            f"Candidate {label} returned no positive probability mass")
    return clipped / totals


def _over_and_expected(
        values: np.ndarray,
        max_goals: int,
        label: str) -> tuple[np.ndarray, np.ndarray]:
    rates = np.asarray(values, dtype=float)
    if rates.ndim == 1:
        rates = rates.reshape(1, -1)
    if rates.ndim != 2 or rates.shape[1] != 2 or rates.shape[0] == 0:
        raise ValueError(
            f"Candidate {label} must output shape (n, 2) lambdas")
    if not np.isfinite(rates).all():
        raise ValueError(f"Candidate {label} returned non-finite lambdas")
    rates = np.maximum(rates, 0.0)
    over = np.empty(rates.shape[0], dtype=float)
    for index in range(rates.shape[0]):
        home = float(rates[index, 0])
        away = float(rates[index, 1])
        matrix = score_matrix_from_lambdas(home, away, max_goals)
        markets = derive_goal_markets(matrix, home, away)
        over[index] = float(markets["over_25"])
    expected = rates[:, 0] + rates[:, 1]
    return np.clip(over, 0.0, 1.0), expected


def _match_index(output: CandidateOutput) -> dict[int, int]:
    _check_widths(output)
    index: dict[int, int] = {}
    for position, match_id in enumerate(output.frame.match_ids.tolist()):
        number = int(match_id)
        if number in index:
            raise ValueError(
                f"Candidate {output.label} repeats match {number}")
        index[number] = position
    return index


def _check_widths(output: CandidateOutput) -> None:
    count = len(output.frame.match_ids)
    columns: list[np.ndarray] = list(output.families.values())
    if output.result_finals is not None:
        columns.append(output.result_finals)
    if output.expected_goals is not None:
        columns.append(output.expected_goals)
    columns.extend([
        output.frame.league_ids,
        output.frame.season_ids,
        output.frame.dates,
        output.frame.home_goals,
        output.frame.away_goals])
    for values in columns:
        if len(values) != count:
            raise ValueError(
                f"Candidate {output.label} fields must share one length")


def _slice_candidate(
        output: CandidateOutput,
        order: list[int],
        index: dict[int, int]) -> CandidateOutput:
    positions = np.asarray(
        [index[match_id] for match_id in order], dtype=int)
    frame = output.frame
    return CandidateOutput(
        label=output.label,
        role=output.role,
        frame=EvaluationFrame(
            match_ids=frame.match_ids[positions],
            league_ids=frame.league_ids[positions],
            season_ids=frame.season_ids[positions],
            dates=frame.dates[positions],
            home_goals=frame.home_goals[positions],
            away_goals=frame.away_goals[positions]),
        families={
            name: values[positions]
            for name, values in output.families.items()},
        result_finals=_slice_optional(output.result_finals, positions),
        expected_goals=_slice_optional(output.expected_goals, positions))


def _slice_optional(
        values: np.ndarray | None,
        positions: np.ndarray) -> np.ndarray | None:
    if values is None:
        return None
    return values[positions]
