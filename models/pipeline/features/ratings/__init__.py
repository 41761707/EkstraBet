"""Chronological football rating timeline without future leakage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from models.pipeline.features.ratings.czech import CzechParams
from models.pipeline.features.ratings.czech import CzechRating
from models.pipeline.features.ratings.czech import new_czech_rating
from models.pipeline.features.ratings.czech import update_czech
from models.pipeline.features.ratings.czech import venue_snapshot
from models.pipeline.features.ratings.elo import EloParams
from models.pipeline.features.ratings.elo import initial_elo
from models.pipeline.features.ratings.elo import update_elo
from models.pipeline.features.ratings.gap import GapParams
from models.pipeline.features.ratings.gap import GapRating
from models.pipeline.features.ratings.gap import new_gap_rating
from models.pipeline.features.ratings.gap import update_gap

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


def _snapshot(
        row: pd.Series,
        elo_state: dict[int, float],
        gap_state: dict[int, GapRating],
        czech_state: dict[int, CzechRating],
        elo_params: EloParams,
        gap_params: GapParams,
        czech_params: CzechParams) -> dict[str, float]:
    home_id = int(row["home_team"])
    away_id = int(row["away_team"])
    home_elo = elo_state.setdefault(home_id, initial_elo(None, elo_params))
    away_elo = elo_state.setdefault(away_id, initial_elo(None, elo_params))
    home_gap = gap_state.setdefault(home_id, new_gap_rating(gap_params))
    away_gap = gap_state.setdefault(away_id, new_gap_rating(gap_params))
    home_czech = czech_state.setdefault(
        home_id, new_czech_rating(czech_params))
    away_czech = czech_state.setdefault(
        away_id, new_czech_rating(czech_params))
    values = {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_gap_att": home_gap.attack,
        "home_gap_def": home_gap.defence,
        "away_gap_att": away_gap.attack,
        "away_gap_def": away_gap.defence
    }
    for name, value in venue_snapshot(home_czech, "home").items():
        values[f"home_czech_{name}"] = value
    for name, value in venue_snapshot(away_czech, "away").items():
        values[f"away_czech_{name}"] = value
    return values


def _update_states(
        row: pd.Series,
        elo_state: dict[int, float],
        gap_state: dict[int, GapRating],
        czech_state: dict[int, CzechRating],
        elo_params: EloParams,
        gap_params: GapParams) -> None:
    home_id = int(row["home_team"])
    away_id = int(row["away_team"])
    home_goals = int(row["home_team_goals"])
    away_goals = int(row["away_team_goals"])
    home_elo, away_elo = update_elo(
        elo_state[home_id],
        elo_state[away_id],
        home_goals,
        away_goals,
        elo_params)
    elo_state[home_id] = home_elo
    elo_state[away_id] = away_elo
    home_gap, away_gap = update_gap(
        gap_state[home_id],
        gap_state[away_id],
        home_goals,
        away_goals,
        gap_params)
    gap_state[home_id] = home_gap
    gap_state[away_id] = away_gap
    update_czech(
        czech_state[home_id],
        czech_state[away_id],
        home_goals,
        away_goals)


def _post_snapshot(
        row: pd.Series,
        elo_state: dict[int, float],
        gap_state: dict[int, GapRating],
        czech_state: dict[int, CzechRating]) -> dict[str, float]:
    home_id = int(row["home_team"])
    away_id = int(row["away_team"])
    values = {
        "home_elo_post": elo_state[home_id],
        "away_elo_post": elo_state[away_id],
        "home_gap_att_post": gap_state[home_id].attack,
        "home_gap_def_post": gap_state[home_id].defence,
        "away_gap_att_post": gap_state[away_id].attack,
        "away_gap_def_post": gap_state[away_id].defence
    }
    for name, value in venue_snapshot(czech_state[home_id], "home").items():
        values[f"home_czech_{name}_post"] = value
    for name, value in venue_snapshot(czech_state[away_id], "away").items():
        values[f"away_czech_{name}_post"] = value
    return values


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
    elo_state: dict[int, float] = {}
    gap_state: dict[int, GapRating] = {}
    czech_state: dict[int, CzechRating] = {}
    snapshots: dict[int, dict[str, float]] = {}
    for game_date, group in valid.groupby("game_date", sort=False):
        del game_date
        for index, row in group.iterrows():
            snapshots[index] = _snapshot(
                row, elo_state, gap_state, czech_state,
                elo_params, gap_params, czech_params)
        for _, row in group.iterrows():
            _update_states(
                row, elo_state, gap_state, czech_state,
                elo_params, gap_params)
            snapshots[row.name].update(_post_snapshot(
                row, elo_state, gap_state, czech_state))
    rating_frame = pd.DataFrame.from_dict(snapshots, orient="index")
    return pd.concat([valid, rating_frame], axis=1)


__all__ = [
    "CzechParams",
    "EloParams",
    "GapParams",
    "compute_ratings_timeline"
]
