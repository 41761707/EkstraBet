"""Parser and exit-code tests for publish-coupon-agent."""

from __future__ import annotations

import inspect
import io
import json
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

import pandas as pd
import pytest

from backend.services.coupon_agent_service import CouponAgentServiceError
from backend.services.coupon_agent_service import PublishBatchReport
from backend.services.coupon_agent_service import PublishReport
from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import main
from models.pipeline.core.cli import run_publish_coupon_agent
from models.scripts import model_runner


_AS_OF = datetime(2026, 10, 25, 12, 0)
_FETCH = "backend.services.coupon_agent_service.fetch_candidates"
_ACCOUNT = "backend.services.coupon_agent_service.get_by_username"
_SETS = (
    "backend.services.coupon_agent_service."
    "fetch_coupon_leg_sets_between")
_CREATE = "backend.services.coupon_agent_service.create_coupon_for_user"
_NOW = "backend.services.coupon_agent_service._warsaw_now"
_PUBLISH = "models.pipeline.core.cli.publish_daily"


def _choices() -> dict[str, object]:
    parser = build_parser()
    action = next(
        item
        for item in parser._actions
        if getattr(item, "choices", None))
    return action.choices


def _published(username: str = "agent-kuponowy") -> PublishReport:
    return PublishReport(
        username=username,
        status="published",
        coupon_id=41,
        candidate_count=1,
        skipped_reason=None)


def _frame() -> pd.DataFrame:
    odds = 1.8
    probability = 0.58
    implied = 1.0 / odds
    return pd.DataFrame([{
        "match_id": 10,
        "event_id": 1,
        "model_id": 4,
        "bookmaker_id": 2,
        "odds": odds,
        "model_probability": probability,
        "implied_probability": implied,
        "value_edge_pp": (probability - implied) * 100.0,
        "kickoff": datetime(2026, 10, 26, 18, 0),
        "league_id": 7,
        "league_tier": 1,
        "event_family": "REZULTAT"}])


def test_model_runner_delegates_to_cli_main() -> None:
    assert model_runner.main is main


def test_parser_accepts_publish_coupon_agent_flags() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "publish-coupon-agent",
        "--username",
        "agent-kuponowy",
        "--dry-run",
        "--as-of",
        "2026-10-25T12:00:00"])
    assert args.command == "publish-coupon-agent"
    assert args.username == "agent-kuponowy"
    assert args.publish_all is False
    assert args.dry_run is True
    assert args.as_of == _AS_OF
    assert args.allow_unready is False
    dated = parser.parse_args([
        "publish-coupon-agent",
        "--all",
        "--as-of",
        "2026-10-25"])
    assert dated.username is None
    assert dated.publish_all is True
    assert dated.dry_run is False
    assert dated.as_of == datetime(2026, 10, 25, 0, 0)
    aware = parser.parse_args([
        "publish-coupon-agent",
        "--as-of",
        "2026-10-25T12:00:00+02:00"])
    offset = timezone(timedelta(hours=2))
    assert aware.as_of == datetime(2026, 10, 25, 12, 0, tzinfo=offset)


def test_parser_defaults_publish_every_agent_for_real() -> None:
    args = build_parser().parse_args(["publish-coupon-agent"])
    assert args.username is None
    assert args.publish_all is False
    assert args.dry_run is False
    assert args.as_of is None
    assert args.allow_unready is False


def test_parser_rejects_username_together_with_all() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "publish-coupon-agent",
            "--username",
            "agent-kuponowy",
            "--all"])


def test_parser_rejects_a_bad_as_of() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "publish-coupon-agent",
            "--as-of",
            "not-a-date"])


def test_parser_has_no_database_path_or_jwt_flag() -> None:
    command = _choices()["publish-coupon-agent"]
    dests = {item.dest for item in command._actions}
    assert "database" not in dests
    assert "dsn" not in dests
    assert "jwt" not in dests
    assert "output" not in dests
    help_text = command.format_help()
    assert "get_db_connection()" in help_text
    assert "DB_*" in help_text
    assert "JWT" in help_text
    source = inspect.getsource(run_publish_coupon_agent).lower()
    assert "import jwt" not in source
    assert "pyjwt" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "urllib" not in source


def test_omitted_as_of_uses_the_warsaw_clock() -> None:
    frozen = datetime(2026, 10, 25, 15, 30)
    report = PublishBatchReport(reports=[_published()])
    stdout = io.StringIO()
    with patch(_PUBLISH, return_value=report) as mocked, \
            patch(
                "models.pipeline.core.cli._coupon_agent_now",
                return_value=frozen), \
            redirect_stdout(stdout):
        code = main(["publish-coupon-agent", "--dry-run"])
    assert code == 0
    mocked.assert_called_once_with(
        frozen,
        username=None,
        dry_run=True,
        allow_unready=False)
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is True
    assert payload["result"]["reports"][0]["status"] == "published"


def test_allow_unready_is_forwarded() -> None:
    report = PublishBatchReport(reports=[_published()])
    with patch(_PUBLISH, return_value=report) as mocked, \
            redirect_stdout(io.StringIO()):
        code = main([
            "publish-coupon-agent",
            "--dry-run",
            "--allow-unready"])
    assert code == 0
    assert mocked.call_args.kwargs["dry_run"] is True
    assert mocked.call_args.kwargs["allow_unready"] is True


