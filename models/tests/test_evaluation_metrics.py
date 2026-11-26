"""Tests for champion and challenger probability metrics."""

from __future__ import annotations

import math

import numpy as np
import pytest

from models.pipeline.evaluation.metrics import binary_brier
from models.pipeline.evaluation.metrics import binary_log_loss
from models.pipeline.evaluation.metrics import expected_calibration_error
from models.pipeline.evaluation.metrics import final_shares
from models.pipeline.evaluation.metrics import multiclass_brier
from models.pipeline.evaluation.metrics import multiclass_log_loss
from models.pipeline.evaluation.metrics import paired_bootstrap_diff
from models.pipeline.evaluation.metrics import per_match_log_loss
from models.pipeline.evaluation.metrics import reliability_table


def test_binary_scores_match_the_hand_formula() -> None:
    probabilities = np.array([0.8, 0.25])
    outcomes = np.array([1, 0])
    expected_loss = -(math.log(0.8) + math.log(0.75)) / 2.0
    expected_brier = (0.2 ** 2 + 0.25 ** 2) / 2.0
    assert binary_log_loss(probabilities, outcomes) == pytest.approx(
        expected_loss)
    assert binary_brier(probabilities, outcomes) == pytest.approx(
        expected_brier)


def test_multiclass_scores_match_the_hand_formula() -> None:
    probabilities = np.array([
        [0.7, 0.2, 0.1],
        [0.1, 0.2, 0.7]
    ])
    labels = np.array([0, 2])
    per_match = per_match_log_loss(probabilities, labels)
    assert per_match == pytest.approx([-math.log(0.7), -math.log(0.7)])
    assert multiclass_log_loss(probabilities, labels) == pytest.approx(
        float(np.mean(per_match)))
    # Suma kwadratów po klasach, potem średnia: 0.3^2 + 0.2^2 + 0.1^2.
    assert multiclass_brier(probabilities, labels) == pytest.approx(0.14)


def test_log_loss_clips_a_zero_probability_at_one_e_minus_12() -> None:
    expected = -math.log(1e-12)
    assert binary_log_loss(
        np.array([0.0]), np.array([1])) == pytest.approx(expected)
    assert multiclass_log_loss(
        np.array([[0.0, 1.0]]), np.array([0])) == pytest.approx(expected)


def test_per_match_log_loss_treats_two_columns_as_binary() -> None:
    probabilities = np.array([0.2, 0.8])
    outcomes = np.array([0, 1])
    two_columns = np.column_stack([1.0 - probabilities, probabilities])
    vector = per_match_log_loss(probabilities, outcomes)
    matrix = per_match_log_loss(two_columns, outcomes)
    assert vector == pytest.approx([-math.log(0.8), -math.log(0.8)])
    assert matrix == pytest.approx(vector)


def test_expected_calibration_error_is_zero_when_perfect() -> None:
    assert expected_calibration_error(
        np.array([0.0, 0.0, 1.0, 1.0]),
        np.array([0, 0, 1, 1])) == pytest.approx(0.0)
    assert expected_calibration_error(
        np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]),
        np.array([0, 1, 2])) == pytest.approx(0.0)


def test_expected_calibration_error_weights_bins_by_count() -> None:
    probabilities = np.array([0.05, 0.05, 0.85, 0.85, 0.85])
    outcomes = np.array([0, 0, 1, 1, 0])
    # 2/5 * 0.05 + 3/5 * |0.85 - 2/3| = 0.13
    assert expected_calibration_error(
        probabilities, outcomes, bins=10) == pytest.approx(0.13)


def test_multiclass_calibration_error_averages_one_vs_rest() -> None:
    probabilities = np.array([
        [0.2, 0.3, 0.5],
        [0.6, 0.2, 0.2]
    ])
    assert expected_calibration_error(
        probabilities, np.array([2, 0]), bins=2) == pytest.approx(0.3)


def test_reliability_table_names_bins_and_skips_empty_ones() -> None:
    rows = reliability_table(
        np.array([0.42, 0.44, 0.1, 0.9]),
        np.array([1, 0, 0, 1]),
        [0.0, 0.4, 0.45, 0.5, 1.0])
    assert [row["bin"] for row in rows] == ["0-40", "40-45", "50-100"]
    middle = rows[1]
    assert middle["n"] == 2
    assert middle["mean_p"] == pytest.approx(0.43)
    assert middle["actual"] == pytest.approx(0.5)


def test_reliability_table_includes_the_right_edge() -> None:
    rows = reliability_table(np.array([1.0]), np.array([1]), [0.0, 1.0])
    assert rows[0]["bin"] == "0-100"
    assert rows[0]["n"] == 1
    assert rows[0]["actual"] == pytest.approx(1.0)


def test_final_shares_cover_every_class() -> None:
    assert final_shares(np.array([0, 0, 1, 2]), 3) == pytest.approx(
        [0.5, 0.25, 0.25])


def test_paired_bootstrap_diff_repeats_for_the_same_seed() -> None:
    loss_a = np.array([0.2, 0.4, 0.1, 0.5, 0.3])
    loss_b = np.array([0.3, 0.2, 0.2, 0.4, 0.35])
    first = paired_bootstrap_diff(loss_a, loss_b, 200, 42)
    second = paired_bootstrap_diff(loss_a, loss_b, 200, 42)
    assert first == second
    assert first["mean_diff"] == pytest.approx(float(np.mean(loss_a - loss_b)))
    assert first["ci_low"] <= first["ci_high"]


def test_paired_bootstrap_diff_rejects_different_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        paired_bootstrap_diff(
            np.array([0.1, 0.2]),
            np.array([0.1]),
            20,
            1)
