"""Unit tests for football team player-stat-leaders helpers."""

from __future__ import annotations

import pytest

from backend.repositories.team_player_stats_repository import (
    ALLOWED_FOOTBALL_LEADER_STATS,
)
from backend.services import player_service


def test_allowed_leader_stats_are_explicit() -> None:
    assert "shots_on_target" in ALLOWED_FOOTBALL_LEADER_STATS
    assert "drop_table" not in ALLOWED_FOOTBALL_LEADER_STATS


def test_unsupported_stat_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args, **_kwargs):
        raise AssertionError("repository should not be called")

    monkeypatch.setattr(
        player_service,
        "fetch_football_team_player_stat_leaders",
        _fail,
    )
    with pytest.raises(ValueError, match="Unsupported leader stat"):
        player_service.get_football_team_player_stat_leaders(
            team_id=1,
            season_id=2,
            stat="not_a_stat",
            match_ids=[1, 2],
            top=5,
        )


def test_leaders_maps_repository_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    import pandas as pd

    frame = pd.DataFrame([
        {
            "player_id": 10,
            "player_name": "Player A",
            "total": 5,
            "appearances": 2,
            "average": 2.5,
        }
    ])

    monkeypatch.setattr(
        player_service,
        "fetch_football_team_player_stat_leaders",
        lambda **_kwargs: frame,
    )
    payload = player_service.get_football_team_player_stat_leaders(
        team_id=7,
        season_id=3,
        stat="goals",
        match_ids=[1, 1, 2],
        top=8,
    )
    assert payload["team_id"] == 7
    assert payload["match_ids"] == [1, 2]
    assert payload["leaders"][0]["player_name"] == "Player A"
    assert payload["leaders"][0]["total"] == 5
