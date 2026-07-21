"""SQL queries for match schedule and detail data."""

from __future__ import annotations
from datetime import date
import pandas as pd
from backend.database import get_db_connection

_MATCH_BASE_COLUMNS = """
    m.id,
    m.league AS league_id,
    m.season AS season_id,
    m.sport_id,
    m.round,
    m.game_date,
    m.result,
    m.home_team_goals,
    m.away_team_goals,
    m.home_team AS home_id,
    t1.name AS home_name,
    t1.shortcut AS home_shortcut,
    m.away_team AS away_id,
    t2.name AS away_name,
    t2.shortcut AS away_shortcut
"""

_MATCH_CHART_STATS_COLUMNS = """
    m.home_team_sc,
    m.away_team_sc,
    m.home_team_sog,
    m.away_team_sog,
    m.home_team_fk,
    m.away_team_fk,
    m.home_team_fouls,
    m.away_team_fouls,
    m.home_team_ck,
    m.away_team_ck,
    m.home_team_off,
    m.away_team_off,
    m.home_team_yc,
    m.away_team_yc,
    m.home_team_rc,
    m.away_team_rc
"""

_HOCKEY_SCORE_RESOLUTION_COLUMNS = """
    hma.OT AS hma_ot,
    hma.SO AS hma_so,
    hma.OTwinner AS hma_ot_winner,
    hma.SOwinner AS hma_so_winner
"""

_HOCKEY_MATCH_ADD_STATS_COLUMNS = """
    hma.home_team_pp_goals,
    hma.away_team_pp_goals,
    hma.home_team_sh_goals,
    hma.away_team_sh_goals,
    hma.home_team_shots_acc,
    hma.away_team_shots_acc,
    hma.home_team_saves,
    hma.away_team_saves,
    hma.home_team_saves_acc,
    hma.away_team_saves_acc,
    hma.home_team_pp_acc,
    hma.away_team_pp_acc,
    hma.home_team_pk_acc,
    hma.away_team_pk_acc,
    hma.home_team_faceoffs,
    hma.away_team_faceoffs,
    hma.home_team_faceoffs_acc,
    hma.away_team_faceoffs_acc,
    hma.home_team_hits,
    hma.away_team_hits,
    hma.home_team_to,
    hma.away_team_to,
    hma.home_team_en,
    hma.away_team_en
"""

_HOCKEY_MATCHES_ADD_JOIN = """
    LEFT JOIN hockey_matches_add hma ON m.id = hma.match_id
"""

_MATCH_DETAIL_STATS_COLUMNS = """
    m.home_team_xg,
    m.away_team_xg,
    m.home_team_bp,
    m.away_team_bp,
    m.home_team_sc,
    m.away_team_sc,
    m.home_team_sog,
    m.away_team_sog,
    m.home_team_fk,
    m.away_team_fk,
    m.home_team_ck,
    m.away_team_ck,
    m.home_team_off,
    m.away_team_off,
    m.home_team_fouls,
    m.away_team_fouls,
    m.home_team_yc,
    m.away_team_yc,
    m.home_team_rc,
    m.away_team_rc
"""

_MATCH_SCORE_RESOLUTION_COLUMNS = """
    fsr.OT AS fsr_ot,
    fsr.PEN AS fsr_pen,
    fsr.home_team_goals_post_ot AS fsr_post_ot_home_goals,
    fsr.away_team_goals_post_ot AS fsr_post_ot_away_goals,
    fsr.home_team_pen_score AS fsr_penalties_home_goals,
    fsr.away_team_pen_score AS fsr_penalties_away_goals
"""

_MATCH_SCORE_RESOLUTION_JOIN = """
    LEFT JOIN football_special_round_add fsr ON fsr.match_id = m.id
"""

_MATCH_SELECT_COLUMNS = f"""
    {_MATCH_BASE_COLUMNS},
    {_MATCH_CHART_STATS_COLUMNS},
    {_MATCH_SCORE_RESOLUTION_COLUMNS},
    {_HOCKEY_SCORE_RESOLUTION_COLUMNS}
"""

_MATCH_DETAIL_SELECT_COLUMNS = f"""
    {_MATCH_BASE_COLUMNS},
    {_MATCH_DETAIL_STATS_COLUMNS},
    {_MATCH_SCORE_RESOLUTION_COLUMNS},
    {_HOCKEY_SCORE_RESOLUTION_COLUMNS},
    {_HOCKEY_MATCH_ADD_STATS_COLUMNS}
"""

MAX_MATCH_HISTORY = 50


