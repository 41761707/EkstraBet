"""Pure stake-advice math. No database, API or model I/O."""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from backend.services.stake_advisor_config import AdvisorWeights


_PROBABILITY_MIN = 0.01
_PROBABILITY_MAX = 0.99
# Brak p modelu: 70% jego wagi przechodzi na pewność usera.
_MODEL_WEIGHT_TO_USER = 0.7
_MONEY_STEP = Decimal("0.01")

LIMIT_BANKROLL_PCT = "max_bankroll_pct"
LIMIT_MAX_UNITS = "max_units"


def blend_probability(
        model_p: float | None,
        implied_p: float,
        confidence_01: float,
        agent_liked: bool,
        cfg: AdvisorWeights) -> float:
    """Blend model, user confidence and the implied probability.

    A missing ``model_p`` moves that weight onto the user (70%) and
    the implied probability (the rest). ``implied_p`` is that
    probability. ``agent_liked`` then adds ``agent_boost``. The
    result stays inside [0.01, 0.99].
    """
    _require_finite(implied_p, "implied_p")
    p_user = _clip_probability(confidence_01)
    if model_p is None:
        weights = _weights_without_model(cfg)
        blended = (
            weights[0] * p_user
            + weights[1] * implied_p)
    else:
        _require_finite(model_p, "model_p")
        blended = (
            cfg.w_model * model_p
            + cfg.w_user * p_user
            + cfg.w_implied * implied_p)
    if agent_liked:
        blended += cfg.agent_boost
    return _clip_probability(blended)


def joint_probability(leg_ps: list[float]) -> float:
    """Return the product of per-leg probabilities.

    An accumulator treats legs as independent. One leg returns that
    leg's probability. An empty list is rejected.
    """
    if not leg_ps:
        raise ValueError("leg_ps must not be empty")
    product = 1.0
    for probability in leg_ps:
        _require_finite(probability, "leg probability")
        product *= probability
    return product


def fractional_kelly(p: float, odds: float, fraction: float) -> float:
    """Return a fractional Kelly stake share, or 0 when there is no edge.

    ``f = fraction * (p * odds - 1) / (odds - 1)``. A non-positive
    result is 0. A price of 1 or below has no Kelly denominator and
    is also 0.
    """
    _require_finite(p, "p")
    _require_finite(odds, "odds")
    _require_finite(fraction, "fraction")
    if fraction < 0.0:
        raise ValueError("fraction must be non-negative")
    if odds <= 1.0:
        return 0.0
    share = fraction * (p * odds - 1.0) / (odds - 1.0)
    if share <= 0.0:
        return 0.0
    return share


def apply_caps(
        raw_stake: float,
        balance: float,
        unit_size: float,
        cfg: AdvisorWeights) -> tuple[float, list[str]]:
    """Cap a raw stake by bankroll share and by max units.

    ``balance`` is the caller's basis. The bankroll cap uses
    ``max(balance, unit_size)``, so a debit does not force a zero
    suggestion from this function alone. The service passes
    ``max(current_balance, initial_capital)`` as ``balance``.
    Each cap is cut down to the cent before it binds. The stake
    then rounds half-up, so the rounded amount stays within the cap.
    """
    _require_finite(raw_stake, "raw_stake")
    _require_finite(balance, "balance")
    _require_finite(unit_size, "unit_size")
    if unit_size <= 0.0:
        raise ValueError("unit_size must be greater than 0")
    stake = raw_stake if raw_stake > 0.0 else 0.0
    basis = max(balance, unit_size)
    # Half-up stawki nie może przeskoczyć twardego capu.
    bankroll_cap = _floor_money(cfg.max_bankroll_pct * basis)
    units_cap = _floor_money(cfg.max_units * unit_size)
    limits: list[str] = []
    if stake > bankroll_cap:
        stake = bankroll_cap
        limits.append(LIMIT_BANKROLL_PCT)
    if stake > units_cap:
        stake = units_cap
        limits.append(LIMIT_MAX_UNITS)
    return _round_money(stake), limits


def _weights_without_model(cfg: AdvisorWeights) -> tuple[float, float]:
    """Return user and implied weights after the model drops out."""
    user_weight = cfg.w_user + cfg.w_model * _MODEL_WEIGHT_TO_USER
    implied_share = 1.0 - _MODEL_WEIGHT_TO_USER
    implied_weight = cfg.w_implied + cfg.w_model * implied_share
    return (user_weight, implied_weight)


def _clip_probability(value: float) -> float:
    """Keep a finite probability inside the open advice band."""
    _require_finite(value, "probability")
    if value < _PROBABILITY_MIN:
        return _PROBABILITY_MIN
    if value > _PROBABILITY_MAX:
        return _PROBABILITY_MAX
    return value


def _round_money(amount: float) -> float:
    """Round money half-up to two decimal places."""
    return _quantize_money(amount, ROUND_HALF_UP)


def _floor_money(amount: float) -> float:
    """Cut a non-negative amount down to the cent."""
    if amount <= 0.0:
        return 0.0
    return _quantize_money(amount, ROUND_DOWN)


def _quantize_money(amount: float, rounding: str) -> float:
    """Quantize money to one cent with the given rounding mode."""
    quantized = Decimal(str(amount)).quantize(
        _MONEY_STEP, rounding=rounding)
    return float(quantized)


def _require_finite(value: float, name: str) -> None:
    """Reject NaN and infinity before they reach a stake."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
