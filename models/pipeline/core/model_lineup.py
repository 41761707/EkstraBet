"""Football model registry and the champion/challenger lineup."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.config import REPO_ROOT
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import load_model_config
from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION
from models.pipeline.core.model_roles import FamilyRole
from models.pipeline.core.model_roles import ModelRoles
from models.pipeline.core.model_roles import fetch_model_roles


DEFAULT_REGISTRY_PATH = REPO_ROOT.joinpath(
    "models",
    "configs",
    "prediction",
    "football_model_registry.json")

_LINEUP_STATUSES = frozenset({
    MODEL_STATUS_CHAMPION,
    MODEL_STATUS_CHALLENGER})


@dataclass(frozen=True)
class LineupEntry:
    """One future-events model selected into the lineup."""

    model_name: str
    model_id: int
    config_path: Path
    config: FutureEventsRunConfig
    family_statuses: dict[int, str]


@dataclass(frozen=True)
class ModelLineup:
    """Champion and challenger models that predict future events."""

    entries: tuple[LineupEntry, ...]

    def champion_entries(self) -> list[LineupEntry]:
        """Return entries that champion at least one family."""
        return _entries_with_status(self.entries, MODEL_STATUS_CHAMPION)

    def challenger_entries(self) -> list[LineupEntry]:
        """Return entries that challenge at least one family."""
        return _entries_with_status(self.entries, MODEL_STATUS_CHALLENGER)


class LineupError(RuntimeError):
    """Raised when the registry or the family lineup is invalid."""


def load_model_registry(
        path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Path]:
    """Map model names to config paths.

    Relative paths are resolved from the repository root. A missing
    config file raises LineupError.
    """
    registry_path = Path(path)
    if not registry_path.is_file():
        raise LineupError(f"Model registry not found: {registry_path}")
    raw = _read_registry_json(registry_path)
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise LineupError(
            f"Model registry {registry_path} must map models "
            "to config paths")
    resolved: dict[str, Path] = {}
    for name, relative in models.items():
        config_path = _config_path(name, relative, registry_path)
        if not config_path.is_file():
            raise LineupError(
                f"Config file not found for {name!r}: {config_path}")
        resolved[name] = config_path
    return resolved


def build_lineup(
        roles: ModelRoles,
        registry: dict[str, Path]) -> ModelLineup:
    """Build a lineup from effective roles and the config registry.

    Models outside the registry whose every role is implicit
    (NULL status and active = 1) are skipped. An explicit champion
    or challenger missing from the registry is an error. Every family
    that remains must have exactly one champion.
    """
    coverage: dict[int, list[tuple[str, str]]] = {}
    entries: list[LineupEntry] = []
    grouped = _roles_by_model(roles)
    for model_name in sorted(grouped):
        model_roles = grouped[model_name]
        publishable = _publishable(model_roles)
        if not publishable:
            continue
        if model_name not in registry:
            _reject_unregistered(model_name, model_roles)
            continue
        entry = _entry_for_model(
            model_name, model_roles, publishable, registry)
        entries.append(entry)
        _record_coverage(coverage, entry)
    _require_one_champion(coverage)
    return ModelLineup(entries=tuple(entries))


def resolve_lineup(
        sport_id: int = 1,
        registry_path: Path = DEFAULT_REGISTRY_PATH) -> ModelLineup:
    """Load roles and the registry, then build the lineup."""
    roles = fetch_model_roles(sport_id)
    registry = load_model_registry(registry_path)
    return build_lineup(roles, registry)


def _entries_with_status(
        entries: tuple[LineupEntry, ...],
        status: str) -> list[LineupEntry]:
    return [
        entry for entry in entries
        if status in entry.family_statuses.values()]


def _read_registry_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LineupError(
            f"Model registry {path} is not valid JSON") from exc


def _config_path(
        name: object,
        relative: object,
        registry_path: Path) -> Path:
    if not isinstance(name, str) or not name.strip():
        raise LineupError(
            f"Model registry {registry_path} has an empty model name")
    if not isinstance(relative, str) or not relative.strip():
        raise LineupError(
            f"Model registry path for {name!r} is empty")
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def _roles_by_model(roles: ModelRoles) -> dict[str, list[FamilyRole]]:
    grouped: dict[str, list[FamilyRole]] = {}
    for role in roles.roles:
        grouped.setdefault(role.model_name, []).append(role)
    return grouped


def _publishable(model_roles: list[FamilyRole]) -> list[FamilyRole]:
    return [
        role for role in model_roles
        if role.status in _LINEUP_STATUSES]


def _reject_unregistered(
        model_name: str,
        model_roles: list[FamilyRole]) -> None:
    # Jawny champion/challenger poza rejestrem to błąd konfiguracji.
    # Sam NULL + active = 1 opisuje stary model spoza przyszłych zdarzeń.
    explicit = any(
        role.raw_status in _LINEUP_STATUSES for role in model_roles)
    if not explicit:
        return
    raise LineupError(
        f"Model {model_name!r} is not in the model registry")


def _entry_for_model(
        model_name: str,
        model_roles: list[FamilyRole],
        publishable: list[FamilyRole],
        registry: dict[str, Path]) -> LineupEntry:
    config_path = Path(registry[model_name])
    try:
        config = load_model_config(config_path)
    except FileNotFoundError as exc:
        raise LineupError(
            f"Config file not found for {model_name!r}: "
            f"{config_path}") from exc
    if not isinstance(config, FutureEventsRunConfig):
        raise LineupError(
            f"Config for {model_name!r} is not a future-events config")
    if config.model_name != model_name:
        raise LineupError(
            f"Config model_name {config.model_name!r} does not match "
            f"registry model {model_name!r}")
    return LineupEntry(
        model_name=model_name,
        model_id=_single_model_id(model_name, model_roles),
        config_path=config_path,
        config=config,
        family_statuses=_family_statuses(model_name, publishable))


def _single_model_id(
        model_name: str,
        model_roles: list[FamilyRole]) -> int:
    model_ids = {role.model_id for role in model_roles}
    if len(model_ids) != 1:
        listed = ", ".join(str(model_id) for model_id in sorted(model_ids))
        raise LineupError(
            f"Model {model_name!r} has multiple ids: {listed}")
    return next(iter(model_ids))


def _family_statuses(
        model_name: str,
        publishable: list[FamilyRole]) -> dict[int, str]:
    statuses: dict[int, str] = {}
    ordered = sorted(publishable, key=lambda role: role.event_family_id)
    for role in ordered:
        if role.event_family_id in statuses:
            raise LineupError(
                f"Model {model_name!r} repeats event family "
                f"{role.event_family_id}")
        statuses[role.event_family_id] = role.status
    return statuses


def _record_coverage(
        coverage: dict[int, list[tuple[str, str]]],
        entry: LineupEntry) -> None:
    for family_id, status in entry.family_statuses.items():
        coverage.setdefault(family_id, []).append(
            (entry.model_name, status))


def _require_one_champion(
        coverage: dict[int, list[tuple[str, str]]]) -> None:
    for family_id in sorted(coverage):
        members = coverage[family_id]
        champions = [
            name for name, status in members
            if status == MODEL_STATUS_CHAMPION]
        if len(champions) == 1:
            continue
        names = champions or [name for name, _status in members]
        listed = ", ".join(names)
        if not champions:
            raise LineupError(
                f"Event family {family_id} has no champion: {listed}")
        raise LineupError(
            f"Event family {family_id} has multiple champions: {listed}")
