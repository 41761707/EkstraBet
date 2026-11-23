"""Champion, challenger and retired roles per event family."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from backend.database import get_db_connection


MODEL_STATUS_CHAMPION = "champion"
MODEL_STATUS_CHALLENGER = "challenger"
MODEL_STATUS_RETIRED = "retired"
MODEL_STATUSES = frozenset({
    MODEL_STATUS_CHAMPION,
    MODEL_STATUS_CHALLENGER,
    MODEL_STATUS_RETIRED})


class ModelRoleError(RuntimeError):
    """Raised when a model role or event-family mapping is invalid."""


@dataclass(frozen=True)
class FamilyRole:
    """Effective role of one model inside one event family.

    ``status`` is already resolved by ``effective_status``.
    """

    model_id: int
    model_name: str
    event_family_id: int
    status: str


@dataclass(frozen=True)
class ModelRoles:
    """Roles loaded for one sport and each model's active flag.

    ``active_by_model`` stores ``models.active``. NULL becomes 0.
    """

    roles: tuple[FamilyRole, ...]
    active_by_model: dict[int, int]

    def status_of(
            self,
            model_id: int,
            event_family_id: int) -> str | None:
        """Return the effective status, or None when absent."""
        for role in self.roles:
            if role.model_id != model_id:
                continue
            if role.event_family_id != event_family_id:
                continue
            return role.status
        return None

    def champions_of(self, event_family_id: int) -> list[FamilyRole]:
        """Return champion roles registered for one event family."""
        return [
            role for role in self.roles
            if role.event_family_id == event_family_id
            and role.status == MODEL_STATUS_CHAMPION]


def effective_status(
        raw_status: str | None,
        model_active: int | None) -> str:
    """Resolve a stored status to champion, challenger or retired.

    A missing status keeps the pre-migration behavior: an active model
    is the champion and every other model is retired.
    """
    if raw_status is None:
        if model_active == 1:
            return MODEL_STATUS_CHAMPION
        return MODEL_STATUS_RETIRED
    if raw_status not in MODEL_STATUSES:
        raise ValueError(f"Unknown model status: {raw_status!r}")
    return raw_status


def fetch_model_roles(sport_id: int) -> ModelRoles:
    """Load effective family roles for one sport."""
    query = """
        SELECT emf.model_id, m.name AS model_name, emf.event_family_id,
               emf.status, m.active
        FROM event_model_families emf
        INNER JOIN models m ON m.id = emf.model_id
        WHERE m.sport_id = %s
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(sport_id,))
    roles: list[FamilyRole] = []
    active_by_model: dict[int, int] = {}
    for _, row in frame.iterrows():
        model_id = int(row["model_id"])
        active = _active_flag(row["active"])
        active_by_model[model_id] = active
        roles.append(FamilyRole(
            model_id=model_id,
            model_name=str(row["model_name"]),
            event_family_id=int(row["event_family_id"]),
            status=effective_status(
                _optional_text(row["status"]), active)))
    return ModelRoles(
        roles=tuple(roles),
        active_by_model=active_by_model)


def fetch_event_family_ids(event_ids: Sequence[int]) -> dict[int, int]:
    """Return MIN(event_family_id) for each event id.

    Raises ModelRoleError when any requested id has no mapping.
    """
    unique_ids = list(dict.fromkeys(int(event_id) for event_id in event_ids))
    if not unique_ids:
        # Puste IN () jest niepoprawnym SQL.
        return {}
    placeholders = ", ".join(["%s"] * len(unique_ids))
    query = f"""
        SELECT event_id, MIN(event_family_id) AS event_family_id
        FROM event_family_mappings
        WHERE event_id IN ({placeholders})
        GROUP BY event_id
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(unique_ids))
    found = {
        int(row["event_id"]): int(row["event_family_id"])
        for _, row in frame.iterrows()}
    missing = [
        event_id for event_id in unique_ids if event_id not in found]
    if missing:
        listed = ", ".join(str(event_id) for event_id in missing)
        raise ModelRoleError(
            f"Event family mapping is missing for event ids: {listed}")
    return {event_id: found[event_id] for event_id in unique_ids}


def _optional_text(value: object) -> str | None:
    if _is_missing(value):
        return None
    return str(value)


def _active_flag(value: object) -> int:
    # NULL w models.active znaczy „nieaktywny”, tak jak 0.
    if _is_missing(value):
        return 0
    return int(value)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    return bool(pd.isna(value))
