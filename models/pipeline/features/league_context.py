"""League aggregates calculated only from matches available at prediction time."""

from __future__ import annotations

from datetime import date
from datetime import datetime

import pandas as pd


def _mean_optional(frame: pd.DataFrame, columns: list[str]) -> float:
    available = [column for column in columns if column in frame.columns]
    if len(available) != len(columns):
        return 0.0
    values = frame[available].apply(pd.to_numeric, errors="coerce")
    if values.dropna(how="all").empty:
        return 0.0
    return float(values.stack().mean())


def build_league_features(
        matches: pd.DataFrame,
        league_id: int,
        as_of_date: date | datetime,
        season_id: int | None = None) -> dict[str, float]:
    """Build stable league aggregates from valid earlier matches."""
    required = {
        "league", "game_date", "result",
        "home_team_goals", "away_team_goals"}
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Missing league feature columns: {sorted(missing)}")
    mask = (
        (matches["league"] == league_id)
        & (pd.to_datetime(matches["game_date"]) < pd.Timestamp(as_of_date))
        & matches["result"].astype(str).isin({"1", "X", "2"})
        & matches["home_team_goals"].notna()
        & matches["away_team_goals"].notna())
    if season_id is not None and "season" in matches.columns:
        mask &= matches["season"] == season_id
    history = matches.loc[mask]
    if history.empty:
        return {
            "league_avg_home_goals": 0.0,
            "league_avg_away_goals": 0.0,
            "league_avg_goals": 0.0,
            "league_btts_pct": 0.0,
            "league_over_25_pct": 0.0,
            "league_avg_xg": 0.0
        }
    home_goals = pd.to_numeric(history["home_team_goals"])
    away_goals = pd.to_numeric(history["away_team_goals"])
    total_goals = home_goals + away_goals
    return {
        "league_avg_home_goals": float(home_goals.mean()),
        "league_avg_away_goals": float(away_goals.mean()),
        "league_avg_goals": float(total_goals.mean()),
        "league_btts_pct": float(
            ((home_goals > 0) & (away_goals > 0)).mean()),
        "league_over_25_pct": float((total_goals > 2.5).mean()),
        "league_avg_xg": _mean_optional(
            history, ["home_team_xg", "away_team_xg"])
    }
