"""Build and read a probable NHL lineup for one club.

``build_probable_lineup`` dresses the last game, drops injured players
and players off the current roster, fills those holes, then scores
every healthy goalie with ``GoalieStartModel``. A club with no
previous game keeps no skaters, so strength stays typical.
``resolve_lineup_for_stage`` reads a stored lineup and, for
``MODEL``, fills goalie ``start_probability`` again because the
table has no column for it. ``initial`` prefers ``CONFIRMED``, then
``EXTERNAL``, then ``MODEL``. ``final`` keeps only ``CONFIRMED``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime

import pandas as pd

from backend.config import REPO_ROOT
from backend.database import get_db_connection
from models.pipeline.core.artifacts import load_model_artifact
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_matches)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.data.hockey_history_repository import (
    select_predictable_matches)
from models.pipeline.features.hockey.line_slots import DEFENSE_POSITIONS
from models.pipeline.features.hockey.line_slots import FORWARD_POSITIONS
from models.pipeline.features.hockey.line_slots import GOALIE_POSITION
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.ratings import HOCKEY_ELO_INITIAL
from models.pipeline.features.hockey.ratings import HockeyTeamRatingState
from models.pipeline.lineups.hockey_goalie_start import GoalieStartHistory
from models.pipeline.lineups.hockey_goalie_start import GoalieStartModel
from models.pipeline.lineups.hockey_goalie_start import load_goalie_start_run


logger = logging.getLogger(__name__)

_INITIAL_STAGE = "initial"
_FINAL_STAGE = "final"
_MODEL_SOURCE = "MODEL"
_CONFIDENCE_GAMES = 5
_FORWARD_GROUP = "F"
_DEFENSE_GROUP = "D"
_SOURCE_RANK = {"CONFIRMED": 0, "EXTERNAL": 1, "MODEL": 2}
_FINISHED_RESULTS = frozenset({"1", "X", "2"})
_GOALIE_CONFIG = (
    REPO_ROOT / "models" / "configs" / "prediction"
    / "hockey_goalie_start_v1.json")
_LINEUP_QUERY = """
    SELECT
        player_id,
        position,
        line,
        pp_unit,
        is_starting_goalie,
        confidence,
        source
    FROM hockey_probable_lineups
    WHERE match_id = %s
      AND team_id = %s
"""
_READ_MODELS: dict[int, "_GoalieReadState"] = {}
_CURRENT_ROSTER_QUERY = """
    SELECT
        hr.team_id,
        hr.player_id,
        COALESCE(NULLIF(hr.position, ''), p.position) AS position,
        hr.line,
        hr.pp AS pp_unit,
        hr.is_injured
    FROM hockey_rosters hr
    LEFT JOIN players p ON p.id = hr.player_id
    ORDER BY hr.team_id, hr.player_id
