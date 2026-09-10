"""League-tier predicates shared by the ML pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence

from models.pipeline.core.config import MatchupInput

MAX_ML_LEAGUE_TIER = 5


def is_ml_eligible_tier(tier: int | None) -> bool:
    """Return True when the league tier is known and at or below the cutoff."""
    if tier is None:
        return False
    return tier <= MAX_ML_LEAGUE_TIER


def ml_eligible_league_sql(league_alias: str = "l") -> str:
    """Return a SQL predicate that keeps leagues at or below the cutoff.

    The cutoff is inlined as an integer literal. ``league_alias`` is an
    internal table alias, not user input.
    """
    return (
        f"{league_alias}.tier IS NOT NULL "
        f"AND {league_alias}.tier <= {MAX_ML_LEAGUE_TIER}")


def filter_ml_eligible_matchups(
        matchups: Sequence[MatchupInput],
        league_tiers: Mapping[int, int | None]) -> list[MatchupInput]:
    """Keep matchups whose league is at or below the ML tier cutoff.

    Rows without ``league_id`` are kept: there is no league to reject.
    """
    kept: list[MatchupInput] = []
    for matchup in matchups:
        if matchup.league_id is None:
            kept.append(matchup)
            continue
        if is_ml_eligible_tier(league_tiers.get(matchup.league_id)):
            kept.append(matchup)
    return kept
