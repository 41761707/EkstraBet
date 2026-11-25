"""Offline compare-models and shadow-report without TensorFlow."""

from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

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
from models.pipeline.data.evaluation_repository import fetch_finished_results
from models.pipeline.data.evaluation_repository import fetch_published_values
from models.pipeline.data.evaluation_repository import fetch_shadow_values
from models.pipeline.evaluation.commands import run_compare_models
from models.pipeline.evaluation.commands import run_shadow_report
from models.pipeline.evaluation.market import flat_stake_roi
from models.pipeline.evaluation.market import market_event_families
from models.pipeline.evaluation.metrics import multiclass_log_loss


_REPOSITORY = "models.pipeline.data.evaluation_repository"


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
    assert report["spec"]["test_from"] == "2026-09-01"
    decision = report["decisions"][0]
    assert decision["family"] == "result"
    assert decision["label"] == "result_v3_challenger"
    assert set(decision["checks"]) == {
        "vs_champion",
        "vs_control",
        "ece",
        "segments",
        "result_finals"}
    for check in decision["checks"].values():
        assert set(check) == {"value", "passed"}
    assert decision["checks"]["result_finals"]["value"][
        "max_home_share"] == pytest.approx(0.7)
    assert [
        row["segment"]
        for row in decision["checks"]["segments"]["value"]
    ] == ["split_year"]
    if decision["passed"]:
        assert report["recommended"] == {
            "result": "result_v3_challenger"}
    else:
        assert report["recommended"] == {"result": None}
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
    assert report["decisions"] == []
    assert report["recommended"] == {"btts": None}


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


