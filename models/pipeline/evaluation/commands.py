"""Offline comparison and the live shadow report."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import ValidationError

from backend.betting_tax import BETTING_TAX_RATE
from backend.config import REPO_ROOT
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import load_model_config
from models.pipeline.core.model_lineup import load_model_registry
from models.pipeline.core.registry import resolve_registered_model_id
from models.pipeline.data.evaluation_repository import fetch_finished_results
from models.pipeline.data.evaluation_repository import fetch_league_names
from models.pipeline.data.evaluation_repository import fetch_match_odds
from models.pipeline.data.evaluation_repository import fetch_published_values
from models.pipeline.data.evaluation_repository import fetch_season_years
from models.pipeline.data.evaluation_repository import fetch_shadow_values
from models.pipeline.evaluation.candidates import CANDIDATE_ROLES
from models.pipeline.evaluation.candidates import FAMILY_BTTS
from models.pipeline.evaluation.candidates import FAMILY_OVER_25
from models.pipeline.evaluation.candidates import FAMILY_RESULT
from models.pipeline.evaluation.candidates import CandidateOutput
from models.pipeline.evaluation.candidates import align_outputs
from models.pipeline.evaluation.candidates import family_of_task
from models.pipeline.evaluation.candidates import load_candidate_output
from models.pipeline.evaluation.gate import GateThresholds
from models.pipeline.evaluation.gate import offline_decision
from models.pipeline.evaluation.gate import recommend
from models.pipeline.evaluation.gate import shadow_decision
from models.pipeline.evaluation.market import consensus_fair_probabilities
from models.pipeline.evaluation.market import flat_stake_roi
from models.pipeline.evaluation.market import market_event_families
from models.pipeline.evaluation.market import market_information_test
from models.pipeline.evaluation.metrics import binary_brier
from models.pipeline.evaluation.metrics import binary_log_loss
from models.pipeline.evaluation.metrics import expected_calibration_error
from models.pipeline.evaluation.metrics import final_shares
from models.pipeline.evaluation.metrics import multiclass_brier
from models.pipeline.evaluation.metrics import multiclass_log_loss
from models.pipeline.evaluation.metrics import per_match_log_loss
from models.pipeline.evaluation.metrics import reliability_table
from models.pipeline.evaluation.segments import SEASON_FORMAT_CALENDAR_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_SPLIT_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_UNKNOWN
from models.pipeline.evaluation.segments import league_table
from models.pipeline.evaluation.segments import season_format_segments


_SPEC_KEYS = (
    "sport_id",
    "test_from",
    "test_to",
    "bootstrap_samples",
    "bootstrap_seed",
    "reliability_edges",
    "candidates",
    "output_path")
_FAMILY_ORDER = (FAMILY_RESULT, FAMILY_BTTS, FAMILY_OVER_25)
_NO_MARKET = "no complete market"
_NO_PRICE = "no priced selections"
_NO_COMPARED = "no comparable matches"
_SHADOW_SPORT_ID = 1
_FAMILY_EVENT_KEYS = {
    FAMILY_RESULT: ("result_home", "result_draw", "result_away"),
    FAMILY_BTTS: ("btts_yes", "btts_no"),
    FAMILY_OVER_25: ("over_25", "under_25")}
_FINISHED_COLUMNS = (
    "id",
    "league",
    "season",
    "game_date",
    "home_team_goals",
    "away_team_goals",
    "result")
_VALUE_COLUMNS = ("match_id", "event_id", "value")


@dataclass(frozen=True)
class _Prices:
    """Fair probabilities and best odds aligned to one match order."""

    fair: np.ndarray
    best: np.ndarray
    complete: np.ndarray


def run_compare_models(args: object) -> dict[str, Any]:
    """Write the offline report described by ``--spec`` and return it.

    Each challenger in a family gets a gate decision. ``recommended``
    names the passing challenger with the lowest log loss, or null
    when nobody in that family passes.
    """
    spec = _read_spec(Path(getattr(args, "spec")))
    loaded = _load_candidates(spec)
    report = _build_report(spec, loaded)
    _write_report(report, _repo_path(spec["output_path"]))
    return report


def run_shadow_report(args: object) -> dict[str, Any]:
    """Write one family's shadow check and return the report.

    The window is ``[date-from, date-to)``. The champion is read
    from ``predictions`` and the challenger from
    ``model_shadow_predictions``. Thresholds are the defaults on
    ``GateThresholds``.
    """
    request = _shadow_request(args)
    event_ids = _registry_event_ids(
        request["family"],
        request["champion_model"],
        request["challenger_model"])
    champion_id = resolve_registered_model_id(request["champion_model"])
    challenger_id = resolve_registered_model_id(
        request["challenger_model"])
    finished = fetch_finished_results(
        request["date_from"],
        request["date_to"],
        _SHADOW_SPORT_ID)
    match_ids = _finished_ids(finished)
    published = fetch_published_values(
        champion_id, event_ids, match_ids)
    shadow = fetch_shadow_values(challenger_id, event_ids, match_ids)
    compared = _compared_matches(
        request["family"], finished, published, shadow, event_ids)
    decision = shadow_decision(
        request["family"],
        compared["champion_p"],
        compared["challenger_p"],
        compared["outcomes"],
        compared["missing_rate"],
        GateThresholds(),
        league_ids=compared["league_ids"])
    report = _shadow_document(
        request, champion_id, challenger_id, compared, decision)
    _write_report(report, Path(request["output"]))
    return report


def _read_spec(path: Path) -> dict[str, Any]:
    source = _spec_file(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Spec is not valid JSON: {source}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Spec must be a JSON object")
    return _checked_spec(raw)


def _spec_file(value: Path) -> Path:
    if value.is_file():
        return value
    repo = REPO_ROOT / value
    if repo.is_file():
        return repo
    raise FileNotFoundError(f"Spec file not found: {value}")


def _checked_spec(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in _SPEC_KEYS if key not in raw]
    if missing:
        raise ValueError("Spec is missing " + ", ".join(missing))
    test_from = _parse_date(raw["test_from"], "test_from")
    test_to = _parse_date(raw["test_to"], "test_to")
    if test_from >= test_to:
        raise ValueError("test_from must be before test_to")
    samples = _plain_int(raw["bootstrap_samples"], "bootstrap_samples")
    if samples < 1:
        raise ValueError("bootstrap_samples must be a positive integer")
    output_path = raw["output_path"]
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError("output_path must be a path")
    edges = raw["reliability_edges"]
    if isinstance(edges, (str, bytes)) or not isinstance(edges, list):
        raise ValueError("reliability_edges must be a list")
    return {
        "raw": raw,
        "sport_id": _plain_int(raw["sport_id"], "sport_id"),
        "test_from": test_from,
        "test_to": test_to,
        "samples": samples,
        "seed": _plain_int(raw["bootstrap_seed"], "bootstrap_seed"),
        "edges": edges,
        "candidates": _candidate_rows(raw["candidates"]),
        "output_path": output_path,
        "thresholds": _gate_thresholds(raw.get("thresholds", {}))}


def _candidate_rows(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("candidates must be a non-empty list")
    rows = [_candidate_row(item, index) for index, item in enumerate(raw)]
    labels = [row["label"] for row in rows]
    if len(labels) != len(set(labels)):
        raise ValueError("Candidate labels must be unique")
    _require_one_champion(rows)
    return rows


def _candidate_row(raw: object, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Candidate {index} must be an object")
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ValueError(f"Candidate {index} needs a label")
    role = raw.get("role")
    if role not in CANDIDATE_ROLES:
        raise ValueError(f"Candidate {label} has unknown role {role!r}")
    families = _declared_families(label, raw.get("families"))
    config = raw.get("config")
    if not isinstance(config, str) or not config.strip():
        raise ValueError(f"Candidate {label} needs a config path")
    return {
        "label": label,
        "role": role,
        "families": families,
        "config": config}


def _declared_families(label: str, raw: object) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"Candidate {label} has no family in the spec")
    names: list[str] = []
    for name in raw:
        if name not in _FAMILY_ORDER:
            raise ValueError(
                f"Candidate {label} has unknown family {name!r}")
        if name in names:
            raise ValueError(f"Candidate {label} repeats family {name}")
        names.append(name)
    return names


def _require_one_champion(rows: list[dict[str, Any]]) -> None:
    champions: dict[str, list[str]] = {}
    for row in rows:
        for family in row["families"]:
            champions.setdefault(family, [])
            if row["role"] == "champion":
                champions[family].append(row["label"])
    for family, labels in champions.items():
        if len(labels) == 1:
            continue
        found = ", ".join(labels) if labels else "none"
        raise ValueError(
            f"Family {family} must have exactly one champion, "
            f"found {found}")


def _load_candidates(spec: dict[str, Any]) -> list[CandidateOutput]:
    loaded: list[CandidateOutput] = []
    for row in spec["candidates"]:
        config = _checked_config(spec, row)
        loaded.append(load_candidate_output(
            row["label"],
            row["role"],
            config.config_path or _repo_path(row["config"]),
            spec["test_from"],
            spec["test_to"]))
    return loaded


def _checked_config(
        spec: dict[str, Any],
        row: dict[str, Any]) -> FutureEventsRunConfig:
    loaded = load_model_config(_repo_path(row["config"]))
    if not isinstance(loaded, FutureEventsRunConfig):
        raise ValueError(
            f"Candidate {row['label']} config is not a future-event model")
    if loaded.sport_id != spec["sport_id"]:
        raise ValueError(
            f"Candidate {row['label']} sport_id {loaded.sport_id} "
            f"does not match spec sport_id {spec['sport_id']}")
    produced = family_of_task(loaded.task_type)
    if row["families"] != [produced]:
        raise ValueError(
            f"Candidate {row['label']} declares families "
            f"{row['families']} but the config produces {produced}")
    return loaded


def _gate_thresholds(raw: object) -> GateThresholds:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    try:
        return GateThresholds.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid thresholds: {exc}") from exc


def _build_report(
        spec: dict[str, Any],
        loaded: list[CandidateOutput]) -> dict[str, Any]:
    events = _event_ids_by_family()
    families: dict[str, Any] = {}
    decisions: list[dict[str, Any]] = []
    for family in _FAMILY_ORDER:
        group = [item for item in loaded if family in item.families]
        if not group:
            continue
        section, family_decisions = _family_section(
            family, group, events[family], spec)
        families[family] = section
        decisions.extend(family_decisions)
    picked = recommend(decisions)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": spec["raw"],
        "families": families,
        "decisions": decisions,
        "recommended": {
            family: picked.get(family) for family in families}}


def _event_ids_by_family() -> dict[str, tuple[int, ...]]:
    result, btts, totals = market_event_families()
    return {
        FAMILY_RESULT: result,
        FAMILY_BTTS: btts,
        FAMILY_OVER_25: totals}


def _family_section(
        family: str,
        group: list[CandidateOutput],
        event_ids: tuple[int, ...],
        spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    before = {item.label: len(item.frame.match_ids) for item in group}
    aligned = align_outputs(group)
    dropped = {
        item.label: before[item.label] - len(item.frame.match_ids)
        for item in aligned}
    frame = aligned[0].frame
    years = fetch_season_years(frame.season_ids)
    names = (
        {} if family == FAMILY_RESULT
        else fetch_league_names(frame.league_ids))
    odds = fetch_match_odds(frame.match_ids, event_ids)
    prices = _price_board(
        consensus_fair_probabilities(odds),
        frame.match_ids,
        event_ids)
    section = {
        "n": int(len(frame.match_ids)),
        "dropped": dropped,
        "candidates": [
            _candidate_metrics(family, item, years, names, prices, spec)
            for item in aligned]}
    # Ten sam słownik sezonów co metryki, żeby bramka cięła tak samo.
    return section, _challenger_decisions(family, aligned, years, spec)


def _challenger_decisions(
        family: str,
        aligned: list[CandidateOutput],
        years: dict[int, str],
        spec: dict[str, Any]) -> list[dict[str, Any]]:
    champions = [item for item in aligned if item.role == "champion"]
    if len(champions) != 1:
        found = ", ".join(item.label for item in champions) or "none"
        raise ValueError(
            f"Family {family} must have exactly one champion, "
            f"found {found}")
    controls = [item for item in aligned if item.role == "control"]
    return [
        offline_decision(
            family,
            item,
            champions[0],
            controls,
            spec["thresholds"],
            spec["samples"],
            spec["seed"],
            years_by_season=years)
        for item in aligned
        if item.role == "challenger"]


def _candidate_metrics(
        family: str,
        item: CandidateOutput,
        years: dict[int, str],
        names: dict[int, str],
        prices: _Prices,
        spec: dict[str, Any]) -> dict[str, Any]:
    if family == FAMILY_RESULT:
        return _result_metrics(item, years, prices, spec)
    return _binary_metrics(family, item, years, names, prices, spec)


def _result_metrics(
        item: CandidateOutput,
        years: dict[int, str],
        prices: _Prices,
        spec: dict[str, Any]) -> dict[str, Any]:
    frame = item.frame
    probabilities = item.families[FAMILY_RESULT]
    outcomes = _result_outcomes(frame.home_goals, frame.away_goals)
    finals = item.result_finals
    if finals is None:
        finals = np.argmax(probabilities, axis=1).astype(int)
    losses = per_match_log_loss(probabilities, outcomes)
    shares = final_shares(finals, 3)
    return {
        "label": item.label,
        "role": item.role,
        "n": int(len(outcomes)),
        "log_loss": multiclass_log_loss(probabilities, outcomes),
        "brier": multiclass_brier(probabilities, outcomes),
        "ece": expected_calibration_error(probabilities, outcomes),
        "mean_p": {
            "h": float(np.mean(probabilities[:, 0])),
            "d": float(np.mean(probabilities[:, 1])),
            "a": float(np.mean(probabilities[:, 2]))},
        "final_shares": {
            "h": shares[0],
            "d": shares[1],
            "a": shares[2]},
        "reliability": _result_bins(probabilities, outcomes, spec["edges"]),
        "segments": _segments(frame.season_ids, losses, years),
        "market": _market_score(
            probabilities, prices.fair, prices.complete, outcomes, spec),
        "roi": _priced_roi(finals == outcomes, finals, prices)}


def _result_bins(
        probabilities: np.ndarray,
        outcomes: np.ndarray,
        edges: list[float]) -> dict[str, list[dict[str, Any]]]:
    return {
        "h": reliability_table(
            probabilities[:, 0], (outcomes == 0).astype(int), edges),
        "d": reliability_table(
            probabilities[:, 1], (outcomes == 1).astype(int), edges),
        "a": reliability_table(
            probabilities[:, 2], (outcomes == 2).astype(int), edges)}


def _binary_metrics(
        family: str,
        item: CandidateOutput,
        years: dict[int, str],
        names: dict[int, str],
        prices: _Prices,
        spec: dict[str, Any]) -> dict[str, Any]:
    frame = item.frame
    probabilities = np.asarray(item.families[family], dtype=float)
    outcomes = _binary_outcomes(
        family, frame.home_goals, frame.away_goals)
    # Remis 0.5 zostaje przy klasie 0, tak jak argmax dwóch kolumn.
    yes = (probabilities > 0.5).astype(int)
    losses = per_match_log_loss(probabilities, outcomes)
    shares = final_shares(yes, 2)
    return {
        "label": item.label,
        "role": item.role,
        "n": int(len(outcomes)),
        "log_loss": binary_log_loss(probabilities, outcomes),
        "brier": binary_brier(probabilities, outcomes),
        "ece": expected_calibration_error(probabilities, outcomes),
        "mean_p": float(np.mean(probabilities)),
        "final_shares": _binary_shares(family, shares),
        "reliability": reliability_table(
            probabilities, outcomes, spec["edges"]),
        "segments": _segments(frame.season_ids, losses, years),
        "leagues": league_table(
            frame.league_ids,
            probabilities,
            outcomes,
            yes,
            names),
        "market": _market_score(
            probabilities,
            prices.fair[:, 0],
            prices.complete,
            outcomes,
            spec),
        "roi": _priced_roi(
            yes == outcomes, _binary_selection(yes), prices)}


def _binary_shares(
        family: str,
        shares: list[float]) -> dict[str, float]:
    if family == FAMILY_BTTS:
        return {"no": shares[0], "yes": shares[1]}
    return {"under": shares[0], "over": shares[1]}


def _binary_selection(yes: np.ndarray) -> np.ndarray:
    """Map a yes/no final onto columns ordered positive, then negative."""
    return np.where(yes == 1, 0, 1)


def _segments(
        season_ids: np.ndarray,
        losses: np.ndarray,
        years: dict[int, str]) -> list[dict[str, Any]]:
    labels = season_format_segments(season_ids, years)
    rows: list[dict[str, Any]] = []
    for name in (
            SEASON_FORMAT_SPLIT_YEAR,
            SEASON_FORMAT_CALENDAR_YEAR,
            SEASON_FORMAT_UNKNOWN):
        chosen = labels == name
        count = int(np.sum(chosen))
        if count == 0:
            continue
        rows.append({
            "segment": name,
            "n": count,
            "log_loss": float(np.mean(losses[chosen]))})
    return rows


def _market_score(
        model: np.ndarray,
        market: np.ndarray,
        complete: np.ndarray,
        outcomes: np.ndarray,
        spec: dict[str, Any]) -> dict[str, Any]:
    """Score the model against the consensus, or skip a thin board."""
    # Niepełny rynek jest diagnostyką. Nie zatrzymuje raportu metryk.
    if not bool(np.any(complete)):
        return {"skipped": _NO_MARKET}
    try:
        return market_information_test(
            model[complete],
            market[complete],
            outcomes[complete],
            spec["samples"],
            spec["seed"])
    except ValueError as exc:
        return {"skipped": str(exc)}


def _priced_roi(
        hit: np.ndarray,
        selection: np.ndarray,
        prices: _Prices) -> dict[str, Any]:
    """Flat-stake the model's final at the best available odds."""
    chosen = prices.best[np.arange(len(hit)), selection]
    usable = prices.complete & np.isfinite(chosen)
    if not bool(np.any(usable)):
        return {"skipped": _NO_PRICE}
    return flat_stake_roi(
        np.asarray(hit, dtype=float)[usable],
        chosen[usable],
        BETTING_TAX_RATE)


