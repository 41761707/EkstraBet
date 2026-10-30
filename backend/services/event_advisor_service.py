"""Compose event suggestions from taste, the draft and the computer.

The service reads coupons and the future pool. It does not place a
coupon, change a bankroll, or store the suggestion.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

from backend.repositories import event_advisor_repository as advisor_repo
from backend.repositories.coupon_agent_repository import (
    ready_model_fingerprint)
from backend.repositories.user_favorite_league_repository import (
    fetch_favorite_league_ids)
from backend.services.event_advisor_config import AdvisorConfig
from backend.services.event_advisor_math import Candidate
from backend.services.event_advisor_math import HistoryRow
from backend.services.event_advisor_math import ScoredCandidate
from backend.services.event_advisor_math import TasteProfile
from backend.services.event_advisor_math import assign_tiers
from backend.services.event_advisor_math import build_profile
from backend.services.event_advisor_math import score_candidate
from backend.services.tipster_service import MAX_LEGS
from backend.services.tipster_service import MIN_ODDS
from backend.services.tipster_service import TipsterUnprocessableError
from backend.services.tipster_service import quantize_catalog_odds
from backend.timezone import WARSAW_TIME_ZONE


logger = logging.getLogger(__name__)

_CONFIG = AdvisorConfig()
_WARSAW = ZoneInfo(WARSAW_TIME_ZONE)
_SCORE_STEP = Decimal("0.001")
_TIER_NAMES = ("S", "A", "B")
# Cap 400 patrzy na affinity sprzed podbicia szkicu. To nie waga scoringu.
_KEEP_AFFINITY_MIN = 0.25


def suggest_events(
        user: dict[str, Any],
        request: dict[str, Any] | None) -> dict[str, Any]:
    """Return S/A/B suggestions for one draft. Nothing is stored.

    History belongs to this user only. A missing betting artifact
    still returns three tiers. An unknown draft match is left out
    of the pool and does not boost a league.
    """
    match_ids = _draft_match_ids(request)
    now = _warsaw_now()
    profile = _load_profile(_user_id(user), now)
    slip_leagues = _slip_league_ids(match_ids)
    pool = _candidate_pool(
        now, set(match_ids), slip_leagues, profile)
    scored = [
        score_candidate(candidate, profile, slip_leagues)
        for candidate in pool]
    return _response(profile, assign_tiers(scored))


def _draft_match_ids(request: object) -> list[int]:
    """Return unique draft match ids.

    The draft has no odds and no source, so coupon validation does
    not apply. A missing legs list is an empty slip. More than eight
    legs, a bad id, or the same match twice cannot be suggested.
    """
    raw_legs = _raw_legs(request)
    if len(raw_legs) > MAX_LEGS:
        raise TipsterUnprocessableError(
            "Draft must have at most 8 legs")
    match_ids: list[int] = []
    seen: set[int] = set()
    for raw in raw_legs:
        match_id = _leg_match_id(raw)
        if match_id in seen:
            raise TipsterUnprocessableError(
                "Duplicate match on draft")
        seen.add(match_id)
        match_ids.append(match_id)
    return match_ids


def _raw_legs(request: object) -> list[Any]:
    """Return draft legs. A missing list is an empty slip."""
    if request is None:
        return []
    if not isinstance(request, dict):
        raise TipsterUnprocessableError("Invalid suggest request")
    if "legs" not in request or request["legs"] is None:
        return []
    raw_legs = request["legs"]
    if not isinstance(raw_legs, list):
        raise TipsterUnprocessableError("legs must be a list")
    return list(raw_legs)


def _leg_match_id(raw: object) -> int:
    """Return one positive match id after the event ids check out."""
    if not isinstance(raw, dict):
        raise TipsterUnprocessableError("Invalid suggest leg")
    match_id = _positive_int(raw.get("match_id"))
    if match_id is None:
        raise TipsterUnprocessableError("Invalid match_id")
    _require_event_ids(raw.get("event_ids"))
    return match_id


def _require_event_ids(raw_ids: object) -> None:
    """Reject an empty, oversized or non-numeric event list."""
    if not isinstance(raw_ids, list) or not raw_ids:
        raise TipsterUnprocessableError(
            "Each leg must have between 1 and 8 events")
    if len(raw_ids) > MAX_LEGS:
        raise TipsterUnprocessableError(
            "Each leg must have between 1 and 8 events")
    for raw_id in raw_ids:
        if _positive_int(raw_id) is None:
            raise TipsterUnprocessableError("Invalid event_id")


def _positive_int(value: object) -> int | None:
    """Return a positive int. Booleans and other types do not count."""
    number = _required_int(value)
    if number is None or number < 1:
        return None
    return number


def _load_profile(user_id: int, now: datetime) -> TasteProfile:
    """Build taste from this user's coupons and favorite leagues."""
    since = now - timedelta(days=_CONFIG.history_days)
    rows: list[HistoryRow] = []
    for raw in advisor_repo.fetch_history(user_id, since):
        row = _history_row(raw)
        if row is not None:
            rows.append(row)
    favorites = fetch_favorite_league_ids(user_id)
    return build_profile(rows, favorites)


