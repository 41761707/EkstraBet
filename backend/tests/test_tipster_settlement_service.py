"""Unit tests for idempotent tipster coupon settlement."""

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.services.tipster_settlement_service import settle_open_coupons


_REPO = "backend.services.tipster_settlement_service.repo"


def _row(
        *,
        coupon_id: int = 1,
        leg_id: int = 10,
        match_id: int = 100,
        event_id: int = 1,
        event_name: str = "Zwycięstwo gospodarza",
        family: str | None = "REZULTAT",
        result: str | None = "1",
        home_goals: int | None = 2,
        away_goals: int | None = 1,
        stake_amount: object = Decimal("10.00"),
        combined_odds: object = Decimal("1.9000"),
        leg_outcome: int | None = None,
        home_ck: int | None = 5,
        away_ck: int | None = 4
        ) -> dict[str, object]:
    return {
        "leg_id": leg_id,
        "coupon_id": coupon_id,
        "match_id": match_id,
        "leg_outcome": leg_outcome,
        "event_id": event_id,
        "event_name": event_name,
        "family": family,
        "result": result,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_ck": home_ck,
        "away_ck": away_ck,
        "home_fouls": 12,
        "away_fouls": 10,
        "home_yc": 1,
        "away_yc": 1,
        "home_rc": 0,
        "away_rc": 0,
        "home_off": 2,
        "away_off": 1,
        "stake_amount": stake_amount,
        "combined_odds": combined_odds}


