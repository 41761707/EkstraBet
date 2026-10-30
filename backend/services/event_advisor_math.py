"""Pure event-suggestion scoring. No database, API or randomness."""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime

from backend.services.event_advisor_config import AdvisorConfig


_CONFIG = AdvisorConfig()

# Liga spoza ulubionych przy zimnym starcie. Osobno od computer_weak.
_COLD_OTHER_LEAGUE_WEIGHT = 0.15
_COLD_FAVORITE_LEAGUE_WEIGHT = 1.0
_COLD_EVENT_WEIGHT = 0.50
_NEUTRAL_ODDS_FIT = 0.50
_REASON_AFFINITY_MIN = 0.50
# Wzór z projektu: position = fraction * (n - 1), potem interpolacja.
_PERCENTILE_LOW = 0.25
_PERCENTILE_HIGH = 0.75
# Kolejność cięcia do reason_limit. bet i lean mają różne computer.
_REASON_ORDER = (
    "computer_bet",
    "league_on_slip",
    "league_history",
    "event_history",
    "odds_in_band",
    "computer_lean")


@dataclass(frozen=True)
class HistoryRow:
    """One event from the user's own coupons, including combined legs."""

    league_id: int
    event_id: int
    odds: float
    event_count_on_leg: int


@dataclass(frozen=True)
class TasteProfile:
    """Historical taste before the current slip boosts a league."""

    cold_start: bool
    history_events: int
    league_affinity: dict[int, float]
    event_affinity: dict[int, float]
    odds_low: float | None
    odds_high: float | None
    favorite_league_ids: tuple[int, ...]


@dataclass(frozen=True)
class Candidate:
    """One future match-event pair with price and model view."""

    match_id: int
    event_id: int
    event_name: str
    league_id: int
    league_name: str
    home_name: str
    away_name: str
    kickoff: datetime
    odds: float
    bookmaker_id: int
    model_probability: float | None
    has_computer_bet: bool


@dataclass(frozen=True)
class ScoredCandidate(Candidate):
    """A candidate with the three scores blended into one."""

    score: float
    computer: float
    odds_fit: float
    reasons: tuple[str, ...]


def build_profile(
        rows: Sequence[HistoryRow],
        favorite_league_ids: Sequence[int]) -> TasteProfile:
    """Summarize the user's own coupon events.

    Every row counts as one event, including events inside a
    combined leg. Cold start (fewer events than the configured
    minimum) keeps favorite leagues and leaves affinity and the
    odds band empty. Otherwise affinity is ``count / max_count``
    and the band is the single-leg quartile span.
    """
    favorites = tuple(favorite_league_ids)
    history_events = len(rows)
    if history_events < _CONFIG.cold_start_min_events:
        return _cold_profile(history_events, favorites)
    odds_low, odds_high = _odds_band(rows)
    return TasteProfile(
        cold_start=False,
        history_events=history_events,
        league_affinity=_affinity(row.league_id for row in rows),
        event_affinity=_affinity(row.event_id for row in rows),
        odds_low=odds_low,
        odds_high=odds_high,
        favorite_league_ids=favorites)


def league_weight(
        league_id: int,
        profile: TasteProfile,
        slip_league_ids: Collection[int]) -> float:
    """Return the league weight, floored when the league is on the slip.

    Cold start trusts favorite leagues and gives every other league
    a small weight. After that, historical affinity is the weight.
    A league already on the draft is raised to the slip floor, so
    the current coupon stays visible next to long-run taste.
    """
    if profile.cold_start:
        if league_id in profile.favorite_league_ids:
            weight = _COLD_FAVORITE_LEAGUE_WEIGHT
        else:
            weight = _COLD_OTHER_LEAGUE_WEIGHT
    else:
        weight = profile.league_affinity.get(league_id, 0.0)
    if league_id in slip_league_ids:
        return max(weight, _CONFIG.slip_league_floor)
    return weight


def event_weight(event_id: int, profile: TasteProfile) -> float:
    """Return the event-type weight, or a flat value on cold start."""
    if profile.cold_start:
        return _COLD_EVENT_WEIGHT
    return profile.event_affinity.get(event_id, 0.0)


