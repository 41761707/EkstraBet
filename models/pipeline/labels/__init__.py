"""Labelers for supervised football models."""

from models.pipeline.labels.football_btts import label_btts
from models.pipeline.labels.football_goals_poisson import label_goals
from models.pipeline.labels.football_goals_poisson import label_goals_poisson
from models.pipeline.labels.football_result import label_result

__all__ = [
    "label_btts",
    "label_goals",
    "label_goals_poisson",
    "label_result"
]
