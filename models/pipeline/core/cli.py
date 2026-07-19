"""Shared CLI entrypoint for all batch ML models."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import validate_events
from models.pipeline.persistence.match_assessment_writer import (
    write_match_assessment)
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


def run_train(config_path: Path) -> dict[str, Any]:
    config = load_model_config(config_path)
    validate_events(config)
    report = train(config)
    return _result_to_dict(report)


def run_evaluate(config_path: Path) -> dict[str, Any]:
    config = load_model_config(config_path)
    validate_events(config)
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
        else:
            parser.error(f"Unknown command: {args.command}")
    except Exception as exc:
        logger.error("Command failed: %s", exc)
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "result": payload}, default=str, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
