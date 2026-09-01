"""Administrative league operations: listing, creation and activation."""

from __future__ import annotations

from typing import Any, NoReturn

from mysql.connector.errors import IntegrityError

from backend.repositories import country_repository
from backend.repositories import league_repository
from backend.repositories import season_repository
from backend.repositories import sport_repository
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError


MAX_LEAGUE_NAME_LENGTH = 45
_MYSQL_NO_REFERENCED_ROW = 1216
_MYSQL_NO_REFERENCED_ROW_2 = 1452
_MYSQL_FK_ERRNOS = frozenset({_MYSQL_NO_REFERENCED_ROW,
    _MYSQL_NO_REFERENCED_ROW_2})


def list_leagues() -> list[dict[str, Any]]:
    """Return all leagues, including inactive, as admin DTOs."""
    return [_to_admin_league(row)
        for row in league_repository.fetch_all_leagues()]


def create_league(
        name: str,
        country_id: int,
        sport_id: int,
        current_season_id: int | None = None,
        tier: int | None = None,
        has_player_stats: bool = False) -> dict[str, Any]:
    """Insert a league after validating name and dictionary foreign keys."""
    normalized_name = _normalize_league_name(name)
    _validate_league_foreign_keys(country_id, sport_id, current_season_id)
    try:
        created = league_repository.create_league(
            normalized_name,
            country_id,
            sport_id,
            current_season_id,
            tier,
            has_player_stats,
            active=True)
    except IntegrityError as exc:
        _raise_league_integrity_error(exc)
    return _to_admin_league(created)


def set_league_active(league_id: int, active: bool) -> dict[str, Any]:
    """Set the active flag or raise when the league id is missing."""
    updated = league_repository.set_league_active(league_id, active)
    if updated is None:
        raise AdminNotFoundError("League not found")
    return _to_admin_league(updated)


def list_countries() -> list[dict[str, Any]]:
    """Return country dropdown rows."""
    return country_repository.fetch_all_countries()


def list_sports() -> list[dict[str, Any]]:
    """Return sport dropdown rows."""
    return sport_repository.fetch_all_sports()


def list_seasons() -> list[dict[str, Any]]:
    """Return season dropdown rows as id and years, newest first."""
    return season_repository.fetch_all_seasons()


def _validate_league_foreign_keys(
        country_id: int,
        sport_id: int,
        current_season_id: int | None) -> None:
    _require_known_id(list_countries(), country_id, "Country")
    _require_known_id(list_sports(), sport_id, "Sport")
    if current_season_id is None:
        return
    _require_known_id(list_seasons(), current_season_id, "Season")


def _require_known_id(
        rows: list[dict[str, Any]],
        record_id: int,
        field_label: str) -> None:
    for row in rows:
        if int(row["id"]) == record_id:
            return
    raise AdminValidationError(f"{field_label} not found")


def _to_admin_league(row: dict[str, Any]) -> dict[str, Any]:
    """Map a repository row to an admin DTO with TINYINT flags as bool."""
    name = row.get("name")
    return {"id": int(row["id"]),
        "name": None if name is None else str(name),
        "country_id": _as_optional_int(row.get("country_id")),
        "country_name": row.get("country_name"),
        "country_emoji": row.get("country_emoji"),
        "sport_id": _as_optional_int(row.get("sport_id")),
        "sport_name": row.get("sport_name"),
        "active": bool(row.get("active")),
        "last_update": row.get("last_update"),
        "current_season_id": _as_optional_int(row.get("current_season_id")),
        "tier": _as_optional_int(row.get("tier")),
        "has_player_stats": bool(row.get("has_player_stats"))}


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _normalize_league_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise AdminValidationError("League name is required")
    if len(normalized) > MAX_LEAGUE_NAME_LENGTH:
        raise AdminValidationError(
            "League name must be at most "
            f"{MAX_LEAGUE_NAME_LENGTH} characters")
    return normalized


def _raise_league_integrity_error(exc: IntegrityError) -> NoReturn:
    errno = getattr(exc, "errno", None)
    if errno in _MYSQL_FK_ERRNOS:
        raise AdminValidationError(
            "Invalid country, sport or season") from exc
    raise AdminValidationError("Invalid league record") from exc
