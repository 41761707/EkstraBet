"""Daily publication onto configured system accounts."""

from __future__ import annotations

import inspect
import unittest
from contextlib import ExitStack
from contextlib import contextmanager
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Iterator
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.services import coupon_agent_config as agent_config
from backend.services import coupon_agent_service as service
from backend.services.coupon_agent_config import AgentSpec
from backend.services.coupon_agent_config import SelectorConfig
from backend.services.coupon_agent_service import CouponAgentServiceError
from backend.services.coupon_agent_service import publish_daily
from backend.services.tipster_service import TipsterUnprocessableError


_AS_OF = datetime(2026, 10, 25, 12, 0)
_DAY_START = datetime(2026, 10, 25, 0, 0)
_DAY_END = datetime(2026, 10, 26, 0, 0)
_ACCOUNT_ROW = {"user_id": 9, "username": "agent-kuponowy"}
_UNSET = object()

_FETCH = "backend.services.coupon_agent_service.fetch_candidates"
_ACCOUNT = "backend.services.coupon_agent_service.get_by_username"
_SETS = (
    "backend.services.coupon_agent_service."
    "fetch_coupon_leg_sets_between")
_CREATE = "backend.services.coupon_agent_service.create_coupon_for_user"
_AGENTS = "backend.services.coupon_agent_config.AGENTS"
_MAX = "backend.services.coupon_agent_config.MAX_COUPONS_PER_DAY"
_NOW = "backend.services.coupon_agent_service._warsaw_now"
_LOGGER = "backend.services.coupon_agent_service"

_REASON_DAY = "Coupon already published for this calendar day"
_REASON_SAME = "Coupon with the same legs already exists today"


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": 10,
        "event_id": 1,
        "model_id": 4,
        "bookmaker_id": 2,
        "odds": 1.8,
        "model_probability": 0.58,
        "kickoff": datetime(2026, 10, 26, 18, 0),
        "league_id": 7,
        "league_tier": 1,
        "event_family": "REZULTAT"}
    row.update(overrides)
    if "kickoff" not in overrides:
        match_id = int(row["match_id"])  # type: ignore[arg-type]
        row["kickoff"] = (
            datetime(2026, 10, 26, 18, 0)
            + timedelta(minutes=match_id))
    if "implied_probability" not in overrides:
        odds = float(row["odds"])  # type: ignore[arg-type]
        row["implied_probability"] = 1.0 / odds
    if "value_edge_pp" not in overrides:
        probability = float(row["model_probability"])  # type: ignore[arg-type]
        implied = float(row["implied_probability"])  # type: ignore[arg-type]
        row["value_edge_pp"] = (probability - implied) * 100.0
    return row


def _frame(
        rows: list[dict[str, object]] | None = None) -> pd.DataFrame:
    if rows is None:
        rows = [_row()]
    return pd.DataFrame(rows)


@contextmanager
def _patched(
        *,
        frame: pd.DataFrame | None = None,
        sets: list[frozenset[tuple[int, int]]] | None = None,
        account: object = _UNSET,
        account_side_effect: object = None,
        agents: list[AgentSpec] | None = None,
        max_per_day: int | None = None,
        create_return: dict[str, int] | None = None,
        create_side_effect: object = None,
        now: datetime | None = None) -> Iterator[dict[str, MagicMock]]:
    """Patch I/O around one ``publish_daily`` call."""
    if frame is None:
        frame = _frame()
    if sets is None:
        sets = []
    if now is None:
        now = _AS_OF
    if create_return is None and create_side_effect is None:
        create_return = {"id": 41}
    if account_side_effect is not None:
        account_patch = patch(
            _ACCOUNT, side_effect=account_side_effect)
    else:
        value = _ACCOUNT_ROW if account is _UNSET else account
        account_patch = patch(_ACCOUNT, return_value=value)
    if create_side_effect is not None:
        create_patch = patch(_CREATE, side_effect=create_side_effect)
    else:
        create_patch = patch(_CREATE, return_value=create_return)
    with ExitStack() as stack:
        fetch = stack.enter_context(patch(_FETCH, return_value=frame))
        account_mock = stack.enter_context(account_patch)
        sets_mock = stack.enter_context(
            patch(_SETS, return_value=sets))
        create = stack.enter_context(create_patch)
        if agents is not None:
            stack.enter_context(patch(_AGENTS, agents))
        if max_per_day is not None:
            stack.enter_context(patch(_MAX, max_per_day))
        stack.enter_context(patch(_NOW, return_value=now))
        yield {
            "fetch": fetch,
            "account": account_mock,
            "sets": sets_mock,
            "create": create}


