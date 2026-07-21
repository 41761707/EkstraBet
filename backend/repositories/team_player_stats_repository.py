"""SQL for aggregated football player leaders on a team."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection

ALLOWED_FOOTBALL_LEADER_STATS = frozenset({
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "fouls_conceded",
    "yellow_cards",
})


def fetch_football_team_player_stat_leaders(
    team_id: int,
    season_id: int,
    stat: str,
    match_ids: list[int],
    top: int,
) -> pd.DataFrame:
    """Aggregate one football stat for team players across match ids."""
    if stat not in ALLOWED_FOOTBALL_LEADER_STATS:
        raise ValueError(f"Unsupported leader stat: {stat}")
    if not match_ids:
        return pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "total",
                "appearances",
                "average",
            ]
        )

    placeholders = ", ".join(["%s"] * len(match_ids))
    # kolumna stat jest z allowlisty — nie interpolujemy wejścia użytkownika
    query = f"""
        SELECT
            p.id AS player_id,
            p.common_name AS player_name,
            COALESCE(
                SUM(
                    CASE
                        WHEN fps.{stat} IS NULL OR fps.{stat} < 0 THEN 0
                        ELSE fps.{stat}
                    END
                ),
                0
            ) AS total,
            COUNT(*) AS appearances
        FROM football_player_stats fps
        JOIN players p ON p.id = fps.player_id
        JOIN matches m ON m.id = fps.match_id
        WHERE fps.team_id = %s
            AND m.season = %s
            AND fps.match_id IN ({placeholders})
            AND p.common_name IS NOT NULL
            AND p.common_name != ''
        GROUP BY p.id, p.common_name
        HAVING total > 0 OR appearances > 0
        ORDER BY total DESC, appearances DESC, player_name ASC
        LIMIT %s
    """
    params: tuple[object, ...] = (
        team_id,
        season_id,
        *match_ids,
        top,
    )
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=params)
    if frame.empty:
        return frame

    frame["total"] = frame["total"].fillna(0).astype(int)
    frame["appearances"] = frame["appearances"].fillna(0).astype(int)
    frame["average"] = frame.apply(
        lambda row: (
            round(float(row["total"]) / float(row["appearances"]), 2)
            if int(row["appearances"]) > 0
            else 0.0
        ),
        axis=1,
    )
    return frame
