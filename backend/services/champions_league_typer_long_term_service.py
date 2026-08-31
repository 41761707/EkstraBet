"""Domain rules for Typer long-term markets: scoring and settlement."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from backend.repositories import (
    champions_league_typer_long_term_repository as repository)


LEAGUE_PHASE_TEAM_COUNT = repository.LEAGUE_PHASE_TEAM_COUNT
LEAGUE_PHASE_MATCHES_PER_TEAM = repository.LEAGUE_PHASE_MATCHES_PER_TEAM
LEAGUE_PHASE_SETTLED_MATCH_COUNT = (
    repository.LEAGUE_PHASE_SETTLED_MATCH_COUNT)


class TyperServiceError(Exception):
    """Base error for long-term Typer domain rules."""


class TyperNotFoundError(TyperServiceError):
    """Market, season or user row was not found."""


class TyperConflictError(TyperServiceError):
    """Settlement cannot proceed in the current stored state."""


class TyperValidationError(TyperServiceError):
    """Request payload violates long-term contest rules."""


@contextmanager
def _repository_errors() -> Iterator[None]:
    try:
        yield
    except repository.TyperNotFoundError as exc:
        raise TyperNotFoundError(str(exc)) from exc
    except repository.TyperConflictError as exc:
        raise TyperConflictError(str(exc)) from exc
    except repository.TyperValidationError as exc:
        raise TyperValidationError(str(exc)) from exc


def score_long_term(
        pick_team_ids: list[int],
        result_team_ids: list[int],
        points_per_correct: float) -> float:
    """Return ``|picks ∩ results| * points_per_correct``.

    Order of ids does not matter. There is no ``scoring_kind`` branch.
    """
    hits = len(set(pick_team_ids) & set(result_team_ids))
    return float(hits) * float(points_per_correct)


def is_league_phase_complete(auto_result: dict[str, Any]) -> bool:
    """Return True when 36 teams each have 8 settled league-phase matches."""
    return (
        int(auto_result["participant_count"]) == LEAGUE_PHASE_TEAM_COUNT
        and int(auto_result["min_matches_per_team"])
        == LEAGUE_PHASE_MATCHES_PER_TEAM
        and int(auto_result["max_matches_per_team"])
        == LEAGUE_PHASE_MATCHES_PER_TEAM
        and int(auto_result["settled_match_count"])
        == LEAGUE_PHASE_SETTLED_MATCH_COUNT)


def get_auto_result(market_id: int) -> dict[str, Any]:
    """Return TOP 8 proposal and league-phase completeness status.

    Auto-calculation never writes results or awards points.
    """
    with _repository_errors():
        document = repository.fetch_auto_result(market_id)
    return _map_auto_result(document)


def settle_market(
        market_id: int,
        team_ids: list[int],
        admin_id: int) -> dict[str, Any]:
    """Approve or correct TOP 8 after the league phase is complete."""
    with _repository_errors():
        auto_result = repository.fetch_auto_result(market_id)
        if not is_league_phase_complete(auto_result):
            raise TyperConflictError("League phase is not complete")
        return repository.settle_market(market_id, team_ids, admin_id)


def _map_auto_result(document: dict[str, Any]) -> dict[str, Any]:
    complete = is_league_phase_complete(document)
    selection_size = int(document["selection_size"])
    standings = list(document["standings"])
    proposed = standings[:selection_size] if complete else []
    return {
        "market_id": int(document["market_id"]),
        "league_id": int(document["league_id"]),
        "season_id": int(document["season_id"]),
        "market_key": str(document["market_key"]),
        "selection_size": selection_size,
        "points_per_correct": float(document["points_per_correct"]),
        "settled_at": document["settled_at"],
        "settled_by": document["settled_by"],
        "is_complete": complete,
        "is_proposal": True,
        "participant_count": int(document["participant_count"]),
        "settled_match_count": int(document["settled_match_count"]),
        "min_matches_per_team": int(document["min_matches_per_team"]),
        "max_matches_per_team": int(document["max_matches_per_team"]),
        "required_participant_count": LEAGUE_PHASE_TEAM_COUNT,
        "required_matches_per_team": LEAGUE_PHASE_MATCHES_PER_TEAM,
        "required_settled_match_count": LEAGUE_PHASE_SETTLED_MATCH_COUNT,
        "proposed_team_ids": [int(row["team_id"]) for row in proposed],
        "proposed_teams": proposed,
        "standings": standings
    }
