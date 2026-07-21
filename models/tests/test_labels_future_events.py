"""Tests for future-event football labels."""

from __future__ import annotations

import pytest

from models.pipeline.labels.football_btts import label_btts
from models.pipeline.labels.football_goals_poisson import label_goals_poisson
from models.pipeline.labels.football_result import label_result


@pytest.mark.parametrize(
    ("result", "expected"),
    [("1", 0), ("X", 1), ("2", 2)])
def test_label_result_maps_database_values(
        result: str,
        expected: int) -> None:
    assert label_result({"result": result}) == expected


def test_label_result_rejects_unfinished_match() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        label_result({"result": "0"})


@pytest.mark.parametrize(
    ("home_goals", "away_goals", "expected"),
    [(1, 1, 1), (3, 2, 1), (0, 2, 0), (2, 0, 0), (0, 0, 0)])
def test_label_btts_maps_goal_values(
        home_goals: int,
        away_goals: int,
        expected: int) -> None:
    row = {
        "home_team_goals": home_goals,
        "away_team_goals": away_goals
    }
    assert label_btts(row) == expected


def test_label_goals_poisson_returns_observed_pair() -> None:
    row = {"home_team_goals": 4, "away_team_goals": 2}
    assert label_goals_poisson(row) == (4, 2)


@pytest.mark.parametrize(
    "labeler",
    [label_btts, label_goals_poisson])
def test_goal_labels_reject_missing_values(labeler: object) -> None:
    with pytest.raises(ValueError, match="Missing goal"):
        labeler({"home_team_goals": None, "away_team_goals": 1})
