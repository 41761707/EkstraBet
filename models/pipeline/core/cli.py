"""Shared CLI entrypoint for all batch ML models."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Sequence

import numpy as np
import pandas as pd

from backend.repositories.model_statistics_maintenance_repository import (
    BetGenerationScope)
from backend.services.model_statistics_maintenance_service import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_PREVIEW_LIMIT,
    StatisticsRefreshReport,
    refresh_model_statistics)
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import get_trainer
from models.pipeline.core.registry import resolve_event_map
from models.pipeline.core.registry import resolve_model_id
from models.pipeline.core.registry import validate_events
from models.pipeline.persistence.match_assessment_writer import (
    write_match_assessment)
from models.pipeline.persistence.prediction_writer import (
    map_predictions_to_rows,
    write_predictions)
from models.pipeline.persistence.season_projection_writer import (
    ProjectionRunStatus,
    SeasonProjectionRun,
    compute_artifact_hash,
    fail_projection_run,
    start_projection_run,
    write_projection)
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.data.shared_history_context import (
    build_shared_history_context)
from models.pipeline.prediction.future_events_predictor import (
    FeatureCache)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
from models.pipeline.simulation.config import (
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    SeasonSimulationConfig,
    SimulationMode)
from models.pipeline.simulation.perf_budget import WallClock
from models.pipeline.simulation.perf_budget import peak_rss_mb
from models.pipeline.simulation.season_simulator import (
    DynamicSeasonSimulator)
from models.pipeline.prediction.predictor import (
    predict_batch,
    predict_match,
    predict_season_batch)
from models.pipeline.training.sklearn_trainer import evaluate, train

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to model JSON config")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging")


def _add_future_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--result-config",
        "--result_config",
        dest="result_config",
        type=Path,
        default=None,
        help="Optional result-family config path")
    parser.add_argument(
        "--btts-config",
        "--btts_config",
        dest="btts_config",
        type=Path,
        default=None,
        help="Optional BTTS-family config path")
    parser.add_argument(
        "--goals-config",
        "--goals_config",
        dest="goals_config",
        type=Path,
        default=None,
        help="Optional goals-family config path")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist predictions for inputs carrying match_id")
    parser.add_argument(
        "--select-finals",
        action="store_true",
        help="Persist each family's highest probability as final")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging")


def build_parser() -> argparse.ArgumentParser:
    """Build the shared model runner argument parser."""
    parser = argparse.ArgumentParser(
        prog="model_runner",
        description="EkstraBet shared ML pipeline runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train a model")
    _add_shared_args(train_parser)

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Evaluate a trained model")
    _add_shared_args(evaluate_parser)

    match_parser = subparsers.add_parser(
        "assess-match", help="Assess a single finished match")
    _add_shared_args(match_parser)
    match_parser.add_argument("--match-id", required=True, type=int)
    match_parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist assessment to match_model_assessments")

    batch_parser = subparsers.add_parser(
        "assess-batch", help="Assess matches in batch")
    _add_shared_args(batch_parser)
    batch_parser.add_argument("--season-id", type=int, default=None)
    batch_parser.add_argument(
        "--match-ids",
        type=str,
        default=None,
        help="Comma-separated match ids")
    batch_parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist assessments to match_model_assessments")

    pair_parser = subparsers.add_parser(
        "predict-pair",
        help=(
            "Predict configured future-event families for one pair "
            "(pass any non-empty subset of family configs)"))
    _add_future_config_args(pair_parser)
    pair_parser.add_argument("--home", required=True, type=int)
    pair_parser.add_argument("--away", required=True, type=int)
    pair_parser.add_argument(
        "--as-of", required=True, type=date.fromisoformat)
    pair_parser.add_argument("--league-id", type=int, default=None)
    pair_parser.add_argument("--season-id", type=int, default=None)
    pair_parser.add_argument("--match-id", type=int, default=None)

    future_batch_parser = subparsers.add_parser(
        "predict-batch",
        help=(
            "Predict configured future-event families from a JSON pair list "
            "or upcoming DB matches with result='0' "
            "(pass any non-empty subset of family configs)"))
    _add_future_config_args(future_batch_parser)
    future_batch_parser.add_argument(
        "--pairs-file",
        type=Path,
        help="JSON list containing MatchupInput-compatible objects")
    future_batch_parser.add_argument(
        "--league-id",
        type=int,
        default=None,
        help=(
            "Limit auto-loaded upcoming matches to one league "
            "(ignored when --pairs-file is set)"))
    future_batch_parser.add_argument(
        "--date-from",
        type=date.fromisoformat,
        default=date.today(),
        help="Upcoming batch start date when --pairs-file is omitted")
    future_batch_parser.add_argument(
        "--date-to",
        type=date.fromisoformat,
        default=None,
        help="Exclusive upcoming batch end date")

    refresh_parser = subparsers.add_parser(
        "refresh-statistics",
        help=(
            "Generate model bets (optional scope filters) then settle "
            "all pending final_predictions / priced-market bets"),
        description=(
            "Two-phase maintenance cycle. Scope flags "
            "(--league-id, --season-id, --match-id, --date-from, "
            "--date-to) filter bet generation only. Settlement always "
            "drains every pending final_prediction and priced-market "
            "bet, regardless of those filters."))
    # Wspólny tekst: filtry nie ograniczają settlementu
    bet_gen_scope_help = (
        "Bet-generation filter only; settlement ignores this and "
        "drains all pending rows")
    refresh_parser.add_argument(
        "--league-id",
        type=int,
        default=None,
        help=bet_gen_scope_help)
    refresh_parser.add_argument(
        "--season-id",
        type=int,
        default=None,
        help=bet_gen_scope_help)
    refresh_parser.add_argument(
        "--match-id",
        type=int,
        default=None,
        help=bet_gen_scope_help)
    refresh_parser.add_argument(
        "--date-from",
        type=date.fromisoformat,
        default=None,
        help=(
            "Inclusive match date lower bound for bet generation "
            "(YYYY-MM-DD); settlement ignores date filters"))
    refresh_parser.add_argument(
        "--date-to",
        type=date.fromisoformat,
        default=None,
        help=(
            "Inclusive match date upper bound for bet generation "
            "(YYYY-MM-DD); settlement ignores date filters"))
    refresh_parser.add_argument(
        "--backfill",
        action="store_true",
        help=(
            "Include finished matches in bet generation; requires a scope "
            "filter (--league-id, --season-id, --match-id, or date range)"))
    refresh_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Settlement keyset page size (default: 500)")
    refresh_parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist changes; omit for dry-run")
    refresh_parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Dry-run with sample planned writes in the JSON report; "
            "scope filters also apply to settlement"))
    refresh_parser.add_argument(
        "--preview-limit",
        type=int,
        default=DEFAULT_PREVIEW_LIMIT,
        help=(
            "Max planned-write samples when --preview is set "
            f"(default: {DEFAULT_PREVIEW_LIMIT})"))
    refresh_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging")

    simulate_parser = subparsers.add_parser(
        "simulate-season",
        help=(
            "Run Monte Carlo season-end projection and cache the result "
            "(requires --goals-config)"))
    simulate_parser.add_argument(
        "--goals-config",
        "--goals_config",
        dest="goals_config",
        type=Path,
        required=True,
        help="Goals Poisson config used for lambda inference")
    simulate_parser.add_argument(
        "--league-id",
        required=True,
        type=int,
        help="Football league id")
    simulate_parser.add_argument(
        "--season-id",
        required=True,
        type=int,
        help="Season id")
    simulate_parser.add_argument(
        "--mode",
        required=True,
        choices=[mode.value for mode in SimulationMode],
        help="from_now (fixed played matches) or from_season_start")
    simulate_parser.add_argument(
        "--trials",
        type=int,
        default=DEFAULT_TRIALS,
        help=f"Number of Monte Carlo trials (default: {DEFAULT_TRIALS})")
    simulate_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed (default: {DEFAULT_SEED})")
    simulate_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bar on stderr")
    simulate_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging")
    return parser


def _parse_match_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def _result_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
        return payload
    return dict(result)


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump())
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def run_train(config_path: Path) -> dict[str, Any]:
    config = load_model_config(config_path)
    validate_events(config)
    if isinstance(config, FutureEventsRunConfig):
        report = get_trainer(config.trainer).train(config)
    else:
        report = train(config)
    return _result_to_dict(report)


def run_evaluate(config_path: Path) -> dict[str, Any]:
    config = load_model_config(config_path)
    validate_events(config)
    if isinstance(config, FutureEventsRunConfig):
        report = get_trainer(config.trainer).evaluate(config)
    else:
        report = evaluate(config)
    return _result_to_dict(report)


def run_assess_match(
        config_path: Path,
        match_id: int,
        write_db: bool) -> dict[str, Any]:
    config = load_model_config(config_path)
    validate_events(config)
    result = predict_match(match_id, config)
    if write_db:
        write_match_assessment(result)
    return _result_to_dict(result)


def run_assess_batch(
        config_path: Path,
        season_id: int | None,
        match_ids: list[int],
        write_db: bool) -> list[dict[str, Any]]:
    config = load_model_config(config_path)
    validate_events(config)
    if season_id is not None:
        results = predict_season_batch(season_id, config, write=write_db)
    elif match_ids:
        results = predict_batch(match_ids, config, write=write_db)
    else:
        raise ValueError("assess-batch requires --season-id or --match-ids")
    return [_result_to_dict(item) for item in results]


def _future_predictor(args: argparse.Namespace) -> FutureEventsPredictor:
    if (
            args.result_config is None
            and args.btts_config is None
            and args.goals_config is None):
        raise ValueError(
            "At least one of --result-config, --btts-config, "
            "or --goals-config is required")
    return FutureEventsPredictor.from_config_paths(
        args.result_config,
        args.btts_config,
        args.goals_config)


def _active_future_configs(
        predictor: FutureEventsPredictor) -> list[FutureEventsRunConfig]:
    configs: list[FutureEventsRunConfig] = []
    for config in (
            predictor.result_config,
            predictor.btts_config,
            predictor.goals_config):
        if config is not None:
            configs.append(config)
    return configs


def _build_predict_history_context(
        predictor: FutureEventsPredictor,
        matchups: Sequence[MatchupInput]
        ) -> SharedHistoryContext | None:
    """Fetch finished matches once for the given predict run."""
    if not matchups:
        return None
    configs = _active_future_configs(predictor)
    max_as_of = max(item.as_of_date for item in matchups)
    logger.info("Building shared history...")
    context = build_shared_history_context(
        configs[0].sport_id,
        max_as_of,
        [config.ratings for config in configs])
    logger.info(
        "History ready (%s finished, %s rating timelines)",
        len(context.finished_matches),
        len(context.ratings_by_key or {}))
    return context


def _predict_batch_progress(
        matchups: Sequence[MatchupInput]
        ) -> Iterable[MatchupInput]:
    """Wrap matchups in tqdm on stderr; disable when not a TTY."""
    from tqdm import tqdm

    # JSON wyniku idzie na stdout — pasek nie może mieszać się z kontraktem
    return tqdm(
        matchups,
        desc="predict-batch",
        unit="match",
        file=sys.stderr,
        disable=not sys.stderr.isatty(),
        dynamic_ncols=True,
        bar_format=(
            "{l_bar}{bar}| {n_fmt}/{total_fmt} matches "
            "[{elapsed}<{remaining}, {rate_fmt}]"))


def _persist_future_prediction(
        predictor: FutureEventsPredictor,
        matchup: MatchupInput,
        prediction: dict[str, object],
        select_finals: bool) -> int:
    if matchup.match_id is None:
        raise ValueError("--write-db requires match_id for every pair")
    model_ids: dict[str, int] = {}
    event_ids: dict[str, int] = {}
    if predictor.result_config is not None:
        model_ids["result"] = resolve_model_id(
            predictor.result_config.model_name)
        event_ids.update(resolve_event_map(predictor.result_config.events))
    if predictor.btts_config is not None:
        model_ids["btts"] = resolve_model_id(
            predictor.btts_config.model_name)
        event_ids.update(resolve_event_map(predictor.btts_config.events))
    if predictor.goals_config is not None:
        model_ids["goals_poisson"] = resolve_model_id(
            predictor.goals_config.model_name)
        event_ids.update(resolve_event_map(predictor.goals_config.events))
    rows = map_predictions_to_rows(
        matchup.match_id,
        prediction,
        model_ids,
        event_ids,
        select_finals)
    return write_predictions(rows)


def run_predict_pair(args: argparse.Namespace) -> dict[str, Any]:
    """Run configured future-event artifacts for one matchup."""
    matchup = MatchupInput(
        home_team_id=args.home,
        away_team_id=args.away,
        league_id=args.league_id,
        season_id=args.season_id,
        as_of_date=args.as_of,
        match_id=args.match_id)
    predictor = _future_predictor(args)
    context = _build_predict_history_context(predictor, [matchup])
    prediction = predictor.predict_pair(matchup, context=context)
    written = 0
    if args.write_db:
        written = _persist_future_prediction(
            predictor, matchup, prediction, args.select_finals)
    return {
        "matchup": matchup.model_dump(),
        "predictions": _json_value(prediction),
        "written": written
    }


def run_predict_batch(args: argparse.Namespace) -> dict[str, Any]:
    """Run future-event artifacts; skip matchups that cannot be predicted."""
    from tqdm.contrib.logging import logging_redirect_tqdm

    raw_matchups = _load_batch_matchups(args)
    matchups = [MatchupInput.model_validate(item) for item in raw_matchups]
    predictor = _future_predictor(args)
    context = _build_predict_history_context(predictor, matchups)
    feature_cache: FeatureCache = {}
    results: list[dict[str, Any]] = []
    skipped = 0
    progress = _predict_batch_progress(matchups)
    # skipi na stderr nie mogą nadpisać paska — tqdm.write czyści i odrysowuje
    with logging_redirect_tqdm():
        for matchup in progress:
            try:
                prediction = predictor.predict_pair(
                    matchup, context=context, feature_cache=feature_cache)
            except Exception as exc:
                skipped += 1
                logger.error(
                    "Skipping match_id=%s home=%s away=%s: %s",
                    matchup.match_id,
                    matchup.home_team_id,
                    matchup.away_team_id,
                    exc)
                results.append({
                    "matchup": matchup.model_dump(),
                    "predictions": None,
                    "written": 0,
                    "skipped": True,
                    "error": str(exc)
                })
                continue
            written = 0
            if args.write_db:
                written = _persist_future_prediction(
                    predictor, matchup, prediction, args.select_finals)
            results.append({
                "matchup": matchup.model_dump(),
                "predictions": _json_value(prediction),
                "written": written,
                "skipped": False
            })
    return {
        "processed": len(matchups),
        "predicted": len(matchups) - skipped,
        "skipped": skipped,
        "results": results
    }


def _load_batch_matchups(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.pairs_file is not None:
        with args.pairs_file.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("--pairs-file must contain a JSON list")
        return payload
    from models.pipeline.data.match_history_repository import (
        fetch_upcoming_matches)

    frame = fetch_upcoming_matches(
        1,
        args.date_from,
        args.date_to,
        league_id=args.league_id)
    return [{
        "home_team_id": int(row["home_team"]),
        "away_team_id": int(row["away_team"]),
        "league_id": _optional_int(row.get("league")),
        "season_id": _optional_int(row.get("season")),
        "as_of_date": _as_of_date(row["game_date"]),
        "match_id": int(row["id"])
    } for _, row in frame.iterrows()]


def _as_of_date(value: Any) -> date:
    """Normalize DB kickoff timestamps to calendar dates."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    stamp = pd.Timestamp(value)
    return stamp.date()


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if bool(np.isnan(value)):
            return None
    except TypeError:
        pass
    return int(value)


