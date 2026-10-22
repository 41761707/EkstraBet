"""Fair probability from one bookmaker's complete overround."""

from __future__ import annotations

import math

import pytest

from models.pipeline.betting.devig import fair_probability


def test_two_three_three_shares_are_three_sevenths_and_two_sevenths() -> None:
    implied = (1.0 / 2.0, 1.0 / 3.0, 1.0 / 3.0)
    total = sum(implied)
    shares = [
        fair_probability(price, total, 3, 3)
        for price in implied]
    assert shares[0] == pytest.approx(3.0 / 7.0)
    assert shares[1] == pytest.approx(2.0 / 7.0)
    assert shares[2] == pytest.approx(2.0 / 7.0)
    assert sum(shares) == pytest.approx(1.0)


def test_partial_board_stays_empty() -> None:
    assert math.isnan(fair_probability(0.2, 0.8, 5, 36))
    assert math.isnan(fair_probability(0.5, 7.0 / 6.0, 2, 3))
    assert math.isnan(fair_probability(0.5, 1.0, 1, 1))


def test_non_positive_inputs_stay_empty() -> None:
    assert math.isnan(fair_probability(0.0, 1.0, 2, 2))
    assert math.isnan(fair_probability(0.5, 0.0, 2, 2))
    assert math.isnan(fair_probability(None, 1.0, 2, 2))
    assert math.isnan(fair_probability(True, 1.0, 2, 2))
