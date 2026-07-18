"""Tests for hockey standings calculations."""

from __future__ import annotations
import pandas as pd
from backend.sports.hockey.standings import build_hockey_standings


def test_build_hockey_standings_counts_regulation_win() -> None:
    teams = pd.DataFrame([
        {"team_id": 1, "team_name": "Home", "team_shortcut": "HOM"},
        {"team_id": 2, "team_name": "Away", "team_shortcut": "AWY"},
    ])
    matches = pd.DataFrame([
        {
            "home_id": 1,
            "away_id": 2,
            "home_team_goals": 3,
            "away_team_goals": 1,
            "round": 100,
            "hma_ot_winner": 0,
            "hma_so_winner": 0,
        }
    ])
    standings = build_hockey_standings(teams, matches, "overall")
    home = next(row for row in standings if row["team_id"] == 1)
    away = next(row for row in standings if row["team_id"] == 2)
    assert home["wins"] == 1
    assert home["points"] == 2
    assert away["losses"] == 1
