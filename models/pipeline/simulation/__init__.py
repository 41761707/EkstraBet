"""Season-end Monte Carlo simulation package."""

from __future__ import annotations

from typing import Any

from models.pipeline.simulation.aggregation import BaselineStanding
from models.pipeline.simulation.aggregation import TeamSeasonProjection
from models.pipeline.simulation.aggregation import aggregate_projection
from models.pipeline.simulation.aggregation import baseline_from_standings
from models.pipeline.simulation.aggregation import rank_teams
from models.pipeline.simulation.config import FixtureValidation
from models.pipeline.simulation.config import ResolvedFixture
from models.pipeline.simulation.config import ScheduleRow
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.outcome_sampler import sample_poisson_scores

# season_simulator importuje schedule_repository — nie ładujemy go tu,
# żeby uniknąć cyklu data → schedule_repository → simulation → season_simulator

__all__ = [
    "BaselineStanding",
    "DynamicSeasonSimulator",
    "FixtureValidation",
    "ResolvedFixture",
    "ScheduleRow",
    "SeasonSimulationConfig",
    "SeasonSimulationInput",
    "SeasonSimulationResult",
    "SimulationMode",
    "TeamSeasonProjection",
    "TrialStandingState",
    "aggregate_projection",
    "baseline_from_standings",
    "rank_teams",
    "sample_poisson_scores"
]

_LAZY_SIMULATOR_EXPORTS = {
    "DynamicSeasonSimulator",
    "SeasonSimulationResult",
    "TrialStandingState"
}


def __getattr__(name: str) -> Any:
    """Lazy-load simulator symbols to break the data↔simulation cycle."""
    if name not in _LAZY_SIMULATOR_EXPORTS:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}")
    from models.pipeline.simulation import season_simulator
    value = getattr(season_simulator, name)
    globals()[name] = value
    return value