def fetch_league_matches(
    league_id: int,
    season_id: int,
    round_num: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None) -> pd.DataFrame:
    """Return matches for a league season with optional filters."""
    conditions = ["m.league = %s", "m.season = %s"]
    params: list[object] = [league_id, season_id]

    if round_num is not None:
        conditions.append("m.round = %s")
        params.append(round_num)

    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)

    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            {_MATCH_SELECT_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {_MATCH_SCORE_RESOLUTION_JOIN}
        {_HOCKEY_MATCHES_ADD_JOIN}
        WHERE {where_clause}
        ORDER BY m.game_date ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def match_exists(match_id: int) -> bool:
    """Return True when the match id exists in the database."""
    query = "SELECT 1 FROM matches WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(match_id,))
    return not frame.empty


def fetch_match_by_id(match_id: int) -> pd.DataFrame:
    """Return a single match row with teams and basic stats."""
    query = f"""
        SELECT
            {_MATCH_DETAIL_SELECT_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {_MATCH_SCORE_RESOLUTION_JOIN}
        {_HOCKEY_MATCHES_ADD_JOIN}
        WHERE m.id = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))


def fetch_head_to_head_for_match(
    home_team_id: int,
    away_team_id: int,
    exclude_match_id: int,
    limit: int = MAX_MATCH_HISTORY) -> pd.DataFrame:
    """Return played H2H matches excluding the current match."""
    query = f"""
        SELECT
            {_MATCH_SELECT_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {_MATCH_SCORE_RESOLUTION_JOIN}
        {_HOCKEY_MATCHES_ADD_JOIN}
        WHERE (
            (m.home_team = %s AND m.away_team = %s)
            OR (m.home_team = %s AND m.away_team = %s)
        )
            AND m.result != '0'
            AND m.id != %s
        ORDER BY m.game_date DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(
                home_team_id,
                away_team_id,
                away_team_id,
                home_team_id,
                exclude_match_id,
                limit))


def fetch_team_matches_before_date(
    team_id: int,
    before_game_date: object,
    exclude_match_id: int,
    limit: int = MAX_MATCH_HISTORY) -> pd.DataFrame:
    """Return played team matches strictly before a reference kick-off."""
    query = f"""
        SELECT
            {_MATCH_SELECT_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {_MATCH_SCORE_RESOLUTION_JOIN}
        {_HOCKEY_MATCHES_ADD_JOIN}
        WHERE (m.home_team = %s OR m.away_team = %s)
            AND m.result != '0'
            AND m.game_date < %s
            AND m.id != %s
        ORDER BY m.game_date DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(
                team_id,
                team_id,
                before_game_date,
                exclude_match_id,
                limit))


def fetch_hockey_match_boxscore(match_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return goalie and skater stats for a hockey match."""
    goalie_query = """
        SELECT
            p.id AS player_id,
            p.common_name AS player_name,
            box.team_id,
            t.name AS team_name,
            box.points,
            box.penalty_minutes,
            box.toi,
            box.shots_against,
            box.shots_saved,
            box.saves_acc
        FROM hockey_match_player_stats box
        JOIN players p ON box.player_id = p.id
        JOIN teams t ON box.team_id = t.id
        WHERE box.match_id = %s
            AND p.position = 'G'
        ORDER BY t.name, p.common_name
    """
    skater_query = """
        SELECT
            p.id AS player_id,
            p.common_name AS player_name,
            box.team_id,
            t.name AS team_name,
            box.goals,
            box.assists,
            box.points,
            box.plus_minus,
            box.penalty_minutes,
            box.sog,
            box.toi
        FROM hockey_match_player_stats box
        JOIN players p ON box.player_id = p.id
        JOIN teams t ON box.team_id = t.id
        WHERE box.match_id = %s
            AND p.position <> 'G'
        ORDER BY t.name, box.points DESC, p.common_name
    """
    with get_db_connection() as conn:
        goalies = pd.read_sql(goalie_query, conn, params=(match_id,))
        skaters = pd.read_sql(skater_query, conn, params=(match_id,))
    return goalies, skaters


def fetch_match_player_stats(match_id: int) -> pd.DataFrame:
    """Return per-player football stats for a single match."""
    query = """
        SELECT
            p.id AS player_id,
            p.common_name AS player_name,
            fps.team_id,
            t.name AS team_name,
            fps.goals,
            fps.assists,
            fps.red_cards,
            fps.yellow_cards,
            fps.corners_won,
            fps.shots,
            fps.shots_on_target,
            fps.blocked_shots,
            fps.passes,
            fps.crosses,
            fps.tackles,
            fps.offsides,
            fps.fouls_conceded,
            fps.fouls_won,
            fps.saves
        FROM football_player_stats fps
        JOIN players p ON fps.player_id = p.id
        JOIN teams t ON fps.team_id = t.id
        WHERE fps.match_id = %s
        ORDER BY t.name, p.common_name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))


