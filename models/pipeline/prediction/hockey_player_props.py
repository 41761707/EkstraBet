"""Score beta skater props for the next predictable NHL matches.

There is no ``--stage`` flag yet. Lineups are resolved as ``initial``
(confirmed, then external, then model). SZP-249 adds the stage flag.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

import pandas as pd

from backend.config import REPO_ROOT
from models.pipeline.core.artifacts import load_model_artifact
from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import resolve_event_map
from models.pipeline.core.registry import resolve_model_id
from models.pipeline.data.hockey_history_repository import fetch_hockey_matches
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.data.hockey_history_repository import fetch_team_arenas
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.player_features import (
    PLAYER_PROP_FEATURE_COLUMNS)
from models.pipeline.features.hockey.player_features import PlayerPropMemory
from models.pipeline.features.hockey.player_features import (
    prepare_player_prop_memory)
from models.pipeline.labels.hockey_player_props import LINES_PER_SKATER
from models.pipeline.lineups.hockey_probable_lineup import (
    resolve_lineup_for_stage)
from models.pipeline.persistence.player_prediction_writer import (
    PlayerPredictionRow)
from models.pipeline.persistence.player_prediction_writer import (
    build_player_prediction_rows)
from models.pipeline.persistence.player_prediction_writer import (
    write_player_predictions)
from models.pipeline.training.hockey_player_props_trainer import (
    TRAINER_NAME)
from models.pipeline.training.hockey_player_props_trainer import (
    HockeyPlayerPropsModel)


logger = logging.getLogger(__name__)

INITIAL_STAGE = "initial"
PROPS_PREDICTION_CONFIG = (
    REPO_ROOT / "models" / "configs" / "prediction"
    / "hockey_player_props_v1.json")


def predict_hockey_props(
        league_id: int,
        match_ids: list[int],
        write_db: bool) -> dict[str, object]:
    """Score dressed skaters. Omit ``write_db`` for a dry-run."""
    report: dict[str, object] = {
        "league_id": int(league_id),
        "match_ids": list(match_ids),
        "dry_run": not write_db,
        "lines_per_skater": LINES_PER_SKATER,
        "skaters": 0,
        "predictions": 0,
        "written": 0,
        "matches": []}
    if not match_ids:
        logger.warning(
            "No predictable hockey matches for league %s", league_id)
        return report
    config = load_model_config(PROPS_PREDICTION_CONFIG)
    if config.trainer != TRAINER_NAME:
        raise ValueError(
            f"Player props config must use trainer {TRAINER_NAME}")
    model = _load_model(config.artifact_dir)
    model_id = resolve_model_id(config.model_name)
    event_ids = resolve_event_map(config.events)
    memory, fixtures = _memory_and_fixtures(league_id, match_ids)
    scored = _score_matches(
        model,
        memory,
        fixtures,
        model_id,
        event_ids,
        write_db)
    report["model_name"] = config.model_name
    report["model_id"] = model_id
    report["matches"] = scored
    report["skaters"] = sum(int(item["skaters"]) for item in scored)
    report["predictions"] = sum(
        int(item["predictions"]) for item in scored)
    report["written"] = sum(int(item["written"]) for item in scored)
    return report


def rows_for_match(
        model: HockeyPlayerPropsModel,
        memory: PlayerPropMemory,
        match_id: int,
        home_team: int,
        away_team: int,
        game_date: datetime,
        season: int,
        home_lineup: ProbableLineup | None,
        away_lineup: ProbableLineup | None,
        model_id: int,
        event_ids: dict[str, int]) -> list[PlayerPredictionRow]:
    """Return seven rows for every skater slot in the two lineups."""
    context = memory.prematch(
        match_id, home_team, away_team, season, game_date)
    home_save = _lineup_save(memory, home_lineup, game_date)
    away_save = _lineup_save(memory, away_lineup, game_date)
    rows: list[PlayerPredictionRow] = []
    rows.extend(_club_rows(
        model, memory, context, home_lineup, True, away_save,
        match_id, season, game_date, model_id, event_ids))
    rows.extend(_club_rows(
        model, memory, context, away_lineup, False, home_save,
        match_id, season, game_date, model_id, event_ids))
    return rows


def _score_matches(
        model: HockeyPlayerPropsModel,
        memory: PlayerPropMemory,
        fixtures: pd.DataFrame,
        model_id: int,
        event_ids: dict[str, int],
        write_db: bool) -> list[dict[str, object]]:
    scored: list[dict[str, object]] = []
    for fixture in fixtures.itertuples(index=False):
        moment = _naive_datetime(fixture.game_date)
        season = _optional_int(fixture.season)
        if moment is None or season is None:
            logger.warning(
                "Skipping hockey props for match %s without date or season",
                int(fixture.match_id))
            continue
        home = resolve_lineup_for_stage(
            int(fixture.match_id), int(fixture.home_team), INITIAL_STAGE)
        away = resolve_lineup_for_stage(
            int(fixture.match_id), int(fixture.away_team), INITIAL_STAGE)
        _warn_missing_lineup(int(fixture.match_id), home, away)
        try:
            rows = rows_for_match(
                model,
                memory,
                int(fixture.match_id),
                int(fixture.home_team),
                int(fixture.away_team),
                moment,
                season,
                home,
                away,
                model_id,
                event_ids)
        except ValueError as exc:
            logger.warning(
                "Could not score props for match %s: %s",
                int(fixture.match_id),
                exc)
            continue
        written = 0
        if write_db and rows:
            written = write_player_predictions(rows)
        skaters = len(rows) // LINES_PER_SKATER
        scored.append({
            "match_id": int(fixture.match_id),
            "skaters": skaters,
            "predictions": len(rows),
            "written": written})
    return scored


def _club_rows(
        model: HockeyPlayerPropsModel,
        memory: PlayerPropMemory,
        context: object,
        lineup: ProbableLineup | None,
        is_home: bool,
        opponent_save: float,
        match_id: int,
        season: int,
        game_date: datetime,
        model_id: int,
        event_ids: dict[str, int]) -> list[PlayerPredictionRow]:
    if lineup is None:
        return []
    rows: list[PlayerPredictionRow] = []
    for player in lineup.players:
        if _is_goalie(player.position):
            continue
        features = memory.skater_features(
            context,
            player,
            int(lineup.team_id),
            is_home,
            opponent_save,
            season,
            game_date)
        if features is None:
            logger.warning(
                "Skipping player %s in match %s without a skater slot",
                player.player_id,
                match_id)
            continue
        rates = _scalar_rates(model, features)
        rows.extend(build_player_prediction_rows(
            match_id,
            int(player.player_id),
            int(lineup.team_id),
            model_id,
            rates,
            event_ids))
    return rows


def _scalar_rates(
        model: HockeyPlayerPropsModel,
        features: dict[str, float]) -> dict[str, float]:
    frame = pd.DataFrame(
        [features], columns=PLAYER_PROP_FEATURE_COLUMNS)
    predicted = model.predict_rates(frame)
    return {
        target: float(values[0])
        for target, values in predicted.items()}


def _memory_and_fixtures(
        league_id: int,
        match_ids: list[int]) -> tuple[PlayerPropMemory, pd.DataFrame]:
    logger.info("Loading hockey history for player props")
    matches = fetch_hockey_matches(league_id)
    memory = prepare_player_prop_memory(
        matches,
        fetch_hockey_match_rosters(league_id),
        fetch_hockey_player_stats(league_id),
        fetch_team_arenas())
    chosen = set(match_ids)
    fixtures = matches.loc[matches["match_id"].isin(chosen)].copy()
    missing = chosen.difference(set(fixtures["match_id"].tolist()))
    for match_id in sorted(missing):
        logger.warning(
            "Predictable hockey match %s is missing from the league",
            match_id)
    fixtures = fixtures.sort_values(["game_date", "match_id"])
    return memory, fixtures.reset_index(drop=True)


def _load_model(artifact_dir: object) -> HockeyPlayerPropsModel:
    model = load_model_artifact(artifact_dir)
    if not isinstance(model, HockeyPlayerPropsModel):
        raise TypeError(
            "Artifact is not a HockeyPlayerPropsModel")
    return model


def _lineup_save(
        memory: PlayerPropMemory,
        lineup: ProbableLineup | None,
        game_date: datetime) -> float:
    if lineup is None:
        return math.nan
    try:
        return memory.goalie_save(list(lineup.players), game_date)
    except ValueError as exc:
        logger.warning(
            "Could not score goalie save for team %s: %s",
            lineup.team_id,
            exc)
        return math.nan


def _warn_missing_lineup(
        match_id: int,
        home: ProbableLineup | None,
        away: ProbableLineup | None) -> None:
    if home is not None and away is not None:
        return
    logger.warning(
        "No probable lineup for match %s side %s; skipping those skaters",
        match_id,
        "both" if home is None and away is None else (
            "home" if home is None else "away"))


def _is_goalie(position: object) -> bool:
    if position is None:
        return False
    return str(position).strip().upper() == "G"


def _naive_datetime(value: object) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _optional_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)
