"""Compose a stake suggestion. Does not write a coupon or a bankroll."""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any

from mysql.connector.errors import Error as MySQLError

from backend.database import DatabaseConnectionError
from backend.repositories.stake_advisor_repository import agent_liked
from backend.repositories.stake_advisor_repository import current_fingerprint
from backend.repositories.stake_advisor_repository import (
    fetch_published_probabilities)
from backend.repositories.stake_advisor_repository import fetch_verdicts
from backend.services.probability_service import to_unit_probability
from backend.services.stake_advisor_config import AGENT_LOOKBACK_DAYS
from backend.services.stake_advisor_config import AdvisorWeights
from backend.services.stake_advisor_math import apply_caps
from backend.services.stake_advisor_math import blend_probability
from backend.services.stake_advisor_math import fractional_kelly
from backend.services.stake_advisor_math import joint_probability
from backend.services.tipster_service import TipsterUnprocessableError
from backend.services.tipster_service import TipsterValidationError
from backend.services.tipster_service import _validated_legs
from backend.services.tipster_service import get_my_bankroll
from backend.services.tipster_service import quantize_catalog_odds


logger = logging.getLogger(__name__)

REASON_OK = "ok"
REASON_NO_BET = "no_bet_low_edge"
REASON_NO_PREDICTION = "no_prediction"
REASON_MODEL_NOT_READY = "model_not_ready"

_CATALOG = "catalog"
_CFG = AdvisorWeights()
_UNIT_STEP = Decimal("0.0001")
_READ_ERRORS = (MySQLError, DatabaseConnectionError, OSError)


def advise(
        user: dict[str, Any],
        request: dict[str, Any]) -> dict[str, Any]:
    """Return stake advice for one coupon draft.

    Legs use the same checks as coupon create. A missing bankroll
    raises the tipster not-found error. A read failure keeps the
    baseline probability and does not write anything.
    """
    confidence = _require_confidence(request)
    legs = _validated_legs(request.get("legs"))
    bankroll = get_my_bankroll(user)
    fingerprint = current_fingerprint()
    advised = [
        _advise_leg(leg, confidence, fingerprint)
        for leg in legs]
    return _response(bankroll, legs, advised, fingerprint)


def _require_confidence(request: dict[str, Any]) -> float:
    """Return confidence on the unit scale, or reject the payload."""
    if not isinstance(request, dict):
        raise TipsterUnprocessableError("Invalid stake advice request")
    raw = request.get("confidence")
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise TipsterUnprocessableError(
            "confidence must be an integer from 0 to 100")
    if raw < 0 or raw > 100:
        raise TipsterUnprocessableError(
            "confidence must be an integer from 0 to 100")
    return raw / 100.0


def _advise_leg(
        leg: dict[str, Any],
        confidence: float,
        fingerprint: str | None) -> dict[str, Any]:
    """Blend one validated leg. Implied probability is 1 / odds."""
    model_p = _model_probability(leg, fingerprint)
    implied = 1.0 / float(leg["odds"])
    liked = _agent_flag(leg)
    return {
        "match_id": int(leg["match_id"]),
        "event_ids": [int(event_id) for event_id in leg["event_ids"]],
        "model_probability": model_p,
        "implied_probability": implied,
        "agent_liked": liked,
        "p_used": blend_probability(
            model_p, implied, confidence, liked, _CFG)
    }


def _agent_flag(leg: dict[str, Any]) -> bool:
    """Return the system-agent flag. A read error is not a like."""
    event_ids = [int(event_id) for event_id in leg["event_ids"]]
    return bool(_read(
        lambda: agent_liked(
            int(leg["match_id"]),
            event_ids,
            AGENT_LOOKBACK_DAYS),
        False))


def _model_probability(
        leg: dict[str, Any],
        fingerprint: str | None) -> float | None:
    """Return the leg probability on the unit scale, or None."""
    event_ids = [int(event_id) for event_id in leg["event_ids"]]
    if len(event_ids) > 1:
        return _combined_probability(leg, event_ids)
    return _event_probability(leg, event_ids[0], fingerprint, True)


def _combined_probability(
        leg: dict[str, Any],
        event_ids: list[int]) -> float | None:
    """Product of published event probabilities. No EB-18 verdict."""
    parts = [
        _event_probability(leg, event_id, None, False)
        for event_id in event_ids]
    if any(part is None for part in parts):
        return None
    return joint_probability([float(part) for part in parts])


def _event_probability(
        leg: dict[str, Any],
        event_id: int,
        fingerprint: str | None,
        allow_verdict: bool) -> float | None:
    """Average published models, upgrading a matching catalog price."""
    rows = _read(
        lambda: fetch_published_probabilities(
            int(leg["match_id"]), event_id),
        [])
    if not rows:
        return None
    verdicts = _verdicts_for(rows, fingerprint, allow_verdict, leg)
    samples = _samples(rows, verdicts, leg, allow_verdict)
    if not samples:
        return None
    return sum(samples) / len(samples)


def _verdicts_for(
        rows: list[dict[str, Any]],
        fingerprint: str | None,
        allow_verdict: bool,
        leg: dict[str, Any]) -> list[dict[str, Any]]:
    """Load verdicts only for one catalog event with a ready digest."""
    if not allow_verdict or fingerprint is None:
        return []
    if not _catalog_single(leg):
        return []
    prediction_ids = [int(row["prediction_id"]) for row in rows]
    loaded = _read(
        lambda: fetch_verdicts(prediction_ids, fingerprint),
        [])
    return list(loaded)


