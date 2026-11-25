"""Offline promotion gate for one challenger on the frozen test.

The checks are pure. Season labels come from the caller, so this
module does not open a database connection and does not load a model.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from pydantic import BaseModel
from pydantic import ConfigDict

from models.pipeline.evaluation.candidates import FAMILY_BTTS
from models.pipeline.evaluation.candidates import FAMILY_OVER_25
from models.pipeline.evaluation.candidates import FAMILY_RESULT
from models.pipeline.evaluation.candidates import CandidateOutput
from models.pipeline.evaluation.candidates import EvaluationFrame
from models.pipeline.evaluation.metrics import binary_log_loss
from models.pipeline.evaluation.metrics import expected_calibration_error
from models.pipeline.evaluation.metrics import final_shares
from models.pipeline.evaluation.metrics import multiclass_log_loss
from models.pipeline.evaluation.metrics import paired_bootstrap_diff
from models.pipeline.evaluation.metrics import per_match_log_loss
from models.pipeline.evaluation.segments import SEASON_FORMAT_CALENDAR_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_SPLIT_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_UNKNOWN
from models.pipeline.evaluation.segments import league_table
from models.pipeline.evaluation.segments import median_within_league_std
from models.pipeline.evaluation.segments import season_format_segments
from models.pipeline.evaluation.segments import weighted_level_error


_FAMILIES = frozenset({FAMILY_RESULT, FAMILY_BTTS, FAMILY_OVER_25})
_SEASON_FORMATS = (
    SEASON_FORMAT_SPLIT_YEAR,
    SEASON_FORMAT_CALENDAR_YEAR,
    SEASON_FORMAT_UNKNOWN)
_FRAME_FIELDS = (
    "match_ids",
    "league_ids",
    "season_ids",
    "home_goals",
    "away_goals")


class GateThresholds(BaseModel):
    """Limits for the offline gate and the later shadow check."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False)

    max_ece_increase: float = 0.01
    max_segment_log_loss_increase: float = 0.005
    max_home_final_share: float = 0.70
    min_btts_within_league_std: float = 0.05
    max_goal_mean_error: float = 0.10
    shadow_min_matches: int = 300
    shadow_max_log_loss_increase: float = 0.005
    shadow_max_ece_increase: float = 0.02
    shadow_max_missing_rate: float = 0.02


def offline_decision(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        controls: Sequence[CandidateOutput],
        thresholds: GateThresholds,
        samples: int,
        seed: int,
        *,
        years_by_season: dict[int, str] | None = None) -> dict[str, Any]:
    """Return one challenger's checks, each with a value and a result.

    Rows must already share matches, leagues, seasons and goals.
    ``years_by_season`` labels season formats. An empty map puts
    every match in ``unknown``. A family with no control passes
    ``vs_control``, because the check is "for each control".
    """
    _require_family(family)
    usable = _aligned_controls(family, challenger, champion, controls)
    outcomes = _outcomes(family, challenger.frame)
    checks: dict[str, dict[str, Any]] = {
        "vs_champion": _vs_champion(
            family, challenger, champion, outcomes, samples, seed),
        "vs_control": _vs_controls(
            family, challenger, usable, outcomes, samples, seed),
        "ece": _ece_check(
            family, challenger, champion, outcomes, thresholds),
        "segments": _segment_check(
            family,
            challenger,
            champion,
            outcomes,
            _years(years_by_season),
            thresholds)}
    checks.update(_family_check(
        family, challenger, champion, outcomes, thresholds))
    passed = all(item["passed"] for item in checks.values())
    return {
        "family": family,
        "label": challenger.label,
        "log_loss": _mean_loss(family, challenger, outcomes),
        "passed": passed,
        "checks": checks}


def recommend(decisions: list[dict[str, Any]]) -> dict[str, str | None]:
    """Pick the passing challenger with the lowest log loss per family.

    A family whose challengers all fail maps to ``None``. Equal log
    loss keeps the earlier decision. Families absent from
    ``decisions`` are absent from the result.
    """
    if not isinstance(decisions, list):
        raise ValueError("decisions must be a list")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in decisions:
        family = _decision_family(item)
        grouped.setdefault(family, []).append(item)
    chosen: dict[str, str | None] = {}
    for family, rows in grouped.items():
        passing = [row for row in rows if row.get("passed") is True]
        chosen[family] = _best_label(passing)
    return chosen


def _vs_champion(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, Any]:
    value = _gap(family, challenger, champion, outcomes, samples, seed)
    # Remis nie jest poprawą: cały przedział musi leżeć poniżej zera.
    return _check(value, value["ci_high"] < 0.0)


def _vs_controls(
        family: str,
        challenger: CandidateOutput,
        controls: Sequence[CandidateOutput],
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, Any]:
    rows = [
        _control_gap(family, challenger, item, outcomes, samples, seed)
        for item in controls]
    return _check(rows, all(row["passed"] for row in rows))