def test_username_and_all_select_the_service_scope() -> None:
    report = PublishBatchReport(reports=[_published()])
    with patch(_PUBLISH, return_value=report) as mocked, \
            redirect_stdout(io.StringIO()):
        assert main([
            "publish-coupon-agent",
            "--username",
            "agent-kuponowy"]) == 0
        assert main([
            "publish-coupon-agent",
            "--all",
            "--dry-run"]) == 0
    named = mocked.call_args_list[0]
    assert named.args[0].tzinfo is not None
    assert named.kwargs == {
        "username": "agent-kuponowy",
        "dry_run": False,
        "allow_unready": False}
    whole = mocked.call_args_list[1]
    assert whole.kwargs == {
        "username": None,
        "dry_run": True,
        "allow_unready": False}


def test_ok_statuses_exit_zero() -> None:
    report = PublishBatchReport(reports=[
        _published(),
        PublishReport(
            username="second",
            status="already_published",
            coupon_id=None,
            candidate_count=4,
            skipped_reason="Coupon already published for this calendar day"),
        PublishReport(
            username="third",
            status="no_bet",
            coupon_id=None,
            candidate_count=0,
            skipped_reason=None)])
    stdout = io.StringIO()
    with patch(_PUBLISH, return_value=report), redirect_stdout(stdout):
        code = main(["publish-coupon-agent", "--all"])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is True
    assert [item["status"] for item in payload["result"]["reports"]] == [
        "published",
        "already_published",
        "no_bet"]


def test_missing_user_exits_one_and_keeps_every_report(
        caplog: pytest.LogCaptureFixture) -> None:
    report = PublishBatchReport(reports=[
        _published(),
        PublishReport(
            username="other",
            status="missing_user",
            coupon_id=None,
            candidate_count=0,
            skipped_reason="System user other is missing")])
    stdout = io.StringIO()
    with patch(_PUBLISH, return_value=report), \
            caplog.at_level("ERROR"), \
            redirect_stdout(stdout):
        code = main(["publish-coupon-agent", "--all", "--dry-run"])
    assert code == 1
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is False
    assert [item["status"] for item in payload["result"]["reports"]] == [
        "published",
        "missing_user"]
    assert any("username=other" in record.message for record in caplog.records)
    joined = " ".join(record.message for record in caplog.records)
    assert "password" not in joined.lower()


def test_io_error_exits_one_without_a_success_payload() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch(
            _PUBLISH,
            side_effect=RuntimeError("connection refused")), \
            redirect_stdout(stdout), \
            redirect_stderr(stderr):
        code = main(["publish-coupon-agent"])
    assert code == 1
    assert stdout.getvalue() == ""
    payload = json.loads(stderr.getvalue())
    assert payload["ok"] is False
    assert payload["error"] == "connection refused"
    assert "password" not in payload["error"].lower()


def test_named_service_error_exits_one() -> None:
    stderr = io.StringIO()
    message = "System user agent-kuponowy is missing"
    with patch(
            _PUBLISH,
            side_effect=CouponAgentServiceError(message)), \
            redirect_stderr(stderr), \
            redirect_stdout(io.StringIO()):
        code = main([
            "publish-coupon-agent",
            "--username",
            "agent-kuponowy"])
    assert code == 1
    payload = json.loads(stderr.getvalue())
    assert payload["ok"] is False
    assert payload["error"] == message


def _json_documents(raw: str) -> list[dict[str, object]]:
    """Parse JSON values printed one after another."""
    decoder = json.JSONDecoder()
    documents: list[dict[str, object]] = []
    index = 0
    text = raw.strip()
    while index < len(text):
        payload, offset = decoder.raw_decode(text, index)
        documents.append(payload)
        index = offset
        while index < len(text) and text[index].isspace():
            index += 1
    return documents


def test_dry_run_does_not_insert_and_a_real_run_does() -> None:
    account = {"user_id": 9, "username": "agent-kuponowy"}
    stdout = io.StringIO()
    with patch(_FETCH, return_value=_frame()), \
            patch(_ACCOUNT, return_value=account), \
            patch(_SETS, return_value=[]), \
            patch(_NOW, return_value=_AS_OF), \
            patch(_CREATE, return_value={"id": 41}) as create, \
            redirect_stdout(stdout):
        dry_code = main([
            "publish-coupon-agent",
            "--dry-run",
            "--as-of",
            "2026-10-25T12:00:00"])
        assert create.call_count == 0
        write_code = main([
            "publish-coupon-agent",
            "--as-of",
            "2026-10-25T12:00:00"])
    assert dry_code == 0
    assert write_code == 0
    create.assert_called_once()
    # Dwa JSON-y lecą jeden po drugim. Pierwszy jest dry-run.
    first, second = _json_documents(stdout.getvalue())
    assert first["ok"] is True
    assert first["result"]["reports"][0]["coupon_id"] is None
    assert first["result"]["reports"][0]["status"] == "published"
    assert second["result"]["reports"][0]["coupon_id"] == 41