class TestAgentConfig(unittest.TestCase):
    """The seed account and the daily cap live in config, not the service."""

    def test_seed_is_one_coupon_for_agent_kuponowy(self) -> None:
        self.assertEqual(agent_config.MAX_COUPONS_PER_DAY, 1)
        self.assertEqual(
            [spec.username for spec in agent_config.AGENTS],
            ["agent-kuponowy"])
        self.assertIsNone(agent_config.AGENTS[0].selector)

    def test_service_does_not_load_a_model(self) -> None:
        source = inspect.getsource(service)
        self.assertNotIn("joblib", source)
        self.assertNotIn("model.joblib", source)


class TestPublishHappyPath(unittest.TestCase):
    """A legal slip is stored through the shared coupon writer."""

    def test_publishes_one_unit_on_single_catalog_events(self) -> None:
        with _patched() as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(len(batch.reports), 1)
        report = batch.reports[0]
        self.assertEqual(report.username, "agent-kuponowy")
        self.assertEqual(report.status, "published")
        self.assertEqual(report.coupon_id, 41)
        self.assertEqual(report.candidate_count, 1)
        self.assertIsNone(report.skipped_reason)
        mocks["account"].assert_called_once_with("agent-kuponowy")
        mocks["fetch"].assert_called_once_with(_AS_OF)
        mocks["sets"].assert_called_once_with(9, _DAY_START, _DAY_END)
        mocks["create"].assert_called_once()
        self.assertEqual(mocks["create"].call_args.args[0], 9)
        request = mocks["create"].call_args.args[1]
        self.assertEqual(request["stake_input_mode"], "units")
        self.assertEqual(request["stake_units"], 1)
        self.assertNotIn("stake_amount", request)
        self.assertEqual(len(request["legs"]), 1)
        leg = request["legs"][0]
        self.assertEqual(leg["match_id"], 10)
        self.assertEqual(leg["event_ids"], [1])
        self.assertEqual(leg["source"], "catalog")
        self.assertEqual(leg["bookmaker_id"], 2)
        self.assertAlmostEqual(leg["odds"], 1.8)

    def test_mysql_float_one_point_zero_one_reaches_the_writer(
            self) -> None:
        raw = 1.0099999904632568
        frame = _frame([
            _row(odds=raw, model_probability=0.99)])
        with _patched(frame=frame) as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(batch.reports[0].status, "published")
        leg = mocks["create"].call_args.args[1]["legs"][0]
        self.assertEqual(leg["odds"], 1.01)

    def test_each_leg_of_a_combined_slip_has_one_event(self) -> None:
        frame = _frame([
            _row(match_id=10, odds=2.0, model_probability=0.55),
            _row(match_id=11, event_id=2, odds=2.0, model_probability=0.55)])
        with _patched(frame=frame) as mocks:
            publish_daily(_AS_OF)
        legs = mocks["create"].call_args.args[1]["legs"]
        self.assertEqual(
            [leg["event_ids"] for leg in legs],
            [[1], [2]])
        for leg in legs:
            self.assertEqual(leg["source"], "catalog")

    def test_selector_override_replaces_stake_units(self) -> None:
        agents = [
            AgentSpec("agent-kuponowy", SelectorConfig(stake_units=2))]
        with _patched(agents=agents) as mocks:
            publish_daily(_AS_OF, username="agent-kuponowy")
        request = mocks["create"].call_args.args[1]
        self.assertEqual(request["stake_units"], 2)

    def test_aware_as_of_uses_warsaw_wall_time(self) -> None:
        """22:30 UTC is still the 25th in Warsaw. The pool uses now."""
        as_of = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc)
        with _patched() as mocks:
            publish_daily(as_of)
        mocks["fetch"].assert_called_once_with(_AS_OF)
        mocks["sets"].assert_called_once_with(9, _DAY_START, _DAY_END)


