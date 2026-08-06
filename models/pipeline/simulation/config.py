"""Configuration and DTO types for season-end simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel
from pydantic import field_validator
from pydantic import model_validator


FOOTBALL_SPORT_ID = 1
MIN_TRIALS = 100
MAX_TRIALS = 10000
DEFAULT_TRIALS = 2000
DEFAULT_SEED = 42
DEFAULT_INFERENCE_BATCH_SIZE = 512
DEFAULT_DAYS_PER_ROUND = 7
# rundy pucharowe / specjalne pomijane jak w standings
MAX_LEAGUE_ROUND = 900


class SimulationMode(str, Enum):
    """How finished match results are treated during simulation."""

    FROM_NOW = "from_now"
    FROM_SEASON_START = "from_season_start"


class SeasonSimulationConfig(BaseModel):
    """Runtime settings for one season projection run."""

    league_id: int
    season_id: int
    mode: SimulationMode
    n_trials: int = DEFAULT_TRIALS
    seed: int = DEFAULT_SEED
    inference_batch_size: int = DEFAULT_INFERENCE_BATCH_SIZE
    days_per_round: int = DEFAULT_DAYS_PER_ROUND
    sport_id: int = FOOTBALL_SPORT_ID

    @field_validator("n_trials")
    @classmethod
    def _validate_n_trials(cls, value: int) -> int:
        if value < MIN_TRIALS or value > MAX_TRIALS:
            raise ValueError(
                f"n_trials must be between {MIN_TRIALS} and {MAX_TRIALS}")
        return value

    @field_validator("inference_batch_size")
    @classmethod
    def _validate_batch_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("inference_batch_size must be >= 1")
        return value

    @field_validator("days_per_round")
    @classmethod
    def _validate_days_per_round(cls, value: int) -> int:
        if value < 1:
            raise ValueError("days_per_round must be >= 1")
        return value

    @model_validator(mode="after")
    def _validate_football_only(self) -> SeasonSimulationConfig:
        # v1 projekcji dotyczy wyłącznie piłki nożnej
        if self.sport_id != FOOTBALL_SPORT_ID:
            raise ValueError(
                "season simulation supports football only "
                f"(sport_id={FOOTBALL_SPORT_ID})")
        return self


@dataclass(frozen=True)
class ScheduleRow:
    """One row from the stable season schedule table."""

    id: int
    match_id: int | None
    league_id: int
    season_id: int
    home_team_id: int
    away_team_id: int
    round: int


@dataclass(frozen=True)
class ResolvedFixture:
    """Schedule row with optional finished match outcome."""

    schedule: ScheduleRow
    result: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    is_fixed: bool = False


@dataclass(frozen=True)
class SeasonSimulationInput:
    """Deterministic simulation input loaded from schedule (+ matches).

    ``team_ids`` is the independent season roster (not derived from
    schedule rows alone), so a missing club cannot shrink N silently.
    """

    league_id: int
    season_id: int
    mode: SimulationMode
    team_ids: list[int]
    fixtures: list[ResolvedFixture]
    input_fingerprint: str


@dataclass(frozen=True)
class FixtureValidation:
    """Result of double round-robin schedule completeness checks."""

    is_valid: bool
    team_count: int
    expected_fixture_count: int
    actual_fixture_count: int
    missing_pairs: tuple[tuple[int, int], ...] = ()
    duplicate_pairs: tuple[tuple[int, int], ...] = ()
    missing_team_ids: tuple[int, ...] = ()
    unexpected_team_ids: tuple[int, ...] = ()
    error_message: str | None = None