def preference_score(
        candidate: Candidate,
        profile: TasteProfile,
        slip_league_ids: Collection[int]) -> float:
    """Blend league and event weights into a score in ``[0, 1]``."""
    league = league_weight(
        candidate.league_id, profile, slip_league_ids)
    event = event_weight(candidate.event_id, profile)
    return _CONFIG.w_league * league + _CONFIG.w_event * event


def computer_score(
        model_probability: float | None,
        odds: float,
        has_computer_bet: bool) -> float:
    """Score how strongly the computer supports this price.

    A stored ``bet`` verdict is the top score. Without a published
    probability, or with odds at or below 1, the score is 0. A
    probability at or above the lean floor is ``lean`` when the
    absolute edge stays inside the cap, and ``fair`` when it does
    not. Every other published probability is ``weak``.
    """
    if has_computer_bet:
        return _CONFIG.computer_bet
    if model_probability is None or odds <= 1.0:
        return 0.0
    edge_pp = (model_probability - 1.0 / odds) * 100.0
    if model_probability < _CONFIG.lean_min_probability:
        return _CONFIG.computer_weak
    if abs(edge_pp) <= _CONFIG.lean_max_abs_edge_pp:
        return _CONFIG.computer_lean
    return _CONFIG.computer_fair


def odds_fit_score(odds: float, profile: TasteProfile) -> float:
    """Score how close ``odds`` sits to the user's single-leg band.

    Cold start and a missing band both return the neutral value.
    Inside the band the score is 1. Outside, it falls linearly to 0
    over one band width, and that width is at least the configured
    floor. The result stays inside ``[0, 1]``.
    """
    if profile.cold_start:
        return _NEUTRAL_ODDS_FIT
    if profile.odds_low is None or profile.odds_high is None:
        return _NEUTRAL_ODDS_FIT
    low = profile.odds_low
    high = profile.odds_high
    if low <= odds <= high:
        return 1.0
    width = max(high - low, _CONFIG.odds_band_floor)
    if width == 0.0:
        return 0.0
    if odds < low:
        raw = 1.0 - (low - odds) / width
    else:
        raw = 1.0 - (odds - high) / width
    return min(1.0, max(0.0, raw))


def score_candidate(
        candidate: Candidate,
        profile: TasteProfile,
        slip_league_ids: Collection[int]) -> ScoredCandidate:
    """Average preference, computer and odds fit, and attach reasons."""
    preference = preference_score(
        candidate, profile, slip_league_ids)
    computer = computer_score(
        candidate.model_probability,
        candidate.odds,
        candidate.has_computer_bet)
    odds_fit = odds_fit_score(candidate.odds, profile)
    score = (preference + computer + odds_fit) / 3.0
    reasons = _select_reasons(
        candidate, profile, slip_league_ids, computer)
    base = asdict(candidate)
    return ScoredCandidate(
        **base,
        score=score,
        computer=computer,
        odds_fit=odds_fit,
        reasons=reasons)


def keep_best_event_per_match(
        rows: Sequence[ScoredCandidate]) -> list[ScoredCandidate]:
    """Keep one row per match: higher score, then lower event id."""
    best: dict[int, ScoredCandidate] = {}
    for row in rows:
        current = best.get(row.match_id)
        if current is None or _beats(row, current):
            best[row.match_id] = row
    return list(best.values())


def assign_tiers(
        rows: Sequence[ScoredCandidate]
        ) -> dict[str, list[ScoredCandidate]]:
    """Bucket the best event per match into S, A and B.

    S also requires a strong computer score and an odds fit at or
    above the floor. Each tier is ordered by score, kickoff, match
    and event, then cut to its cap. The same rows always produce
    the same lists.
    """
    grouped: dict[str, list[ScoredCandidate]] = {
        "S": [],
        "A": [],
        "B": []}
    for row in keep_best_event_per_match(rows):
        tier = _tier_of(row)
        if tier is None:
            continue
        grouped[tier].append(row)
    result: dict[str, list[ScoredCandidate]] = {}
    for tier, bucket in grouped.items():
        ordered = sorted(bucket, key=_tier_sort_key)
        cap = _CONFIG.tier_caps[tier]
        result[tier] = ordered[:cap]
    return result