class TestPublishIdempotency(unittest.TestCase):
    """One coupon per Warsaw day, plus the same leg-set lock."""

    def test_second_publish_does_not_insert_a_different_pool(self) -> None:
        frame = _frame([_row(match_id=50, event_id=3)])
        with _patched(
                frame=frame,
                sets=[frozenset({(99, 8)})]) as mocks:
            batch = publish_daily(_AS_OF)
        report = batch.reports[0]
        self.assertEqual(report.status, "already_published")
        self.assertIsNone(report.coupon_id)
        self.assertEqual(report.candidate_count, 0)
        self.assertEqual(report.skipped_reason, _REASON_DAY)
        mocks["fetch"].assert_not_called()
        mocks["create"].assert_not_called()

    def test_same_leg_set_blocks_when_the_daily_cap_allows_another(
            self) -> None:
        with _patched(
                sets=[frozenset({(10, 1)})],
                max_per_day=2) as mocks:
            batch = publish_daily(_AS_OF)
        report = batch.reports[0]
        self.assertEqual(report.status, "already_published")
        self.assertEqual(report.skipped_reason, _REASON_SAME)
        self.assertEqual(report.candidate_count, 1)
        mocks["fetch"].assert_called_once()
        mocks["create"].assert_not_called()

    def test_same_match_with_another_event_is_not_the_same_set(
            self) -> None:
        with _patched(
                sets=[frozenset({(10, 2)})],
                max_per_day=2) as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(batch.reports[0].status, "published")
        self.assertEqual(batch.reports[0].coupon_id, 41)
        mocks["create"].assert_called_once()

    def test_previous_day_as_of_does_not_insert_on_a_second_call(
            self) -> None:
        """created_at would be now, so a stale as_of must not write."""
        yesterday = datetime(2026, 10, 24, 12, 0)
        with _patched() as mocks:
            for _attempt in range(2):
                with self.assertRaises(CouponAgentServiceError) as ctx:
                    publish_daily(yesterday)
                self.assertEqual(
                    str(ctx.exception),
                    "as_of must fall on the current Warsaw day")
        mocks["create"].assert_not_called()
        mocks["fetch"].assert_not_called()


