"""Date windows for future-event training."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from models.pipeline.core.config import ChronoSplit


@dataclass(frozen=True)
class SplitIndexes:
    """Row positions for train, validation and calibration.

    ``validation`` is empty only when ``validation_from`` is omitted
    (fixed-epoch refit). ``calibration`` is empty when
    ``calibration_from`` is omitted.
    """

    train: np.ndarray
    validation: np.ndarray
    calibration: np.ndarray


def split_by_dates(
        dates: np.ndarray,
        split: ChronoSplit,
        date_to: date) -> SplitIndexes:
    """Split samples into half-open windows ending at ``date_to``.

    Train is strictly before the first boundary. Validation starts at
    ``validation_from``. Calibration starts at ``calibration_from``.
    The frozen test begins at ``date_to`` and is not returned.
    """
    stamps = np.asarray(dates, dtype="datetime64[ns]")
    if stamps.ndim != 1:
        raise ValueError("dates must be a one-dimensional array")
    order = np.argsort(stamps, kind="stable")
    ordered = stamps[order]
    train_end = split.validation_from or split.calibration_from or date_to
    train = _window(order, ordered, None, train_end)
    validation = _optional_window(
        order,
        ordered,
        split.validation_from,
        split.calibration_from or date_to)
    calibration = _optional_window(
        order, ordered, split.calibration_from, date_to)
    assigned = len(train) + len(validation) + len(calibration)
    if assigned != len(stamps):
        raise ValueError("dates must be strictly before date_to")
    _require_rows("train", train)
    if split.validation_from is not None:
        _require_rows("validation", validation)
    if split.calibration_from is not None:
        _require_rows("calibration", calibration)
    return SplitIndexes(
        train=train,
        validation=validation,
        calibration=calibration)


def _optional_window(
        order: np.ndarray,
        ordered: np.ndarray,
        start: date | None,
        end: date) -> np.ndarray:
    if start is None:
        return np.array([], dtype=np.int64)
    return _window(order, ordered, start, end)


def _window(
        order: np.ndarray,
        ordered: np.ndarray,
        start: date | None,
        end: date) -> np.ndarray:
    # Prawostronnie otwarte, żeby dzień graniczny nie wpadł do dwóch okien.
    mask = ordered < np.datetime64(end, "ns")
    if start is not None:
        mask = mask & (ordered >= np.datetime64(start, "ns"))
    return np.asarray(order[mask], dtype=np.int64)


def _require_rows(name: str, indexes: np.ndarray) -> None:
    if len(indexes) == 0:
        raise ValueError(f"{name} window is empty")
