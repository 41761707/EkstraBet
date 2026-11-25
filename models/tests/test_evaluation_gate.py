"""Offline gate checks, one pass and one fail each."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from models.pipeline.evaluation.candidates import FAMILY_BTTS
from models.pipeline.evaluation.candidates import FAMILY_OVER_25
from models.pipeline.evaluation.candidates import FAMILY_RESULT
from models.pipeline.evaluation.candidates import CandidateOutput
from models.pipeline.evaluation.candidates import EvaluationFrame
from models.pipeline.evaluation.gate import GateThresholds
from models.pipeline.evaluation.gate import offline_decision
from models.pipeline.evaluation.gate import recommend
from models.pipeline.evaluation.gate import shadow_decision


_RESULT_LABELS = [0, 0, 0, 0, 0, 1, 1, 2, 2, 2]
_SCORE = {0: (1, 0), 1: (1, 1), 2: (0, 1)}


def test_gate_thresholds_use_the_documented_defaults() -> None:
    limits = GateThresholds()
    assert limits.max_ece_increase == pytest.approx(0.01)
    assert limits.max_segment_log_loss_increase == pytest.approx(0.005)
    assert limits.max_home_final_share == pytest.approx(0.70)
    assert limits.min_btts_within_league_std == pytest.approx(0.05)
    assert limits.max_goal_mean_error == pytest.approx(0.10)
    assert limits.shadow_min_matches == 300
    assert limits.shadow_max_log_loss_increase == pytest.approx(0.005)
    assert limits.shadow_max_ece_increase == pytest.approx(0.02)
    assert limits.shadow_max_missing_rate == pytest.approx(0.02)


def test_result_gate_passes_when_every_check_passes() -> None:
    decision = _decide(
        FAMILY_RESULT,
        _result("next", "challenger", _certain(_RESULT_LABELS)),
        _result("now", "champion", _uniform(len(_RESULT_LABELS))))
    assert decision["passed"] is True
    assert decision["log_loss"] == pytest.approx(0.0)
    assert decision["label"] == "next"
    assert decision["checks"]["vs_control"]["value"] == []
    for check in decision["checks"].values():
        assert check["passed"] is True


def test_vs_champion_fails_on_a_tie() -> None:
    certain = _certain(_RESULT_LABELS)
    decision = _decide(
        FAMILY_RESULT,
        _result("next", "challenger", certain),
        _result("now", "champion", certain))
    check = decision["checks"]["vs_champion"]
    assert check["value"]["ci_high"] == pytest.approx(0.0)
    assert check["passed"] is False
    assert decision["passed"] is False


def test_vs_control_passes_when_each_control_is_worse() -> None:
    decision = _decide(
        FAMILY_RESULT,
        _result("next", "challenger", _certain(_RESULT_LABELS)),
        _result("now", "champion", _uniform(len(_RESULT_LABELS))),
        [_result("old", "control", _uniform(len(_RESULT_LABELS)))])
    check = decision["checks"]["vs_control"]
    assert check["passed"] is True
    assert check["value"][0]["label"] == "old"
    assert check["value"][0]["ci_high"] < 0.0


def test_vs_control_fails_when_any_control_is_not_beaten() -> None:
    certain = _certain(_RESULT_LABELS)
    decision = _decide(
        FAMILY_RESULT,
        _result("next", "challenger", certain),
        _result("now", "champion", _uniform(len(_RESULT_LABELS))),
        [
            _result("old", "control", _uniform(len(_RESULT_LABELS))),
            _result("twin", "control", certain)])
    check = decision["checks"]["vs_control"]
    by_label = {row["label"]: row["passed"] for row in check["value"]}
    assert by_label == {"old": True, "twin": False}
    assert check["passed"] is False


def test_vs_control_ignores_a_control_from_another_family() -> None:
    other = _marked(
        "btts_control",
        "control",
        FAMILY_BTTS,
        np.array([0.2]),
        [(0, 1)])
    decision = _decide(
        FAMILY_RESULT,
        _result("next", "challenger", _certain(_RESULT_LABELS)),
        _result("now", "champion", _uniform(len(_RESULT_LABELS))),
        [other])
    assert decision["checks"]["vs_control"]["value"] == []
    assert decision["checks"]["vs_control"]["passed"] is True


def test_ece_fails_when_calibration_gets_worse() -> None:
    decision = _worse_result_calibration()
    check = decision["checks"]["ece"]
    assert check["value"]["challenger"] > check["value"]["limit"]
    assert check["passed"] is False


def test_ece_passes_inside_the_allowed_increase() -> None:
    decision = _worse_result_calibration(max_ece_increase=1.0)
    check = decision["checks"]["ece"]
    assert check["value"]["limit"] == pytest.approx(
        check["value"]["champion"] + 1.0)
    assert check["passed"] is True


def test_segments_fail_when_one_format_gets_worse() -> None:
    decision = _split_decision()
    rows = {
        row["segment"]: row
        for row in decision["checks"]["segments"]["value"]}
    assert rows["split_year"]["passed"] is False
    assert rows["calendar_year"]["passed"] is True
    assert decision["checks"]["segments"]["passed"] is False


def test_segments_pass_inside_the_allowed_increase() -> None:
    decision = _split_decision(max_segment_log_loss_increase=2.0)
    assert decision["checks"]["segments"]["passed"] is True


def test_segments_pass_when_every_format_holds() -> None:
    challenger, champion, years = _split_pair(worse=False)
    decision = _decide(
        FAMILY_RESULT, challenger, champion, years=years)
    rows = decision["checks"]["segments"]["value"]
    assert [row["segment"] for row in rows] == [
        "split_year", "calendar_year"]
    assert decision["checks"]["segments"]["passed"] is True


def test_result_finals_fail_when_home_share_is_too_high() -> None:
    count = len(_RESULT_LABELS)
    decision = _decide(
        FAMILY_RESULT,
        _result(
            "next",
            "challenger",
            _certain(_RESULT_LABELS),
            finals=np.zeros(count, dtype=int)),
        _result("now", "champion", _uniform(count)))
    check = decision["checks"]["result_finals"]
    assert check["value"]["home_share"] > check["value"]["max_home_share"]
    assert check["value"]["draw_share"] <= check["value"]["actual_draw_share"]
    assert check["passed"] is False
    assert decision["checks"]["vs_champion"]["passed"] is True
    assert decision["checks"]["ece"]["passed"] is True
    assert decision["passed"] is False


def test_result_finals_fail_when_draw_share_exceeds_the_test() -> None:
    count = len(_RESULT_LABELS)
    decision = _decide(
        FAMILY_RESULT,
        _result(
            "next",
            "challenger",
            _certain(_RESULT_LABELS),
            finals=np.ones(count, dtype=int)),
        _result("now", "champion", _uniform(count)))
    value = decision["checks"]["result_finals"]["value"]
    assert value["home_share"] <= value["max_home_share"]
    assert value["draw_share"] > value["actual_draw_share"]
    assert decision["checks"]["result_finals"]["passed"] is False


def test_btts_gate_passes_when_spread_and_level_hold() -> None:
    decision = _btts_decision(
        _alternate(0.7, 0.9, 30),
        _alternate(0.2, 0.4, 30))
    check = decision["checks"]["btts_leagues"]
    assert check["value"]["within_league_std"] >= check["value"][
        "min_within_league_std"]
    assert check["value"]["level_error"] <= check["value"][
        "champion_level_error"]
    assert "error" not in check["value"]
    assert decision["passed"] is True


def test_btts_fails_when_within_league_spread_is_flat() -> None:
    decision = _btts_decision(
        np.full(30, 0.8),
        np.full(30, 0.3))
    value = decision["checks"]["btts_leagues"]["value"]
    assert value["within_league_std"] == pytest.approx(0.0)
    assert value["level_error"] <= value["champion_level_error"]
    assert decision["checks"]["btts_leagues"]["passed"] is False
    assert decision["checks"]["vs_champion"]["passed"] is True


def test_btts_fails_when_level_error_is_worse_than_the_champion() -> None:
    decision = _btts_decision(
        _alternate(0.05, 0.95, 30),
        np.full(30, 0.05),
        yes=False)
    value = decision["checks"]["btts_leagues"]["value"]
    assert value["within_league_std"] >= value["min_within_league_std"]
    assert value["level_error"] > value["champion_level_error"]
    assert decision["checks"]["btts_leagues"]["passed"] is False


def test_btts_fails_when_no_league_has_enough_matches() -> None:
    decision = _btts_decision(
        _alternate(0.2, 0.8, 4),
        np.full(4, 0.4),
        yes=False)
    value = decision["checks"]["btts_leagues"]["value"]
    assert value["within_league_std"] is None
    assert "30" in value["error"]
    assert decision["checks"]["btts_leagues"]["passed"] is False


def test_goal_mean_passes_when_expected_goals_match() -> None:
    decision = _goal_decision(np.full(8, 3.0))
    value = decision["checks"]["goal_mean"]["value"]
    assert value["error"] == pytest.approx(0.0)
    assert value["actual"] == pytest.approx(3.0)
    assert decision["passed"] is True


def test_goal_mean_fails_when_expected_goals_drift() -> None:
    decision = _goal_decision(np.full(8, 5.0))
    check = decision["checks"]["goal_mean"]
    assert check["value"]["error"] > check["value"]["max_error"]
    assert check["passed"] is False
    assert decision["checks"]["vs_champion"]["passed"] is True
    assert decision["passed"] is False


def test_goal_mean_requires_expected_goals() -> None:
    challenger = _marked(
        "next",
        "challenger",
        FAMILY_OVER_25,
        np.full(4, 0.6),
        [(2, 1)] * 4)
    champion = _marked(
        "now",
        "champion",
        FAMILY_OVER_25,
        np.full(4, 0.4),
        [(2, 1)] * 4)
    with pytest.raises(ValueError, match="expected goals"):
        _decide(FAMILY_OVER_25, challenger, champion)


def test_goal_mean_rejects_non_finite_expected_goals() -> None:
    with pytest.raises(ValueError, match="finite"):
        _goal_decision(np.array([np.nan, 3.0]))


def test_offline_decision_rejects_a_misaligned_challenger() -> None:
    challenger = _result("next", "challenger", _certain(_RESULT_LABELS))
    champion = _result("now", "champion", _uniform(2), labels=[0, 1])
    with pytest.raises(ValueError, match="match_ids"):
        _decide(FAMILY_RESULT, challenger, champion)


def test_offline_decision_rejects_an_unknown_family() -> None:
    challenger = _result("next", "challenger", _certain(_RESULT_LABELS))
    champion = _result("now", "champion", _uniform(len(_RESULT_LABELS)))
    with pytest.raises(ValueError, match="Unknown evaluation family"):
        _decide("exact", challenger, champion)


def test_offline_decision_rejects_a_champion_passed_as_challenger() -> None:
    row = _result("now", "champion", _uniform(len(_RESULT_LABELS)))
    with pytest.raises(ValueError, match="expected challenger"):
        _decide(FAMILY_RESULT, row, row)


def test_recommend_picks_the_lowest_passing_log_loss() -> None:
    chosen = recommend([
        {
            "family": "result",
            "label": "low_fail",
            "log_loss": 0.1,
            "passed": False},
        {
            "family": "result",
            "label": "mid",
            "log_loss": 0.4,
            "passed": True},
        {
            "family": "result",
            "label": "high",
            "log_loss": 0.5,
            "passed": True},
        {
            "family": "btts",
            "label": "btts_fail",
            "log_loss": 0.2,
            "passed": False}])
    assert chosen == {"result": "mid", "btts": None}


def test_recommend_keeps_the_earlier_tie() -> None:
    chosen = recommend([
        {
            "family": "result",
            "label": "first",
            "log_loss": 0.4,
            "passed": True},
        {
            "family": "result",
            "label": "second",
            "log_loss": 0.4,
            "passed": True}])
    assert chosen == {"result": "first"}


def test_recommend_returns_an_empty_map_without_decisions() -> None:
    assert recommend([]) == {}


def test_recommend_rejects_a_passing_row_without_log_loss() -> None:
    with pytest.raises(ValueError, match="log_loss"):
        recommend([{
            "family": "result",
            "label": "bare",
            "passed": True}])


def _decide(
        family: str,
        challenger: CandidateOutput,
        champion: CandidateOutput,
        controls: list[CandidateOutput] | None = None,
        years: dict[int, str] | None = None,
        **thresholds: float) -> dict[str, Any]:
    return offline_decision(
        family,
        challenger,
        champion,
        [] if controls is None else controls,
        GateThresholds(**thresholds),
        40,
        1,
        years_by_season=years)


def _worse_result_calibration(**thresholds: float) -> dict[str, Any]:
    count = len(_RESULT_LABELS)
    return _decide(
        FAMILY_RESULT,
        _result("next", "challenger", _uniform(count)),
        _result("now", "champion", _certain(_RESULT_LABELS)),
        **thresholds)


def _split_decision(**thresholds: float) -> dict[str, Any]:
    challenger, champion, years = _split_pair(worse=True)
    return _decide(
        FAMILY_RESULT,
        challenger,
        champion,
        years=years,
        **thresholds)


def _split_pair(*, worse: bool):
    labels = [0, 1, 2, 0, 1, 2, 0, 1, 0, 1, 2, 0, 1, 2, 0, 1]
    seasons = np.array([1] * 8 + [2] * 8)
    certain = _certain(labels)
    challenger_probs = certain.copy()
    if worse:
        challenger_probs[:8] = 1.0 / 3.0
    years = {1: "2026/2027", 2: "2026"}
    return (
        _result(
            "next",
            "challenger",
            challenger_probs,
            labels=labels,
            season_ids=seasons),
        _result(
            "now",
            "champion",
            certain,
            labels=labels,
            season_ids=seasons),
        years)


def _btts_decision(
        challenger_p: np.ndarray,
        champion_p: np.ndarray,
        *,
        yes: bool = True) -> dict[str, Any]:
    score = (1, 1) if yes else (1, 0)
    goals = [score] * len(challenger_p)
    return _decide(
        FAMILY_BTTS,
        _marked("next", "challenger", FAMILY_BTTS, challenger_p, goals),
        _marked("now", "champion", FAMILY_BTTS, champion_p, goals))


def _goal_decision(expected: np.ndarray) -> dict[str, Any]:
    count = len(expected)
    goals = [(2, 1)] * count
    return _decide(
        FAMILY_OVER_25,
        _marked(
            "next",
            "challenger",
            FAMILY_OVER_25,
            np.full(count, 0.9),
            goals,
            expected=expected),
        _marked(
            "now",
            "champion",
            FAMILY_OVER_25,
            np.full(count, 0.4),
            goals,
            expected=np.full(count, 3.0)))


def test_shadow_decision_passes_when_the_challenger_holds() -> None:
    labels = [0, 1, 2, 0]
    probabilities = _confident(labels)
    decision = shadow_decision(
        FAMILY_RESULT,
        probabilities,
        probabilities,
        np.asarray(labels),
        0.0,
        _shadow_limits(4))
    assert decision["passed"] is True
    assert decision["log_loss"] == pytest.approx(float(-np.log(0.9)))
    assert set(decision["checks"]) == {
        "matches",
        "log_loss",
        "ece",
        "missing_rate",
        "result_finals"}
    for check in decision["checks"].values():
        assert check["passed"] is True


def test_shadow_decision_fails_when_there_are_too_few_matches() -> None:
    labels = [0, 1, 2, 0]
    probabilities = _confident(labels)
    decision = shadow_decision(
        FAMILY_RESULT,
        probabilities,
        probabilities,
        np.asarray(labels),
        0.0,
        GateThresholds())
    check = decision["checks"]["matches"]
    assert check["value"]["n"] == 4
    assert check["value"]["min_matches"] == 300
    assert check["passed"] is False
    assert decision["checks"]["log_loss"]["passed"] is True
    assert decision["passed"] is False


def test_shadow_decision_fails_when_the_missing_rate_is_high() -> None:
    labels = [0, 1, 2, 0]
    probabilities = _confident(labels)
    decision = shadow_decision(
        FAMILY_RESULT,
        probabilities,
        probabilities,
        np.asarray(labels),
        0.05,
        _shadow_limits(4))
    check = decision["checks"]["missing_rate"]
    assert check["value"]["missing_rate"] == pytest.approx(0.05)
    assert check["value"]["max_missing_rate"] == pytest.approx(0.02)
    assert check["passed"] is False
    assert decision["passed"] is False


def test_shadow_missing_rate_passes_at_the_limit() -> None:
    labels = [0, 1, 2, 0]
    decision = shadow_decision(
        FAMILY_RESULT,
        _confident(labels),
        _confident(labels),
        np.asarray(labels),
        0.02,
        _shadow_limits(4))
    assert decision["checks"]["missing_rate"]["passed"] is True


def test_shadow_log_loss_fails_when_the_point_gap_exceeds_the_limit() -> None:
    labels = [0, 1, 2, 0]
    decision = shadow_decision(
        FAMILY_RESULT,
        _confident(labels),
        _uniform(len(labels)),
        np.asarray(labels),
        0.0,
        _shadow_limits(4, shadow_max_log_loss_increase=0.005))
    check = decision["checks"]["log_loss"]
    assert check["value"]["diff"] > check["value"]["limit"]
    assert check["passed"] is False


def test_shadow_log_loss_allows_a_tie_inside_the_limit() -> None:
    labels = [0, 1, 2, 0]
    probabilities = _confident(labels)
    decision = shadow_decision(
        FAMILY_RESULT,
        probabilities,
        probabilities,
        np.asarray(labels),
        0.0,
        _shadow_limits(4))
    check = decision["checks"]["log_loss"]
    assert check["value"]["diff"] == pytest.approx(0.0)
    assert check["passed"] is True


def test_shadow_ece_uses_the_shadow_allowance() -> None:
    labels = [0, 1, 2, 0]
    probabilities = _confident(labels)
    decision = shadow_decision(
        FAMILY_RESULT,
        probabilities,
        probabilities,
        np.asarray(labels),
        0.0,
        _shadow_limits(4, shadow_max_ece_increase=-0.01))
    check = decision["checks"]["ece"]
    assert check["value"]["limit"] == pytest.approx(
        check["value"]["champion"] - 0.01)
    assert check["passed"] is False


def test_shadow_result_finals_fail_when_home_share_is_too_high() -> None:
    labels = [0, 0, 0, 0]
    decision = shadow_decision(
        FAMILY_RESULT,
        _confident(labels),
        _confident(labels),
        np.asarray(labels),
        0.0,
        _shadow_limits(4))
    check = decision["checks"]["result_finals"]
    assert check["value"]["home_share"] == pytest.approx(1.0)
    assert check["passed"] is False


def test_shadow_over_has_no_goal_mean_check() -> None:
    probabilities = np.array([0.7, 0.4])
    decision = shadow_decision(
        FAMILY_OVER_25,
        probabilities,
        probabilities,
        np.array([1, 0]),
        0.0,
        _shadow_limits(2))
    assert set(decision["checks"]) == {
        "matches",
        "log_loss",
        "ece",
        "missing_rate"}
    assert decision["passed"] is True


def test_shadow_btts_needs_league_ids() -> None:
    with pytest.raises(ValueError, match="league_ids"):
        shadow_decision(
            FAMILY_BTTS,
            np.array([0.6, 0.4]),
            np.array([0.6, 0.4]),
            np.array([1, 0]),
            0.0,
            _shadow_limits(2))


def test_shadow_btts_passes_when_leagues_separate_and_level_holds() -> None:
    count = 30
    probabilities = np.tile(np.array([0.2, 0.8]), count // 2)
    outcomes = np.tile(np.array([0, 1]), count // 2)
    decision = shadow_decision(
        FAMILY_BTTS,
        np.full(count, 0.9),
        probabilities,
        outcomes,
        0.0,
        _shadow_limits(count),
        league_ids=np.ones(count, dtype=int))
    check = decision["checks"]["btts_leagues"]
    assert check["value"]["within_league_std"] >= 0.05
    assert check["value"]["level_error"] <= check["value"][
        "champion_level_error"]
    assert check["passed"] is True


def test_shadow_btts_fails_when_no_league_is_large_enough() -> None:
    decision = shadow_decision(
        FAMILY_BTTS,
        np.array([0.2, 0.8]),
        np.array([0.2, 0.8]),
        np.array([0, 1]),
        0.0,
        _shadow_limits(2),
        league_ids=np.array([1, 1]))
    check = decision["checks"]["btts_leagues"]
    assert check["passed"] is False
    assert "error" in check["value"]


def test_shadow_decision_keeps_checks_when_nothing_is_comparable() -> None:
    decision = shadow_decision(
        FAMILY_RESULT,
        np.zeros((0, 3)),
        np.zeros((0, 3)),
        np.zeros((0,), dtype=int),
        1.0,
        GateThresholds())
    assert decision["log_loss"] is None
    assert decision["passed"] is False
    assert decision["checks"]["log_loss"]["value"]["error"] == (
        "no comparable matches")
    assert decision["checks"]["missing_rate"]["passed"] is False


def test_shadow_decision_rejects_a_rate_above_one() -> None:
    with pytest.raises(ValueError, match="missing_rate"):
        shadow_decision(
            FAMILY_OVER_25,
            np.array([0.5]),
            np.array([0.5]),
            np.array([1]),
            1.2,
            GateThresholds())


def _shadow_limits(min_matches: int, **overrides: float) -> GateThresholds:
    values: dict[str, float] = {"shadow_min_matches": min_matches}
    values.update(overrides)
    return GateThresholds.model_validate(values)


def _confident(labels: list[int], confidence: float = 0.9) -> np.ndarray:
    rows = np.full((len(labels), 3), (1.0 - confidence) / 2.0)
    for index, label in enumerate(labels):
        rows[index, label] = confidence
    return rows


def _result(
        label: str,
        role: str,
        probabilities: np.ndarray,
        *,
        labels: list[int] | None = None,
        finals: np.ndarray | None = None,
        season_ids: np.ndarray | None = None) -> CandidateOutput:
    chosen = _RESULT_LABELS if labels is None else labels
    return _marked(
        label,
        role,
        FAMILY_RESULT,
        probabilities,
        [_SCORE[item] for item in chosen],
        finals=finals,
        season_ids=season_ids)


def _marked(
        label: str,
        role: str,
        family: str,
        probabilities: np.ndarray,
        goals: list[tuple[int, int]],
        *,
        season_ids: np.ndarray | None = None,
        league_ids: np.ndarray | None = None,
        finals: np.ndarray | None = None,
        expected: np.ndarray | None = None) -> CandidateOutput:
    count = len(goals)
    seasons = (
        season_ids if season_ids is not None
        else np.ones(count, dtype=int))
    leagues = (
        league_ids if league_ids is not None
        else np.ones(count, dtype=int))
    return CandidateOutput(
        label=label,
        role=role,
        frame=EvaluationFrame(
            match_ids=np.arange(1, count + 1),
            league_ids=leagues,
            season_ids=seasons,
            dates=np.arange(count),
            home_goals=np.asarray([item[0] for item in goals]),
            away_goals=np.asarray([item[1] for item in goals])),
        families={family: np.asarray(probabilities, dtype=float)},
        result_finals=finals,
        expected_goals=expected)


def _certain(labels: list[int]) -> np.ndarray:
    matrix = np.zeros((len(labels), 3), dtype=float)
    matrix[np.arange(len(labels)), labels] = 1.0
    return matrix


def _uniform(count: int) -> np.ndarray:
    return np.full((count, 3), 1.0 / 3.0)


def _alternate(low: float, high: float, count: int) -> np.ndarray:
    values = np.empty(count, dtype=float)
    values[0::2] = low
    values[1::2] = high
    return values
