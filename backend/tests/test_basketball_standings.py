"""Tests for basketball standings calculated from FT scores."""

from __future__ import annotations

import pandas as pd

from backend.sports.basketball.standings import build_basketball_standings


def test_build_basketball_standings_counts_full_time_win() -> None:
    teams = pd.DataFrame([
        {"team_id": 1, "team_name": "Home", "team_shortcut": "HOM"},
        {"team_id": 2, "team_name": "Away", "team_shortcut": "AWY"}
    ])
    matches = pd.DataFrame([
        {
            "home_id": 1,
            "away_id": 2,
            "home_team_goals": 112,
            "away_team_goals": 108,
            "round": 100
        }
    ])
    standings = build_basketball_standings(teams, matches, "overall")
    home = next(row for row in standings if row["team_id"] == 1)
    away = next(row for row in standings if row["team_id"] == 2)
    assert home["wins"] == 1
    assert home["losses"] == 0
    assert home["points_for"] == 112
    assert away["wins"] == 0
    assert away["losses"] == 1
    assert away["points_against"] == 112
