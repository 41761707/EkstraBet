"""Temperature and isotonic calibration for football classifiers.

The fit runs on the calibration window only. Inference applies the
saved temperature first and, for BTTS, an isotonic map on P(yes).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import log_loss


# Jedyna nazwa okna, na którym ten moduł dopasowuje temperaturę.
_CALIBRATION_WINDOW = "calibration"
_TEMPERATURE_BOUNDS = (0.3, 5.0)
_PROBABILITY_FLOOR = 1e-12


def fit_temperature(
        probabilities: np.ndarray,
        labels: np.ndarray) -> float:
    """Return the temperature that minimizes log loss on this window.

    The objective is ``softmax(log(p) / T)``. A window that does not
    contain both BTTS classes, or all three 1X2 classes, raises
    ``ValueError`` and names the calibration window.
    """
    matrix = _probability_matrix(probabilities)
    _require_window_classes(matrix, labels)
    observed = np.asarray(labels)

    def _objective(temperature: float) -> float:
        adjusted = apply_temperature(matrix, float(temperature))
        return _log_loss(observed, adjusted)

    fitted = minimize_scalar(
        _objective,
        bounds=_TEMPERATURE_BOUNDS,
        method="bounded")
    if not fitted.success:
        raise ValueError(
            f"{_CALIBRATION_WINDOW} window temperature fit failed")
    return float(fitted.x)


def apply_temperature(
        probabilities: np.ndarray,
        temperature: float) -> np.ndarray:
    """Return ``softmax(log(p) / T)`` with the input's rank preserved."""
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    matrix = _probability_matrix(probabilities)
    single_row = np.asarray(probabilities).ndim == 1
    if matrix.shape[0] == 0:
        restored = matrix
    else:
        clipped = np.clip(matrix, _PROBABILITY_FLOOR, None)
        scaled = np.log(clipped) / float(temperature)
        # max w wierszu trzyma exp(log(p) / T) w zakresie float
        scaled -= np.max(scaled, axis=1, keepdims=True)
        exp_values = np.exp(scaled)
        restored = exp_values / np.sum(exp_values, axis=1, keepdims=True)
    if single_row:
        return restored[0]
    return restored


def fit_isotonic(
        p_yes: np.ndarray,
        outcomes: np.ndarray) -> IsotonicRegression:
    """Fit a clipped isotonic map from P(yes) to the BTTS outcome."""
    model = IsotonicRegression(out_of_bounds="clip")
    model.fit(np.asarray(p_yes, dtype=float), np.asarray(outcomes))
    return model


def apply_calibration(
        probabilities: np.ndarray,
        meta: dict[str, Any],
        calibrator: Any | None) -> np.ndarray:
    """Apply temperature, then BTTS isotonic, and normalize rows.

    ``calibration`` missing or ``none`` returns the input unchanged so
    a V2 artifact keeps today's probabilities.
    """
    mode = str(meta.get("calibration", "none"))
    if mode == "none":
        return np.asarray(probabilities, dtype=float)
    temperature = meta.get("temperature")
    if temperature is None:
        raise ValueError("calibration meta is missing temperature")
    matrix = _probability_matrix(probabilities)
    single_row = np.asarray(probabilities).ndim == 1
    adjusted = apply_temperature(matrix, float(temperature))
    if mode == "temperature_isotonic":
        adjusted = _apply_isotonic(adjusted, calibrator)
    elif mode != "temperature":
        raise ValueError(f"Unknown calibration mode: {mode}")
    else:
        adjusted = _normalize_rows(adjusted)
    if single_row:
        return adjusted[0]
    return adjusted


def _apply_isotonic(
        probabilities: np.ndarray,
        calibrator: Any | None) -> np.ndarray:
    """Map column 1 through the isotonic model and rebuild the pair."""
    if calibrator is None:
        raise ValueError(
            "temperature_isotonic calibration requires a calibrator")
    if probabilities.shape[1] != 2:
        raise ValueError(
            "temperature_isotonic calibration requires two classes")
    # Kolumna 1 to P(yes), tak jak label_btts i predyktor BTTS.
    p_yes = np.clip(
        np.asarray(calibrator.predict(probabilities[:, 1]), dtype=float),
        0.0,
        1.0)
    stacked = np.column_stack([1.0 - p_yes, p_yes])
    return _normalize_rows(stacked)


def _normalize_rows(probabilities: np.ndarray) -> np.ndarray:
    """Return non-negative rows that each sum to one."""
    clipped = np.clip(probabilities, 0.0, None)
    totals = clipped.sum(axis=1, keepdims=True)
    if np.any(totals <= 0.0):
        raise ValueError("calibration removed all probability mass")
    return clipped / totals


def _probability_matrix(probabilities: np.ndarray) -> np.ndarray:
    """Return a two-dimensional class matrix."""
    values = np.asarray(probabilities, dtype=float)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2:
        raise ValueError(
            "probabilities must be a one or two dimensional array")
    if values.shape[0] > 0 and values.shape[1] < 2:
        raise ValueError(
            "probabilities must contain at least two classes")
    return values


def _require_window_classes(
        probabilities: np.ndarray,
        labels: np.ndarray) -> None:
    """Reject a calibration window that misses a required class."""
    classes = int(probabilities.shape[1])
    if classes == 2:
        required = {0, 1}
        kind = "BTTS"
    elif classes == 3:
        required = {0, 1, 2}
        kind = "1X2"
    else:
        raise ValueError(
            f"{_CALIBRATION_WINDOW} window has {classes} "
            "probability columns")
    observed = {int(value) for value in np.asarray(labels).reshape(-1)}
    missing = sorted(required - observed)
    if missing:
        raise ValueError(
            f"{_CALIBRATION_WINDOW} window is missing {kind} "
            f"classes {missing}")


def _log_loss(labels: np.ndarray, probabilities: np.ndarray) -> float:
    classes = list(range(probabilities.shape[1]))
    return float(log_loss(labels, probabilities, labels=classes))