def _samples(
        rows: list[dict[str, Any]],
        verdicts: list[dict[str, Any]],
        leg: dict[str, Any],
        allow_verdict: bool) -> list[float]:
    """One unit probability per published model."""
    samples: list[float] = []
    for row in rows:
        unit = _published_unit(row.get("value"))
        override = _override(verdicts, row, leg, allow_verdict)
        if override is not None:
            unit = override
        if unit is not None:
            samples.append(unit)
    return samples


def _catalog_single(leg: dict[str, Any]) -> bool:
    """Return True when the leg is one catalog event with a bookmaker."""
    if leg.get("source") != _CATALOG:
        return False
    if leg.get("bookmaker_id") is None:
        return False
    return len(leg["event_ids"]) == 1


def _override(
        verdicts: list[dict[str, Any]],
        row: dict[str, Any],
        leg: dict[str, Any],
        allow_verdict: bool) -> float | None:
    """Return calibrated probability when the odds row is the leg price.

    The stored value is already on the unit scale. Dividing it by 100
    would turn a real chance into a fraction of a percent.
    """
    if not allow_verdict or not verdicts:
        return None
    chosen = _best_verdict(verdicts, int(row["prediction_id"]), leg)
    if chosen is None:
        return None
    return _open_unit(chosen.get("calibrated_probability"))


def _best_verdict(
        verdicts: list[dict[str, Any]],
        prediction_id: int,
        leg: dict[str, Any]) -> dict[str, Any] | None:
    """Pick the lowest odds id among rows that quote this leg."""
    matches = [
        verdict
        for verdict in verdicts
        if int(verdict["prediction_id"]) == prediction_id
        and _same_price(verdict, leg)]
    if not matches:
        return None
    return min(matches, key=lambda item: int(item["odds_id"]))


def _same_price(verdict: dict[str, Any], leg: dict[str, Any]) -> bool:
    """Match match, event, bookmaker and the quantized catalog price."""
    if int(verdict["match_id"]) != int(leg["match_id"]):
        return False
    if int(verdict["event_id"]) != int(leg["event_ids"][0]):
        return False
    if int(verdict["bookmaker_id"]) != int(leg["bookmaker_id"]):
        return False
    verdict_odds = quantize_catalog_odds(float(verdict["odds"]))
    leg_odds = quantize_catalog_odds(float(leg["odds"]))
    return verdict_odds == leg_odds


def _published_unit(value: object) -> float | None:
    """Convert a stored percent, including the 0 and 100 ends.

    The open-interval cut belongs to calibrated probabilities.
    A published endpoint keeps the model weight in the blend.
    """
    number = _finite(value)
    if number is None:
        return None
    return to_unit_probability(number)


def _open_unit(value: object) -> float | None:
    """Keep a finite probability inside the open unit interval."""
    number = _finite(value)
    if number is None or number <= 0.0 or number >= 1.0:
        return None
    return number


def _finite(value: object) -> float | None:
    """Return a finite float, or None for a blank or non-numeric value."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _response(
        bankroll: dict[str, Any],
        legs: list[dict[str, Any]],
        advised: list[dict[str, Any]],
        fingerprint: str | None) -> dict[str, Any]:
    """Apply Kelly to the joint probability and cap the stake."""
    current = float(bankroll["current_balance"])
    initial = float(bankroll["initial_capital"])
    unit_size = float(bankroll["unit_size"])
    if unit_size <= 0.0:
        raise TipsterValidationError("unit_size must be greater than 0")
    # Saldo ujemne nie zeruje rady: kapitał startowy zostaje w podstawie.
    basis = max(current, initial, unit_size)
    odds = _combined_odds(legs)
    blend = joint_probability(
        [float(leg["p_used"]) for leg in advised])
    share = fractional_kelly(blend, odds, _CFG.kelly_fraction)
    stake, limits = apply_caps(
        share * basis, max(current, initial), unit_size, _CFG)
    return {
        "advice": {
            "suggested_stake": stake,
            "suggested_units": _units(stake, unit_size),
            "kelly_fraction": share,
            "p_blend": blend,
            "combined_odds": odds,
            "no_bet": stake == 0.0,
            "reason": _reason(share, advised, fingerprint),
            "legs": advised,
            "limits_applied": limits
        },
        "currency": str(bankroll["currency"]),
        "current_balance": current,
        "unit_size": unit_size
    }


def _reason(
        share: float,
        legs: list[dict[str, Any]],
        fingerprint: str | None) -> str:
    """Pick one reason. A zero Kelly share wins over the artifact gate."""
    if share <= 0.0:
        return REASON_NO_BET
    if all(leg["model_probability"] is None for leg in legs):
        return REASON_NO_PREDICTION
    if fingerprint is None:
        return REASON_MODEL_NOT_READY
    return REASON_OK


def _combined_odds(legs: list[dict[str, Any]]) -> float:
    """Return the product of per-leg odds."""
    product = Decimal("1")
    for leg in legs:
        product *= Decimal(str(leg["odds"]))
    return float(product)


def _units(stake: float, unit_size: float) -> float:
    """Convert money to units, half-up to four decimal places."""
    amount = Decimal(str(stake)) / Decimal(str(unit_size))
    quantized = amount.quantize(_UNIT_STEP, rounding=ROUND_HALF_UP)
    return float(quantized)


def _read(loader: Any, fallback: Any) -> Any:
    """Return ``fallback`` when a read fails. Advice still continues."""
    try:
        return loader()
    except _READ_ERRORS:
        logger.warning("Stake advisor read failed", exc_info=True)
        return fallback
