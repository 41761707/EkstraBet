"""Regulation goal totals and overtime-winner labels for NHL."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler


OT_WINNER_HOME = 1
OT_WINNER_AWAY = 2
OT_WINNER_SHOOTOUT = 3
SO_WINNER_HOME = 1


@dataclass(frozen=True)
class HockeyGoalLabels:
    """Targets for one finished match.

    ``ot_home_win`` is set only for a regulation tie: 1 when the
    home team wins in overtime or the shootout, 0 when the away
    team does, and None when the winner is missing.
    """

    goals_home: int
    goals_away: int
    ot_home_win: int | None


def label_hockey_goals(row: Mapping[str, Any]) -> HockeyGoalLabels:
    """Return regulation goals and, for ties, who won extra time."""
    home = _validated_goal(row, "home_team_goals")
    away = _validated_goal(row, "away_team_goals")
    if home != away:
        return HockeyGoalLabels(home, away, None)
    return HockeyGoalLabels(
        home, away, _ot_home_win(row.get("ot_winner"), row.get("so_winner")))


def _validated_goal(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None or _is_missing(value):
        raise ValueError(f"Missing goal value: {key}")
    try:
        goal = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid goal value for {key}: {value!r}") from exc
    if goal < 0:
        raise ValueError(f"Goal value cannot be negative: {key}")
    return goal


def _ot_home_win(ot_winner: object, so_winner: object) -> int | None:
    """Map OTwinner and SOwinner onto a home-win indicator."""
    winner = _optional_int(ot_winner)
    if winner == OT_WINNER_HOME:
        return 1
    if winner == OT_WINNER_AWAY:
        return 0
    if winner != OT_WINNER_SHOOTOUT:
        return None
    shootout = _optional_int(so_winner)
    if shootout is None:
        return None
    if shootout == SO_WINNER_HOME:
        return 1
    return 0


def _optional_int(value: object) -> int | None:
    if _is_missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


@register_labeler("HockeyGoalsLabeler")
class HockeyGoalsLabeler:
    """Build regulation-goal and overtime labels for a match frame."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        del config

    def label(self, row: Mapping[str, Any]) -> HockeyGoalLabels:
        """Label one match."""
        return label_hockey_goals(row)

    def build_labels(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return goals_home, goals_away and ot_home_win for every row."""
        records = frame.to_dict(orient="records")
        labeled = [label_hockey_goals(row) for row in records]
        return pd.DataFrame(
            [
                {
                    "goals_home": item.goals_home,
                    "goals_away": item.goals_away,
                    "ot_home_win": item.ot_home_win
                }
                for item in labeled
            ],
            index=frame.index)
