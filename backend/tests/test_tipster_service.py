"""Unit tests for tipster onboarding, stake and coupon rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.services.tipster_service import TipsterConflictError
from backend.services.tipster_service import TipsterForbiddenError
from backend.services.tipster_service import TipsterNotFoundError
from backend.services.tipster_service import TipsterUnprocessableError
from backend.services.tipster_service import TipsterValidationError
from backend.services.tipster_service import _combined_odds
from backend.services.tipster_service import _resolve_stake
from backend.services.tipster_service import configure_bankroll
from backend.services.tipster_service import create_coupon
from backend.services.tipster_service import create_coupon_for_user
from backend.services.tipster_service import get_catalog_matches
from backend.services.tipster_service import get_leaderboard
from backend.services.tipster_service import get_my_bankroll
from backend.services.tipster_service import get_my_coupons
from backend.services.tipster_service import get_my_performance
from backend.services.tipster_service import get_public_profile
from backend.services.tipster_service import get_suggested_catalog_odds
from backend.services.tipster_service import top_up
from backend.services.tipster_service import top_up_for_user


_REPO = "backend.services.tipster_service.repo"
_USERS = "backend.services.tipster_service.user_repository"

_USER = {
    "id": 7,
    "username": "alice",
    "display_name": "Alice",
    "is_active": 1,
    "is_system": 0
}
_SYSTEM_USER = {
    "id": 9,
    "username": "agent",
    "display_name": "Agent",
    "is_active": 1,
    "is_system": 1
}
_STRANGER = {
    "id": 8,
    "username": "bob",
    "display_name": "Bob",
    "is_active": 1,
    "is_system": 0
}

_BANKROLL = {
    "user_id": 7,
    "currency": "PLN",
    "initial_capital": 100.0,
    "unit_size": 5.0,
    "current_balance": -50.0,
    "open_stake": 0.0,
    "realized_pnl": -150.0
}
_PUBLIC_BANKROLL = {
    "currency": "PLN",
    "current_balance": -50.0
}

_OPEN_MATCHES = [
    {"id": match_id, "league_id": 1}
    for match_id in range(100, 110)]
_SETTLEABLE_EVENTS = [
    {"id": 1, "name": "Zwycięstwo gospodarza"},
    {"id": 6, "name": "Obie drużyny strzelą"},
    {"id": 12, "name": "Powyżej 2.5 goli"},
    {"id": 173, "name": "Dokładna liczba goli"}]
_CATALOG = {
    "matches": _OPEN_MATCHES,
    "events": _SETTLEABLE_EVENTS
}


def _leg(
        match_id: int = 100,
        event_ids: list[int] | None = None,
        odds: float = 1.85,
        source: str = "catalog",
        bookmaker_id: object = 1) -> dict[str, object]:
    return {
        "match_id": match_id,
        "event_ids": event_ids or [1],
        "odds": odds,
        "source": source,
        "bookmaker_id": bookmaker_id
    }


def _request(
        *,
        mode: str = "units",
        stake_amount: float | None = None,
        stake_units: float | None = 2.0,
        legs: list[dict[str, object]] | None = None
        ) -> dict[str, object]:
    payload: dict[str, object] = {
        "stake_input_mode": mode,
        "legs": legs or [_leg()]}
    if stake_amount is not None:
        payload["stake_amount"] = stake_amount
    if stake_units is not None:
        payload["stake_units"] = stake_units
    return payload


class TestResolveStakeAndCombinedOdds(unittest.TestCase):
    """Unit conversion and combined-leg price product."""

    def test_units_times_unit_size(self) -> None:
        self.assertEqual(_resolve_stake("units", None, 2, 5), 10.0)

    def test_money_mode_keeps_amount(self) -> None:
        self.assertEqual(_resolve_stake("money", 12.5, None, 5), 12.5)

    def test_rejects_zero_stake(self) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            _resolve_stake("money", 0, None, 5)
        self.assertEqual(str(ctx.exception), "Stake must be greater than 0")

    def test_money_sub_cent_rounds_to_zero_and_is_rejected(self) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            _resolve_stake("money", 0.001, None, 5)
        self.assertEqual(str(ctx.exception), "Stake must be greater than 0")

    def test_units_sub_cent_result_is_rejected(self) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            _resolve_stake("units", None, 0.001, 0.01)
        self.assertEqual(str(ctx.exception), "Stake must be greater than 0")

    def test_combined_odds_uses_leg_prices_not_events(self) -> None:
        product = _combined_odds([
            {"odds": 1.85, "event_ids": [6, 12]},
            {"odds": 2.0, "event_ids": [1]}])
        self.assertAlmostEqual(product, 3.7)


class TestGetMyBankroll(unittest.TestCase):
    """GET /me/bankroll maps a missing row to 404."""

    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_returns_configured_bankroll(
            self, mock_get: MagicMock) -> None:
        self.assertEqual(get_my_bankroll(_USER), _BANKROLL)
        mock_get.assert_called_once_with(7, apply_tax=False)

    @patch(f"{_REPO}.get_bankroll", return_value=None)
    def test_missing_bankroll_is_not_found(
            self, mock_get: MagicMock) -> None:
        with self.assertRaises(TipsterNotFoundError) as ctx:
            get_my_bankroll(_USER)
        self.assertEqual(str(ctx.exception), "Bankroll not configured")
        mock_get.assert_called_once_with(7, apply_tax=False)


class TestConfigureBankroll(unittest.TestCase):
    """Onboarding rejects system users and currency changes after volume."""

    @patch(f"{_REPO}.get_bankroll")
    @patch(f"{_REPO}.upsert_bankroll")
    def test_onboarding_upserts_then_reads_back(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock) -> None:
        mock_get.side_effect = [None, _BANKROLL]
        document = configure_bankroll(_USER, "pln", 100, 5)
        self.assertEqual(document, _BANKROLL)
        mock_upsert.assert_called_once_with(7, "PLN", 100.0, 5.0)

    @patch(f"{_REPO}.upsert_bankroll")
    def test_rejects_system_user(
            self, mock_upsert: MagicMock) -> None:
        with self.assertRaises(TipsterForbiddenError) as ctx:
            configure_bankroll(_SYSTEM_USER, "PLN", 100, 5)
        self.assertEqual(
            str(ctx.exception),
            "System accounts cannot use /me mutations")
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.upsert_bankroll")
    def test_rejects_non_positive_capital(
            self, mock_upsert: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            configure_bankroll(_USER, "PLN", 0, 5)
        self.assertEqual(
            str(ctx.exception),
            "initial_capital must be greater than 0")
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.upsert_bankroll")
    def test_rejects_unknown_currency(
            self, mock_upsert: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            configure_bankroll(_USER, "GBP", 100, 5)
        self.assertEqual(str(ctx.exception), "Unsupported currency")
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.upsert_bankroll")
    def test_rejects_sub_cent_capital(
            self, mock_upsert: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            configure_bankroll(_USER, "PLN", 0.001, 5)
        self.assertEqual(
            str(ctx.exception),
            "initial_capital must be greater than 0")
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.fetch_coupons", return_value=([], 1))
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_REPO}.upsert_bankroll")
    def test_currency_change_after_coupon_conflicts(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock,
            mock_coupons: MagicMock) -> None:
        with self.assertRaises(TipsterConflictError) as ctx:
            configure_bankroll(_USER, "EUR", 100, 5)
        self.assertEqual(
            str(ctx.exception),
            "Currency cannot be changed after the first coupon")
        mock_coupons.assert_called_once_with(7, None, 1, 1)
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.update_bankroll_settings")
    @patch(f"{_REPO}.fetch_coupons", return_value=([], 0))
    @patch(f"{_REPO}.get_bankroll")
    @patch(f"{_REPO}.upsert_bankroll")
    def test_currency_change_allowed_before_first_coupon(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock,
            mock_coupons: MagicMock,
            mock_update: MagicMock) -> None:
        updated = {**_BANKROLL, "currency": "EUR"}
        mock_get.side_effect = [_BANKROLL, updated]
        document = configure_bankroll(_USER, "EUR", 100, 5)
        self.assertEqual(document["currency"], "EUR")
        mock_coupons.assert_called_once_with(7, None, 1, 1)
        mock_update.assert_called_once_with(7, "EUR", 5.0)
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.update_bankroll_settings")
    @patch(f"{_REPO}.get_bankroll")
    @patch(f"{_REPO}.upsert_bankroll")
    def test_existing_row_can_change_unit_size(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock,
            mock_update: MagicMock) -> None:
        updated = {**_BANKROLL, "unit_size": 10.0}
        mock_get.side_effect = [_BANKROLL, updated]
        document = configure_bankroll(_USER, "PLN", 100, 10)
        self.assertEqual(document["unit_size"], 10.0)
        mock_update.assert_called_once_with(7, "PLN", 10.0)
        mock_upsert.assert_not_called()

    @patch(f"{_REPO}.update_bankroll_settings")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_REPO}.upsert_bankroll")
    def test_existing_row_rejects_capital_decrease(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock,
            mock_update: MagicMock) -> None:
        with self.assertRaises(TipsterConflictError) as ctx:
            configure_bankroll(_USER, "PLN", 50, 5)
        self.assertEqual(
            str(ctx.exception),
            "Initial capital cannot be changed after onboarding")
        mock_upsert.assert_not_called()
        mock_update.assert_not_called()
        mock_get.assert_called_once_with(7)

    @patch(f"{_REPO}.update_bankroll_settings")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_REPO}.upsert_bankroll")
    def test_existing_row_rejects_capital_increase(
            self,
            mock_upsert: MagicMock,
            mock_get: MagicMock,
            mock_update: MagicMock) -> None:
        with self.assertRaises(TipsterConflictError) as ctx:
            configure_bankroll(_USER, "PLN", 200, 5)
        self.assertEqual(
            str(ctx.exception),
            "Initial capital cannot be changed after onboarding")
        mock_upsert.assert_not_called()
        mock_update.assert_not_called()


class TestTopUp(unittest.TestCase):
    """Top-up only increases initial_capital and recomputes SQL balances."""

    @patch(f"{_REPO}.add_to_initial_capital")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_top_up_after_loss_raises_capital_and_balance(
            self,
            mock_get: MagicMock,
            mock_add: MagicMock) -> None:
        # initial 100 + profit -150 + top-up 100 -> initial 200, balance 50
        mock_add.return_value = {
            **_BANKROLL,
            "initial_capital": 200.0,
            "current_balance": 50.0,
            "realized_pnl": -150.0}
        document = top_up(_USER, 100)
        self.assertEqual(document["initial_capital"], 200.0)
        self.assertEqual(document["current_balance"], 50.0)
        mock_add.assert_called_once_with(7, 100.0)
        mock_get.assert_called_once_with(7)

    @patch(f"{_REPO}.add_to_initial_capital")
    @patch(f"{_REPO}.get_bankroll", return_value=None)
    def test_top_up_without_bankroll(
            self,
            mock_get: MagicMock,
            mock_add: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            top_up(_USER, 100)
        self.assertEqual(str(ctx.exception), "Bankroll not configured")
        mock_add.assert_not_called()
        mock_get.assert_called_once_with(7)

    @patch(f"{_REPO}.add_to_initial_capital")
    def test_rejects_non_positive_amount(
            self, mock_add: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            top_up(_USER, 0)
        self.assertEqual(
            str(ctx.exception), "amount must be greater than 0")
        mock_add.assert_not_called()

    @patch(f"{_REPO}.add_to_initial_capital")
    def test_rejects_sub_cent_amount(
            self, mock_add: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            top_up(_USER, 0.001)
        self.assertEqual(
            str(ctx.exception), "amount must be greater than 0")
        mock_add.assert_not_called()

    @patch(f"{_REPO}.add_to_initial_capital")
    def test_rejects_system_user(
            self, mock_add: MagicMock) -> None:
        with self.assertRaises(TipsterForbiddenError):
            top_up(_SYSTEM_USER, 100)
        mock_add.assert_not_called()

    @patch(f"{_REPO}.add_to_initial_capital")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_id", return_value=_SYSTEM_USER)
    def test_job_path_allows_system_user(
            self,
            mock_fetch_user: MagicMock,
            mock_get: MagicMock,
            mock_add: MagicMock) -> None:
        mock_add.return_value = {
            **_BANKROLL,
            "user_id": 9,
            "initial_capital": 200.0}
        document = top_up_for_user(9, 100)
        self.assertEqual(document["initial_capital"], 200.0)
        mock_fetch_user.assert_called_once_with(9)
        mock_get.assert_called_once_with(9)
        mock_add.assert_called_once_with(9, 100.0)

    @patch(f"{_REPO}.add_to_initial_capital")
    @patch(f"{_USERS}.fetch_user_by_id", return_value=None)
    def test_job_path_missing_user(
            self,
            mock_fetch_user: MagicMock,
            mock_add: MagicMock) -> None:
        with self.assertRaises(TipsterNotFoundError) as ctx:
            top_up_for_user(99, 100)
        self.assertEqual(str(ctx.exception), "User not found")
        mock_fetch_user.assert_called_once_with(99)
        mock_add.assert_not_called()


class TestCreateCoupon(unittest.TestCase):
    """Stake, combined legs, uniqueness and settleable-catalog rules."""

    @patch(f"{_REPO}.insert_coupon", return_value={"id": 10})
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_units_stake_is_two_times_five(
            self,
            mock_bankroll: MagicMock,
            mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        document = create_coupon(_USER, _request(mode="units", stake_units=2))
        self.assertEqual(document, {"id": 10})
        mock_insert.assert_called_once()
        user_id, amount, units, mode, legs = mock_insert.call_args.args
        self.assertEqual(user_id, 7)
        self.assertEqual(amount, 10.0)
        self.assertEqual(units, 2)
        self.assertEqual(mode, "units")
        self.assertEqual(len(legs), 1)
        mock_bankroll.assert_called_once_with(7)
        mock_catalog.assert_called_once_with(None, None, None)

    @patch(f"{_REPO}.insert_coupon", return_value={"id": 10})
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_debit_does_not_block_insert(
            self,
            mock_bankroll: MagicMock,
            mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        # saldo -50, stawka 10 — plan świadomie pozwala na debet
        create_coupon(_USER, _request(mode="money", stake_amount=10, stake_units=None))
        mock_insert.assert_called_once()
        amount = mock_insert.call_args.args[1]
        self.assertEqual(amount, 10.0)
        self.assertLess(_BANKROLL["current_balance"], amount)
        mock_bankroll.assert_called_once()
        mock_catalog.assert_called_once()

    @patch(f"{_REPO}.insert_coupon", return_value={"id": 10})
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_combined_btts_over_is_one_leg_one_price(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        request = _request(
            mode="money",
            stake_amount=10,
            stake_units=None,
            legs=[_leg(100, [6, 12], 1.85, source="custom_odds")])
        create_coupon(_USER, request)
        legs = mock_insert.call_args.args[4]
        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0]["event_ids"], [6, 12])
        self.assertEqual(legs[0]["odds"], 1.85)
        self.assertEqual(legs[0]["source"], "custom_odds")
        self.assertEqual(_combined_odds(legs), 1.85)
        self.assertEqual(mock_insert.call_args.kwargs["combined_odds"], 1.85)

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_nine_legs_are_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        legs = [_leg(100 + index) for index in range(9)]
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(_USER, _request(legs=legs))
        self.assertEqual(
            str(ctx.exception),
            "Coupon must have between 1 and 8 legs")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_second_leg_on_same_match_is_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        legs = [_leg(100, [6], 1.7), _leg(100, [12], 1.8)]
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(_USER, _request(legs=legs))
        self.assertEqual(str(ctx.exception), "Duplicate match on coupon")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_unsupported_event_is_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(
                _USER, _request(legs=[_leg(event_ids=[173])]))
        self.assertEqual(str(ctx.exception), "Event is not settleable")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_finished_match_is_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(
                _USER, _request(legs=[_leg(match_id=999)]))
        self.assertEqual(
            str(ctx.exception),
            "Match is finished or not open for betting")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches")
    @patch(f"{_REPO}.get_bankroll", return_value=None)
    def test_coupon_without_bankroll(
            self,
            mock_bankroll: MagicMock,
            mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterValidationError) as ctx:
            create_coupon(_USER, _request())
        self.assertEqual(str(ctx.exception), "Bankroll not configured")
        mock_insert.assert_not_called()
        mock_catalog.assert_not_called()
        mock_bankroll.assert_called_once_with(7)

    @patch(f"{_REPO}.insert_coupon")
    def test_me_rejects_system_user(
            self, mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterForbiddenError):
            create_coupon(_SYSTEM_USER, _request())
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon", return_value={"id": 11})
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_id", return_value=_SYSTEM_USER)
    def test_job_path_allows_system_user(
            self,
            mock_fetch_user: MagicMock,
            mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        document = create_coupon_for_user(9, _request(mode="units", stake_units=2))
        self.assertEqual(document, {"id": 11})
        mock_fetch_user.assert_called_once_with(9)
        mock_bankroll.assert_called_once_with(9)
        mock_insert.assert_called_once()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_USERS}.fetch_user_by_id")
    def test_inactive_user_cannot_place(
            self,
            mock_fetch_user: MagicMock,
            mock_insert: MagicMock) -> None:
        mock_fetch_user.return_value = {**_USER, "is_active": 0}
        with self.assertRaises(TipsterForbiddenError) as ctx:
            create_coupon_for_user(7, _request())
        self.assertEqual(str(ctx.exception), "User account is inactive")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_USERS}.fetch_user_by_id", return_value=None)
    def test_job_path_missing_user(
            self,
            mock_fetch_user: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterNotFoundError) as ctx:
            create_coupon_for_user(99, _request())
        self.assertEqual(str(ctx.exception), "User not found")
        mock_fetch_user.assert_called_once_with(99)
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon", return_value={"id": 10})
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_same_catalog_event_on_two_matches_is_allowed(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        legs = [_leg(100, [6], 1.7), _leg(101, [6], 1.8)]
        create_coupon(_USER, _request(legs=legs))
        inserted = mock_insert.call_args.args[4]
        self.assertEqual(
            [leg["event_ids"] for leg in inserted], [[6], [6]])
        self.assertAlmostEqual(
            mock_insert.call_args.kwargs["combined_odds"], 3.06)

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_duplicate_event_on_same_leg_is_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(
                _USER, _request(legs=[_leg(100, [6, 6])]))
        self.assertEqual(str(ctx.exception), "Duplicate event_id on a leg")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_odds_below_minimum_are_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(_USER, _request(legs=[_leg(odds=1.0)]))
        self.assertEqual(str(ctx.exception), "Odds must be at least 1.01")
        mock_insert.assert_not_called()

    @patch(f"{_REPO}.insert_coupon")
    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_non_integer_bookmaker_id_is_rejected(
            self,
            _mock_bankroll: MagicMock,
            _mock_catalog: MagicMock,
            mock_insert: MagicMock) -> None:
        with self.assertRaises(TipsterUnprocessableError) as ctx:
            create_coupon(
                _USER, _request(legs=[_leg(bookmaker_id="sts")]))
        self.assertEqual(str(ctx.exception), "Invalid bookmaker_id")
        mock_insert.assert_not_called()


class TestPublicProfileAndLeaderboard(unittest.TestCase):
    """Coupon lists stay private for a stranger viewing a human."""

    @patch(f"{_REPO}.fetch_performance")
    @patch(f"{_REPO}.fetch_coupons")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_username", return_value=_USER)
    def test_stranger_sees_null_coupons_for_human(
            self,
            mock_fetch_user: MagicMock,
            mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        profile = get_public_profile("alice", _STRANGER)
        self.assertIsNone(profile["coupons"])
        self.assertIsNone(profile["performance"])
        self.assertEqual(profile["bankroll"], _PUBLIC_BANKROLL)
        self.assertNotIn("unit_size", profile["bankroll"])
        self.assertNotIn("initial_capital", profile["bankroll"])
        self.assertEqual(profile["is_system"], 0)
        mock_coupons.assert_not_called()
        mock_perf.assert_not_called()
        mock_fetch_user.assert_called_once_with("alice")
        mock_bankroll.assert_called_once_with(7, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance", return_value={"by_league": []})
    @patch(f"{_REPO}.fetch_coupons", return_value=([{"id": 1}], 1))
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_username", return_value=_USER)
    def test_owner_sees_own_coupons(
            self,
            _mock_fetch_user: MagicMock,
            _mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        profile = get_public_profile("alice", _USER, page=2, page_size=10)
        self.assertEqual(profile["coupons"], {
            "items": [{"id": 1}],
            "total": 1,
            "page": 2,
            "page_size": 10})
        self.assertEqual(profile["performance"], {"by_league": []})
        self.assertEqual(profile["bankroll"], _BANKROLL)
        mock_coupons.assert_called_once_with(
            7, None, 2, 10, apply_tax=False)
        mock_perf.assert_called_once_with(7, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance", return_value={"by_league": []})
    @patch(f"{_REPO}.fetch_coupons", return_value=([], 0))
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_username", return_value=_SYSTEM_USER)
    def test_system_profile_is_public(
            self,
            _mock_fetch_user: MagicMock,
            _mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        profile = get_public_profile("agent", _STRANGER)
        self.assertEqual(profile["coupons"], {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20})
        self.assertEqual(profile["is_system"], 1)
        self.assertEqual(profile["bankroll"], _PUBLIC_BANKROLL)
        mock_coupons.assert_called_once_with(
            9, None, 1, 20, apply_tax=False)
        mock_perf.assert_called_once_with(9, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance")
    @patch(f"{_REPO}.fetch_coupons")
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_username", return_value=_USER)
    def test_anonymous_viewer_hides_human_coupons(
            self,
            mock_fetch_user: MagicMock,
            mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        profile = get_public_profile("alice", None)
        self.assertIsNone(profile["coupons"])
        self.assertIsNone(profile["performance"])
        self.assertEqual(profile["bankroll"], _PUBLIC_BANKROLL)
        mock_coupons.assert_not_called()
        mock_perf.assert_not_called()
        mock_fetch_user.assert_called_once_with("alice")
        mock_bankroll.assert_called_once_with(7, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance", return_value={"by_league": []})
    @patch(f"{_REPO}.fetch_coupons", return_value=([], 0))
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    @patch(f"{_USERS}.fetch_user_by_username", return_value=_SYSTEM_USER)
    def test_anonymous_viewer_sees_system_coupon_page(
            self,
            _mock_fetch_user: MagicMock,
            _mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        profile = get_public_profile("agent", None)
        self.assertEqual(profile["coupons"], {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20})
        self.assertEqual(profile["is_system"], 1)
        self.assertEqual(profile["bankroll"], _PUBLIC_BANKROLL)
        mock_coupons.assert_called_once_with(
            9, None, 1, 20, apply_tax=False)
        mock_perf.assert_called_once_with(9, apply_tax=False)

    @patch(f"{_USERS}.fetch_user_by_username", return_value=None)
    def test_unknown_username_is_not_found(
            self, mock_fetch_user: MagicMock) -> None:
        with self.assertRaises(TipsterNotFoundError) as ctx:
            get_public_profile("missing", _USER)
        self.assertEqual(str(ctx.exception), "User not found")
        mock_fetch_user.assert_called_once_with("missing")

    @patch(f"{_REPO}.fetch_leaderboard")
    def test_leaderboard_maps_frame_without_coupon_lists(
            self, mock_fetch: MagicMock) -> None:
        row = {
            "user_id": 7,
            "username": "alice",
            "currency": "PLN",
            "profit_total": 12.5,
            "current_balance": 50.0}
        mock_fetch.return_value = (
            pd.DataFrame([row], dtype=object), 1)
        payload = get_leaderboard({"sort_by": "profit_total"})
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["username"], "alice")
        self.assertEqual(payload["items"][0]["currency"], "PLN")
        self.assertNotIn("coupons", payload["items"][0])
        mock_fetch.assert_called_once_with({"sort_by": "profit_total"})

    @patch(f"{_REPO}.fetch_leaderboard")
    def test_empty_leaderboard(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = (pd.DataFrame(dtype=object), 0)
        payload = get_leaderboard()
        self.assertEqual(payload, {"items": [], "total": 0})


class TestThinReads(unittest.TestCase):
    """Pass-through reads used by /me and the catalog picker."""

    @patch(f"{_REPO}.fetch_coupons", return_value=([{"id": 3}], 4))
    def test_get_my_coupons_returns_page(
            self, mock_fetch: MagicMock) -> None:
        payload = get_my_coupons(_USER, settled=0, page=2, page_size=5)
        self.assertEqual(payload, {
            "items": [{"id": 3}],
            "total": 4,
            "page": 2,
            "page_size": 5})
        mock_fetch.assert_called_once_with(
            7, 0, 2, 5, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance", return_value={"by_league": []})
    def test_get_my_performance(
            self, mock_fetch: MagicMock) -> None:
        self.assertEqual(
            get_my_performance(_USER), {"by_league": []})
        mock_fetch.assert_called_once_with(7, apply_tax=False)

    @patch(f"{_REPO}.fetch_performance", return_value={"by_league": []})
    @patch(f"{_REPO}.fetch_coupons", return_value=([], 0))
    @patch(f"{_REPO}.get_bankroll", return_value=_BANKROLL)
    def test_apply_tax_is_forwarded_on_owner_reads(
            self,
            mock_bankroll: MagicMock,
            mock_coupons: MagicMock,
            mock_perf: MagicMock) -> None:
        get_my_bankroll(_USER, apply_tax=True)
        get_my_coupons(_USER, apply_tax=True)
        get_my_performance(_USER, apply_tax=True)
        mock_bankroll.assert_called_once_with(7, apply_tax=True)
        mock_coupons.assert_called_once_with(
            7, None, 1, 20, apply_tax=True)
        mock_perf.assert_called_once_with(7, apply_tax=True)

    @patch(f"{_REPO}.fetch_catalog_matches", return_value=_CATALOG)
    def test_get_catalog_matches(
            self, mock_fetch: MagicMock) -> None:
        self.assertEqual(get_catalog_matches(None, None, [1]), _CATALOG)
        mock_fetch.assert_called_once_with(None, None, [1])

    @patch(f"{_REPO}.fetch_suggested_catalog_odds", return_value=2.204)
    def test_suggested_odds_are_rounded_to_two_places(
            self, mock_fetch: MagicMock) -> None:
        self.assertEqual(
            get_suggested_catalog_odds(124426, 1), {"odds": 2.2})
        mock_fetch.assert_called_once_with(124426, 1, 1.01)

    @patch(f"{_REPO}.fetch_suggested_catalog_odds", return_value=None)
    def test_missing_suggested_odds_stay_empty(
            self, _mock_fetch: MagicMock) -> None:
        self.assertEqual(
            get_suggested_catalog_odds(10, 8), {"odds": None})

    def test_suggested_odds_reject_non_positive_ids(self) -> None:
        with self.assertRaises(TipsterUnprocessableError):
            get_suggested_catalog_odds(0, 1)


if __name__ == "__main__":
    unittest.main()