def _history_row(raw: dict[str, Any]) -> HistoryRow | None:
    """Map one history cell, or None when a value is blank."""
    league_id = _required_int(raw.get("league_id"))
    event_id = _required_int(raw.get("event_id"))
    odds = _finite_float(raw.get("odds"))
    event_count = _required_int(raw.get("event_count_on_leg"))
    if league_id is None or event_id is None or odds is None:
        return None
    if event_count is None or event_count < 1:
        return None
    return HistoryRow(
        league_id=league_id,
        event_id=event_id,
        odds=odds,
        event_count_on_leg=event_count)


def _slip_league_ids(match_ids: list[int]) -> set[int]:
    """Return leagues of draft matches that exist.

    A missing match adds no league. Its id is still excluded from
    the pool by the caller.
    """
    found = advisor_repo.fetch_slip_leagues(match_ids)
    return set(found.values())


def _candidate_pool(
        now: datetime,
        excluded_match_ids: set[int],
        slip_leagues: set[int],
        profile: TasteProfile) -> list[Candidate]:
    """Load, price and cap the future pool for this draft."""
    horizon_end = now + timedelta(days=_CONFIG.horizon_days)
    rows = advisor_repo.fetch_candidates(now, horizon_end)
    fingerprint = _read_fingerprint()
    bet_pairs = _bet_pairs(fingerprint, now, horizon_end)
    priced = _priced_candidates(
        rows, excluded_match_ids, bet_pairs)
    return _cap_candidates(priced, profile, slip_leagues)


def _read_fingerprint() -> str | None:
    """Return the artifact digest, or None when it cannot be used.

    A missing digest only clears the bet flag. Predictions still
    score, and the suggestion response stays successful.
    """
    # Funkcja odcisku łapie błędy pliku. Tu łapiemy resztę, żeby
    # panel nie dostał 500, gdy odczyt artefaktu padnie inaczej.
    try:
        return ready_model_fingerprint()
    except Exception as exc:
        logger.warning(
            "Event advisor could not read the betting artifact: %s",
            exc)
        return None


def _bet_pairs(
        fingerprint: str | None,
        now: datetime,
        horizon_end: datetime) -> set[tuple[int, int]]:
    """Return bet pairs only when an artifact digest exists."""
    if fingerprint is None:
        return set()
    return advisor_repo.fetch_computer_bet_pairs(
        fingerprint, now, horizon_end)


def _priced_candidates(
        rows: list[dict[str, Any]],
        excluded_match_ids: set[int],
        bet_pairs: set[tuple[int, int]]) -> list[Candidate]:
    """Keep rows that can be offered, with quantized prices."""
    priced: list[Candidate] = []
    for row in rows:
        candidate = _candidate(row, excluded_match_ids, bet_pairs)
        if candidate is not None:
            priced.append(candidate)
    return priced