def run_refresh_statistics(
        args: argparse.Namespace
) -> StatisticsRefreshReport:
    """Generate scoped bets, then settle all pending outcomes."""
    if args.preview and args.write_db:
        raise ValueError("--preview cannot be combined with --write-db")
    if args.preview_limit <= 0:
        raise ValueError("preview_limit must be a positive integer")
    scope = BetGenerationScope(
        league_id=args.league_id,
        season_id=args.season_id,
        match_id=args.match_id,
        date_from=args.date_from,
        date_to=args.date_to,
        backfill=bool(args.backfill))
    dry_run = not bool(args.write_db)
    preview = bool(args.preview)
    # Bez --preview scope dotyczy tylko generate_bets; z --preview
    # settlement też respektuje filtry zakresu
    if preview:
        settlement_note = (
            "settlement uses the same scope filters as bet generation")
    else:
        settlement_note = (
            "settlement drains all pending final_predictions and "
            "priced-market bets (scope filters do not apply)")
    logger.info(
        "refresh-statistics dry_run=%s preview=%s preview_limit=%s "
        "backfill=%s batch_size=%s; bet-generation scope league_id=%s "
        "season_id=%s match_id=%s date_from=%s date_to=%s; %s",
        dry_run,
        preview,
        args.preview_limit,
        scope.backfill,
        args.batch_size,
        scope.league_id,
        scope.season_id,
        scope.match_id,
        scope.date_from,
        scope.date_to,
        settlement_note)
    return refresh_model_statistics(
        scope,
        batch_size=args.batch_size,
        dry_run=dry_run,
        preview=preview,
        preview_limit=args.preview_limit)


