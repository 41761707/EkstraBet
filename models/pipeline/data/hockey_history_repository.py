"""Read NHL match history, player stats, rosters and arenas."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from backend.database import get_db_connection

logger = logging.getLogger(__name__)

HOCKEY_SPORT_ID = 2
UNPLAYED_RESULT = "0"
FINAL_RESULTS = frozenset({"1", "X", "2"})
POSTPONED_MATCH_HOURS = 24
_MISSING_TOI = "--:--"

HOCKEY_MATCH_COLUMNS = [
    "match_id",
    "league",
    "season",
    "home_team",
    "away_team",
    "game_date",
    "round",
    "sport_id",
    "home_team_goals",
    "away_team_goals",
    "result",
    "home_team_sog",
    "away_team_sog",
    "ot",
    "so",
    "home_team_pp_goals",
    "away_team_pp_goals",
    "home_team_sh_goals",
    "away_team_sh_goals",
    "home_team_shots_acc",
    "away_team_shots_acc",
    "home_team_saves",
    "away_team_saves",
    "home_team_saves_acc",
    "away_team_saves_acc",
    "home_team_pp_acc",
    "away_team_pp_acc",
    "home_team_pk_acc",
    "away_team_pk_acc",
    "home_team_faceoffs",
    "away_team_faceoffs",
    "home_team_faceoffs_acc",
    "away_team_faceoffs_acc",
    "home_team_hits",
    "away_team_hits",
    "home_team_to",
    "away_team_to",
    "home_team_en",
    "away_team_en",
    "ot_winner",
    "so_winner"]

HOCKEY_PLAYER_STAT_COLUMNS = [
    "id",
    "match_id",
    "player_id",
    "team_id",
    "game_date",
    "season",
    "goals",
    "assists",
    "points",
    "plus_minus",
    "sog",
    "toi",
    "toi_seconds",
    "shots_against",
    "shots_saved"]

HOCKEY_MATCH_ROSTER_COLUMNS = [
    "id",
    "match_id",
    "player_id",
    "team_id",
    "position",
    "line",
    "number",
    "game_date",
    "season"]

HOCKEY_ROSTER_COLUMNS = [
    "id",
    "team_id",
    "player_id",
    "number",
    "line",
    "position",
    "pp",
    "is_injured",
    "injury_status",
    "injury_note",
    "updated_at"]

HOCKEY_ARENA_COLUMNS = [
    "team_id",
    "latitude",
    "longitude",
    "timezone"]

_MATCH_SELECT = [
    "m.id AS match_id",
    "m.league",
    "m.season",
    "m.home_team",
    "m.away_team",
    "m.game_date",
    "m.round",
    "m.sport_id",
    "m.home_team_goals",
    "m.away_team_goals",
    "m.result",
    "m.home_team_sog",
    "m.away_team_sog",
    "a.OT AS ot",
    "a.SO AS so",
    "a.home_team_pp_goals",
    "a.away_team_pp_goals",
    "a.home_team_sh_goals",
    "a.away_team_sh_goals",
    "a.home_team_shots_acc",
    "a.away_team_shots_acc",
    "a.home_team_saves",
    "a.away_team_saves",
    "a.home_team_saves_acc",
    "a.away_team_saves_acc",
    "a.home_team_pp_acc",
    "a.away_team_pp_acc",
    "a.home_team_pk_acc",
    "a.away_team_pk_acc",
    "a.home_team_faceoffs",
    "a.away_team_faceoffs",
    "a.home_team_faceoffs_acc",
    "a.away_team_faceoffs_acc",
    "a.home_team_hits",
    "a.away_team_hits",
    "a.home_team_to",
    "a.away_team_to",
    "a.home_team_en",
    "a.away_team_en",
    "a.OTwinner AS ot_winner",
    "a.SOwinner AS so_winner"]

_PLAYER_STAT_SELECT = [
    "s.id",
    "s.match_id",
    "s.player_id",
    "s.team_id",
    "m.game_date",
    "m.season",
    "s.goals",
    "s.assists",
    "s.points",
    "s.plus_minus",
    "s.sog",
    "s.toi",
    "s.shots_against",
    "s.shots_saved"]

_MATCH_ROSTER_SELECT = [
    "r.id",
    "r.match_id",
    "r.player_id",
    "r.team_id",
    "r.position",
    "r.line",
    "r.number",
    "m.game_date",
    "m.season"]

_SCHEDULE_QUERY = """
    SELECT
        m.id AS match_id,
        m.home_team,
        m.away_team,
        m.game_date,
        m.result
    FROM matches m
    WHERE m.league = %s
      AND m.sport_id = %s
    ORDER BY m.game_date, m.id