class TestPublishAgents(unittest.TestCase):
    """Each configured username is an independent account."""

    def test_two_agents_insert_two_coupons_from_one_pool(self) -> None:
        def _account(username: str) -> dict[str, object]:
            if username == "agent-drugi":
                return {"user_id": 10, "username": username}
            return {"user_id": 9, "username": username}

        agents = [
            AgentSpec("agent-kuponowy"),
            AgentSpec("agent-drugi")]
        with _patched(
                agents=agents,
                account_side_effect=_account,
                create_side_effect=[{"id": 41}, {"id": 42}]) as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(
            [report.status for report in batch.reports],
            ["published", "published"])
        self.assertEqual(
            [report.coupon_id for report in batch.reports],
            [41, 42])
        self.assertEqual(mocks["fetch"].call_count, 1)
        self.assertEqual(mocks["account"].call_count, 2)
        self.assertEqual(
            [call.args[0] for call in mocks["sets"].call_args_list],
            [9, 10])
        self.assertEqual(
            [call.args[0] for call in mocks["create"].call_args_list],
            [9, 10])

    def test_batch_skips_a_missing_user_and_publishes_the_rest(
            self) -> None:
        def _account(username: str) -> dict[str, object] | None:
            if username == "agent-kuponowy":
                return None
            return {"user_id": 10, "username": username}

        agents = [
            AgentSpec("agent-kuponowy"),
            AgentSpec("agent-drugi")]
        with _patched(
                agents=agents,
                account_side_effect=_account) as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(batch.reports[0].status, "missing_user")
        self.assertEqual(
            batch.reports[0].skipped_reason,
            "System user agent-kuponowy is missing")
        self.assertEqual(batch.reports[1].status, "published")
        self.assertEqual(batch.reports[1].coupon_id, 41)
        mocks["create"].assert_called_once()
        self.assertEqual(mocks["create"].call_args.args[0], 10)

    def test_named_missing_user_raises_and_does_not_insert(self) -> None:
        with _patched(account=None) as mocks:
            with self.assertRaises(CouponAgentServiceError) as ctx:
                publish_daily(_AS_OF, username="agent-kuponowy")
        self.assertEqual(
            str(ctx.exception),
            "System user agent-kuponowy is missing")
        mocks["create"].assert_not_called()
        mocks["fetch"].assert_not_called()

    def test_unknown_username_raises_before_lookup(self) -> None:
        with _patched() as mocks:
            with self.assertRaises(CouponAgentServiceError) as ctx:
                publish_daily(_AS_OF, username="not-an-agent")
        self.assertEqual(
            str(ctx.exception),
            "Unknown coupon agent not-an-agent")
        mocks["account"].assert_not_called()
        mocks["create"].assert_not_called()


class TestPublishDryRunAndNoBet(unittest.TestCase):
    """Dry-run and an empty legal pool never insert."""

    def test_dry_run_logs_legs_and_does_not_insert(self) -> None:
        with _patched() as mocks:
            with self.assertLogs(_LOGGER, level="INFO") as captured:
                batch = publish_daily(_AS_OF, dry_run=True)
        report = batch.reports[0]
        self.assertEqual(report.status, "published")
        self.assertIsNone(report.coupon_id)
        self.assertEqual(report.candidate_count, 1)
        mocks["create"].assert_not_called()
        text = "\n".join(captured.output)
        self.assertIn("dry_run=True", text)
        self.assertIn("score=", text)
        self.assertIn("10:1@1.8", text)

    def test_empty_pool_is_no_bet(self) -> None:
        with _patched(frame=pd.DataFrame()) as mocks:
            batch = publish_daily(_AS_OF)
        report = batch.reports[0]
        self.assertEqual(report.status, "no_bet")
        self.assertIsNone(report.coupon_id)
        self.assertEqual(report.candidate_count, 0)
        self.assertIsNone(report.skipped_reason)
        mocks["create"].assert_not_called()

    def test_selector_rejection_is_no_bet_without_insert(self) -> None:
        frame = _frame([
            _row(odds=6.0, model_probability=0.50)])
        with _patched(frame=frame) as mocks:
            batch = publish_daily(_AS_OF)
        self.assertEqual(batch.reports[0].status, "no_bet")
        self.assertEqual(batch.reports[0].candidate_count, 1)
        mocks["create"].assert_not_called()

    def test_coupon_writer_errors_propagate(self) -> None:
        error = TipsterUnprocessableError("Odds must be at least 1.01")
        with _patched(create_side_effect=error) as mocks:
            with self.assertRaises(TipsterUnprocessableError) as ctx:
                publish_daily(_AS_OF)
        self.assertIs(ctx.exception, error)
        mocks["create"].assert_called_once()

    def test_as_of_must_be_a_datetime(self) -> None:
        with _patched() as mocks:
            with self.assertRaises(ValueError):
                publish_daily(date(2026, 10, 25))  # type: ignore[arg-type]
        mocks["fetch"].assert_not_called()
        mocks["account"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