def _candidate(
        row: dict[str, Any],
        excluded_match_ids: set[int],
        bet_pairs: set[tuple[int, int]]) -> Candidate | None:
    """Return one priced candidate, or None when it cannot be offered."""
    identity = _candidate_identity(row, excluded_match_ids)
    names = _candidate_names(row)
    kickoff = row.get("kickoff")
    if identity is None or names is None:
        return None
    if not isinstance(kickoff, datetime):
        return None
    match_id = identity["match_id"]
    event_id = identity["event_id"]
    return Candidate(
        match_id=match_id,
        event_id=event_id,
        event_name=names["event_name"],
        league_id=identity["league_id"],
        league_name=names["league_name"],
        home_name=names["home_name"],
        away_name=names["away_name"],
        kickoff=kickoff,
        odds=identity["odds"],
        bookmaker_id=identity["bookmaker_id"],
        model_probability=identity["model_probability"],
        has_computer_bet=(match_id, event_id) in bet_pairs)


def _candidate_identity(
        row: dict[str, Any],
        excluded_match_ids: set[int]) -> dict[str, Any] | None:
    """Return priced identity, or None when the row cannot be offered.

    Odds below 1.01 after half-up quantization are dropped, as are
    rows without a model probability. That probability is already
    on the unit scale. A match already on the draft is dropped too.
    """
    match_id = _required_int(row.get("match_id"))
    event_id = _required_int(row.get("event_id"))
    if match_id is None or event_id is None:
        return None
    if match_id in excluded_match_ids:
        return None
    league_id = _required_int(row.get("league_id"))
    bookmaker_id = _required_int(row.get("bookmaker_id"))
    if league_id is None or bookmaker_id is None:
        return None
    odds = _catalog_odds(row.get("odds"))
    probability = _finite_float(row.get("model_probability"))
    if odds is None or probability is None:
        return None
    return {
        "match_id": match_id,
        "event_id": event_id,
        "league_id": league_id,
        "bookmaker_id": bookmaker_id,
        "odds": odds,
        "model_probability": probability}


def _candidate_names(row: dict[str, Any]) -> dict[str, str] | None:
    """Return display names, or None when one of them is blank."""
    event_name = _text(row.get("event_name"))
    league_name = _text(row.get("league_name"))
    home_name = _text(row.get("home_name"))
    away_name = _text(row.get("away_name"))
    if event_name is None or league_name is None:
        return None
    if home_name is None or away_name is None:
        return None
    return {
        "event_name": event_name,
        "league_name": league_name,
        "home_name": home_name,
        "away_name": away_name}


def _catalog_odds(raw: object) -> float | None:
    """Quantize a price and drop anything below the catalog minimum."""
    number = _finite_float(raw)
    if number is None:
        return None
    try:
        odds = quantize_catalog_odds(number)
    except (ArithmeticError, ValueError):
        return None
    if not math.isfinite(odds) or odds < MIN_ODDS:
        return None
    return odds


def _cap_candidates(
        rows: list[Candidate],
        profile: TasteProfile,
        slip_league_ids: set[int]) -> list[Candidate]:
    """Keep at most the configured count, in a fixed priority.

    Bet pairs come first, then historical affinity at or above the
    keep floor, then slip leagues, then favorite leagues on a cold
    start. Whatever remains is filled by kickoff, match id and
    event id. The same pool always keeps the same rows.
    """
    limit = _CONFIG.max_scored_candidates
    if len(rows) <= limit:
        return list(rows)
    ordered = sorted(rows, key=_pool_sort_key)
    chosen: list[Candidate] = []
    seen: set[tuple[int, int]] = set()
    predicates = _keep_predicates(profile, slip_league_ids)
    for predicate in predicates:
        _take(ordered, predicate, chosen, seen, limit)
        if len(chosen) >= limit:
            return chosen
    return chosen