def _frame(*rows: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestSettleOpenCoupons(unittest.TestCase):
    """Win/loss, ako, combined AND, retry, and pending boxscore stats."""

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_empty_fetch_writes_nothing(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame()
        counts = settle_open_coupons()
        self.assertEqual(counts, {
            "legs_settled": 0,
            "coupons_settled": 0,
            "legs_skipped": 0})
        mock_write.assert_not_called()
        mock_complete.assert_not_called()

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_single_win_closes_coupon_with_profit(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row())
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        self.assertEqual(counts["coupons_settled"], 1)
        self.assertEqual(counts["legs_skipped"], 0)
        mock_write.assert_called_once_with(10, 1)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_single_loss_closes_coupon_with_negative_stake(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row(result="2", home_goals=0))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        self.assertEqual(counts["coupons_settled"], 1)
        mock_write.assert_called_once_with(10, 0)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_parlay_wins_when_every_leg_wins(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(
            _row(
                combined_odds=Decimal("3.6000"),
                event_id=1,
                match_id=100,
                leg_id=10),
            _row(
                combined_odds=Decimal("3.6000"),
                event_id=1,
                match_id=101,
                leg_id=11))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 2)
        self.assertEqual(counts["coupons_settled"], 1)
        self.assertEqual(
            mock_write.call_args_list,
            [((10, 1),), ((11, 1),)])
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_parlay_loses_when_one_leg_loses(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(
            _row(leg_id=10, match_id=100, combined_odds=Decimal("3.6000")),
            _row(
                leg_id=11,
                match_id=101,
                combined_odds=Decimal("3.6000"),
                result="2",
                home_goals=0,
                away_goals=1))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 2)
        self.assertEqual(counts["coupons_settled"], 1)
        mock_write.assert_any_call(10, 1)
        mock_write.assert_any_call(11, 0)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_combined_and_loses_when_one_event_loses(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        # 1:1 — BTTS wygrywa, Over 2.5 przegrywa; zdarzenie łączone = 0
        mock_fetch.return_value = _frame(
            _row(
                event_id=6,
                event_name="Obie drużyny strzelą",
                family="BTTS",
                result="X",
                home_goals=1,
                away_goals=1,
                combined_odds=Decimal("2.1000")),
            _row(
                event_id=8,
                event_name="Powyżej 2.5 gola",
                family="OU",
                result="X",
                home_goals=1,
                away_goals=1,
                combined_odds=Decimal("2.1000")))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        mock_write.assert_called_once_with(10, 0)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_combined_and_wins_when_every_event_wins(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(
            _row(
                event_id=6,
                event_name="Obie drużyny strzelą",
                family="BTTS",
                combined_odds=Decimal("2.1000")),
            _row(
                event_id=8,
                event_name="Powyżej 2.5 gola",
                family="OU",
                combined_odds=Decimal("2.1000")))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        mock_write.assert_called_once_with(10, 1)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_retry_does_not_rewrite_or_change_profit(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.side_effect = [
            _frame(_row()),
            pd.DataFrame()]
        first = settle_open_coupons()
        second = settle_open_coupons()
        self.assertEqual(first["coupons_settled"], 1)
        self.assertEqual(second, {
            "legs_settled": 0,
            "coupons_settled": 0,
            "legs_skipped": 0})
        mock_write.assert_called_once_with(10, 1)
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_already_settled_legs_only_complete_coupon(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        # crash po write_leg_outcome, przed complete_coupon
        mock_fetch.return_value = _frame(_row(leg_outcome=1))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 0)
        self.assertEqual(counts["coupons_settled"], 1)
        mock_write.assert_not_called()
        mock_complete.assert_called_once_with(1)

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_missing_corner_stats_leave_leg_open(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family=None,
            home_ck=None,
            away_ck=4))
        with self.assertNoLogs(
                "backend.services.tipster_settlement_service",
                level="WARNING"):
            counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 0)
        self.assertEqual(counts["legs_skipped"], 1)
        self.assertEqual(counts["coupons_settled"], 0)
        mock_write.assert_not_called()
        mock_complete.assert_not_called()

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_unsupported_event_logs_and_leaves_leg_open(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row(
            event_id=173,
            event_name="Dokładna liczba goli",
            family="GOALS"))
        with self.assertLogs(
                "backend.services.tipster_settlement_service",
                level="WARNING") as logs:
            counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 0)
        self.assertEqual(counts["legs_skipped"], 1)
        self.assertEqual(counts["coupons_settled"], 0)
        joined = " ".join(logs.output)
        self.assertIn("leg_id=10", joined)
        self.assertIn("event_id=173", joined)
        self.assertIn("Dokładna liczba goli", joined)
        mock_write.assert_not_called()
        mock_complete.assert_not_called()

    @patch(f"{_REPO}.complete_coupon", return_value=0)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_complete_coupon_noop_does_not_count_as_settled(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row(leg_outcome=1))
        counts = settle_open_coupons()
        mock_complete.assert_called_once_with(1)
        self.assertEqual(counts["legs_settled"], 0)
        self.assertEqual(counts["coupons_settled"], 0)
        mock_write.assert_not_called()

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_unfinished_sibling_leg_keeps_coupon_open(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(
            _row(leg_id=10, match_id=100, combined_odds=Decimal("3.6000")),
            _row(
                leg_id=11,
                match_id=101,
                combined_odds=Decimal("3.6000"),
                result=None,
                home_goals=None,
                away_goals=None))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        self.assertEqual(counts["legs_skipped"], 1)
        self.assertEqual(counts["coupons_settled"], 0)
        mock_write.assert_called_once_with(10, 1)
        mock_complete.assert_not_called()

    @patch(f"{_REPO}.complete_coupon", return_value=1)
    @patch(f"{_REPO}.write_leg_outcome")
    @patch(f"{_REPO}.fetch_open_legs_for_finished_matches")
    def test_corners_line_settles_from_boxscore(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock,
            mock_complete: MagicMock) -> None:
        mock_fetch.return_value = _frame(_row(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family=None,
            home_ck=5,
            away_ck=4,
            combined_odds=Decimal("1.7500")))
        counts = settle_open_coupons()
        self.assertEqual(counts["legs_settled"], 1)
        mock_write.assert_called_once_with(10, 1)
        mock_complete.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
