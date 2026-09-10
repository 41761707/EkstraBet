"""Tests for match history SQL filters used by the ML pipeline."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from models.pipeline.data import match_history_repository as history_repo
from models.pipeline.data.match_history_repository import (
    fetch_finished_matches)
from models.pipeline.data.match_history_repository import fetch_league_context
from models.pipeline.data.match_history_repository import (
    fetch_upcoming_matches)
from models.pipeline.data.ml_league_filter import MAX_ML_LEAGUE_TIER
from models.pipeline.data.ml_league_filter import ml_eligible_league_sql


def _capture_read_sql(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False

    def fake_read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(history_repo, "get_db_connection", lambda: context)
    monkeypatch.setattr(history_repo.pd, "read_sql", fake_read_sql)
    return captured


def _assert_ml_tier_sql(query: str) -> None:
    assert "INNER JOIN leagues l ON l.id = m.league" in query
    assert ml_eligible_league_sql() in query
    assert f"l.tier <= {MAX_ML_LEAGUE_TIER}" in query
    # Championship (tier=2) musi przejść — nie zawężamy do pierwszej ligi
    assert "tier = 1" not in query


def test_fetch_finished_matches_joins_leagues_and_filters_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_finished_matches(1, date(2026, 7, 24))
    _assert_ml_tier_sql(str(captured["query"]))
    assert captured["params"] == (1, date(2026, 7, 24))


def test_fetch_upcoming_matches_joins_leagues_and_filters_tier(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_upcoming_matches(1, date(2026, 7, 24), league_id=42)
    _assert_ml_tier_sql(str(captured["query"]))
    assert "m.league = %s" in str(captured["query"])
    assert captured["params"] == (1, date(2026, 7, 24), 42)


def test_fetch_league_context_does_not_apply_ml_tier_filter(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_read_sql(monkeypatch)
    fetch_league_context(1, league_id=42)
    query = str(captured["query"])
    assert ml_eligible_league_sql() not in query
    assert "INNER JOIN" not in query
    assert "FROM leagues l" in query
