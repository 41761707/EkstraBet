"""Tests for refresh-statistics CLI command."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

import pytest

from backend.repositories.model_statistics_maintenance_repository import (
    BetGenerationScope)
from backend.services.model_statistics_maintenance_service import (
    DEFAULT_BATCH_SIZE,
    StatisticsRefreshReport)
from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import main


def test_parser_accepts_refresh_statistics_flags() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "refresh-statistics",
        "--league-id",
        "1",
        "--season-id",
        "2",
        "--match-id",
        "99",
        "--date-from",
        "2026-07-27",
        "--date-to",
        "2026-07-28",
        "--batch-size",
        "250",
        "--write-db",
        "--verbose"
    ])
    assert args.command == "refresh-statistics"
    assert args.league_id == 1
    assert args.season_id == 2
    assert args.match_id == 99
    assert args.date_from == date(2026, 7, 27)
    assert args.date_to == date(2026, 7, 28)
    assert args.batch_size == 250
    assert args.write_db is True
    assert args.verbose is True


def test_parser_defaults_to_dry_run_and_default_batch_size() -> None:
    parser = build_parser()
    args = parser.parse_args(["refresh-statistics"])
    assert args.write_db is False
    assert args.batch_size == DEFAULT_BATCH_SIZE
    assert args.league_id is None
    assert args.date_from is None


def test_refresh_statistics_help_states_scope_is_bet_generation_only(
) -> None:
    parser = build_parser()
    subparsers_action = next(
        action
        for action in parser._actions
        if getattr(action, "choices", None))
    refresh = subparsers_action.choices["refresh-statistics"]
    help_text = refresh.format_help()
    assert "filter bet generation only" in help_text
    assert "Settlement always" in help_text
    assert "Bet-generation filter only" in help_text
    assert "settlement ignores date filters" in help_text


def test_cli_refresh_statistics_logs_settlement_scope_warning(
        caplog: pytest.LogCaptureFixture
) -> None:
    report = StatisticsRefreshReport(dry_run=True)
    with patch(
            "models.pipeline.core.cli.refresh_model_statistics",
            return_value=report), \
            caplog.at_level("INFO", logger="models.pipeline.core.cli"), \
            redirect_stdout(io.StringIO()):
        code = main(["refresh-statistics", "--match-id", "42"])
    assert code == 0
    assert any(
        "settlement drains all pending" in record.message
        for record in caplog.records)


def test_cli_refresh_statistics_dry_run_prints_json() -> None:
    report = StatisticsRefreshReport(
        read=3,
        generated=1,
        settled=2,
        skipped=0,
        dry_run=True)
    stdout = io.StringIO()
    with patch(
            "models.pipeline.core.cli.refresh_model_statistics",
            return_value=report) as mocked, redirect_stdout(stdout):
        code = main([
            "refresh-statistics",
            "--league-id",
            "1",
            "--date-from",
            "2026-07-27",
            "--date-to",
            "2026-07-28"
        ])
    assert code == 0
    mocked.assert_called_once_with(
        BetGenerationScope(
            league_id=1,
            date_from=date(2026, 7, 27),
            date_to=date(2026, 7, 28)),
        batch_size=DEFAULT_BATCH_SIZE,
        dry_run=True)
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is True
    assert payload["result"]["read"] == 3
    assert payload["result"]["generated"] == 1
    assert payload["result"]["settled"] == 2
    assert payload["result"]["dry_run"] is True


def test_cli_refresh_statistics_write_db_disables_dry_run() -> None:
    report = StatisticsRefreshReport(
        read=1,
        generated=1,
        updated=1,
        settled=1,
        dry_run=False)
    stdout = io.StringIO()
    with patch(
            "models.pipeline.core.cli.refresh_model_statistics",
            return_value=report) as mocked, redirect_stdout(stdout):
        code = main([
            "refresh-statistics",
            "--match-id",
            "42",
            "--batch-size",
            "100",
            "--write-db"
        ])
    assert code == 0
    mocked.assert_called_once_with(
        BetGenerationScope(match_id=42),
        batch_size=100,
        dry_run=False)
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is True
    assert payload["result"]["dry_run"] is False


def test_cli_refresh_statistics_rejects_inverted_dates() -> None:
    stderr = io.StringIO()
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main([
            "refresh-statistics",
            "--date-from",
            "2026-07-28",
            "--date-to",
            "2026-07-27"
        ])
    assert code == 1
    error_payload = json.loads(stderr.getvalue())
    assert error_payload["ok"] is False
    assert "date_to must be >= date_from" in error_payload["error"]


def test_cli_refresh_statistics_propagates_service_failure() -> None:
    stderr = io.StringIO()
    stdout = io.StringIO()
    with patch(
            "models.pipeline.core.cli.refresh_model_statistics",
            side_effect=RuntimeError("db write failed")), \
            redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["refresh-statistics", "--write-db"])
    assert code == 1
    error_payload = json.loads(stderr.getvalue())
    assert error_payload["ok"] is False
    assert "db write failed" in error_payload["error"]


def test_cli_refresh_statistics_rejects_non_positive_batch_size() -> None:
    stderr = io.StringIO()
    with patch(
            "models.pipeline.core.cli.refresh_model_statistics",
            side_effect=ValueError("batch_size must be a positive integer")), \
            redirect_stderr(stderr):
        code = main(["refresh-statistics", "--batch-size", "0"])
    assert code == 1
    error_payload = json.loads(stderr.getvalue())
    assert error_payload["ok"] is False
    assert "batch_size" in error_payload["error"]


def test_cli_refresh_statistics_invalid_date_format_exits() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args([
            "refresh-statistics",
            "--date-from",
            "27-07-2026"
        ])
    assert exc_info.value.code == 2