"""


def parse_toi_seconds(raw: object) -> int | None:
    """Parse a time-on-ice value into whole seconds.

    Accepts ``MM:SS``, a trailing ``:00`` (``MM:SS:00``), ``00:00:SS``,
    dotted ``MM.SS``, and ``0``. ``--:--``, blank and unknown text
    return ``None`` without raising.
    """
    if _is_missing(raw):
        return None
    text = str(raw).strip()
    if text == "" or text == _MISSING_TOI:
        return None
    if text == "0":
        return 0
    if ":" in text:
        return _parse_colon_toi(text)
    if "." in text:
        return _parse_dotted_toi(text)
    return None


def fetch_hockey_matches(league_id: int) -> pd.DataFrame:
    """Fetch league matches left-joined with ``hockey_matches_add``.

    Columns are ``HOCKEY_MATCH_COLUMNS``. Unplayed matches keep null
    extras. Rows are ordered by game date and match id.
    """
    frame = _read_sql(_match_query(), (league_id, HOCKEY_SPORT_ID))
    logger.info("Fetched %s hockey matches", len(frame))
    return _project_columns(frame, HOCKEY_MATCH_COLUMNS)


def fetch_hockey_player_stats(league_id: int) -> pd.DataFrame:
    """Fetch player box scores for one league, with TOI in seconds.

    ``game_date`` and ``season`` come from ``matches`` so later
    features can stay as-of. Columns are
    ``HOCKEY_PLAYER_STAT_COLUMNS``.
    """
    columns = ",\n        ".join(_PLAYER_STAT_SELECT)
    query = f"""
        SELECT
            {columns}
        FROM hockey_match_player_stats s
        INNER JOIN matches m ON m.id = s.match_id
        WHERE m.league = %s
          AND m.sport_id = %s
        ORDER BY m.game_date, s.id
    """
    frame = _with_toi_seconds(
        _read_sql(query, (league_id, HOCKEY_SPORT_ID)))
    logger.info("Fetched %s hockey player stat rows", len(frame))
    return _project_columns(frame, HOCKEY_PLAYER_STAT_COLUMNS)


def fetch_hockey_match_rosters(league_id: int) -> pd.DataFrame:
    """Fetch historical game rosters for one league.

    Columns are ``HOCKEY_MATCH_ROSTER_COLUMNS``, including
    ``game_date`` and ``season`` from ``matches``.
    """
    columns = ",\n        ".join(_MATCH_ROSTER_SELECT)
    query = f"""
        SELECT
            {columns}
        FROM hockey_match_rosters r
        INNER JOIN matches m ON m.id = r.match_id
        WHERE m.league = %s
          AND m.sport_id = %s
        ORDER BY m.game_date, r.id
    """
    frame = _read_sql(query, (league_id, HOCKEY_SPORT_ID))
    logger.info("Fetched %s hockey match roster rows", len(frame))
    return _project_columns(frame, HOCKEY_MATCH_ROSTER_COLUMNS)


def fetch_current_rosters() -> pd.DataFrame:
    """Fetch the current ``hockey_rosters`` rows.

    Columns are ``HOCKEY_ROSTER_COLUMNS``.
    """
    columns = ",\n        ".join(HOCKEY_ROSTER_COLUMNS)
    query = f"""
        SELECT
            {columns}
        FROM hockey_rosters
        ORDER BY team_id, id
    """
    frame = _read_sql(query, ())
    logger.info("Fetched %s current hockey roster rows", len(frame))
    return _project_columns(frame, HOCKEY_ROSTER_COLUMNS)


def fetch_team_arenas() -> pd.DataFrame:
    """Fetch arena coordinates and IANA time zones.

    Columns are ``HOCKEY_ARENA_COLUMNS``.
    """
    columns = ",\n        ".join(HOCKEY_ARENA_COLUMNS)
    query = f"""
        SELECT
            {columns}
        FROM hockey_team_arenas
        ORDER BY team_id
    """
    frame = _read_sql(query, ())
    logger.info("Fetched %s hockey arenas", len(frame))
    return _project_columns(frame, HOCKEY_ARENA_COLUMNS)


def fetch_upcoming_hockey_matches(league_id: int) -> pd.DataFrame:
    """Fetch league matches whose ``result`` is ``0``.

    Columns match ``fetch_hockey_matches``.
    """
    frame = _read_sql(
        _match_query("m.result = '0'"),
        (league_id, HOCKEY_SPORT_ID))
    logger.info("Fetched %s upcoming hockey matches", len(frame))
    return _project_columns(frame, HOCKEY_MATCH_COLUMNS)


def select_predictable_matches(
        league_id: int,
        now: datetime) -> list[int]:
    """Return match ids that are the next game for both clubs.

    A match is included when it is the earliest unplayed game for
    both teams and every earlier game of both teams already has a
    final result. Unplayed games older than 24 hours are postponed:
    they are logged and do not block the following game.
    """
    frame = _read_sql(
        _SCHEDULE_QUERY,
        (league_id, HOCKEY_SPORT_ID))
    selected = _predictable_match_ids(frame, now)
    logger.info(
        "Selected %s predictable hockey matches for league %s",
        len(selected),
        league_id)
    return selected


def _parse_colon_toi(text: str) -> int | None:
    pieces = text.split(":")
    if len(pieces) not in (2, 3):
        return None
    numbers = _clock_numbers(pieces)
    if numbers is None:
        return None
    if len(numbers) == 2:
        return _minutes_and_seconds(numbers[0], numbers[1])
    minutes, seconds, tail = numbers
    # 00:00:10 to jedyny zapis HH:MM:SS; reszta to MM:SS z dopiskiem :00
    if minutes == 0 and seconds == 0:
        return tail
    return _minutes_and_seconds(minutes, seconds)


def _parse_dotted_toi(text: str) -> int | None:
    # kilka wierszy scrapera ma MM.SS zamiast MM:SS
    pieces = text.split(".")
    if len(pieces) != 2 or len(pieces[1]) != 2:
        return None
    numbers = _clock_numbers(pieces)
    if numbers is None:
        return None
    return _minutes_and_seconds(numbers[0], numbers[1])


def _clock_numbers(pieces: list[str]) -> list[int] | None:
    numbers: list[int] = []
    for piece in pieces:
        if not piece.isdigit():
            return None
        numbers.append(int(piece))
    return numbers


def _minutes_and_seconds(minutes: int, seconds: int) -> int | None:
    if seconds >= 60:
        return None
    return minutes * 60 + seconds


def _is_missing(raw: object) -> bool:
    if raw is None:
        return True
    if isinstance(raw, float) and pd.isna(raw):
        return True
    return False


def _match_query(extra_filter: str | None = None) -> str:
    columns = ",\n        ".join(_MATCH_SELECT)
    where = "m.league = %s AND m.sport_id = %s"
    if extra_filter is not None:
        where = f"{where} AND {extra_filter}"
    return f"""
        SELECT
            {columns}
        FROM matches m
        LEFT JOIN hockey_matches_add a ON a.match_id = m.id
        WHERE {where}
        ORDER BY m.game_date, m.id
    """


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)


def _with_toi_seconds(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    if "toi" not in working.columns:
        working["toi_seconds"] = pd.Series(dtype="Int64")
        return working
    seconds = [
        parse_toi_seconds(value) for value in working["toi"].tolist()]
    working["toi_seconds"] = pd.array(seconds, dtype="Int64")
    return working


def _project_columns(
        frame: pd.DataFrame,
        columns: list[str]) -> pd.DataFrame:
    projected = frame.copy()
    for column in columns:
        if column not in projected.columns:
            projected[column] = pd.NA
    return projected.loc[:, columns]


def _predictable_match_ids(
        frame: pd.DataFrame,
        now: datetime) -> list[int]:
    if frame.empty:
        return []
    working = _prepare_schedule(frame)
    if working.empty:
        return []
    postponed = _postponed_mask(working, now)
    _warn_postponed(working.loc[postponed])
    active = working.loc[~postponed]
    sequences = _team_sequences(active)
    selected: list[int] = []
    for match_id, home_team, away_team, result in _schedule_rows(active):
        if not _is_unplayed(result):
            continue
        home_next = _next_open_match_id(sequences[home_team])
        away_next = _next_open_match_id(sequences[away_team])
        if home_next == match_id and away_next == match_id:
            selected.append(match_id)
    return selected


def _prepare_schedule(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["game_date"] = pd.to_datetime(working["game_date"])
    working = working.dropna(subset=["match_id", "home_team", "away_team"])
    return working.sort_values(
        ["game_date", "match_id"],
        na_position="last")


def _postponed_mask(frame: pd.DataFrame, now: datetime) -> pd.Series:
    cutoff = _naive_timestamp(now) - pd.Timedelta(
        hours=POSTPONED_MATCH_HOURS)
    unplayed = frame["result"].map(_is_unplayed)
    return unplayed & frame["game_date"].notna() & frame["game_date"].lt(
        cutoff)


def _warn_postponed(frame: pd.DataFrame) -> None:
    for match_id, game_date in zip(
            frame["match_id"].tolist(),
            frame["game_date"].tolist()):
        logger.warning(
            "Skipping postponed hockey match %s game_date=%s",
            int(match_id),
            game_date)


def _team_sequences(
        frame: pd.DataFrame) -> dict[int, list[tuple[int, object]]]:
    sequences: dict[int, list[tuple[int, object]]] = {}
    for match_id, home_team, away_team, result in _schedule_rows(frame):
        entry = (match_id, result)
        sequences.setdefault(home_team, []).append(entry)
        sequences.setdefault(away_team, []).append(entry)
    return sequences


def _schedule_rows(
        frame: pd.DataFrame) -> list[tuple[int, int, int, object]]:
    rows: list[tuple[int, int, int, object]] = []
    zipped = zip(
        frame["match_id"].tolist(),
        frame["home_team"].tolist(),
        frame["away_team"].tolist(),
        frame["result"].tolist())
    for match_id, home_team, away_team, result in zipped:
        rows.append((
            int(match_id),
            int(home_team),
            int(away_team),
            result))
    return rows


def _next_open_match_id(
        sequence: list[tuple[int, object]]) -> int | None:
    for match_id, result in sequence:
        if _is_unplayed(result):
            return match_id
        if not _has_final_result(result):
            return None
    return None


def _is_unplayed(value: object) -> bool:
    return _result_text(value) == UNPLAYED_RESULT


def _has_final_result(value: object) -> bool:
    return _result_text(value) in FINAL_RESULTS


def _result_text(value: object) -> str | None:
    if _is_missing(value):
        return None
    return str(value)


def _naive_timestamp(value: datetime) -> pd.Timestamp:
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)
    return pd.Timestamp(value)
