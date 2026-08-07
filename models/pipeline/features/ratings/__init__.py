"""Chronological football rating timeline without future leakage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from models.pipeline.features.ratings.czech import CzechParams
from models.pipeline.features.ratings.elo import EloParams
from models.pipeline.features.ratings.gap import GapParams
from models.pipeline.features.ratings.state import RatingState

RatingParams = Mapping[str, Any] | None


def _parameter_objects(
        params: RatingParams) -> tuple[EloParams, GapParams, CzechParams]:
    values = params or {}
    elo = values.get("elo", EloParams())
    gap = values.get("gap", GapParams())
    czech = values.get("czech", CzechParams())
    if isinstance(elo, bool):
        elo = EloParams()
    if isinstance(gap, bool):
        gap = GapParams()
    if isinstance(czech, bool):
        czech = CzechParams()
    if isinstance(elo, Mapping):
        elo = EloParams(**elo)
    if isinstance(gap, Mapping):
        gap = GapParams(**gap)
    if isinstance(czech, Mapping):
        czech = CzechParams(**czech)
    return elo, gap, czech


def compute_ratings_timeline(
        matches: pd.DataFrame,
        teams: pd.DataFrame | None = None,
        params: RatingParams = None) -> pd.DataFrame:
    """Attach pre-match ratings and update states in chronological order."""
    del teams
    required = {
        "home_team", "away_team", "game_date",
        "home_team_goals", "away_team_goals", "result"}
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Missing rating columns: {sorted(missing)}")
    valid = matches.loc[
        matches["result"].astype(str).isin({"1", "X", "2"})
        & matches["home_team_goals"].notna()
        & matches["away_team_goals"].notna()].copy()
    sort_columns = ["game_date"]
    if "id" in valid.columns:
        sort_columns.append("id")
    valid = valid.sort_values(sort_columns).reset_index(drop=True)
    elo_params, gap_params, czech_params = _parameter_objects(params)
    state = RatingState(elo_params, gap_params, czech_params)
    snapshots: dict[int, dict[str, float]] = {}
    for game_date, group in valid.groupby("game_date", sort=False):
        del game_date
        # najpierw snapshot całej kolejki, potem commit — bez leakage
        for index, row in group.iterrows():
            snapshots[index] = state.snapshot(
                int(row["home_team"]), int(row["away_team"]))
        for _, row in group.iterrows():
            home_id = int(row["home_team"])
            away_id = int(row["away_team"])
            state.commit(
                home_id,
                away_id,
                int(row["home_team_goals"]),
                int(row["away_team_goals"]))
            snapshots[row.name].update(
                state.post_snapshot(home_id, away_id))
    rating_frame = pd.DataFrame.from_dict(snapshots, orient="index")
    return pd.concat([valid, rating_frame], axis=1)


__all__ = [
    "CzechParams",
    "EloParams",
    "GapParams",
    "RatingState",
    "compute_ratings_timeline"
]
