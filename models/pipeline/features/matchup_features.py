"""Static pre-match features for a football team pairing."""

from __future__ import annotations

from datetime import date
from datetime import datetime

import numpy as np
import pandas as pd

from models.pipeline.features.league_context import build_league_features

STATIC_FEATURE_COLUMNS = [
    "elo_home",
    "elo_away",
    "elo_diff",
    "home_att",
    "home_def",
    "away_att",
    "away_def",
    "home_att_vs_away_def",
    "away_att_vs_home_def",
    "home_czech_win_pct",
    "home_czech_goals_for_avg",
    "home_czech_goals_against_avg",
    "home_czech_goals_for_std",
    "home_czech_goals_against_std",
    "away_czech_win_pct",
    "away_czech_goals_for_avg",
    "away_czech_goals_against_avg",
    "away_czech_goals_for_std",
    "away_czech_goals_against_std",
    "league_avg_home_goals",
    "league_avg_away_goals",
    "league_avg_goals",
    "league_btts_pct",
    "league_over_25_pct",
    "league_avg_xg",
    "h2h_home_goals_avg",
    "h2h_away_goals_avg",
    "h2h_home_wins",
    "h2h_draws",
    "h2h_away_wins",
    "h2h_btts_pct",
    "home_rest_days",
    "away_rest_days",
    "rest_days_diff",
    "league_tier"
]


def _latest_team_row(
        ratings: pd.DataFrame,
        team_id: int,
        as_of_date: date | datetime) -> tuple[pd.Series | None, str | None]:
    dates = pd.to_datetime(ratings["game_date"])
    rows = ratings.loc[
        ((ratings["home_team"] == team_id)
         | (ratings["away_team"] == team_id))
        & (dates < pd.Timestamp(as_of_date))].copy()
    if rows.empty:
        return None, None
    rows["_matchup_date"] = pd.to_datetime(rows["game_date"])
    row = rows.sort_values("_matchup_date").iloc[-1]
    side = "home" if int(row["home_team"]) == team_id else "away"
    return row, side


def _rating_features(
        ratings: pd.DataFrame,
        team_id: int,
        as_of_date: date | datetime,
        target_venue: str) -> dict[str, float]:
    row, side = _latest_team_row(ratings, team_id, as_of_date)
    if row is None or side is None:
        return {
            "elo": 1500.0,
            "att": 1.0,
            "def": 1.0,
            "win_pct": 0.0,
            "goals_for_avg": 0.0,
            "goals_against_avg": 0.0,
            "goals_for_std": 0.0,
            "goals_against_std": 0.0
        }
    values = {
        "elo": float(row.get(f"{side}_elo_post", row[f"{side}_elo"])),
        "att": float(row.get(
            f"{side}_gap_att_post", row[f"{side}_gap_att"])),
        "def": float(row.get(
            f"{side}_gap_def_post", row[f"{side}_gap_def"]))
    }
    venue_rows = ratings.loc[
        (ratings[f"{target_venue}_team"] == team_id)
        & (pd.to_datetime(ratings["game_date"]) < pd.Timestamp(as_of_date))]
    venue_row = venue_rows.sort_values("game_date").iloc[-1] \
        if not venue_rows.empty else row
    source_side = target_venue if not venue_rows.empty else side
    for statistic in [
            "win_pct", "goals_for_avg", "goals_against_avg",
            "goals_for_std", "goals_against_std"]:
        key = f"{source_side}_czech_{statistic}_post"
        fallback = f"{source_side}_czech_{statistic}"
        values[statistic] = float(venue_row.get(key, venue_row.get(fallback, 0)))
    return values


