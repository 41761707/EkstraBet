"""Settle open tipster coupons from finished-match boxscore."""

from __future__ import annotations

import logging
from typing import Any
from typing import cast

import pandas as pd

from backend.repositories import tipster_repository as repo
from backend.sports.football.event_settlement_registry import MatchBoxscore
from backend.sports.football.outcome_evaluator import EventFamily
from backend.sports.football.outcome_evaluator import InvalidMatchResultError
from backend.sports.football.outcome_evaluator import SettlementCandidate
from backend.sports.football.outcome_evaluator import UnsupportedFootballEventError
from backend.sports.football.outcome_evaluator import VALID_MATCH_RESULTS
from backend.sports.football.outcome_evaluator import evaluate_football_outcome


_KNOWN_FAMILIES = frozenset({
    "REZULTAT", "BTTS", "OU", "GOALS", "EXACT"})
_FALLBACK_FAMILY: EventFamily = "OU"
_EMPTY_COUNTS = {
    "legs_settled": 0,
    "coupons_settled": 0,
    "legs_skipped": 0}

logger = logging.getLogger(__name__)


def settle_open_coupons() -> dict[str, int]:
    """Evaluate open legs and close coupons whose legs are all settled.

    Combined legs win only when every event is 1. Missing boxscore stats
    leave the leg open. Writes are idempotent (NULL / unsettled guards).
    """
    frame = repo.fetch_open_legs_for_finished_matches()
    if frame.empty:
        return dict(_EMPTY_COUNTS)
    legs_settled = 0
    legs_skipped = 0
    coupons_settled = 0
    for coupon in _group_coupon_graphs(frame):
        settled, skipped = _settle_open_legs(coupon)
        legs_settled += settled
        legs_skipped += skipped
        if _complete_ready_coupon(coupon):
            coupons_settled += 1
    return {
        "legs_settled": legs_settled,
        "coupons_settled": coupons_settled,
        "legs_skipped": legs_skipped}


def _settle_open_legs(coupon: dict[str, Any]) -> tuple[int, int]:
    """Write outcomes for evaluable open legs; skip pending stats."""
    settled = 0
    skipped = 0
    for leg in coupon["legs"]:
        if leg["outcome"] is not None:
            continue
        outcome = _evaluate_open_leg(leg)
        if outcome is None:
            skipped += 1
            continue
        repo.write_leg_outcome(leg["id"], outcome)
        leg["outcome"] = outcome
        settled += 1
    return settled, skipped


def _complete_ready_coupon(coupon: dict[str, Any]) -> bool:
    """Close the coupon when every in-memory leg is settled and SQL agrees."""
    outcomes = [leg["outcome"] for leg in coupon["legs"]]
    if not outcomes or any(value is None for value in outcomes):
        return False
    # rowcount 1 = ten worker zamknął kupon; 0 = no-op (wyścig / otwarta noga)
    return repo.complete_coupon(coupon["id"]) == 1


def _evaluate_open_leg(leg: dict[str, Any]) -> int | None:
    """Return 0/1 for a finished match, or None when stats are missing."""
    if leg["result"] not in VALID_MATCH_RESULTS:
        return None
    if not leg["events"]:
        return None
    event_outcomes: list[int] = []
    for event in leg["events"]:
        try:
            event_outcomes.append(
                evaluate_football_outcome(_candidate_from_leg(leg, event)))
        except InvalidMatchResultError:
            return None
        except UnsupportedFootballEventError:
            logger.warning(
                "Unsupported tipster event left open "
                "leg_id=%s event_id=%s event_name=%s",
                leg["id"],
                event["event_id"],
                event["event_name"])
            return None
    return 1 if all(value == 1 for value in event_outcomes) else 0


def _candidate_from_leg(
        leg: dict[str, Any], event: dict[str, Any]) -> SettlementCandidate:
    """Build a tipster_leg candidate for one event of a coupon leg."""
    return SettlementCandidate(
        record_id=int(leg["id"]),
        target="tipster_leg",
        event_id=int(event["event_id"]),
        event_name=str(event["event_name"]),
        family=event["family"],
        result=str(leg["result"]),
        home_goals=leg["home_goals"],
        away_goals=leg["away_goals"],
        match_id=int(leg["match_id"]),
        boxscore=leg["boxscore"])


def _group_coupon_graphs(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Nest DataFrame event rows into coupon → legs → events."""
    coupons: dict[int, dict[str, Any]] = {}
    legs: dict[int, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        coupon_id = int(row["coupon_id"])
        leg_id = int(row["leg_id"])
        if coupon_id not in coupons:
            coupons[coupon_id] = {
                "id": coupon_id,
                "legs": []}
        if leg_id not in legs:
            legs[leg_id] = _leg_from_row(row)
            coupons[coupon_id]["legs"].append(legs[leg_id])
        legs[leg_id]["events"].append({
            "event_id": int(row["event_id"]),
            "event_name": str(row["event_name"]),
            "family": _coerce_family(row.get("family"))})
    return list(coupons.values())


def _leg_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map one DataFrame row to a mutable leg document."""
    return {
        "id": int(row["leg_id"]),
        "match_id": int(row["match_id"]),
        "outcome": _optional_int(row.get("leg_outcome")),
        "result": _optional_str(row.get("result")),
        "home_goals": _optional_int(row.get("home_goals")),
        "away_goals": _optional_int(row.get("away_goals")),
        "boxscore": _boxscore_from_row(row),
        "events": []}


def _boxscore_from_row(row: dict[str, Any]) -> MatchBoxscore:
    """Build the evaluator boxscore from aliased match columns."""
    result = _optional_str(row.get("result")) or ""
    return MatchBoxscore(
        result=result,
        home_goals=_optional_int(row.get("home_goals")),
        away_goals=_optional_int(row.get("away_goals")),
        home_ck=_optional_int(row.get("home_ck")),
        away_ck=_optional_int(row.get("away_ck")),
        home_fouls=_optional_int(row.get("home_fouls")),
        away_fouls=_optional_int(row.get("away_fouls")),
        home_yc=_optional_int(row.get("home_yc")),
        away_yc=_optional_int(row.get("away_yc")),
        home_rc=_optional_int(row.get("home_rc")),
        away_rc=_optional_int(row.get("away_rc")),
        home_off=_optional_int(row.get("home_off")),
        away_off=_optional_int(row.get("away_off")))


def _coerce_family(value: object) -> EventFamily:
    """Use a typed family when the catalog has one; else OU as placeholder."""
    # Rożne/DNB/handicap nie mają wiersza w event_families — evaluator
    # i tak rozlicza je po id / parserze linii, nie po family.
    if isinstance(value, str) and value in _KNOWN_FAMILIES:
        return cast(EventFamily, value)
    return _FALLBACK_FAMILY


def _optional_int(value: Any) -> int | None:
    if _is_missing(value):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if _is_missing(value):
        return None
    return str(value)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
