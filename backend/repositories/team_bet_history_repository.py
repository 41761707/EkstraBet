"""Recent finished matches for the team-bet history strip."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.database import get_db_connection


# Kotwica: drużyna, mecz, termin, sport, filtr statystyki.
TeamHistoryAnchor = tuple[int, int, datetime, int, str]

_FOR_COLUMNS = {
    "corners_for": ("m.home_team_ck", "m.away_team_ck"),
    "fouls_for": ("m.home_team_fouls", "m.away_team_fouls"),
    "yellows_for": ("m.home_team_yc", "m.away_team_yc"),
    "offsides_for": ("m.home_team_off", "m.away_team_off")}
_TOTAL_COLUMNS = {
    "corners_total": ("m.home_team_ck", "m.away_team_ck"),
    "fouls_total": ("m.home_team_fouls", "m.away_team_fouls"),
    "yellows_total": ("m.home_team_yc", "m.away_team_yc"),
    "offsides_total": ("m.home_team_off", "m.away_team_off")}
_STAT_FILTERS = frozenset({"goals"}) | frozenset(_FOR_COLUMNS) | frozenset(
    _TOTAL_COLUMNS)


def fetch_team_recent_matches(
        anchors: list[TeamHistoryAnchor],
        window: int) -> pd.DataFrame:
    """Return up to ``window`` earlier matches for each team anchor.

    An anchor is ``(team_id, match_id, kickoff, sport_id, stat_filter)``.
    The current match is excluded. Each filter keeps only matches that
    recorded that stat, before ``LIMIT``, so the window does not shrink
    in Python. Rows are not ordered; the caller sorts them. An empty
    anchor list does not open a connection.
    """
    if not anchors:
        return pd.DataFrame()
    unique = _unique_anchors(anchors)
    grouped = _group_anchors(unique)
    frames: list[pd.DataFrame] = []
    with get_db_connection() as conn:
        for stat_filter, group in grouped:
            frames.append(_read_recent(conn, stat_filter, group, window))
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True)


def _unique_anchors(
        anchors: list[TeamHistoryAnchor]) -> list[TeamHistoryAnchor]:
    """Keep the first anchor for each team, match and stat filter."""
    seen: set[tuple[int, int, str]] = set()
    unique: list[TeamHistoryAnchor] = []
    for team_id, match_id, kickoff, sport_id, stat_filter in anchors:
        _assert_stat_filter(stat_filter)
        key = (team_id, match_id, stat_filter)
        if key in seen:
            continue
        seen.add(key)
        unique.append((team_id, match_id, kickoff, sport_id, stat_filter))
    return unique


def _group_anchors(
        anchors: list[TeamHistoryAnchor]
        ) -> list[tuple[str, list[tuple[int, int, datetime, int]]]]:
    """Group anchors by stat filter, in the order filters first appear."""
    grouped: dict[str, list[tuple[int, int, datetime, int]]] = {}
    for team_id, match_id, kickoff, sport_id, stat_filter in anchors:
        grouped.setdefault(stat_filter, []).append(
            (team_id, match_id, kickoff, sport_id))
    return list(grouped.items())


def _read_recent(
        conn: object,
        stat_filter: str,
        group: list[tuple[int, int, datetime, int]],
        window: int) -> pd.DataFrame:
    """Run one lateral query for every anchor of a single stat filter."""
    params: list[object] = []
    for team_id, match_id, kickoff, sport_id in group:
        params.extend((team_id, match_id, kickoff, sport_id))
    params.append(window)
    query = _history_query(stat_filter, len(group))
    frame = pd.read_sql(query, conn, params=tuple(params))
    frame["stat_filter"] = stat_filter
    return frame


def _assert_stat_filter(stat_filter: str) -> None:
    """Reject a filter that is not one of the strip stats."""
    if stat_filter in _STAT_FILTERS:
        return
    raise ValueError(f"Unknown team history stat filter: {stat_filter}")


def _history_query(stat_filter: str, anchor_count: int) -> str:
    """Build one lateral query. Team ids stay in parameters."""
    _assert_stat_filter(stat_filter)
    union_sql = _anchor_union(anchor_count)
    predicate = _stat_predicate(stat_filter)
    return f"""
        SELECT
            anchor.team_id AS team_id,
            anchor.match_id AS anchor_match_id,
            hist.match_id AS match_id,
            hist.game_date AS game_date,
            hist.home_team_id AS home_team_id,
            hist.away_team_id AS away_team_id,
            hist.home_goals AS home_goals,
            hist.away_goals AS away_goals,
            hist.result AS result,
            hist.home_corners AS home_corners,
            hist.away_corners AS away_corners,
            hist.home_fouls AS home_fouls,
            hist.away_fouls AS away_fouls,
            hist.home_yellows AS home_yellows,
            hist.away_yellows AS away_yellows,
            hist.home_offsides AS home_offsides,
            hist.away_offsides AS away_offsides,
            hist.ot_winner AS ot_winner,
            hist.so_winner AS so_winner
        FROM (
            {union_sql}
        ) anchor
        JOIN LATERAL (
            SELECT
                m.id AS match_id,
                m.game_date AS game_date,
                m.home_team AS home_team_id,
                m.away_team AS away_team_id,
                m.home_team_goals AS home_goals,
                m.away_team_goals AS away_goals,
                m.result AS result,
                m.home_team_ck AS home_corners,
                m.away_team_ck AS away_corners,
                m.home_team_fouls AS home_fouls,
                m.away_team_fouls AS away_fouls,
                m.home_team_yc AS home_yellows,
                m.away_team_yc AS away_yellows,
                m.home_team_off AS home_offsides,
                m.away_team_off AS away_offsides,
                hma.OTwinner AS ot_winner,
                hma.SOwinner AS so_winner
            FROM matches m
            LEFT JOIN hockey_matches_add hma ON hma.match_id = m.id
            WHERE (m.home_team = anchor.team_id
                OR m.away_team = anchor.team_id)
                AND m.sport_id = anchor.sport_id
                AND m.game_date < anchor.before_ts
                AND m.id <> anchor.match_id
                AND m.home_team_goals IS NOT NULL
                AND m.away_team_goals IS NOT NULL
                AND m.result IN ('1', 'X', '2')
                {predicate}
            ORDER BY m.game_date DESC, m.id DESC
            LIMIT %s
        ) hist ON TRUE
    """


def _stat_predicate(stat_filter: str) -> str:
    """Return the IS NOT NULL clause that belongs before LIMIT."""
    if stat_filter == "goals":
        return ""
    if stat_filter in _FOR_COLUMNS:
        home_column, away_column = _FOR_COLUMNS[stat_filter]
        return (
            "AND ((m.home_team = anchor.team_id "
            f"AND {home_column} IS NOT NULL) "
            "OR (m.away_team = anchor.team_id "
            f"AND {away_column} IS NOT NULL))")
    home_column, away_column = _TOTAL_COLUMNS[stat_filter]
    return (
        f"AND {home_column} IS NOT NULL "
        f"AND {away_column} IS NOT NULL")


def _anchor_union(anchor_count: int) -> str:
    """Build the anchor derived table. The first row names columns."""
    first = (
        "SELECT %s AS team_id, %s AS match_id, "
        "%s AS before_ts, %s AS sport_id")
    if anchor_count == 1:
        return first
    rest = "\n            UNION ALL\n            SELECT %s, %s, %s, %s"
    return first + rest * (anchor_count - 1)