def _head_to_head(
        matches: pd.DataFrame,
        home_id: int,
        away_id: int,
        as_of_date: date | datetime) -> dict[str, float]:
    pair = (
        (((matches["home_team"] == home_id)
          & (matches["away_team"] == away_id))
         | ((matches["home_team"] == away_id)
            & (matches["away_team"] == home_id)))
        & (pd.to_datetime(matches["game_date"]) < pd.Timestamp(as_of_date))
        & matches["result"].astype(str).isin({"1", "X", "2"}))
    history = matches.loc[pair].sort_values("game_date").tail(5)
    if history.empty:
        return {key: 0.0 for key in [
            "h2h_home_goals_avg", "h2h_away_goals_avg",
            "h2h_home_wins", "h2h_draws", "h2h_away_wins",
            "h2h_btts_pct"]}
    home_goals: list[float] = []
    away_goals: list[float] = []
    home_wins = away_wins = draws = 0
    for _, row in history.iterrows():
        direct = int(row["home_team"]) == home_id
        home_goal = row["home_team_goals"] if direct else row["away_team_goals"]
        away_goal = row["away_team_goals"] if direct else row["home_team_goals"]
        home_goals.append(float(home_goal))
        away_goals.append(float(away_goal))
        home_wins += int(home_goal > away_goal)
        away_wins += int(away_goal > home_goal)
        draws += int(home_goal == away_goal)
    return {
        "h2h_home_goals_avg": float(np.mean(home_goals)),
        "h2h_away_goals_avg": float(np.mean(away_goals)),
        "h2h_home_wins": float(home_wins),
        "h2h_draws": float(draws),
        "h2h_away_wins": float(away_wins),
        "h2h_btts_pct": float(np.mean(
            [(home > 0 and away > 0)
             for home, away in zip(home_goals, away_goals)]))
    }


def _rest_days(
        matches: pd.DataFrame,
        team_id: int,
        as_of_date: date | datetime) -> float:
    dates = pd.to_datetime(matches["game_date"])
    team_dates = dates.loc[
        ((matches["home_team"] == team_id)
         | (matches["away_team"] == team_id))
        & (dates < pd.Timestamp(as_of_date))]
    if team_dates.empty:
        return 0.0
    return float((pd.Timestamp(as_of_date) - team_dates.max()).days)


def build_matchup_static(
        home_id: int,
        away_id: int,
        as_of_date: date | datetime,
        league_id: int,
        matches: pd.DataFrame,
        ratings_timeline: pd.DataFrame | None = None,
        league_tier: int | None = None,
        feature_cols: list[str] | None = None) -> np.ndarray:
    """Build an ordered numeric vector of static matchup features."""
    ratings = ratings_timeline if ratings_timeline is not None else matches
    home = _rating_features(ratings, home_id, as_of_date, "home")
    away = _rating_features(ratings, away_id, as_of_date, "away")
    values = {
        "elo_home": home["elo"],
        "elo_away": away["elo"],
        "elo_diff": home["elo"] - away["elo"],
        "home_att": home["att"],
        "home_def": home["def"],
        "away_att": away["att"],
        "away_def": away["def"],
        "home_att_vs_away_def": home["att"] - away["def"],
        "away_att_vs_home_def": away["att"] - home["def"]
    }
    for statistic in [
            "win_pct", "goals_for_avg", "goals_against_avg",
            "goals_for_std", "goals_against_std"]:
        values[f"home_czech_{statistic}"] = home[statistic]
        values[f"away_czech_{statistic}"] = away[statistic]
    values.update(build_league_features(matches, league_id, as_of_date))
    values.update(_head_to_head(matches, home_id, away_id, as_of_date))
    home_rest = _rest_days(matches, home_id, as_of_date)
    away_rest = _rest_days(matches, away_id, as_of_date)
    values.update({
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "rest_days_diff": home_rest - away_rest,
        "league_tier": float(league_tier or 0)
    })
    h2h_count = max(
        values["h2h_home_wins"]
        + values["h2h_draws"]
        + values["h2h_away_wins"],
        1.0)
    values.update({
        "home_attack": values["home_att"],
        "home_defense": values["home_def"],
        "away_attack": values["away_att"],
        "away_defense": values["away_def"],
        "home_attack_away_defense": values["home_att_vs_away_def"],
        "away_attack_home_defense": values["away_att_vs_home_def"],
        "home_czech_win_rate": values["home_czech_win_pct"],
        "away_czech_win_rate": values["away_czech_win_pct"],
        "league_btts_rate": values["league_btts_pct"],
        "league_over_25_rate": values["league_over_25_pct"],
        "h2h_home_win_rate": values["h2h_home_wins"] / h2h_count,
        "h2h_draw_rate": values["h2h_draws"] / h2h_count
    })
    columns = feature_cols or STATIC_FEATURE_COLUMNS
    missing = set(columns).difference(values)
    if missing:
        raise KeyError(f"Unknown static features: {sorted(missing)}")
    return np.asarray(
        [values[column] for column in columns],
        dtype=np.float32)
