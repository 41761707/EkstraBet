"""Reference strategies that select at most one candidate per match."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import DecisionKind
from models.pipeline.betting.domain import SelectionDecision


_RankKey = tuple[float, int, int, int, int, int, int, datetime, int]
_Score = Callable[[BettingCandidate], float]
_Reason = Callable[
    [BettingCandidate, BettingCandidate | None],
    str]


class SelectionStrategy(Protocol):
    """Choose bet or no-bet for each candidate in one pool."""

    def decide(
            self,
            candidates: Sequence[BettingCandidate]
            ) -> list[SelectionDecision]:
        """Return one decision per candidate, in input order."""


class NoBetStrategy:
    """Leave every candidate unselected."""

    def decide(
            self,
            candidates: Sequence[BettingCandidate]
            ) -> list[SelectionDecision]:
        """Mark the whole pool as no-bet."""
        _require_candidates(candidates)
        return [
            _decision(candidate, None, "no-bet baseline")
            for candidate in candidates]


class ConfidenceSingleStrategy:
    """Bet the highest model probability inside each match."""

    def decide(
            self,
            candidates: Sequence[BettingCandidate]
            ) -> list[SelectionDecision]:
        """Select one row in each match. Ties use prediction id."""
        _require_candidates(candidates)
        winners = _match_winners(candidates, _model_probability)
        return _decisions(candidates, winners, _confidence_reason)


class PositiveEvSingleStrategy:
    """Bet the highest positive expected value inside each match."""

    def decide(
            self,
            candidates: Sequence[BettingCandidate]
            ) -> list[SelectionDecision]:
        """Select one positive-EV row in each match, or none."""
        _require_candidates(candidates)
        winners = _match_winners(
            candidates,
            _expected_value,
            _has_positive_ev)
        return _decisions(candidates, winners, _ev_reason)


def _decisions(
        candidates: Sequence[BettingCandidate],
        winners: dict[int, BettingCandidate],
        reason_for: _Reason) -> list[SelectionDecision]:
    """Attach one decision to every input row, without reordering."""
    decisions = []
    for candidate in candidates:
        winner = winners.get(candidate.match_id)
        decisions.append(_decision(
            candidate,
            winner,
            reason_for(candidate, winner)))
    return decisions


def _match_winners(
        candidates: Sequence[BettingCandidate],
        score: _Score,
        eligible: Callable[[BettingCandidate], bool] | None = None
        ) -> dict[int, BettingCandidate]:
    """Pick at most one winner inside each match."""
    # Jeden zakład na mecz. Całe okno nie jest jednym wyborem.
    grouped: dict[int, list[BettingCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.match_id, []).append(candidate)
    winners: dict[int, BettingCandidate] = {}
    for match_id, group in grouped.items():
        pool = _eligible_group(group, eligible)
        winner = _select_winner(pool, score)
        if winner is not None:
            winners[match_id] = winner
    return winners


def _eligible_group(
        group: list[BettingCandidate],
        eligible: Callable[[BettingCandidate], bool] | None
        ) -> list[BettingCandidate]:
    """Keep the whole match, or only rows the strategy can bet."""
    if eligible is None:
        return group
    return [candidate for candidate in group if eligible(candidate)]


def _has_positive_ev(candidate: BettingCandidate) -> bool:
    """Return whether the row's expected value is strictly positive."""
    return _expected_value(candidate) > 0.0


def _decision(
        candidate: BettingCandidate,
        winner: BettingCandidate | None,
        reason: str) -> SelectionDecision:
    """Build a decision whose probability is the base model percent."""
    kind: DecisionKind = "bet" if candidate is winner else "no_bet"
    return SelectionDecision(
        decision=kind,
        candidate=candidate,
        calibrated_probability=_model_probability(candidate),
        reason=reason)


def _select_winner(
        candidates: Sequence[BettingCandidate],
        score: _Score) -> BettingCandidate | None:
    """Return the best candidate, or none when the pool is empty."""
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: _rank_key(candidate, score(candidate)))


def _rank_key(
        candidate: BettingCandidate,
        score: float) -> _RankKey:
    """Order a higher score first, then a stable candidate identity.

    Input order is not part of the key, so a shuffle cannot change
    the selected row.
    """
    # Ostatni element rozstrzyga dwa równe obiekty bez patrzenia na
    # pozycję w liście.
    return (
        -score,
        candidate.prediction_id,
        candidate.odds_id,
        candidate.match_id,
        candidate.event_id,
        candidate.model_id,
        candidate.bookmaker_id,
        candidate.kickoff,
        id(candidate))


def _confidence_reason(
        candidate: BettingCandidate,
        winner: BettingCandidate | None) -> str:
    """Explain a confidence choice, including a lost tie."""
    if candidate is winner:
        return "highest model probability"
    if (
            winner is not None
            and _model_probability(candidate) == _model_probability(winner)):
        return "tied model probability"
    return "lower model probability"


def _ev_reason(
        candidate: BettingCandidate,
        winner: BettingCandidate | None) -> str:
    """Explain an expected-value choice, including a non-positive row."""
    if candidate is winner:
        return "highest positive expected value"
    candidate_ev = _expected_value(candidate)
    if winner is None or candidate_ev <= 0.0:
        return "non-positive expected value"
    if candidate_ev == _expected_value(winner):
        return "tied expected value"
    return "lower expected value"


def _model_probability(candidate: BettingCandidate) -> float:
    """Return the stored percent on the unit interval."""
    # Baseline nie ma kalibratora. To samo wejście co cecha
    # model_probability.
    return float(candidate.value_pct) / 100.0


def _expected_value(candidate: BettingCandidate) -> float:
    """Return model probability times price, minus one."""
    # Ten sam wzór co cecha ev: surowa cena, bez de-vig.
    return _model_probability(candidate) * float(candidate.odds) - 1.0


def _require_candidates(candidates: Sequence[BettingCandidate]) -> None:
    """Reject anything that is not a pool of candidates."""
    if isinstance(candidates, (str, bytes)) or not isinstance(
            candidates, Sequence):
        raise ValueError("candidates must be a sequence")
    for candidate in candidates:
        if not isinstance(candidate, BettingCandidate):
            raise ValueError(
                "candidates must contain BettingCandidate values")