"""


@dataclass
class ProjectionContext:
    """Frames and models shared by every club in one build.

    Calls must move forward in time. ``ratings.snapshot`` and the
    goalie history both reject an earlier date.
    """

    matches: pd.DataFrame
    game_rosters: pd.DataFrame
    current_roster: pd.DataFrame
    player_stats: pd.DataFrame
    goalie_model: GoalieStartModel
    goalie_starts: pd.DataFrame
    ratings: HockeyTeamRatingState


@dataclass(frozen=True)
class _RosterPlayer:
    player_id: int
    position: str
    line: int | None
    pp_unit: int | None
    injured: bool


@dataclass
class _GoalieReadState:
    """Fitted start model and the history used to score a stored lineup."""

    model: GoalieStartModel
    starts: pd.DataFrame
    matches: pd.DataFrame
    ratings: HockeyTeamRatingState


def build_probable_lineup(
        match_id: int,
        team_id: int,
        as_of: datetime,
        context: ProjectionContext | None = None) -> ProbableLineup:
    """Project one club as of ``as_of``.

    Skaters come from the previous game. A player who is injured or
    absent from ``hockey_rosters`` is replaced by the healthy skater
    in the same position group with the highest average time on ice.
    Goalies are every healthy goalie, with ``is_starting_goalie`` on
    the highest ``GoalieStartModel`` probability. ``confidence`` is
    the share of the last five team games. Pass ``context`` to reuse
    one league load; omit it to read the database.
    """
    loaded = context if context is not None else _context_for_match(
        int(match_id))
    return _project_club(loaded, int(match_id), int(team_id), as_of)


def build_predictable_lineups(
        league_id: int,
        now: datetime) -> list[ProbableLineup]:
    """Project both clubs for each next predictable match."""
    match_ids = select_predictable_matches(int(league_id), now)
    if not match_ids:
        logger.warning(
            "No predictable hockey matches for league %s", league_id)
        return []
    context = _load_league_context(int(league_id))
    return _project_matches(context, match_ids)


def resolve_lineup_for_stage(
        match_id: int,
        team_id: int,
        stage: str) -> ProbableLineup | None:
    """Return the stored lineup for this stage, or None.

    A ``MODEL`` lineup gets goalie start probabilities from
    ``GoalieStartModel``. The table does not store them, and an
    unconfirmed starter is an expectation over those weights.
    """
    frame = _fetch_rows(int(match_id), int(team_id))
    lineup = lineup_for_stage(int(match_id), int(team_id), stage, frame)
    if lineup is None or not _has_model_goalie(lineup):
        return lineup
    try:
        return _restore_model_goalie_probabilities(lineup)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        logger.warning(
            "Could not score goalie starts for match %s team %s: %s",
            match_id,
            team_id,
            exc)
        return lineup


def lineup_for_stage(
        match_id: int,
        team_id: int,
        stage: str,
        frame: pd.DataFrame) -> ProbableLineup | None:
    """Pick one source from rows already loaded for a club."""
    chosen = _rows_for_stage(frame, stage)
    if chosen.empty:
        return None
    players = [
        player
        for player in (
            _player_from_row(row) for row in chosen.itertuples(index=False))
        if player is not None]
    if not players:
        return None
    return ProbableLineup(
        match_id=match_id,
        team_id=team_id,
        players=players)


def apply_model_start_probabilities(
        lineup: ProbableLineup,
        model: GoalieStartModel,
        goalie_starts: pd.DataFrame,
        opponent_elo: float,
        as_of: datetime) -> ProbableLineup:
    """Set ``start_probability`` on ``MODEL`` goalies.

    ``is_starting_goalie`` stays as stored. Prediction weights the
    unconfirmed net by these probabilities instead of treating the
    marked starter as certain.
    """
    goalies = [
        player for player in lineup.players if _is_model_goalie(player)]
    if not goalies:
        return lineup
    ordered = sorted(goalies, key=lambda player: player.player_id)
    history = GoalieStartHistory.from_starts(
        _starts_before(goalie_starts, as_of))
    features = pd.DataFrame([
        history.feature_row(
            lineup.team_id,
            player.player_id,
            as_of,
            opponent_elo)
        for player in ordered])
    probabilities = model.predict_proba(features)
    scored = {
        player.player_id: float(probabilities[index])
        for index, player in enumerate(ordered)}
    return ProbableLineup(
        match_id=lineup.match_id,
        team_id=lineup.team_id,
        players=[
            _with_start_probability(player, scored)
            for player in lineup.players])


def _restore_model_goalie_probabilities(
        lineup: ProbableLineup) -> ProbableLineup:
    state = _read_model_for_match(lineup.match_id)
    moment = _match_moment(state.matches, lineup.match_id)
    elo = _elo_for_read(state, lineup.match_id, lineup.team_id, moment)
    return apply_model_start_probabilities(
        lineup, state.model, state.starts, elo, moment)


def _read_model_for_match(match_id: int) -> "_GoalieReadState":
    league_id = _league_id(match_id)
    cached = _READ_MODELS.get(league_id)
    if cached is not None:
        return cached
    matches = fetch_hockey_matches(league_id)
    rosters = fetch_hockey_match_rosters(league_id)
    state = _GoalieReadState(
        model=_load_goalie_model(),
        starts=_goalie_start_rows(rosters),
        matches=matches,
        ratings=_replay_ratings(matches))
    _READ_MODELS[league_id] = state
    return state


def _league_id(match_id: int) -> int:
    frame = _read_sql(
        "SELECT league FROM matches WHERE id = %s",
        (int(match_id),))
    if frame.empty:
        raise ValueError(f"Match {match_id} was not found")
    return int(frame.iloc[0]["league"])


def _elo_for_read(
        state: "_GoalieReadState",
        match_id: int,
        team_id: int,
        as_of: datetime) -> float:
    try:
        return _elo_against(
            state.matches, state.ratings, match_id, team_id, as_of)
    except ValueError:
        # Odczyt cofnął datę. Jedno odtworzenie ratingów i ponowna próba.
        logger.warning(
            "Replaying hockey ratings before match %s", match_id)
        state.ratings = _replay_ratings(state.matches)
        return _elo_against(
            state.matches, state.ratings, match_id, team_id, as_of)


def _match_moment(matches: pd.DataFrame, match_id: int) -> datetime:
    return _as_naive(_match_row(matches, match_id)["game_date"])


def _with_start_probability(
        player: ProbableLineupPlayer,
        scored: dict[int, float]) -> ProbableLineupPlayer:
    probability = scored.get(player.player_id)
    if probability is None:
        return player
    return replace(player, start_probability=probability)


def _has_model_goalie(lineup: ProbableLineup) -> bool:
    return any(_is_model_goalie(player) for player in lineup.players)


def _is_model_goalie(player: ProbableLineupPlayer) -> bool:
    return (
        player.source == _MODEL_SOURCE
        and _position_group(player.position) == GOALIE_POSITION)


def _project_matches(
        context: ProjectionContext,
        match_ids: list[int]) -> list[ProbableLineup]:
    chosen = _selected_matches(context.matches, match_ids)
    if chosen.empty:
        logger.warning("Predictable match ids are missing from history")
        return []
    lineups: list[ProbableLineup] = []
    for row in chosen.itertuples(index=False):
        moment = _as_naive(row.game_date)
        match_id = int(row.match_id)
        for team_id in (int(row.home_team), int(row.away_team)):
            lineups.append(build_probable_lineup(
                match_id, team_id, moment, context))
    logger.info("Built %s probable club lineups", len(lineups))
    return lineups


def _project_club(
        context: ProjectionContext,
        match_id: int,
        team_id: int,
        as_of: datetime) -> ProbableLineup:
    moment = _as_naive(as_of)
    roster = _roster_map(context.current_roster, team_id)
    club_games = _club_games(context.game_rosters, team_id, moment)
    recent = _recent_appearances(club_games)
    toi = _mean_toi(context.player_stats, moment)
    elo = _opponent_elo(context, match_id, team_id, moment)
    players = _project_skaters(club_games, roster, recent, toi, team_id)
    players.extend(_project_goalies(
        context, roster, recent, team_id, moment, elo))
    logger.info(
        "Probable lineup for match %s team %s has %s players",
        match_id,
        team_id,
        len(players))
    return ProbableLineup(
        match_id=match_id,
        team_id=team_id,
        players=players)


def _project_skaters(
        club_games: pd.DataFrame,
        roster: dict[int, _RosterPlayer],
        recent: list[set[int]],
        toi: dict[int, float],
        team_id: int) -> list[ProbableLineupPlayer]:
    last = _last_game(club_games)
    if last.empty:
        # Cały roster to nie skład meczowy. Pusto zostawia typową siłę.
        logger.warning(
            "Team %s has no previous game; leaving skaters empty",
            team_id)
        return []
    kept: list[ProbableLineupPlayer] = []
    gaps: list[tuple[str, int | None]] = []
    used: set[int] = set()
    for row in last.itertuples(index=False):
        _collect_skater(row, roster, recent, kept, gaps, used)
    kept.extend(_fill_gaps(gaps, roster, used, recent, toi, team_id))
    return kept


def _collect_skater(
        row: object,
        roster: dict[int, _RosterPlayer],
        recent: list[set[int]],
        kept: list[ProbableLineupPlayer],
        gaps: list[tuple[str, int | None]],
        used: set[int]) -> None:
    position = _text(getattr(row, "position", None))
    group = _position_group(position)
    if position is None or group is None or group == GOALIE_POSITION:
        return
    player_id = _whole(getattr(row, "player_id", None))
    line = _whole(getattr(row, "line", None))
    if player_id is None:
        return
    entry = roster.get(player_id)
    if entry is None or entry.injured:
        gaps.append((position, line))
        return
    used.add(player_id)
    kept.append(_skater_player(entry, position, line, recent))


def _fill_gaps(
        gaps: list[tuple[str, int | None]],
        roster: dict[int, _RosterPlayer],
        used: set[int],
        recent: list[set[int]],
        toi: dict[int, float],
        team_id: int) -> list[ProbableLineupPlayer]:
    filled: list[ProbableLineupPlayer] = []
    ordered = sorted(gaps, key=_gap_sort_key)
    for position, line in ordered:
        group = _position_group(position)
        choice = _best_replacement(roster, used, toi, group)
        if choice is None:
            logger.warning(
                "No healthy %s replacement for team %s line %s",
                position,
                team_id,
                line)
            continue
        used.add(choice.player_id)
        filled.append(_skater_player(choice, position, line, recent))
    return filled


def _project_goalies(
        context: ProjectionContext,
        roster: dict[int, _RosterPlayer],
        recent: list[set[int]],
        team_id: int,
        as_of: datetime,
        opponent_elo: float) -> list[ProbableLineupPlayer]:
    healthy = [
        entry
        for entry in roster.values()
        if not entry.injured
        and _position_group(entry.position) == GOALIE_POSITION]
    if not healthy:
        logger.warning("Team %s has no healthy goalie", team_id)
        return []
    ordered = sorted(healthy, key=lambda entry: entry.player_id)
    history = GoalieStartHistory.from_starts(
        _starts_before(context.goalie_starts, as_of))
    features = pd.DataFrame([
        history.feature_row(
            team_id, entry.player_id, as_of, opponent_elo)
        for entry in ordered])
    probabilities = context.goalie_model.predict_proba(features)
    starter = _starter_index(probabilities)
    return [
        _goalie_player(entry, recent, probabilities[index], index == starter)
        for index, entry in enumerate(ordered)]


def _skater_player(
        entry: _RosterPlayer,
        position: str,
        line: int | None,
        recent: list[set[int]]) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=entry.player_id,
        position=position,
        line=line,
        pp_unit=entry.pp_unit,
        is_starting_goalie=None,
        confidence=_appearance_share(entry.player_id, recent),
        source=_MODEL_SOURCE,
        start_probability=None)


def _goalie_player(
        entry: _RosterPlayer,
        recent: list[set[int]],
        probability: float,
        starts: bool) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=entry.player_id,
        position=GOALIE_POSITION,
        line=1 if starts else 2,
        pp_unit=entry.pp_unit,
        is_starting_goalie=1 if starts else 0,
        confidence=_appearance_share(entry.player_id, recent),
        source=_MODEL_SOURCE,
        start_probability=float(probability))


def _best_replacement(
        roster: dict[int, _RosterPlayer],
        used: set[int],
        toi: dict[int, float],
        group: str | None) -> _RosterPlayer | None:
    if group is None or group == GOALIE_POSITION:
        return None
    choices = [
        entry
        for entry in roster.values()
        if entry.player_id not in used
        and not entry.injured
        and _position_group(entry.position) == group]
    if not choices:
        return None
    choices.sort(key=lambda entry: (
        -toi.get(entry.player_id, 0.0),
        entry.player_id))
    return choices[0]


def _gap_sort_key(gap: tuple[str, int | None]) -> tuple[int, str]:
    line = gap[1]
    return (99 if line is None else line, gap[0])


def _appearance_share(player_id: int, recent: list[set[int]]) -> float:
    if not recent:
        return 0.0
    played = sum(1 for game in recent if player_id in game)
    return played / len(recent)


def _opponent_elo(
        context: ProjectionContext,
        match_id: int,
        team_id: int,
        as_of: datetime) -> float:
    try:
        return _elo_against(
            context.matches,
            context.ratings,
            match_id,
            team_id,
            as_of)
    except ValueError as exc:
        logger.warning(
            "Opponent Elo unavailable for match %s: %s",
            match_id,
            exc)
        return HOCKEY_ELO_INITIAL


def _elo_against(
        matches: pd.DataFrame,
        ratings: HockeyTeamRatingState,
        match_id: int,
        team_id: int,
        as_of: datetime) -> float:
    row = _match_row(matches, match_id)
    home_team = int(row["home_team"])
    away_team = int(row["away_team"])
    if team_id not in (home_team, away_team):
        raise ValueError(
            f"Team {team_id} does not play match {match_id}")
    season = _whole(row["season"])
    if season is None:
        season = 0
    snapshot = ratings.snapshot(home_team, away_team, season, as_of)
    if team_id == home_team:
        return float(snapshot["away_elo"])
    return float(snapshot["home_elo"])


def _starter_index(probabilities: object) -> int:
    values = [float(item) for item in list(probabilities)]
    best = 0
    for index, value in enumerate(values):
        if value > values[best]:
            best = index
    return best


def _context_for_match(match_id: int) -> ProjectionContext:
    return _load_league_context(_league_id(match_id))


def _load_league_context(league_id: int) -> ProjectionContext:
    matches = fetch_hockey_matches(league_id)
    rosters = fetch_hockey_match_rosters(league_id)
    return ProjectionContext(
        matches=matches,
        game_rosters=rosters,
        current_roster=_read_sql(_CURRENT_ROSTER_QUERY, ()),
        player_stats=fetch_hockey_player_stats(league_id),
        goalie_model=_load_goalie_model(),
        goalie_starts=_goalie_start_rows(rosters),
        ratings=_replay_ratings(matches))


def _load_goalie_model() -> GoalieStartModel:
    run = load_goalie_start_run(_GOALIE_CONFIG)
    model = load_model_artifact(run.artifact_dir)
    if not isinstance(model, GoalieStartModel):
        raise TypeError(
            "Goalie start artifact is not a GoalieStartModel")
    return model


def _replay_ratings(matches: pd.DataFrame) -> HockeyTeamRatingState:
    state = HockeyTeamRatingState()
    ready = _finished_matches(matches)
    if ready.empty:
        return state
    ready = ready.sort_values(["game_date", "match_id"])
    grouped = ready.groupby("game_date", sort=False)
    for _game_date, group in grouped:
        rows = list(group.itertuples(index=False))
        for row in rows:
            state.snapshot(
                int(row.home_team),
                int(row.away_team),
                int(row.season),
                row.game_date)
        for row in rows:
            _commit_finished(state, row)
    return state


def _commit_finished(state: HockeyTeamRatingState, row: object) -> None:
    home_goals = _whole(getattr(row, "home_team_goals", None))
    away_goals = _whole(getattr(row, "away_team_goals", None))
    if home_goals is None or away_goals is None:
        return
    state.commit(
        home_id=int(row.home_team),
        away_id=int(row.away_team),
        home_goals=home_goals,
        away_goals=away_goals,
        home_sog=_whole(getattr(row, "home_team_sog", None)),
        away_sog=_whole(getattr(row, "away_team_sog", None)),
        home_saves=_whole(getattr(row, "home_team_saves", None)),
        away_saves=_whole(getattr(row, "away_team_saves", None)),
        home_empty_net=_count(getattr(row, "home_team_en", None)),
        away_empty_net=_count(getattr(row, "away_team_en", None)),
        ot_winner=_whole(getattr(row, "ot_winner", None)),
        so_winner=_whole(getattr(row, "so_winner", None)))


def _finished_matches(matches: pd.DataFrame) -> pd.DataFrame:
    if matches.empty or "result" not in matches.columns:
        return matches.iloc[0:0]
    result = matches["result"].astype(str)
    ready = matches.loc[result.isin(_FINISHED_RESULTS)].copy()
    if ready.empty:
        return ready
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    if "home_team_goals" not in ready.columns:
        return ready.iloc[0:0]
    ready = ready.loc[ready["home_team_goals"].notna()]
    return ready.loc[ready["away_team_goals"].notna()]


def _goalie_start_rows(rosters: pd.DataFrame) -> pd.DataFrame:
    columns = ["team_id", "player_id", "game_date"]
    if rosters.empty:
        return pd.DataFrame(columns=columns)
    position = rosters["position"].astype(str).str.strip().str.upper()
    line = pd.to_numeric(rosters["line"], errors="coerce")
    starters = rosters.loc[(position == GOALIE_POSITION) & (line == 1)]
    if starters.empty:
        return pd.DataFrame(columns=columns)
    return starters.loc[:, columns].copy()


def _selected_matches(
        matches: pd.DataFrame,
        match_ids: list[int]) -> pd.DataFrame:
    if matches.empty:
        return matches
    wanted = {int(match_id) for match_id in match_ids}
    chosen = matches.loc[
        matches["match_id"].astype(int).isin(wanted)].copy()
    if chosen.empty:
        return chosen
    chosen["game_date"] = pd.to_datetime(chosen["game_date"])
    return chosen.sort_values(["game_date", "match_id"])


def _roster_map(
        frame: pd.DataFrame,
        team_id: int) -> dict[int, _RosterPlayer]:
    if frame.empty:
        return {}
    club = frame.loc[frame["team_id"].astype(int) == int(team_id)]
    mapping: dict[int, _RosterPlayer] = {}
    for row in club.itertuples(index=False):
        player_id = _whole(getattr(row, "player_id", None))
        if player_id is None:
            continue
        mapping[player_id] = _RosterPlayer(
            player_id=player_id,
            position=_text(getattr(row, "position", None)) or "",
            line=_whole(getattr(row, "line", None)),
            pp_unit=_whole(getattr(row, "pp_unit", None)),
            injured=_is_injured(getattr(row, "is_injured", None)))
    return mapping


def _club_games(
        rosters: pd.DataFrame,
        team_id: int,
        as_of: datetime) -> pd.DataFrame:
    if rosters.empty:
        return rosters
    club = rosters.loc[rosters["team_id"].astype(int) == int(team_id)]
    if club.empty or "game_date" not in club.columns:
        return club.iloc[0:0]
    dates = pd.to_datetime(club["game_date"])
    return club.loc[dates < pd.Timestamp(as_of)].copy()


def _last_game(club_games: pd.DataFrame) -> pd.DataFrame:
    if club_games.empty:
        return club_games
    ordered = club_games.sort_values(["game_date", "match_id"])
    last_match = int(ordered.iloc[-1]["match_id"])
    return ordered.loc[ordered["match_id"].astype(int) == last_match]


def _recent_appearances(club_games: pd.DataFrame) -> list[set[int]]:
    if club_games.empty:
        return []
    ordered = club_games.sort_values(["game_date", "match_id"])
    match_ids: list[int] = []
    for match_id in ordered["match_id"].astype(int):
        if not match_ids or match_ids[-1] != int(match_id):
            match_ids.append(int(match_id))
    window = match_ids[-_CONFIDENCE_GAMES:]
    appearances: list[set[int]] = []
    for match_id in window:
        rows = ordered.loc[ordered["match_id"].astype(int) == match_id]
        appearances.append({
            int(player_id)
            for player_id in rows["player_id"].astype(int)})
    return appearances


def _mean_toi(stats: pd.DataFrame, as_of: datetime) -> dict[int, float]:
    if stats.empty or "toi_seconds" not in stats.columns:
        return {}
    frame = stats.copy()
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    prior = frame.loc[frame["game_date"] < pd.Timestamp(as_of)]
    seconds = pd.to_numeric(prior["toi_seconds"], errors="coerce")
    prior = prior.loc[seconds.notna() & (seconds > 0)].copy()
    if prior.empty:
        return {}
    prior["toi_seconds"] = seconds.loc[prior.index]
    means = prior.groupby("player_id")["toi_seconds"].mean()
    return {
        int(player_id): float(value)
        for player_id, value in means.items()}


def _starts_before(
        starts: pd.DataFrame,
        as_of: datetime) -> pd.DataFrame:
    if starts.empty:
        return starts
    dates = pd.to_datetime(starts["game_date"])
    return starts.loc[dates < pd.Timestamp(as_of)].copy()


def _position_group(position: str | None) -> str | None:
    if position is None:
        return None
    if position in FORWARD_POSITIONS:
        return _FORWARD_GROUP
    if position in DEFENSE_POSITIONS:
        return _DEFENSE_GROUP
    if position == GOALIE_POSITION:
        return GOALIE_POSITION
    return None


def _match_row(matches: pd.DataFrame, match_id: int) -> pd.Series:
    rows = matches.loc[matches["match_id"].astype(int) == int(match_id)]
    if rows.empty:
        raise ValueError(
            f"Match {match_id} is not in the projection context")
    return rows.iloc[0]


def _fetch_rows(match_id: int, team_id: int) -> pd.DataFrame:
    frame = _read_sql(_LINEUP_QUERY, (match_id, team_id))
    logger.info(
        "Fetched %s probable lineup rows for match %s team %s",
        len(frame),
        match_id,
        team_id)
    return frame


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params or None)


def _rows_for_stage(frame: pd.DataFrame, stage: str) -> pd.DataFrame:
    if frame.empty or "source" not in frame.columns:
        return frame.iloc[0:0]
    sources = frame["source"].astype(str)
    if stage == _FINAL_STAGE:
        return frame.loc[sources == "CONFIRMED"]
    if stage != _INITIAL_STAGE:
        return frame.iloc[0:0]
    ranked = sources.map(lambda source: _SOURCE_RANK.get(source, 99))
    best = int(ranked.min())
    if best > max(_SOURCE_RANK.values()):
        return frame.iloc[0:0]
    return frame.loc[ranked == best]


def _player_from_row(row: object) -> ProbableLineupPlayer | None:
    player_id = _whole(getattr(row, "player_id", None))
    position = _text(getattr(row, "position", None))
    if player_id is None or position is None:
        return None
    source = getattr(row, "source", None)
    if not isinstance(source, str) or source not in _SOURCE_RANK:
        return None
    return ProbableLineupPlayer(
        player_id=player_id,
        position=position,
        line=_whole(getattr(row, "line", None)),
        pp_unit=_whole(getattr(row, "pp_unit", None)),
        is_starting_goalie=_whole(
            getattr(row, "is_starting_goalie", None)),
        confidence=_finite(getattr(row, "confidence", None)),
        source=source,
        start_probability=None)


def _is_injured(value: object) -> bool:
    number = _whole(value)
    return number == 1


def _count(value: object) -> int:
    number = _whole(value)
    if number is None:
        return 0
    return number


def _text(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    text = str(value).strip().upper()
    if text == "" or text == "NONE" or text == "NAN":
        return None
    return text


def _as_naive(value: object) -> datetime:
    moment = pd.Timestamp(value)
    if pd.isna(moment):
        raise ValueError("game_date is missing")
    converted = moment.to_pydatetime()
    if converted.tzinfo is not None:
        return converted.replace(tzinfo=None)
    return converted


def _whole(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not number.is_integer():
        return None
    return int(number)


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number