def test_compare_models_applies_spec_thresholds(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    probabilities = np.array([[0.7, 0.2, 0.1], [0.2, 0.6, 0.2]])
    goals = [(2, 0), (1, 1)]
    outputs = {
        "result_v2_champion": _result_output(
            "result_v2_champion",
            "champion",
            [1, 2],
            probabilities,
            goals),
        "result_v3_challenger": _result_output(
            "result_v3_challenger",
            "challenger",
            [1, 2],
            probabilities,
            goals)}
    spec_path = _write_spec(
        tmp_path,
        [
            _candidate("result_v2_champion", "champion"),
            _candidate("result_v3_challenger", "challenger")],
        thresholds={"max_home_final_share": 0.0})
    _patch_sources(monkeypatch, outputs)
    report = run_compare_models(SimpleNamespace(spec=spec_path))
    check = report["decisions"][0]["checks"]["result_finals"]
    assert check["passed"] is False
    assert check["value"]["max_home_share"] == 0.0
    assert report["recommended"]["result"] is None


def test_compare_models_rejects_an_unknown_threshold(
        tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path,
        [_candidate("result_v2_champion", "champion")],
        thresholds={"max_ece_increse": 0.2})
    with pytest.raises(ValueError, match="thresholds"):
        run_compare_models(SimpleNamespace(spec=spec_path))


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
        seed: int = 1,
        thresholds: dict[str, object] | None = None) -> Path:
    target = output_path or (tmp_path / "report.json")
    payload = {
        "sport_id": 1,
        "test_from": "2026-09-01",
        "test_to": "2026-11-10",
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
        "reliability_edges": [0, 0.5, 1],
        "candidates": candidates,
        "thresholds": {} if thresholds is None else thresholds,
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


def test_parser_shadow_report_requires_the_window() -> None:
    args = build_parser().parse_args([
        "shadow-report",
        "--family",
        "btts",
        "--champion-model",
        "FOOTBALL_BTTS_V2",
        "--challenger-model",
        "FOOTBALL_BTTS_NEXT",
        "--date-from",
        "2026-09-01",
        "--date-to",
        "2026-11-10",
        "--output",
        "shadow.json"])
    assert args.command == "shadow-report"
    assert args.family == "btts"
    assert args.champion_model == "FOOTBALL_BTTS_V2"
    assert args.date_from == date(2026, 9, 1)
    assert args.date_to == date(2026, 11, 10)
    assert args.output == Path("shadow.json")
    with pytest.raises(SystemExit):
        build_parser().parse_args([
            "shadow-report",
            "--family",
            "result"])
    with pytest.raises(SystemExit):
        build_parser().parse_args([
            "shadow-report",
            "--family",
            "goals",
            "--champion-model",
            "FOOTBALL_GOALS_POISSON_V1",
            "--challenger-model",
            "FOOTBALL_GOALS_NEXT",
            "--date-from",
            "2026-09-01",
            "--date-to",
            "2026-11-10",
            "--output",
            "shadow.json"])


def test_shadow_report_scores_percentages_and_the_missing_rate(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "reports" / "shadow.json"
    calls: dict[str, object] = {}
    _patch_shadow(monkeypatch, calls)
    report = run_shadow_report(SimpleNamespace(
        family="result",
        champion_model="FOOTBALL_RESULT_V2",
        challenger_model="FOOTBALL_RESULT_NEXT",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 11, 10),
        output=output_path))
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == report
    assert calls["finished"] == (
        date(2026, 9, 1), date(2026, 11, 10), 1)
    assert calls["published_ids"] == (8, (1, 2, 3), [1, 2, 3])
    assert calls["shadow_ids"] == (11, (1, 2, 3), [1, 2, 3])
    assert report["n_finished"] == 3
    assert report["n_champion"] == 3
    assert report["n_compared"] == 2
    assert report["missing_rate"] == pytest.approx(1.0 / 3.0)
    assert report["passed"] is False
    assert report["checks"]["matches"]["passed"] is False
    assert report["checks"]["matches"]["value"]["n"] == 2
    assert report["checks"]["missing_rate"]["value"]["missing_rate"] == (
        pytest.approx(1.0 / 3.0))
    assert report["family"] == "result"
    assert "result_finals" in report["checks"]
    expected = multiclass_log_loss(
        np.array([[0.7, 0.2, 0.1], [0.7, 0.2, 0.1]]),
        np.array([0, 0]))
    assert report["metrics"]["champion"]["log_loss"] == pytest.approx(
        expected)
    assert report["metrics"]["challenger"]["mean_p"]["h"] == pytest.approx(
        0.7)
    assert report["champion_model_id"] == 8
    assert report["challenger_model_id"] == 11


def test_shadow_report_rejects_a_reversed_window(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("registry should not be read")

    monkeypatch.setattr(command_module, "load_model_registry", _boom)
    with pytest.raises(ValueError, match="date-from"):
        run_shadow_report(SimpleNamespace(
            family="result",
            champion_model="FOOTBALL_RESULT_V2",
            challenger_model="FOOTBALL_RESULT_NEXT",
            date_from="2026-11-10",
            date_to="2026-09-01",
            output="shadow.json"))


def test_shadow_report_rejects_a_model_outside_the_registry(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config = (
        REPO_ROOT / "models" / "configs" / "prediction"
        / "football_result_v2.json")

    def _registry(_path: object = None) -> dict[str, Path]:
        return {"FOOTBALL_RESULT_V2": config}

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("database should not be opened")

    monkeypatch.setattr(command_module, "load_model_registry", _registry)
    monkeypatch.setattr(
        command_module, "resolve_registered_model_id", _boom)
    with pytest.raises(ValueError, match="not in the model registry"):
        run_shadow_report(SimpleNamespace(
            family="result",
            champion_model="FOOTBALL_RESULT_V2",
            challenger_model="FOOTBALL_RESULT_NEXT",
            date_from=date(2026, 9, 1),
            date_to=date(2026, 11, 10),
            output="shadow.json"))


def test_shadow_report_rejects_a_config_without_the_family(
        monkeypatch: pytest.MonkeyPatch) -> None:
    result = (
        REPO_ROOT / "models" / "configs" / "prediction"
        / "football_result_v2.json")
    btts = (
        REPO_ROOT / "models" / "configs" / "prediction"
        / "football_btts_v2.json")

    def _registry(_path: object = None) -> dict[str, Path]:
        return {
            "FOOTBALL_RESULT_V2": result,
            "FOOTBALL_BTTS_V2": btts}

    monkeypatch.setattr(command_module, "load_model_registry", _registry)
    with pytest.raises(ValueError, match="no event result_home"):
        run_shadow_report(SimpleNamespace(
            family="result",
            champion_model="FOOTBALL_RESULT_V2",
            challenger_model="FOOTBALL_BTTS_V2",
            date_from=date(2026, 9, 1),
            date_to=date(2026, 11, 10),
            output="shadow.json"))


def test_fetch_finished_results_uses_an_exclusive_end() -> None:
    captured: list[tuple[str, tuple[object, ...]]] = []
    frame = pd.DataFrame({
        "id": [4],
        "league": [7],
        "season": [3],
        "game_date": [datetime(2026, 9, 1, 18, 0)],
        "home_team_goals": [1],
        "away_team_goals": [1],
        "result": ["X"]})

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[object, ...] = ()) -> pd.DataFrame:
        captured.append((query, params))
        return frame

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_finished_results(
            date(2026, 9, 1), date(2026, 11, 10), 1)
    query, params = captured[0]
    assert "game_date >=" in query
    assert "game_date <" in query
    assert "result IN ('1', 'X', '2')" in query
    assert "home_team_goals IS NOT NULL" in query
    assert params == (1, date(2026, 9, 1), date(2026, 11, 10))
    assert list(loaded["id"]) == [4]
    assert list(loaded.columns) == [
        "id",
        "league",
        "season",
        "game_date",
        "home_team_goals",
        "away_team_goals",
        "result"]


def test_fetch_finished_results_rejects_an_empty_window() -> None:
    with patch(f"{_REPOSITORY}.get_db_connection") as connect:
        with pytest.raises(ValueError, match="date_from"):
            fetch_finished_results(
                date(2026, 11, 10), date(2026, 9, 1), 1)
    connect.assert_not_called()


def test_fetch_published_values_reads_batches_of_500() -> None:
    captured: list[tuple[str, tuple[object, ...]]] = []
    frames = [
        pd.DataFrame({
            "match_id": [1],
            "event_id": [1],
            "value": [60.0]}),
        pd.DataFrame({
            "match_id": [501],
            "event_id": [1],
            "value": [40.0]})]

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[object, ...] = ()) -> pd.DataFrame:
        captured.append((query, params))
        return frames[len(captured) - 1]

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()) as connect, patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_published_values(8, [1, 2, 3], list(range(1, 502)))
    assert connect.call_count == 1
    assert len(captured) == 2
    assert "FROM predictions" in captured[0][0]
    assert captured[0][1][0] == 8
    assert captured[0][1][1:501] == tuple(range(1, 501))
    assert captured[0][1][501:] == (1, 2, 3)
    assert captured[1][1] == (8, 501, 1, 2, 3)
    assert list(loaded["match_id"]) == [1, 501]


