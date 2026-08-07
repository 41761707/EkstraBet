"""Cloneable ELO, GAP and Czech rating state for simulation trials."""

from __future__ import annotations

from collections import deque
from copy import deepcopy

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


class RatingState:
    """Mutable ELO/GAP/Czech maps with snapshot-before-commit semantics.

    Callers batch same-round fixtures by taking every ``snapshot`` first,
    then applying every ``commit``. Deep ``copy`` isolates simulation trials.
    """

    def __init__(
            self,
            elo_params: EloParams | None = None,
            gap_params: GapParams | None = None,
            czech_params: CzechParams | None = None) -> None:
        self._elo_params = elo_params or EloParams()
        self._gap_params = gap_params or GapParams()
        self._czech_params = czech_params or CzechParams()
        self._elo: dict[int, float] = {}
        self._gap: dict[int, GapRating] = {}
        self._czech: dict[int, CzechRating] = {}

    def snapshot(self, home_id: int, away_id: int) -> dict[str, float]:
        """Return pre-match ratings, initializing missing teams lazily."""
        home_elo = self._ensure_elo(home_id)
        away_elo = self._ensure_elo(away_id)
        home_gap = self._ensure_gap(home_id)
        away_gap = self._ensure_gap(away_id)
        home_czech = self._ensure_czech(home_id)
        away_czech = self._ensure_czech(away_id)
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

    def commit(
            self,
            home_id: int,
            away_id: int,
            home_goals: int,
            away_goals: int) -> None:
        """Update ratings after a finished match (in place)."""
        # commit wymaga wcześniejszego snapshotu obu drużyn
        home_elo, away_elo = update_elo(
            self._elo[home_id],
            self._elo[away_id],
            home_goals,
            away_goals,
            self._elo_params)
        self._elo[home_id] = home_elo
        self._elo[away_id] = away_elo
        home_gap, away_gap = update_gap(
            self._gap[home_id],
            self._gap[away_id],
            home_goals,
            away_goals,
            self._gap_params)
        self._gap[home_id] = home_gap
        self._gap[away_id] = away_gap
        update_czech(
            self._czech[home_id],
            self._czech[away_id],
            home_goals,
            away_goals)

    def post_snapshot(
            self, home_id: int, away_id: int) -> dict[str, float]:
        """Return post-match ratings for teams already present in state."""
        values = {
            "home_elo_post": self._elo[home_id],
            "away_elo_post": self._elo[away_id],
            "home_gap_att_post": self._gap[home_id].attack,
            "home_gap_def_post": self._gap[home_id].defence,
            "away_gap_att_post": self._gap[away_id].attack,
            "away_gap_def_post": self._gap[away_id].defence
        }
        for name, value in venue_snapshot(
                self._czech[home_id], "home").items():
            values[f"home_czech_{name}_post"] = value
        for name, value in venue_snapshot(
                self._czech[away_id], "away").items():
            values[f"away_czech_{name}_post"] = value
        return values

    def copy(self) -> RatingState:
        """Return an independent deep copy for one simulation trial."""
        cloned = RatingState(
            elo_params=self._elo_params,
            gap_params=self._gap_params,
            czech_params=self._czech_params)
        cloned._elo = dict(self._elo)
        cloned._gap = {
            team_id: GapRating(rating.attack, rating.defence)
            for team_id, rating in self._gap.items()
        }
        cloned._czech = {
            team_id: _copy_czech_rating(rating)
            for team_id, rating in self._czech.items()
        }
        return cloned

    def _ensure_elo(self, team_id: int) -> float:
        return self._elo.setdefault(
            team_id, initial_elo(None, self._elo_params))

    def _ensure_gap(self, team_id: int) -> GapRating:
        return self._gap.setdefault(
            team_id, new_gap_rating(self._gap_params))

    def _ensure_czech(self, team_id: int) -> CzechRating:
        return self._czech.setdefault(
            team_id, new_czech_rating(self._czech_params))


def _copy_czech_rating(rating: CzechRating) -> CzechRating:
    """Deep-copy venue windows; Czech updates mutate deques in place."""
    return CzechRating(
        home=deque(
            (deepcopy(result) for result in rating.home),
            maxlen=rating.home.maxlen),
        away=deque(
            (deepcopy(result) for result in rating.away),
            maxlen=rating.away.maxlen))
