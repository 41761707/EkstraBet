"""Offline comparison of champion, control and challenger models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.config import REPO_ROOT
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import load_model_config
from models.pipeline.data.evaluation_repository import fetch_league_names
from models.pipeline.data.evaluation_repository import fetch_match_odds
from models.pipeline.data.evaluation_repository import fetch_season_years
from models.pipeline.evaluation.candidates import CANDIDATE_ROLES
from models.pipeline.evaluation.candidates import FAMILY_BTTS
from models.pipeline.evaluation.candidates import FAMILY_OVER_25
from models.pipeline.evaluation.candidates import FAMILY_RESULT
from models.pipeline.evaluation.candidates import CandidateOutput
from models.pipeline.evaluation.candidates import align_outputs
from models.pipeline.evaluation.candidates import family_of_task
from models.pipeline.evaluation.candidates import load_candidate_output
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


@dataclass(frozen=True)
class _Prices:
    """Fair probabilities and best odds aligned to one match order."""

    fair: np.ndarray
    best: np.ndarray
    complete: np.ndarray


def run_compare_models(args: object) -> dict[str, Any]:
    """Write the offline report described by ``--spec`` and return it.

    Gate decisions are added by the offline gate. This report stores
    the scores those checks read.
    """
    spec = _read_spec(Path(getattr(args, "spec")))
    loaded = _load_candidates(spec)
    report = _build_report(spec, loaded)
    _write_report(report, _repo_path(spec["output_path"]))
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
        "output_path": output_path}


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


def _build_report(
        spec: dict[str, Any],
        loaded: list[CandidateOutput]) -> dict[str, Any]:
    events = _event_ids_by_family()
    families: dict[str, Any] = {}
    for family in _FAMILY_ORDER:
        group = [item for item in loaded if family in item.families]
        if not group:
            continue
        families[family] = _family_section(
            family, group, events[family], spec)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": spec["raw"],
        "families": families}


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
        spec: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "n": int(len(frame.match_ids)),
        "dropped": dropped,
        "candidates": [
            _candidate_metrics(family, item, years, names, prices, spec)
            for item in aligned]}


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
