"""SQL contract for the latest hockey match roster."""

from __future__ import annotations

import pandas as pd

from backend.repositories.hockey_team_roster_repository import (
    fetch_last_match_roster)
from backend.repositories.hockey_team_roster_repository import (
    fetch_season_player_stats)
from backend.repositories.sport_league_repository import REGULAR_SEASON_ROUND

TEAM_ID = 870
MATCH_ID = 55


def test_last_match_requires_roster_rows(monkeypatch) -> None:
    queries: list[tuple[str, tuple[object, ...]]] = []

    def fake_read(
            query: str,
            params: tuple[object, ...]) -> pd.DataFrame:
        queries.append((query, params))
        if len(queries) == 1:
            return pd.DataFrame([{"id": MATCH_ID}])
        return pd.DataFrame()

    monkeypatch.setattr(
        "backend.repositories.hockey_team_roster_repository._read_sql",
        fake_read)

    fetch_last_match_roster(TEAM_ID)

    match_query, match_params = queries[0]
    assert "hockey_match_rosters" in match_query
    assert "JOIN matches" in match_query
    assert "m.result" in match_query
    assert "m.game_date DESC, m.id DESC" in match_query
    assert match_params == (TEAM_ID, "0")
    assert queries[1][1][0] == MATCH_ID


def test_season_stats_reject_a_playoff_round(monkeypatch) -> None:
    queries: list[tuple[str, tuple[object, ...]]] = []

    def fake_read(
            query: str,
            params: tuple[object, ...]) -> pd.DataFrame:
        queries.append((query, params))
        return pd.DataFrame()

    monkeypatch.setattr(
        "backend.repositories.hockey_team_roster_repository._read_sql",
        fake_read)

    fetch_season_player_stats(TEAM_ID, 12)

    query, params = queries[0]
    assert "m.round = %s" in query
    assert "m.result <> %s" in query
    assert REGULAR_SEASON_ROUND == 100
    assert params == (TEAM_ID, 12, "0", REGULAR_SEASON_ROUND)
