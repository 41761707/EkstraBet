"""Tests for ML league-tier predicates."""

from __future__ import annotations

from datetime import date

import pytest

from models.pipeline.core.config import MatchupInput
from models.pipeline.data.ml_league_filter import MAX_ML_LEAGUE_TIER
from models.pipeline.data.ml_league_filter import filter_ml_eligible_matchups
from models.pipeline.data.ml_league_filter import is_ml_eligible_tier
from models.pipeline.data.ml_league_filter import ml_eligible_league_sql


def _matchup(league_id: int | None) -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=league_id,
        season_id=1,
        as_of_date=date(2026, 7, 24),
        match_id=None)


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        (None, False),
        (0, True),
        (1, True),
        (2, True),
        (5, True),
        (6, False),
        (100, False)
    ])
def test_is_ml_eligible_tier(
        tier: int | None,
        expected: bool) -> None:
    assert is_ml_eligible_tier(tier) is expected


def test_ml_eligible_league_sql_uses_cutoff_constant() -> None:
    clause = ml_eligible_league_sql()
    assert "l.tier IS NOT NULL" in clause
    assert f"l.tier <= {MAX_ML_LEAGUE_TIER}" in clause
    assert "<= 5" in clause


def test_ml_eligible_league_sql_uses_alias() -> None:
    clause = ml_eligible_league_sql("leagues")
    assert clause == (
        "leagues.tier IS NOT NULL AND leagues.tier <= 5")


def test_filter_ml_eligible_matchups_keeps_domestic_drops_cups() -> None:
    domestic = _matchup(1)
    champions_league = _matchup(42)
    kept = filter_ml_eligible_matchups(
        [domestic, champions_league],
        {1: 1, 42: 100})
    assert kept == [domestic]


def test_filter_ml_eligible_matchups_keeps_missing_league_id() -> None:
    matchup = _matchup(None)
    kept = filter_ml_eligible_matchups([matchup], {42: 100})
    assert kept == [matchup]


def test_filter_ml_eligible_matchups_drops_unknown_or_null_tier() -> None:
    unknown = _matchup(99)
    null_tier = _matchup(7)
    kept = filter_ml_eligible_matchups(
        [unknown, null_tier],
        {7: None})
    assert kept == []
