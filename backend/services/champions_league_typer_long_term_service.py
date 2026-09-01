"""Domain rules for Typer long-term markets, picks and settlement."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from backend.repositories import (
    champions_league_typer_long_term_repository as repository)
from backend.repositories import user_repository


LEAGUE_PHASE_TEAM_COUNT = repository.LEAGUE_PHASE_TEAM_COUNT
LEAGUE_PHASE_MATCHES_PER_TEAM = repository.LEAGUE_PHASE_MATCHES_PER_TEAM
LEAGUE_PHASE_SETTLED_MATCH_COUNT = (
    repository.LEAGUE_PHASE_SETTLED_MATCH_COUNT)


class TyperServiceError(Exception):
    """Base error for long-term Typer domain rules."""


class TyperNotFoundError(TyperServiceError):
    """Market, season or user row was not found."""


class TyperConflictError(TyperServiceError):
    """Pick or settlement cannot proceed in the current stored state."""


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


def get_dashboard(
        user_id: int,
        season_id: int | None) -> dict[str, Any]:
    """Return markets, candidates and the caller's private picks."""
    with _repository_errors():
        document = repository.fetch_long_term_dashboard(
            user_id, season_id)
    return _map_dashboard(document)


def save_picks(
        user_id: int,
        market_id: int,
        team_ids: list[int]) -> dict[str, Any]:
    """Replace the caller's set; identical sets skip audit."""
    with _repository_errors():
        stored = repository.save_long_term_picks(
            user_id, market_id, team_ids)
    return _map_saved_picks(stored)


def get_own_history(
        user_id: int,
        market_id: int) -> list[dict[str, Any]]:
    """Return chronological audit rows for the caller's market set."""
    with _repository_errors():
        return repository.fetch_own_long_term_history(
            user_id, market_id)


def get_admin_history(
        user_uuid: str,
        market_id: int | None = None,
        season_id: int | None = None) -> list[dict[str, Any]]:
    """Return audit rows for a user identified by public UUID."""
    with _repository_errors():
        return repository.fetch_admin_long_term_history(
            user_uuid, market_id, season_id)


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
        stored = repository.settle_market(market_id, team_ids, admin_id)
    return _map_settled(stored)


def _map_auto_result(document: dict[str, Any]) -> dict[str, Any]:
    complete = is_league_phase_complete(document)
    selection_size = int(document["selection_size"])
    standings = list(document["standings"])
    proposed = standings[:selection_size] if complete else []
    settler = _settler_public_identity(document.get("settled_by"))
    return {
        "market_id": int(document["market_id"]),
        "league_id": int(document["league_id"]),
        "season_id": int(document["season_id"]),
        "market_key": str(document["market_key"]),
        "selection_size": selection_size,
        "points_per_correct": float(document["points_per_correct"]),
        "settled_at": document["settled_at"],
        "settled_by_uuid": settler["settled_by_uuid"],
        "settled_by_display_name": settler["settled_by_display_name"],
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
        "result_team_ids": [
            int(team_id)
            for team_id in document.get("result_team_ids") or []],
        "standings": standings
    }


def _map_dashboard(document: dict[str, Any]) -> dict[str, Any]:
    changes_by_market: dict[int, list[dict[str, Any]]] = {}
    for row in document.get("changes") or []:
        market_id = int(row["market_id"])
        changes_by_market.setdefault(market_id, []).append(row)
    markets = [
        _map_dashboard_market(
            market,
            changes_by_market.get(int(market["market_id"]), []))
        for market in document.get("markets") or []]
    return {
        "season_id": int(document["season_id"]),
        "markets": markets
    }


def _map_dashboard_market(
        market: dict[str, Any],
        changes: list[dict[str, Any]]) -> dict[str, Any]:
    picked = [int(team_id) for team_id in market["picked_team_ids"]]
    results = [int(team_id) for team_id in market["result_team_ids"]]
    points = None
    if results:
        # punkty dopiero po settle: puste result_team_ids to brak wyniku
        points = score_long_term(
            picked, results, float(market["points_per_correct"]))
    return {
        "market_id": int(market["market_id"]),
        "league_id": int(market["league_id"]),
        "season_id": int(market["season_id"]),
        "market_key": str(market["market_key"]),
        "title": str(market["title"]),
        "description": market["description"],
        "selection_size": int(market["selection_size"]),
        "points_per_correct": float(market["points_per_correct"]),
        "settled_at": market["settled_at"],
        "deadline_at": market["deadline_at"],
        "is_locked": bool(market["is_locked"]),
        "candidates": list(market["candidates"]),
        "picked_team_ids": picked,
        "result_team_ids": results,
        "points": points,
        "changes": changes
    }


def _map_saved_picks(stored: dict[str, Any]) -> dict[str, Any]:
    previous = stored["previous_team_ids"]
    return {
        "market_id": int(stored["market_id"]),
        "team_ids": [int(team_id) for team_id in stored["team_ids"]],
        "previous_team_ids": (
            None if previous is None
            else [int(team_id) for team_id in previous]),
        "audit_written": bool(stored["audit_written"])
    }


def _map_settled(stored: dict[str, Any]) -> dict[str, Any]:
    team_ids = [int(team_id) for team_id in stored["team_ids"]]
    settler = _settler_public_identity(stored.get("settled_by"))
    return {
        "market_id": int(stored["market_id"]),
        "team_ids": team_ids,
        "settled_by_uuid": settler["settled_by_uuid"],
        "settled_by_display_name": settler["settled_by_display_name"],
        "settled_at": stored["settled_at"],
        "result_team_ids": [
            int(team_id) for team_id in stored["result_team_ids"]]
    }


def _settler_public_identity(
        settled_by: object) -> dict[str, str | None]:
    empty = {
        "settled_by_uuid": None,
        "settled_by_display_name": None
    }
    if settled_by is None:
        return empty
    user = user_repository.fetch_user_by_id(int(settled_by))
    if user is None:
        return empty
    display_name = user.get("display_name")
    return {
        "settled_by_uuid": str(user["uuid"]),
        "settled_by_display_name": (
            None if display_name is None else str(display_name))
    }
