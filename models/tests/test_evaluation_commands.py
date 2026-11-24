"""Offline compare-models report without TensorFlow."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.betting_tax import BETTING_TAX_RATE
from backend.config import REPO_ROOT
from models.pipeline.core.cli import build_parser
from models.pipeline.evaluation import commands as command_module
from models.pipeline.evaluation.candidates import FAMILY_BTTS
from models.pipeline.evaluation.candidates import FAMILY_RESULT
from models.pipeline.evaluation.candidates import CandidateOutput
from models.pipeline.evaluation.candidates import EvaluationFrame
from models.pipeline.evaluation.candidates import align_outputs
from models.pipeline.evaluation.candidates import load_candidate_output
from models.pipeline.evaluation.candidates import _families_from_task
from models.pipeline.evaluation.commands import run_compare_models
from models.pipeline.evaluation.market import flat_stake_roi
from models.pipeline.evaluation.market import market_event_families
from models.pipeline.evaluation.metrics import multiclass_log_loss


def test_compare_models_rejects_spec_without_champion(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, [_candidate("only_control", "control")])
    with pytest.raises(ValueError, match="exactly one champion"):
        run_compare_models(SimpleNamespace(spec=spec_path))


def test_compare_models_rejects_two_champions(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, [
        _candidate("first", "champion"),
        _candidate("second", "champion")])
    with pytest.raises(ValueError, match="exactly one champion"):
        run_compare_models(SimpleNamespace(spec=spec_path))


def test_compare_models_rejects_candidate_without_family(
        tmp_path: Path) -> None:
    row = _candidate("bare", "champion")
    row["families"] = []
    spec_path = _write_spec(tmp_path, [row])
    with pytest.raises(ValueError, match="has no family"):
        run_compare_models(SimpleNamespace(spec=spec_path))


def test_compare_models_rejects_family_the_config_does_not_produce(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = _write_config(tmp_path, "result")
    row = _candidate("result_model", "champion", config_path)
    row["families"] = ["btts"]
    spec_path = _write_spec(tmp_path, [row])

    def _fail(*_args: object, **_kwargs: object) -> CandidateOutput:
        raise AssertionError("model should not be loaded")

    monkeypatch.setattr(command_module, "load_candidate_output", _fail)
    with pytest.raises(ValueError, match="produces result"):
        run_compare_models(SimpleNamespace(spec=spec_path))


def test_load_candidate_output_names_missing_artifact(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = _write_config(tmp_path, "result")

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("database should not be opened")

    monkeypatch.setattr(
        "models.pipeline.evaluation.candidates.fetch_finished_matches",
        _fail)
    with pytest.raises(FileNotFoundError, match="result_v2_champion"):
        load_candidate_output(
            "result_v2_champion",
            "champion",
            config_path,
            date(2026, 9, 1),
            date(2026, 11, 10))


def test_compare_models_writes_aligned_result_metrics(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    champion_probs = np.array([
        [0.6, 0.2, 0.2],
        [0.2, 0.6, 0.2],
        [0.2, 0.2, 0.6]])
    challenger_probs = np.array([
        [0.7, 0.2, 0.1],
        [0.2, 0.5, 0.3]])
    outputs = {
        "result_v2_champion": _result_output(
            "result_v2_champion",
            "champion",
            [1, 2, 3],
            champion_probs,
            [(2, 0), (1, 1), (0, 1)]),
        "result_v3_challenger": _result_output(
            "result_v3_challenger",
            "challenger",
            [1, 2],
            challenger_probs,
            [(2, 0), (1, 1)])}
    output_path = tmp_path / "reports" / "offline.json"
    spec_path = _write_spec(tmp_path, [
        _candidate("result_v2_champion", "champion"),
        _candidate("result_v3_challenger", "challenger")], output_path)
    _patch_sources(monkeypatch, outputs)
    report = run_compare_models(SimpleNamespace(spec=spec_path))
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == report
    assert "T" in report["generated_at"]
    assert "decisions" not in report
    assert report["spec"]["test_from"] == "2026-09-01"
    family = report["families"]["result"]
    assert family["n"] == 2
    assert family["dropped"] == {
        "result_v2_champion": 1,
        "result_v3_challenger": 0}
    champion = family["candidates"][0]
    assert champion["label"] == "result_v2_champion"
    assert champion["log_loss"] == pytest.approx(multiclass_log_loss(
        champion_probs[:2], np.array([0, 1])))
    assert champion["market"] == {"skipped": "no complete market"}
    assert champion["roi"] == {"skipped": "no priced selections"}
    assert champion["segments"] == [{
        "segment": "split_year",
        "n": 2,
        "log_loss": champion["log_loss"]}]
    assert set(champion["final_shares"]) == {"h", "d", "a"}
    assert "h" in champion["reliability"]


def test_compare_models_scores_btts_market_and_roi(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    yes_id, no_id = market_event_families()[1]
    probabilities = np.array([0.8, 0.2, 0.7, 0.4])
    output = _btts_output(probabilities)
    output_path = tmp_path / "btts.json"
    row = _candidate(
        "btts_v2_champion",
        "champion",
        REPO_ROOT / "models" / "configs" / "prediction" / "football_btts_v2.json")
    row["families"] = ["btts"]
    spec_path = _write_spec(
        tmp_path, [row], output_path, samples=12, seed=3)
    yes_odds = (1.6, 2.4, 1.7, 2.3)
    no_odds = (2.4, 1.6, 2.3, 1.7)
    quotes = []
    for match_id, yes_price, no_price in zip(
            (1, 2, 3, 4), yes_odds, no_odds):
        quotes.extend([
            _quote(match_id, yes_id, yes_price),
            _quote(match_id, no_id, no_price)])
    _patch_sources(
        monkeypatch,
        {"btts_v2_champion": output},
        odds=pd.DataFrame(quotes),
        years={3: "2026"},
        names={7: "Alpha", 8: "Beta"})
    report = run_compare_models(SimpleNamespace(spec=spec_path))
    candidate = report["families"]["btts"]["candidates"][0]
    expected = flat_stake_roi(
        np.ones(4),
        np.array([1.6, 1.6, 1.7, 1.7]),
        BETTING_TAX_RATE)
    assert candidate["n"] == 4
    assert candidate["roi"]["roi"] == pytest.approx(expected["roi"])
    assert candidate["roi"]["roi_after_tax"] == pytest.approx(
        expected["roi_after_tax"])
    assert candidate["roi"]["bets"] == 4.0
    assert "model_coef" in candidate["market"]
    assert [row["league_id"] for row in candidate["leagues"]] == [7, 8]
    assert candidate["leagues"][0]["league_name"] == "Alpha"
    assert candidate["segments"][0]["segment"] == "calendar_year"
    assert candidate["final_shares"]["yes"] == pytest.approx(0.5)


def test_align_outputs_keeps_shared_matches_in_first_order() -> None:
    first = _result_output(
        "first", "champion", [3, 1, 2],
        np.array([
            [0.3, 0.3, 0.4],
            [0.1, 0.2, 0.7],
            [0.5, 0.4, 0.1]]),
        [(0, 1), (2, 0), (1, 1)])
    second = _result_output(
        "second", "challenger", [2, 1],
        np.array([[0.2, 0.2, 0.6], [0.4, 0.4, 0.2]]),
        [(1, 1), (2, 0)])
    aligned = align_outputs([first, second])
    assert aligned[0].frame.match_ids.tolist() == [1, 2]
    assert aligned[1].frame.match_ids.tolist() == [1, 2]
    assert aligned[0].families[FAMILY_RESULT][0, 0] == pytest.approx(0.1)
    assert aligned[1].families[FAMILY_RESULT][0, 2] == pytest.approx(0.2)


def test_align_outputs_rejects_empty_intersection() -> None:
    first = _result_output(
        "first", "champion", [1],
        np.array([[0.5, 0.3, 0.2]]), [(1, 0)])
    second = _result_output(
        "second", "challenger", [2],
        np.array([[0.2, 0.3, 0.5]]), [(0, 1)])
    with pytest.raises(ValueError, match="no matches in common"):
        align_outputs([first, second])


def test_families_from_task_normalizes_classes_and_lambdas() -> None:
    families, finals, expected = _families_from_task(
        "result",
        np.array([[2.0, 2.0, 0.0], [0.0, 0.0, 3.0]]),
        5,
        "demo")
    assert finals is not None
    assert finals.tolist() == [0, 2]
    assert families[FAMILY_RESULT][0, 0] == pytest.approx(0.5)
    assert expected is None
    btts, btts_finals, btts_expected = _families_from_task(
        "btts", np.array([[1.0, 3.0]]), 5, "btts")
    assert btts[FAMILY_BTTS][0] == pytest.approx(0.75)
    assert btts_finals is None
    assert btts_expected is None
    goals, goal_finals, goal_expected = _families_from_task(
        "goals_poisson",
        np.array([[1.0, 1.0], [-0.2, 0.4]]),
        5,
        "goals")
    assert goal_finals is None
    assert goal_expected.tolist() == pytest.approx([2.0, 0.4])
    assert goals["over_25"].shape == (2,)
    assert np.all((goals["over_25"] >= 0.0) & (goals["over_25"] <= 1.0))


def test_parser_compare_models_requires_spec() -> None:
    args = build_parser().parse_args([
        "compare-models",
        "--spec",
        "models/configs/evaluation/eb44_offline_gate.json"])
    assert args.command == "compare-models"
    assert args.spec == Path(
        "models/configs/evaluation/eb44_offline_gate.json")
    with pytest.raises(SystemExit):
        build_parser().parse_args(["compare-models"])


def test_offline_gate_spec_lists_three_champions() -> None:
    path = (
        REPO_ROOT / "models" / "configs" / "evaluation"
        / "eb44_offline_gate.json")
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert spec["test_from"] == "2026-09-01"
    assert spec["test_to"] == "2026-11-10"
    families = {
        row["families"][0]: row["role"] for row in spec["candidates"]}
    assert families == {
        "result": "champion",
        "btts": "champion",
        "over_25": "champion"}


def _write_spec(
        tmp_path: Path,
        candidates: list[dict[str, object]],
        output_path: Path | None = None,
        samples: int = 20,
        seed: int = 1) -> Path:
    target = output_path or (tmp_path / "report.json")
    payload = {
        "sport_id": 1,
        "test_from": "2026-09-01",
        "test_to": "2026-11-10",
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
        "reliability_edges": [0, 0.5, 1],
        "candidates": candidates,
        "thresholds": {},
        "output_path": str(target)}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(
        label: str,
        role: str,
        config: Path | None = None) -> dict[str, object]:
    return {
        "label": label,
        "role": role,
        "families": ["result"],
        "config": str(config or "models/configs/prediction/football_result_v2.json")}


def _write_config(tmp_path: Path, task_type: str) -> Path:
    path = tmp_path / f"{task_type}.json"
    path.write_text(json.dumps({
        "model_name": "demo",
        "sport_id": 1,
        "task_type": task_type,
        "artifact_dir": str(tmp_path / "missing-artifact"),
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "FootballResultLabeler",
        "trainer": "LstmTrainer",
        "output_columns": ["p_home", "p_draw", "p_away"],
        "feature_config": {}}), encoding="utf-8")
    return path


def _patch_sources(
        monkeypatch: pytest.MonkeyPatch,
        outputs: dict[str, CandidateOutput],
        odds: pd.DataFrame | None = None,
        years: dict[int, str] | None = None,
        names: dict[int, str] | None = None) -> None:
    def _load(label: str, *_args: object, **_kwargs: object) -> CandidateOutput:
        return outputs[label]

    empty = pd.DataFrame(columns=[
        "match_id", "bookmaker_id", "event_id", "odds"])
    monkeypatch.setattr(command_module, "load_candidate_output", _load)
    monkeypatch.setattr(
        command_module,
        "fetch_season_years",
        lambda _ids: years if years is not None else {1: "2026/2027"})
    monkeypatch.setattr(
        command_module,
        "fetch_league_names",
        lambda _ids: names or {})
    monkeypatch.setattr(
        command_module,
        "fetch_match_odds",
        lambda _matches, _events: empty if odds is None else odds)


def _result_output(
        label: str,
        role: str,
        match_ids: list[int],
        probabilities: np.ndarray,
        goals: list[tuple[int, int]]) -> CandidateOutput:
    return CandidateOutput(
        label=label,
        role=role,
        frame=_frame(match_ids, goals, league_id=1, season_id=1),
        families={FAMILY_RESULT: probabilities},
        result_finals=np.argmax(probabilities, axis=1).astype(int),
        expected_goals=None)


def _btts_output(probabilities: np.ndarray) -> CandidateOutput:
    goals = [(1, 1), (1, 0), (2, 1), (0, 0)]
    return CandidateOutput(
        label="btts_v2_champion",
        role="champion",
        frame=_frame(
            [1, 2, 3, 4],
            goals,
            league_id=None,
            season_id=3,
            league_ids=np.array([7, 7, 8, 8])),
        families={FAMILY_BTTS: probabilities},
        result_finals=None,
        expected_goals=None)


def _frame(
        match_ids: list[int],
        goals: list[tuple[int, int]],
        league_id: int | None,
        season_id: int,
        league_ids: np.ndarray | None = None) -> EvaluationFrame:
    count = len(match_ids)
    leagues = (
        league_ids if league_ids is not None
        else np.full(count, league_id, dtype=int))
    return EvaluationFrame(
        match_ids=np.asarray(match_ids, dtype=int),
        league_ids=leagues,
        season_ids=np.full(count, season_id, dtype=int),
        dates=np.arange(count),
        home_goals=np.asarray([item[0] for item in goals], dtype=int),
        away_goals=np.asarray([item[1] for item in goals], dtype=int))


def _quote(match_id: int, event_id: int, odds: float) -> dict[str, object]:
    return {
        "match_id": match_id,
        "bookmaker_id": 1,
        "event_id": event_id,
        "odds": odds}