def _cold_profile(
        history_events: int,
        favorites: tuple[int, ...]) -> TasteProfile:
    """Return an empty profile that still remembers favorites."""
    return TasteProfile(
        cold_start=True,
        history_events=history_events,
        league_affinity={},
        event_affinity={},
        odds_low=None,
        odds_high=None,
        favorite_league_ids=favorites)


def _affinity(item_ids: Iterable[int]) -> dict[int, float]:
    """Scale counts so the most common id weighs 1."""
    counts: dict[int, int] = {}
    for item_id in item_ids:
        counts[item_id] = counts.get(item_id, 0) + 1
    max_count = max(counts.values())
    return {
        item_id: count / max_count
        for item_id, count in counts.items()}


def _odds_band(
        rows: Sequence[HistoryRow]) -> tuple[float | None, float | None]:
    """Return the single-leg 25th and 75th price percentiles.

    A combined price is not the price of one event, so those rows
    stay in affinity and stay out of the band. No single-event row
    leaves both ends empty.
    """
    prices = sorted(
        row.odds
        for row in rows
        if row.event_count_on_leg == 1)
    if not prices:
        return (None, None)
    low = _percentile(prices, _PERCENTILE_LOW)
    high = _percentile(prices, _PERCENTILE_HIGH)
    return (low, high)


def _percentile(sorted_values: list[float], fraction: float) -> float:
    """Interpolate one percentile on an ascending sample."""
    count = len(sorted_values)
    if count == 1:
        return sorted_values[0]
    position = fraction * (count - 1)
    lower = math.floor(position)
    if lower >= count - 1:
        return sorted_values[count - 1]
    weight = position - lower
    upper = lower + 1
    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight)


def _select_reasons(
        candidate: Candidate,
        profile: TasteProfile,
        slip_league_ids: Collection[int],
        computer: float) -> tuple[str, ...]:
    """Keep at most ``reason_limit`` codes, in the fixed priority."""
    # league_history patrzy na affinity przed podbiciem szkicu.
    league_affinity = profile.league_affinity.get(
        candidate.league_id, 0.0)
    event_affinity = profile.event_affinity.get(
        candidate.event_id, 0.0)
    enabled = {
        "computer_bet": candidate.has_computer_bet,
        "league_on_slip": candidate.league_id in slip_league_ids,
        "league_history": (
            league_affinity >= _REASON_AFFINITY_MIN),
        "event_history": (
            not profile.cold_start
            and event_affinity >= _REASON_AFFINITY_MIN),
        "odds_in_band": _odds_inside_band(candidate.odds, profile),
        "computer_lean": computer == _CONFIG.computer_lean}
    picked = [
        code for code in _REASON_ORDER
        if enabled[code]]
    return tuple(picked[:_CONFIG.reason_limit])


def _odds_inside_band(odds: float, profile: TasteProfile) -> bool:
    """Return whether the price sits inside the historical band."""
    if profile.cold_start:
        return False
    if profile.odds_low is None or profile.odds_high is None:
        return False
    return profile.odds_low <= odds <= profile.odds_high


def _beats(
        challenger: ScoredCandidate,
        current: ScoredCandidate) -> bool:
    """Return whether the challenger replaces the current row."""
    if challenger.score != current.score:
        return challenger.score > current.score
    return challenger.event_id < current.event_id


def _tier_of(row: ScoredCandidate) -> str | None:
    """Return S, A, B, or None when the row is below every floor."""
    if (
            row.score >= _CONFIG.tier_s_min
            and row.computer >= _CONFIG.tier_s_min_computer
            and row.odds_fit >= _CONFIG.tier_s_min_odds_fit):
        return "S"
    if row.score >= _CONFIG.tier_a_min:
        return "A"
    if row.score >= _CONFIG.tier_b_min:
        return "B"
    return None


def _tier_sort_key(
        row: ScoredCandidate) -> tuple[float, datetime, int, int]:
    """Order a tier by score, kickoff, match id and event id."""
    return (-row.score, row.kickoff, row.match_id, row.event_id)