def _season_round_progress(
        config: SeasonSimulationConfig,
        *,
        enabled: bool
) -> Callable[[Sequence[int]], Iterable[int]] | None:
    """Return a tqdm wrapper over round numbers, or None when disabled."""
    if not enabled:
        return None

    def _wrap(round_numbers: Sequence[int]) -> Iterable[int]:
        from tqdm import tqdm

        return tqdm(
            round_numbers,
            desc=(
                f"simulate-season L{config.league_id} "
                f"S{config.season_id}"),
            unit="round",
            dynamic_ncols=True,
            file=sys.stderr,
            bar_format=(
                "{l_bar}{bar}| {n_fmt}/{total_fmt} rounds "
                "[{elapsed}<{remaining}, {rate_fmt}]"),
            postfix={
                "mode": config.mode.value,
                "trials": config.n_trials
            })

    return _wrap


def run_simulate_season(args: argparse.Namespace) -> dict[str, Any]:
    """Run season Monte Carlo offline and atomically cache the projection."""
    goals_config = load_model_config(args.goals_config)
    if not isinstance(goals_config, FutureEventsRunConfig):
        raise TypeError("--goals-config must be a future-events config")
    if goals_config.task_type != "goals_poisson":
        raise ValueError("--goals-config must use task_type=goals_poisson")
    mode = SimulationMode(args.mode)
    config = SeasonSimulationConfig(
        league_id=args.league_id,
        season_id=args.season_id,
        mode=mode,
        n_trials=args.trials,
        seed=args.seed)
    artifact_hash = compute_artifact_hash(goals_config.artifact_dir)
    started_at = datetime.utcnow()
    run_id = start_projection_run(SeasonProjectionRun(
        league_id=config.league_id,
        season_id=config.season_id,
        mode=config.mode,
        status=ProjectionRunStatus.RUNNING,
        model_name=goals_config.model_name,
        model_version=goals_config.model_version,
        artifact_hash=artifact_hash,
        n_trials=config.n_trials,
        seed=config.seed,
        fixed_matches=0,
        simulated_matches=0,
        input_fingerprint="",
        started_at=started_at))
    round_progress = _season_round_progress(
        config, enabled=not bool(getattr(args, "no_progress", False)))
    wall_seconds = 0.0
    try:
        predictor = FutureEventsPredictor(goals_config=goals_config)
        with WallClock() as clock:
            result = DynamicSeasonSimulator(predictor).run(
                config, round_progress=round_progress)
        wall_seconds = clock.elapsed
        write_projection(
            result,
            result.input_fingerprint,
            model_name=goals_config.model_name,
            model_version=goals_config.model_version,
            artifact_hash=artifact_hash,
            run_id=run_id,
            started_at=started_at)
    except Exception as exc:
        # fail statusu nie może maskować pierwotnego błędu symulacji
        try:
            fail_projection_run(run_id, str(exc))
        except Exception as fail_exc:
            logger.error(
                "Failed to mark projection run_id=%s as FAILED "
                "after simulation error: %s",
                run_id,
                fail_exc,
                exc_info=True)
        raise
    rss = peak_rss_mb()
    return {
        "run_id": run_id,
        "league_id": config.league_id,
        "season_id": config.season_id,
        "mode": config.mode.value,
        "n_trials": config.n_trials,
        "seed": config.seed,
        "model_name": goals_config.model_name,
        "model_version": goals_config.model_version,
        "artifact_hash": artifact_hash,
        "input_fingerprint": result.input_fingerprint,
        "fixed_matches": result.fixed_matches,
        "simulated_matches": result.simulated_matches,
        "teams": len(result.projections),
        "wall_seconds": round(wall_seconds, 2),
        "peak_rss_mb": (
            None if rss is None else round(rss, 1))
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main used by models/scripts/model_runner.py."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(bool(getattr(args, "verbose", False)))

    try:
        if args.command == "train":
            payload = run_train(args.config)
        elif args.command == "evaluate":
            payload = run_evaluate(args.config)
        elif args.command == "assess-match":
            payload = run_assess_match(
                args.config, args.match_id, args.write_db)
        elif args.command == "assess-batch":
            payload = run_assess_batch(
                args.config,
                args.season_id,
                _parse_match_ids(args.match_ids),
                args.write_db)
        elif args.command == "predict-pair":
            payload = run_predict_pair(args)
        elif args.command == "predict-batch":
            payload = run_predict_batch(args)
        elif args.command == "refresh-statistics":
            payload = run_refresh_statistics(args)
        elif args.command == "simulate-season":
            payload = run_simulate_season(args)
        else:
            parser.error(f"Unknown command: {args.command}")
    except Exception as exc:
        logger.error("Command failed: %s", exc)
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(
        {"ok": True, "result": _json_value(payload)},
        default=str,
        indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
