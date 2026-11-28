"""SQL reads for a league season knockout bracket."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection


# Rundy od tego numeru są fazą pucharową. Niższe zostają kolejką.
_KNOCKOUT_ROUND = 900


def fetch_knockout_matches(
        league_id: int,
        season_id: int) -> pd.DataFrame:
    """Return knockout matches for one league season.

    One select reads matches from round 900 up, both team names
    and the football and hockey columns that decide a tie. OT and
    SO flags travel with OTwinner and SOwinner. The winner is read
    from those winner columns. The tree is not built here. A match
    without both teams is left out by the team joins.
    """
    query = """
        SELECT
            m.id AS match_id,
            m.sport_id,
            m.round AS round_number,
            m.game_date,
            m.result,
            m.home_team_goals AS home_goals,
            m.away_team_goals AS away_goals,
            m.home_team AS home_team_id,
            t1.name AS home_team_name,
            t1.shortcut AS home_team_shortcut,
            m.away_team AS away_team_id,
            t2.name AS away_team_name,
            t2.shortcut AS away_team_shortcut,
            fsr.home_team_goals_post_ot AS home_extra_time_goals,
            fsr.away_team_goals_post_ot AS away_extra_time_goals,
            fsr.home_team_pen_score AS home_penalty_goals,
            fsr.away_team_pen_score AS away_penalty_goals,
            hma.OT AS ot,
            hma.SO AS so,
            hma.OTwinner AS ot_winner,
            hma.SOwinner AS so_winner
        FROM matches m
        JOIN teams t1 ON t1.id = m.home_team
        JOIN teams t2 ON t2.id = m.away_team
        LEFT JOIN football_special_round_add fsr
            ON fsr.match_id = m.id
        LEFT JOIN hockey_matches_add hma
            ON hma.match_id = m.id
        WHERE m.league = %s
            AND m.season = %s
            AND m.round >= %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id, _KNOCKOUT_ROUND))


def count_unplayed_league_matches(
        league_id: int,
        season_id: int) -> int:
    """Count league-phase matches that have no result yet.

    A knockout round is 900 or above and is not counted. An empty
    result and ``"0"`` are both unplayed. The profile stays off
    while this count is not zero.
    """
    query = """
        SELECT COUNT(*) AS total
        FROM matches
        WHERE league = %s
            AND season = %s
            AND round < %s
            AND (
                result IS NULL
                OR result = ''
                OR result = '0')
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(
            query,
            conn,
            params=(league_id, season_id, _KNOCKOUT_ROUND))
    if frame.empty:
        return 0
    total = frame.iloc[0]["total"]
    if pd.isna(total):
        return 0
    return int(total)