def _control_gap(
        family: str,
        challenger: CandidateOutput,
        control: CandidateOutput,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, Any]:
    gap = _gap(family, challenger, control, outcomes, samples, seed)
    return {
        "label": control.label,
        "mean_diff": gap["mean_diff"],
        "ci_low": gap["ci_low"],
        "ci_high": gap["ci_high"],
        "passed": bool(gap["ci_high"] < 0.0)}


def _ece_check(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        outcomes: np.ndarray,
        thresholds: GateThresholds) -> dict[str, Any]:
    challenger_ece = expected_calibration_error(
        _probabilities(challenger, family), outcomes)
    champion_ece = expected_calibration_error(
        _probabilities(champion, family), outcomes)
    limit = champion_ece + thresholds.max_ece_increase
    value = {
        "challenger": challenger_ece,
        "champion": champion_ece,
        "limit": limit}
    return _check(value, challenger_ece <= limit)


def _segment_check(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        outcomes: np.ndarray,
        years: dict[int, str],
        thresholds: GateThresholds) -> dict[str, Any]:
    labels = season_format_segments(challenger.frame.season_ids, years)
    left = _losses(family, challenger, outcomes)
    right = _losses(family, champion, outcomes)
    rows: list[dict[str, Any]] = []
    for name in _SEASON_FORMATS:
        chosen = labels == name
        count = int(np.sum(chosen))
        if count == 0:
            continue
        challenger_loss = float(np.mean(left[chosen]))
        champion_loss = float(np.mean(right[chosen]))
        diff = challenger_loss - champion_loss
        rows.append({
            "segment": name,
            "n": count,
            "challenger": challenger_loss,
            "champion": champion_loss,
            "diff": diff,
            "passed": bool(
                diff <= thresholds.max_segment_log_loss_increase)})
    if not rows:
        raise ValueError("segment check has no matches")
    return _check(rows, all(row["passed"] for row in rows))


def _family_check(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        outcomes: np.ndarray,
        thresholds: GateThresholds) -> dict[str, dict[str, Any]]:
    if family == FAMILY_RESULT:
        return {
            "result_finals": _result_finals(
                challenger, outcomes, thresholds)}
    if family == FAMILY_BTTS:
        return {"btts_leagues": _btts_leagues(
            family, challenger, champion, outcomes, thresholds)}
    return {"goal_mean": _goal_mean(challenger, thresholds)}


def _result_finals(
        challenger: CandidateOutput,
        outcomes: np.ndarray,
        thresholds: GateThresholds) -> dict[str, Any]:
    finals = challenger.result_finals
    if finals is None:
        probabilities = _probabilities(challenger, FAMILY_RESULT)
        finals = np.argmax(probabilities, axis=1).astype(int)
    shares = final_shares(finals, 3)
    home_share = shares[0]
    draw_share = shares[1]
    actual_draw = float(np.mean(outcomes == 1))
    value = {
        "home_share": home_share,
        "max_home_share": thresholds.max_home_final_share,
        "draw_share": draw_share,
        "actual_draw_share": actual_draw}
    passed = (
        home_share <= thresholds.max_home_final_share
        and draw_share <= actual_draw)
    return _check(value, passed)


def _btts_leagues(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        outcomes: np.ndarray,
        thresholds: GateThresholds) -> dict[str, Any]:
    level = weighted_level_error(_binary_table(family, challenger, outcomes))
    champion_level = weighted_level_error(
        _binary_table(family, champion, outcomes))
    spread, error = _within_league_std(
        _binary_table(family, challenger, outcomes))
    value: dict[str, Any] = {
        "within_league_std": spread,
        "min_within_league_std": thresholds.min_btts_within_league_std,
        "level_error": level,
        "champion_level_error": champion_level}
    if error is not None:
        value["error"] = error
    spread_ok = (
        spread is not None
        and spread >= thresholds.min_btts_within_league_std)
    return _check(value, spread_ok and level <= champion_level)


def _goal_mean(
        challenger: CandidateOutput,
        thresholds: GateThresholds) -> dict[str, Any]:
    expected = challenger.expected_goals
    if expected is None:
        raise ValueError(
            f"Candidate {challenger.label} has no expected goals")
    rates = np.asarray(expected, dtype=float)
    if len(rates) != len(challenger.frame.match_ids):
        raise ValueError(
            f"Candidate {challenger.label} expected goals do not "
            "match the matches")
    if not np.isfinite(rates).all():
        raise ValueError(
            f"Candidate {challenger.label} expected goals must be finite")
    actual = (
        np.asarray(challenger.frame.home_goals, dtype=float)
        + np.asarray(challenger.frame.away_goals, dtype=float))
    expected_mean = float(np.mean(rates))
    actual_mean = float(np.mean(actual))
    error = abs(expected_mean - actual_mean)
    value = {
        "error": error,
        "max_error": thresholds.max_goal_mean_error,
        "expected": expected_mean,
        "actual": actual_mean}
    return _check(value, error <= thresholds.max_goal_mean_error)