def _keep_predicates(
        profile: TasteProfile,
        slip_league_ids: set[int]
        ) -> list[Callable[[Candidate], bool]]:
    """Return the cap buckets in priority order."""
    def has_bet(row: Candidate) -> bool:
        return row.has_computer_bet

    def strong_league(row: Candidate) -> bool:
        affinity = profile.league_affinity.get(row.league_id, 0.0)
        return affinity >= _KEEP_AFFINITY_MIN

    def on_slip(row: Candidate) -> bool:
        return row.league_id in slip_league_ids

    def any_row(row: Candidate) -> bool:
        return True

    predicates: list[Callable[[Candidate], bool]] = [
        has_bet,
        strong_league,
        on_slip]
    if profile.cold_start:
        predicates.append(_favorite_predicate(profile))
    predicates.append(any_row)
    return predicates


def _favorite_predicate(
        profile: TasteProfile) -> Callable[[Candidate], bool]:
    """Match a cold-start favorite league."""
    favorites = frozenset(profile.favorite_league_ids)

    def favorite(row: Candidate) -> bool:
        return row.league_id in favorites

    return favorite


def _take(
        ordered: list[Candidate],
        predicate: Callable[[Candidate], bool],
        chosen: list[Candidate],
        seen: set[tuple[int, int]],
        limit: int) -> None:
    """Append rows the predicate accepts, until the cap is full."""
    for row in ordered:
        if len(chosen) >= limit:
            return
        key = (row.match_id, row.event_id)
        if key in seen or not predicate(row):
            continue
        seen.add(key)
        chosen.append(row)


def _pool_sort_key(row: Candidate) -> tuple[datetime, int, int]:
    """Order a cap bucket by kickoff, match id and event id."""
    return (row.kickoff, row.match_id, row.event_id)


def _response(
        profile: TasteProfile,
        tiers: dict[str, list[ScoredCandidate]]) -> dict[str, Any]:
    """Shape the three tiers and the profile summary."""
    payload: dict[str, list[dict[str, Any]]] = {}
    for tier in _TIER_NAMES:
        payload[tier] = [
            _suggestion(row, tier)
            for row in tiers.get(tier, [])]
    return {
        "cold_start": profile.cold_start,
        "history_events": profile.history_events,
        "odds_low": profile.odds_low,
        "odds_high": profile.odds_high,
        "tiers": payload}


def _suggestion(
        row: ScoredCandidate,
        tier: str) -> dict[str, Any]:
    """Map one scored row onto the response contract."""
    return {
        "tier": tier,
        "match_id": row.match_id,
        "event_id": row.event_id,
        "event_name": row.event_name,
        "league_id": row.league_id,
        "league_name": row.league_name,
        "home_name": row.home_name,
        "away_name": row.away_name,
        "game_date": row.kickoff.isoformat(),
        "odds": row.odds,
        "bookmaker_id": row.bookmaker_id,
        "score": _rounded_score(row.score),
        "reasons": list(row.reasons)}


def _rounded_score(score: float) -> float:
    """Round a blend to three decimal places, half up."""
    quantized = Decimal(f"{score:.10f}").quantize(
        _SCORE_STEP, rounding=ROUND_HALF_UP)
    return float(quantized)


def _warsaw_now() -> datetime:
    """Return the process clock as naive Warsaw wall time.

    Match kickoff and coupon ``created_at`` use that clock, the
    same one as the coupon agent.
    """
    return datetime.now(_WARSAW).replace(tzinfo=None)


def _user_id(user: dict[str, Any]) -> int:
    """Return the JWT user id that scopes coupon history."""
    return int(user["id"])


def _required_int(value: object) -> int | None:
    """Return an int, or None for a blank or non-numeric cell."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _finite_float(value: object) -> float | None:
    """Return a finite float, or None for a blank or non-numeric cell."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _text(value: object) -> str | None:
    """Return text, or None when the cell is blank."""
    if not isinstance(value, str) or value == "":
        return None
    return value