def test_fetch_shadow_values_reads_the_shadow_table() -> None:
    captured: list[str] = []

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[object, ...] = ()) -> pd.DataFrame:
        captured.append(query)
        return pd.DataFrame({
            "match_id": [3],
            "event_id": [8],
            "value": [55.0]})

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_shadow_values(11, [8], [3])
    assert "FROM model_shadow_predictions" in captured[0]
    assert list(loaded["value"]) == [55.0]


def test_fetch_values_skip_the_database_when_empty() -> None:
    with patch(f"{_REPOSITORY}.get_db_connection") as connect:
        empty_matches = fetch_published_values(8, [1], [])
        empty_events = fetch_shadow_values(11, [], [3])
    connect.assert_not_called()
    assert empty_matches.empty
    assert empty_events.empty
    assert list(empty_matches.columns) == ["match_id", "event_id", "value"]


def test_fetch_values_reject_a_non_integer_id() -> None:
    with pytest.raises(ValueError, match="integers"):
        fetch_published_values(8, [1.5], [1])


def _patch_shadow(
        monkeypatch: pytest.MonkeyPatch,
        calls: dict[str, object]) -> None:
    result = (
        REPO_ROOT / "models" / "configs" / "prediction"
        / "football_result_v2.json")

    def _registry(_path: object = None) -> dict[str, Path]:
        return {
            "FOOTBALL_RESULT_V2": result,
            "FOOTBALL_RESULT_NEXT": result}

    def _model_id(name: str) -> int:
        return {
            "FOOTBALL_RESULT_V2": 8,
            "FOOTBALL_RESULT_NEXT": 11}[name]

    def _finished(
            date_from: date,
            date_to: date,
            sport_id: int) -> pd.DataFrame:
        calls["finished"] = (date_from, date_to, sport_id)
        return _finished_frame()

    def _published(
            model_id: int,
            event_ids: tuple[int, ...],
            match_ids: list[int]) -> pd.DataFrame:
        calls["published_ids"] = (model_id, tuple(event_ids), match_ids)
        return _percent_rows(include_third=True)

    def _shadow(
            model_id: int,
            event_ids: tuple[int, ...],
            match_ids: list[int]) -> pd.DataFrame:
        calls["shadow_ids"] = (model_id, tuple(event_ids), match_ids)
        return _percent_rows(include_third=False)

    monkeypatch.setattr(command_module, "load_model_registry", _registry)
    monkeypatch.setattr(
        command_module, "resolve_registered_model_id", _model_id)
    monkeypatch.setattr(command_module, "fetch_finished_results", _finished)
    monkeypatch.setattr(command_module, "fetch_published_values", _published)
    monkeypatch.setattr(command_module, "fetch_shadow_values", _shadow)


def _finished_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "id": [1, 2, 3],
        "league": [7, 7, 9],
        "season": [3, 3, 3],
        "game_date": [
            date(2026, 9, 1),
            date(2026, 9, 8),
            date(2026, 9, 15)],
        "home_team_goals": [2, 1, 0],
        "away_team_goals": [0, 0, 2],
        "result": ["1", "1", "2"]})


def _percent_rows(include_third: bool) -> pd.DataFrame:
    rows = [
        _percent(1, 1, 70.0),
        _percent(1, 2, 20.0),
        _percent(1, 3, 10.0),
        _percent(2, 1, 0.7),
        _percent(2, 2, 0.2),
        _percent(2, 3, 0.1)]
    if include_third:
        rows.extend([
            _percent(3, 1, 10.0),
            _percent(3, 2, 20.0),
            _percent(3, 3, 70.0)])
    return pd.DataFrame(rows)


def _percent(
        match_id: int,
        event_id: int,
        value: float) -> dict[str, int | float]:
    return {"match_id": match_id, "event_id": event_id, "value": value}


def _db_context() -> MagicMock:
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return context


def _quote(match_id: int, event_id: int, odds: float) -> dict[str, object]:
    return {
        "match_id": match_id,
        "bookmaker_id": 1,
        "event_id": event_id,
        "odds": odds}