def _gap(
        family: str,
        left: CandidateOutput,
        right: CandidateOutput,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, float]:
    diff = paired_bootstrap_diff(
        _losses(family, left, outcomes),
        _losses(family, right, outcomes),
        samples,
        seed)
    return {
        "mean_diff": diff["mean_diff"],
        "ci_low": diff["ci_low"],
        "ci_high": diff["ci_high"]}


def _aligned_controls(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        controls: Sequence[CandidateOutput]) -> list[CandidateOutput]:
    if isinstance(controls, (str, bytes)) or not isinstance(
            controls, Sequence):
        raise ValueError("controls must be a sequence of candidates")
    _require_role(challenger, "challenger")
    _require_role(champion, "champion")
    _probabilities(challenger, family)
    _probabilities(champion, family)
    _require_same_frame(challenger, champion)
    usable: list[CandidateOutput] = []
    for item in controls:
        if family not in item.families:
            continue
        _require_role(item, "control")
        _probabilities(item, family)
        _require_same_frame(challenger, item)
        usable.append(item)
    return usable


def _require_same_frame(
        reference: CandidateOutput,
        other: CandidateOutput) -> None:
    for name in _FRAME_FIELDS:
        left = getattr(reference.frame, name)
        right = getattr(other.frame, name)
        if np.array_equal(left, right):
            continue
        raise ValueError(
            f"Candidate {other.label} {name} does not match "
            f"{reference.label}")


def _binary_table(
        family: str,
        item: CandidateOutput,
        outcomes: np.ndarray) -> list[dict[str, int | float | str]]:
    probabilities = np.asarray(_probabilities(item, family), dtype=float)
    # Remis 0.5 zostaje przy „nie”, tak jak argmax dwóch kolumn.
    yes = (probabilities > 0.5).astype(int)
    return league_table(
        item.frame.league_ids,
        probabilities,
        outcomes,
        yes,
        {})


def _within_league_std(
        table: list[dict[str, int | float | str]]
        ) -> tuple[float | None, str | None]:
    try:
        return median_within_league_std(table), None
    except ValueError as exc:
        # Za mała liga nie może przerwać raportu pozostałych rodzin.
        return None, str(exc)


def _losses(
        family: str,
        item: CandidateOutput,
        outcomes: np.ndarray) -> np.ndarray:
    return per_match_log_loss(_probabilities(item, family), outcomes)


def _mean_loss(
        family: str,
        item: CandidateOutput,
        outcomes: np.ndarray) -> float:
    probabilities = _probabilities(item, family)
    if family == FAMILY_RESULT:
        return multiclass_log_loss(probabilities, outcomes)
    return binary_log_loss(probabilities, outcomes)


def _probabilities(item: CandidateOutput, family: str) -> np.ndarray:
    if family not in item.families:
        raise ValueError(
            f"Candidate {item.label} has no {family} probabilities")
    return np.asarray(item.families[family], dtype=float)


def _outcomes(family: str, frame: EvaluationFrame) -> np.ndarray:
    home = np.asarray(frame.home_goals)
    away = np.asarray(frame.away_goals)
    if family == FAMILY_RESULT:
        outcomes = np.full(len(home), 2, dtype=int)
        outcomes[home > away] = 0
        outcomes[home == away] = 1
        return outcomes
    scored = home.astype(int)
    conceded = away.astype(int)
    if family == FAMILY_BTTS:
        return ((scored > 0) & (conceded > 0)).astype(int)
    return (scored + conceded > 2).astype(int)


def _years(years_by_season: dict[int, str] | None) -> dict[int, str]:
    if years_by_season is None:
        return {}
    if not isinstance(years_by_season, dict):
        raise ValueError("years_by_season must map season id to a label")
    return years_by_season


def _require_family(family: str) -> None:
    if family not in _FAMILIES:
        raise ValueError(f"Unknown evaluation family {family!r}")


def _require_role(item: CandidateOutput, role: str) -> None:
    if item.role != role:
        raise ValueError(
            f"Candidate {item.label} role is {item.role}, expected {role}")


def _decision_family(item: object) -> str:
    if not isinstance(item, dict):
        raise ValueError("decisions must be a list of objects")
    family = item.get("family")
    if not isinstance(family, str) or not family:
        raise ValueError("decision is missing family")
    return family


def _best_label(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    best = min(rows, key=_decision_loss)
    label = best.get("label")
    if not isinstance(label, str) or not label:
        raise ValueError("decision is missing label")
    return label


def _decision_loss(row: dict[str, Any]) -> float:
    value = row.get("log_loss")
    if isinstance(value, bool):
        raise ValueError("decision log_loss must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("decision log_loss must be a number") from None
    if not math.isfinite(number):
        raise ValueError("decision log_loss must be finite")
    return number


def _check(value: Any, passed: bool) -> dict[str, Any]:
    return {"value": value, "passed": bool(passed)}