def _price_board(
        consensus: pd.DataFrame,
        match_ids: np.ndarray,
        event_ids: tuple[int, ...]) -> _Prices:
    width = len(event_ids)
    count = len(match_ids)
    fair = np.full((count, width), np.nan)
    best = np.full((count, width), np.nan)
    lookup = _price_lookup(consensus)
    for index, match_id in enumerate(np.asarray(match_ids).tolist()):
        for class_index, event_id in enumerate(event_ids):
            found = lookup.get((int(match_id), int(event_id)))
            if found is None:
                continue
            fair[index, class_index] = found[0]
            best[index, class_index] = found[1]
    complete = np.isfinite(fair).all(axis=1) & np.isfinite(best).all(axis=1)
    return _Prices(fair=fair, best=best, complete=complete)


def _price_lookup(
        consensus: pd.DataFrame) -> dict[tuple[int, int], tuple[float, float]]:
    lookup: dict[tuple[int, int], tuple[float, float]] = {}
    if consensus.empty:
        return lookup
    for row in consensus.itertuples(index=False):
        lookup[(int(row.match_id), int(row.event_id))] = (
            float(row.fair_p), float(row.best_odds))
    return lookup


def _result_outcomes(
        home_goals: np.ndarray,
        away_goals: np.ndarray) -> np.ndarray:
    home = np.asarray(home_goals)
    away = np.asarray(away_goals)
    outcomes = np.full(len(home), 2, dtype=int)
    outcomes[home > away] = 0
    outcomes[home == away] = 1
    return outcomes


