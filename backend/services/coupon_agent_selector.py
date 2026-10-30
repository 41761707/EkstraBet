"""Deterministic coupon selector. No database and no model I/O."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from backend.services.coupon_agent_config import SelectorConfig


_ODDS_TOLERANCE = 1e-9
_REASON_PUBLISHED = "published"
_REASON_NO_BET = "no_bet"
_Combo = tuple[int, ...]
_Ranked = tuple[float, _Combo]


@dataclass(frozen=True)
class AgentCandidate:
    """One settleable prediction-odds pair the selector may pick."""

    match_id: int
    event_id: int
    model_id: int
    bookmaker_id: int
    odds: float
    model_probability: float
    implied_probability: float
    value_edge_pp: float
    kickoff: datetime
    league_id: int | None
    league_tier: int | None
    event_family: str | None


@dataclass(frozen=True)
class CouponSelection:
    """Legs chosen for one coupon, or an explicit no-bet."""

    legs: list[AgentCandidate]
    combined_odds: float | None
    score: float | None
    reason: str


@dataclass(frozen=True)
class _ScoredLeg:
    """A candidate that passed the hard filters, with its leg score."""

    candidate: AgentCandidate
    score: float


def score_candidate(
        candidate: AgentCandidate,
        cfg: SelectorConfig) -> float:
    """Return a higher score for a leg the agent would rather play.

    Probability below the floor, an edge past the cap, or a probability
    outside (0, 1) scores as negative infinity.
    """
    if not _eligible(candidate, cfg):
        return float("-inf")
    model_p = candidate.model_probability
    gap = abs(model_p - candidate.implied_probability)
    longshot = max(0.0, candidate.value_edge_pp) / 100.0
    return (
        cfg.w_confidence * model_p
        - cfg.w_disagreement * gap
        - cfg.w_longshot * longshot)


def select_coupon(
        candidates: list[AgentCandidate],
        cfg: SelectorConfig) -> CouponSelection:
    """Pick one coupon, or ``no_bet`` when nothing legal remains.

    At most one leg per match and at most ``max_legs`` legs. A leg
    priced below ``min_leg_odds`` is ignored. The product of prices
    cannot exceed ``max_combined_odds``. The coupon
    score is the sum of leg scores minus ``leg_penalty`` for every
    leg after the first. A mean of the same scores would always keep
    a single leg.
    """
    pool = _prepare_pool(candidates, cfg)
    if not pool:
        return _no_bet()
    chosen = _beam_search(pool, cfg)
    if chosen is None:
        return _no_bet()
    return _to_selection(chosen, cfg)


def _eligible(candidate: AgentCandidate, cfg: SelectorConfig) -> bool:
    """Return True when the leg may enter the scored pool."""
    probability = candidate.model_probability
    edge = candidate.value_edge_pp
    implied = candidate.implied_probability
    if not math.isfinite(probability) or not math.isfinite(edge):
        return False
    if not math.isfinite(implied):
        return False
    if probability <= 0.0 or probability >= 1.0:
        return False
    if probability < cfg.min_probability:
        return False
    return abs(edge) <= cfg.max_abs_edge_pp


def _prepare_pool(
        candidates: list[AgentCandidate],
        cfg: SelectorConfig) -> list[_ScoredLeg]:
    """Score legs, keep one per match, then the best ``max_candidates``."""
    by_match: dict[int, _ScoredLeg] = {}
    for candidate in candidates:
        scored = _score_leg(candidate, cfg)
        if scored is None:
            continue
        current = by_match.get(candidate.match_id)
        if current is None or _replaces(scored, current):
            by_match[candidate.match_id] = scored
    ordered = sorted(by_match.values(), key=_pool_sort_key)
    return ordered[:cfg.max_candidates]


def _score_leg(
        candidate: AgentCandidate,
        cfg: SelectorConfig) -> _ScoredLeg | None:
    """Score one leg, or drop it when it can never sit on a legal slip."""
    odds = candidate.odds
    if not math.isfinite(odds) or odds <= 1.0:
        return None
    # Kurs 1.5 jest dozwolony. Poniżej tej ceny zdarzenie odpada.
    if odds + _ODDS_TOLERANCE < cfg.min_leg_odds:
        return None
    if odds > cfg.max_combined_odds + _ODDS_TOLERANCE:
        return None
    value = score_candidate(candidate, cfg)
    if not math.isfinite(value):
        return None
    return _ScoredLeg(candidate=candidate, score=value)


def _replaces(incoming: _ScoredLeg, current: _ScoredLeg) -> bool:
    """Return True when the incoming leg wins the same match."""
    if incoming.score != current.score:
        return incoming.score > current.score
    return _identity(incoming.candidate) < _identity(current.candidate)


def _identity(
        candidate: AgentCandidate) -> tuple[int, int, int, float]:
    """Order two legs of one match when their scores are equal."""
    return (
        candidate.event_id,
        candidate.model_id,
        candidate.bookmaker_id,
        candidate.odds)


def _pool_sort_key(
        item: _ScoredLeg) -> tuple[float, int, int, int, int]:
    """Best scores first, then stable ids so the beam does not flicker."""
    candidate = item.candidate
    return (
        -item.score,
        candidate.match_id,
        candidate.event_id,
        candidate.model_id,
        candidate.bookmaker_id)


def _beam_search(
        pool: list[_ScoredLeg],
        cfg: SelectorConfig) -> tuple[_ScoredLeg, ...] | None:
    """Return the highest-scoring combination that respects the cap."""
    beam: list[_Combo] = [()]
    best: _Ranked | None = None
    width = cfg.beam_width if cfg.beam_width >= 1 else 1
    for _depth in range(max(cfg.max_legs, 0)):
        found = _expand(beam, pool, cfg)
        if not found:
            break
        found.sort(key=_beam_rank)
        best = _keep_best(best, found, cfg)
        beam = [combo for _score, combo in found[:width]]
    if best is None:
        return None
    return tuple(pool[index] for index in best[1])


def _expand(
        beam: list[_Combo],
        pool: list[_ScoredLeg],
        cfg: SelectorConfig) -> list[_Ranked]:
    """Append one later leg when the running product stays within the cap."""
    found: list[_Ranked] = []
    for partial in beam:
        start = partial[-1] + 1 if partial else 0
        product = _indexed_product(partial, pool)
        for index in range(start, len(pool)):
            odds = pool[index].candidate.odds
            if not _product_fits(product * odds, cfg):
                continue
            extended = partial + (index,)
            score = _coupon_score(extended, pool, cfg)
            found.append((score, extended))
    return found


def _keep_best(
        best: _Ranked | None,
        found: list[_Ranked],
        cfg: SelectorConfig) -> _Ranked | None:
    """Keep the preferred coupon that already has enough legs."""
    chosen: _Ranked | None = None
    for item in found:
        if len(item[1]) < cfg.min_legs:
            continue
        chosen = item
        break
    if chosen is None:
        return best
    if best is None or _beam_rank(chosen) < _beam_rank(best):
        return chosen
    return best


def _beam_rank(item: _Ranked) -> tuple[float, int, _Combo]:
    """Higher coupon score first, then the shorter slip, then lower ids."""
    score, combo = item
    return (-score, len(combo), combo)


def _coupon_score(
        combo: _Combo,
        pool: list[_ScoredLeg],
        cfg: SelectorConfig) -> float:
    """Sum leg scores and charge the penalty for every extra leg."""
    total = 0.0
    for index in combo:
        total += pool[index].score
    return total - cfg.leg_penalty * (len(combo) - 1)


def _indexed_product(combo: _Combo, pool: list[_ScoredLeg]) -> float:
    """Return the product of prices for the given pool indexes."""
    product = 1.0
    for index in combo:
        product *= pool[index].candidate.odds
    return product


def _product_fits(product: float, cfg: SelectorConfig) -> bool:
    """Return True when the product does not cross the hard odds ceiling."""
    return product <= cfg.max_combined_odds + _ODDS_TOLERANCE


def _to_selection(
        chosen: tuple[_ScoredLeg, ...],
        cfg: SelectorConfig) -> CouponSelection:
    """Build the published slip in kickoff order."""
    ordered = sorted(
        chosen,
        key=lambda item: _output_key(item.candidate))
    product = 1.0
    total = 0.0
    for item in ordered:
        product *= item.candidate.odds
        total += item.score
    extra = len(ordered) - 1
    return CouponSelection(
        legs=[item.candidate for item in ordered],
        combined_odds=product,
        score=total - cfg.leg_penalty * extra,
        reason=_REASON_PUBLISHED)


def _output_key(
        candidate: AgentCandidate) -> tuple[datetime, int, int, int, int]:
    """Sort a published slip by kickoff, then by stable ids."""
    return (
        candidate.kickoff,
        candidate.match_id,
        candidate.event_id,
        candidate.model_id,
        candidate.bookmaker_id)


def _no_bet() -> CouponSelection:
    """Return the empty selection used when the agent stays out."""
    return CouponSelection(
        legs=[],
        combined_odds=None,
        score=None,
        reason=_REASON_NO_BET)
