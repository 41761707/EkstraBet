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
from typing import Any, Sequence

import numpy as np
import pandas as pd

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
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
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
    prediction = predictor.predict_pair(matchup)
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
    raw_matchups = _load_batch_matchups(args)
    matchups = [MatchupInput.model_validate(item) for item in raw_matchups]
    predictor = _future_predictor(args)
    results: list[dict[str, Any]] = []
    skipped = 0
    for matchup in matchups:
        try:
            prediction = predictor.predict_pair(matchup)
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
