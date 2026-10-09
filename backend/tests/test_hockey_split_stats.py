"""Tests for hockey season split statistics."""

from __future__ import annotations

import pandas as pd

from backend.services.team_service import (
    _apply_split_match,
    _empty_split_stats)


def _tied_row(**overrides: object) -> pd.Series:
    row = {
        "home_id": 1,
        "away_id": 2,
        "home_team_goals": 2,
        "away_team_goals": 2,
        "sport_id": 2,
        "result": "X",
        "hma_ot": 1,
        "hma_so": 0,
        "hma_ot_winner": 1,
        "hma_so_winner": 0
    }
    row.update(overrides)
    return pd.Series(row)


def test_hockey_overtime_win_counts_as_win_with_extra_goal() -> None:
    stats = _empty_split_stats()
    _apply_split_match(stats, 1, _tied_row())
    assert stats["wins"] == 1
    assert stats["points"] == 2
    assert stats["goals_for"] == 3
    assert stats["goals_conceded"] == 2
    assert stats["losses"] == 0
    assert stats["overtime_losses"] == 0
    assert stats["draws"] == 0


def test_hockey_shootout_loss_counts_as_overtime_loss() -> None:
    stats = _empty_split_stats()
    _apply_split_match(
        stats,
        2,
        _tied_row(hma_ot_winner=3, hma_so=1, hma_so_winner=1))
    assert stats["overtime_losses"] == 1
    assert stats["points"] == 1
    assert stats["losses"] == 0
    assert stats["wins"] == 0
    assert stats["goals_for"] == 2
    assert stats["goals_conceded"] == 3
    assert stats["draws"] == 0


def test_hockey_regulation_loss_scores_zero_points() -> None:
    stats = _empty_split_stats()
    row = _tied_row(
        home_team_goals=3,
        away_team_goals=1,
        result="1",
        hma_ot=0,
        hma_ot_winner=0)
    _apply_split_match(stats, 2, row)
    assert stats["losses"] == 1
    assert stats["points"] == 0
    assert stats["overtime_losses"] == 0
    assert stats["wins"] == 0
    assert stats["draws"] == 0
    assert stats["goals_for"] == 1
    assert stats["goals_conceded"] == 3