def _binary_outcomes(
        family: str,
        home_goals: np.ndarray,
        away_goals: np.ndarray) -> np.ndarray:
    home = np.asarray(home_goals).astype(int)
    away = np.asarray(away_goals).astype(int)
    if family == FAMILY_BTTS:
        return ((home > 0) & (away > 0)).astype(int)
    return (home + away > 2).astype(int)


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8")


def _repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _parse_date(value: object, name: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date") from exc


def _plain_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _shadow_request(args: object) -> dict[str, Any]:
    family = getattr(args, "family")
    if family not in _FAMILY_ORDER:
        raise ValueError(f"Unknown evaluation family {family!r}")
    date_from = _coerce_date(getattr(args, "date_from"), "date-from")
    date_to = _coerce_date(getattr(args, "date_to"), "date-to")
    if date_from >= date_to:
        raise ValueError("date-from must be before date-to")
    output = getattr(args, "output")
    if not isinstance(output, (str, Path)) or not str(output).strip():
        raise ValueError("output must be a path")
    return {
        "family": family,
        "champion_model": _model_name(
            getattr(args, "champion_model"), "champion-model"),
        "challenger_model": _model_name(
            getattr(args, "challenger_model"), "challenger-model"),
        "date_from": date_from,
        "date_to": date_to,
        "output": str(output)}


def _model_name(value: object, flag: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{flag} must be a model name")
    return value


def _coerce_date(value: object, name: str) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        return _parse_date(value, name)
    raise ValueError(f"{name} must be an ISO date")


def _registry_event_ids(
        family: str,
        champion_model: str,
        challenger_model: str) -> tuple[int, ...]:
    """Read one family's event ids from the two named configs.

    Ids come only from those configs. A key that is missing, not an
    integer, or that disagrees between the two models is an error.
    """
    keys = _FAMILY_EVENT_KEYS[family]
    registry = load_model_registry()
    found: dict[str, int] = {}
    for model_name in (champion_model, challenger_model):
        events = _registry_events(registry, model_name)
        _collect_family_ids(keys, events, model_name, found)
    return tuple(found[key] for key in keys)


def _registry_events(
        registry: dict[str, Path],
        model_name: str) -> dict[str, int | str]:
    if model_name not in registry:
        raise ValueError(
            f"Model {model_name} is not in the model registry")
    return load_model_config(registry[model_name]).events


def _collect_family_ids(
        keys: tuple[str, ...],
        events: dict[str, int | str],
        model_name: str,
        found: dict[str, int]) -> None:
    for key in keys:
        if key not in events:
            raise ValueError(
                f"Model {model_name} config has no event {key}")
        event_id = _configured_event_id(key, events[key], model_name)
        previous = found.get(key)
        if previous is not None and previous != event_id:
            raise ValueError(
                f"Event {key} has ids {previous} and {event_id}")
        found[key] = event_id


def _configured_event_id(
        key: str,
        reference: object,
        model_name: str) -> int:
    if isinstance(reference, bool) or not isinstance(reference, int):
        raise ValueError(
            f"Event {key} in {model_name} must be an integer id")
    return reference


def _finished_ids(finished: pd.DataFrame) -> list[int]:
    _require_frame(finished, _FINISHED_COLUMNS, "finished results")
    return [int(value) for value in finished["id"].tolist()]


def _compared_matches(
        family: str,
        finished: pd.DataFrame,
        published: pd.DataFrame,
        shadow: pd.DataFrame,
        event_ids: tuple[int, ...]) -> dict[str, Any]:
    match_ids = _finished_ids(finished)
    champion = _ready_rows(published, match_ids, event_ids)
    challenger = _ready_rows(shadow, match_ids, event_ids)
    covered = [
        match_id for match_id in match_ids if match_id in champion]
    compared = [
        match_id for match_id in covered if match_id in challenger]
    return {
        "n_finished": len(match_ids),
        "n_champion": len(covered),
        "n_compared": len(compared),
        "missing_rate": _missing_rate(covered, compared),
        "champion_p": _stack_ready(family, champion, compared),
        "challenger_p": _stack_ready(family, challenger, compared),
        "outcomes": _compared_outcomes(family, finished, compared),
        "league_ids": _compared_column(finished, compared, "league")}


def _missing_rate(covered: list[int], compared: list[int]) -> float:
    # Brak wiersza mistrza nie jest luką cienia: nie ma czego porównać.
    if not covered:
        return 1.0
    return (len(covered) - len(compared)) / len(covered)


def _ready_rows(
        values: pd.DataFrame,
        match_ids: list[int],
        event_ids: tuple[int, ...]) -> dict[int, np.ndarray]:
    lookup = _value_lookup(values)
    ready: dict[int, np.ndarray] = {}
    for match_id in match_ids:
        distribution = _match_distribution(lookup, match_id, event_ids)
        if distribution is None:
            continue
        ready[match_id] = distribution
    return ready


def _value_lookup(frame: pd.DataFrame) -> dict[tuple[int, int], float]:
    _require_frame(frame, _VALUE_COLUMNS, "predictions")
    lookup: dict[tuple[int, int], float] = {}
    rows = zip(
        frame["match_id"].tolist(),
        frame["event_id"].tolist(),
        frame["value"].tolist())
    for match_id, event_id, value in rows:
        key = (int(match_id), int(event_id))
        if key in lookup:
            raise ValueError(
                f"Duplicate prediction for match {key[0]} "
                f"event {key[1]}")
        number = _stored_percent(key, value)
        lookup[key] = number
    return lookup


def _stored_percent(key: tuple[int, int], value: object) -> float:
    if isinstance(value, bool) or not isinstance(
            value, (int, float, np.floating)):
        raise ValueError(
            f"Prediction value for match {key[0]} event {key[1]} "
            "must be between 0 and 100")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 100.0:
        raise ValueError(
            f"Prediction value for match {key[0]} event {key[1]} "
            "must be between 0 and 100")
    return number


def _match_distribution(
        lookup: dict[tuple[int, int], float],
        match_id: int,
        event_ids: tuple[int, ...]) -> np.ndarray | None:
    values: list[float] = []
    for event_id in event_ids:
        found = lookup.get((match_id, event_id))
        if found is None:
            return None
        values.append(found)
    total = float(sum(values))
    if total <= 0.0:
        raise ValueError(
            f"Prediction values for match {match_id} "
            "must sum to more than 0")
    # Suma, nie /100: wiersz procentowy i ułamkowy dają ten sam rozkład.
    return np.asarray(values, dtype=float) / total


def _stack_ready(
        family: str,
        ready: dict[int, np.ndarray],
        match_ids: list[int]) -> np.ndarray:
    if not match_ids:
        if family == FAMILY_RESULT:
            return np.zeros((0, 3), dtype=float)
        return np.zeros((0,), dtype=float)
    stacked = np.vstack([ready[match_id] for match_id in match_ids])
    if family == FAMILY_RESULT:
        return stacked
    return stacked[:, 0]


def _compared_outcomes(
        family: str,
        finished: pd.DataFrame,
        match_ids: list[int]) -> np.ndarray:
    if not match_ids:
        return np.zeros((0,), dtype=int)
    home = _compared_column(finished, match_ids, "home_team_goals")
    away = _compared_column(finished, match_ids, "away_team_goals")
    if family == FAMILY_RESULT:
        return _result_outcomes(home, away)
    return _binary_outcomes(family, home, away)


def _compared_column(
        finished: pd.DataFrame,
        match_ids: list[int],
        column: str) -> np.ndarray:
    if not match_ids:
        return np.zeros((0,), dtype=int)
    lookup = {
        int(match_id): value
        for match_id, value in zip(
            finished["id"].tolist(),
            finished[column].tolist())}
    return np.asarray(
        [int(lookup[match_id]) for match_id in match_ids],
        dtype=int)


def _shadow_document(
        request: dict[str, Any],
        champion_id: int,
        challenger_id: int,
        compared: dict[str, Any],
        decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "champion_model": request["champion_model"],
        "challenger_model": request["challenger_model"],
        "champion_model_id": champion_id,
        "challenger_model_id": challenger_id,
        "date_from": request["date_from"].isoformat(),
        "date_to": request["date_to"].isoformat(),
        "sport_id": _SHADOW_SPORT_ID,
        "n_finished": compared["n_finished"],
        "n_champion": compared["n_champion"],
        "n_compared": compared["n_compared"],
        "missing_rate": compared["missing_rate"],
        "metrics": _shadow_metrics(request["family"], compared),
        "family": decision["family"],
        "log_loss": decision["log_loss"],
        "passed": decision["passed"],
        "checks": decision["checks"]}


def _shadow_metrics(
        family: str,
        compared: dict[str, Any]) -> dict[str, Any]:
    outcomes = compared["outcomes"]
    if len(outcomes) == 0:
        skipped = {"skipped": _NO_COMPARED}
        return {"champion": skipped, "challenger": skipped}
    return {
        "champion": _family_scores(
            family, compared["champion_p"], outcomes),
        "challenger": _family_scores(
            family, compared["challenger_p"], outcomes)}


def _family_scores(
        family: str,
        probabilities: np.ndarray,
        outcomes: np.ndarray) -> dict[str, Any]:
    if family == FAMILY_RESULT:
        return _result_scores(probabilities, outcomes)
    return _binary_scores(family, probabilities, outcomes)


def _result_scores(
        probabilities: np.ndarray,
        outcomes: np.ndarray) -> dict[str, Any]:
    shares = final_shares(
        np.argmax(probabilities, axis=1).astype(int), 3)
    return {
        "n": int(len(outcomes)),
        "log_loss": multiclass_log_loss(probabilities, outcomes),
        "brier": multiclass_brier(probabilities, outcomes),
        "ece": expected_calibration_error(probabilities, outcomes),
        "mean_p": {
            "h": float(np.mean(probabilities[:, 0])),
            "d": float(np.mean(probabilities[:, 1])),
            "a": float(np.mean(probabilities[:, 2]))},
        "final_shares": {
            "h": shares[0],
            "d": shares[1],
            "a": shares[2]}}


def _binary_scores(
        family: str,
        probabilities: np.ndarray,
        outcomes: np.ndarray) -> dict[str, Any]:
    vector = np.asarray(probabilities, dtype=float)
    yes = (vector > 0.5).astype(int)
    shares = final_shares(yes, 2)
    return {
        "n": int(len(outcomes)),
        "log_loss": binary_log_loss(vector, outcomes),
        "brier": binary_brier(vector, outcomes),
        "ece": expected_calibration_error(vector, outcomes),
        "mean_p": float(np.mean(vector)),
        "final_shares": _binary_shares(family, shares)}


def _require_frame(
        frame: object,
        columns: tuple[str, ...],
        label: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError(f"{label} must be a DataFrame")
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ValueError(
            f"{label} are missing " + ", ".join(missing))
