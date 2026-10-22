"""Proportional fair probability for one bookmaker's complete market."""

from __future__ import annotations

import math


def fair_probability(
        implied: object,
        implied_sum: object,
        priced_outcomes: object,
        market_size: object) -> float:
    """Return implied divided by the bookmaker's overround.

    The share is empty unless ``priced_outcomes`` equals ``market_size``.
    A partial board, including a top-five exact score, stays empty.
    """
    if not _is_complete_market(priced_outcomes, market_size):
        return math.nan
    implied_ok = _is_positive_finite(implied)
    sum_ok = _is_positive_finite(implied_sum)
    if not implied_ok or not sum_ok:
        return math.nan
    share = float(implied) / float(implied_sum)
    if not math.isfinite(share) or share <= 0.0 or share > 1.0:
        return math.nan
    return share


def _is_complete_market(priced_outcomes: object, market_size: object) -> bool:
    """Return whether every outcome of the market has one price."""
    priced = _integral(priced_outcomes)
    size = _integral(market_size)
    if priced is None or size is None:
        return False
    return size >= 2 and priced == size


def _is_positive_finite(value: object) -> bool:
    """Return whether the value is a finite number above zero."""
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def _integral(value: object) -> int | None:
    """Return an int when the value is a whole number."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)
