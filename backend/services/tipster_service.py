"""Business rules for tipster bankroll, coupons and public ranking."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict

from backend.repositories import tipster_repository as repo
from backend.repositories import user_repository
from backend.sports.football.event_settlement_registry import (
    is_settleable_event)


StakeInputMode = Literal["money", "units"]
LegSource = Literal["catalog", "custom_odds"]
CurrencyCode = Literal["PLN", "EUR", "USD"]


class CouponLegCreate(TypedDict):
    """One coupon leg: a single bookmaker price, possibly several events."""

    match_id: int
    event_ids: list[int]
    odds: float
    source: LegSource
    bookmaker_id: NotRequired[int | None]


class CouponCreateRequest(TypedDict):
    """Payload used by /me and by EB-9 job placement."""

    stake_input_mode: StakeInputMode
    legs: list[CouponLegCreate]
    stake_amount: NotRequired[float | None]
    stake_units: NotRequired[float | None]


class BankrollSettings(TypedDict):
    """Bankroll row plus SQL-computed balances."""

    user_id: int
    currency: CurrencyCode
    initial_capital: float
    unit_size: float
    current_balance: float
    open_stake: float
    realized_pnl: float


MIN_ODDS = 1.01
MIN_LEGS = 1
MAX_LEGS = 8
MONEY_QUANT = Decimal("0.01")
ALLOWED_CURRENCIES = frozenset({"PLN", "EUR", "USD"})
ALLOWED_SOURCES = frozenset({"catalog", "custom_odds"})
ALLOWED_STAKE_MODES = frozenset({"money", "units"})
DEFAULT_COUPON_PAGE_SIZE = 20


class TipsterServiceError(Exception):
    """Base error for tipster bankroll and coupon operations."""


class TipsterNotFoundError(TipsterServiceError):
    """Raised when a user or bankroll document is missing (HTTP 404)."""


class TipsterForbiddenError(TipsterServiceError):
    """Raised when the actor cannot mutate this resource (HTTP 403)."""


class TipsterConflictError(TipsterServiceError):
    """Raised when a mutation conflicts with persisted state (HTTP 409)."""


class TipsterValidationError(TipsterServiceError):
    """Raised when business input is invalid (HTTP 400)."""


class TipsterUnprocessableError(TipsterServiceError):
    """Raised when a coupon payload cannot be processed (HTTP 422)."""


def get_my_bankroll(
        user: dict[str, Any],
        apply_tax: bool = False) -> dict[str, Any]:
    """Return the caller's bankroll or raise when onboarding is missing."""
    bankroll = repo.get_bankroll(_user_id(user), apply_tax=apply_tax)
    if bankroll is None:
        raise TipsterNotFoundError("Bankroll not configured")
    return bankroll


def configure_bankroll(
        user: dict[str, Any],
        currency: str,
        initial_capital: float,
        unit_size: float) -> dict[str, Any]:
    """Create or update bankroll settings for an interactive user.

    After the first row exists, ``initial_capital`` is frozen (only
    ``top_up`` may raise it). ``unit_size`` may still change.
    """
    _reject_system_me(user)
    code = _validated_currency(currency)
    capital = _require_positive(initial_capital, "initial_capital")
    unit = _require_positive(unit_size, "unit_size")
    user_id = _user_id(user)
    existing = repo.get_bankroll(user_id)
    _assert_initial_capital_unchanged(existing, capital)
    _assert_currency_change_allowed(existing, code)
    if existing is None:
        repo.upsert_bankroll(user_id, code, capital, unit)
    else:
        # kapitał rusza wyłącznie top_up — bez wyścigu get/upsert
        repo.update_bankroll_settings(user_id, code, unit)
    bankroll = repo.get_bankroll(user_id)
    if bankroll is None:
        raise RuntimeError("Bankroll could not be read back")
    return bankroll


def top_up(user: dict[str, Any], amount: float) -> dict[str, Any]:
    """Increase initial_capital; system accounts cannot top up via /me."""
    _reject_system_me(user)
    return _apply_top_up(_user_id(user), amount)


def top_up_for_user(user_id: int, amount: float) -> dict[str, Any]:
    """Increase initial_capital for any user, including system agents."""
    if user_repository.fetch_user_by_id(user_id) is None:
        raise TipsterNotFoundError("User not found")
    return _apply_top_up(user_id, amount)


def create_coupon(
        user: dict[str, Any],
        request: dict[str, Any]) -> dict[str, Any]:
    """Place a coupon for the interactive /me caller."""
    _reject_system_me(user)
    return _create_coupon_for_loaded_user(user, request)


def create_coupon_for_user(
        user_id: int,
        request: dict[str, Any]) -> dict[str, Any]:
    """Place a coupon for any user, including system agents (EB-9 jobs)."""
    user = user_repository.fetch_user_by_id(user_id)
    if user is None:
        raise TipsterNotFoundError("User not found")
    return _create_coupon_for_loaded_user(user, request)


def get_my_coupons(
        user: dict[str, Any],
        settled: int | None = None,
        page: int = 1,
        page_size: int = DEFAULT_COUPON_PAGE_SIZE,
        apply_tax: bool = False) -> dict[str, Any]:
    """Return a coupon page for the authenticated owner."""
    return _coupon_page(
        _user_id(user), settled, page, page_size, apply_tax)


def get_my_performance(
        user: dict[str, Any],
        apply_tax: bool = False) -> dict[str, Any]:
    """Return settled-coupon breakdowns for the authenticated owner."""
    return repo.fetch_performance(_user_id(user), apply_tax=apply_tax)


def get_leaderboard(
        filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a ranking page; coupon lists are never included."""
    frame, total = repo.fetch_leaderboard(filters)
    if frame.empty:
        items: list[dict[str, Any]] = []
    else:
        items = frame.to_dict(orient="records")
    return {
        "items": items,
        "total": total
    }


def get_public_profile(
        username: str,
        viewer: dict[str, Any] | None,
        page: int = 1,
        page_size: int = DEFAULT_COUPON_PAGE_SIZE,
        apply_tax: bool = False) -> dict[str, Any]:
    """Return public identity; coupons only for owner or system target."""
    target = user_repository.fetch_user_by_username(username)
    if target is None:
        raise TipsterNotFoundError("User not found")
    target_id = int(target["id"])
    coupons: dict[str, Any] | None = None
    performance: dict[str, Any] | None = None
    if _can_view_coupons(target, viewer):
        coupons = _coupon_page(
            target_id, None, page, page_size, apply_tax)
        performance = repo.fetch_performance(
            target_id, apply_tax=apply_tax)
    return {
        "user_id": target_id,
        "username": str(target["username"]),
        "display_name": target.get("display_name"),
        "is_system": int(target.get("is_system") or 0),
        "bankroll": _visible_bankroll(
            repo.get_bankroll(target_id, apply_tax=apply_tax),
            target,
            viewer),
        "coupons": coupons,
        "performance": performance
    }


def get_catalog_matches(
        date_from: date | None = None,
        date_to: date | None = None,
        league_ids: list[int] | None = None) -> dict[str, Any]:
    """Return upcoming unfinished matches and settleable catalog events."""
    return repo.fetch_catalog_matches(date_from, date_to, league_ids)


def get_suggested_catalog_odds(
        match_id: int, event_id: int) -> dict[str, Any]:
    """Suggest current bookmaker odds for one predicted catalog event.

    ``odds`` is null when the event has no stored prediction or no price
    at or above the coupon minimum. The value is a default the user can
    replace, because prices move after they are fetched.
    """
    if match_id < 1 or event_id < 1:
        raise TipsterUnprocessableError("Invalid match or event")
    raw = repo.fetch_suggested_catalog_odds(match_id, event_id, MIN_ODDS)
    return {"odds": _quantize_suggested_odds(raw)}


def _quantize_suggested_odds(raw: float | None) -> float | None:
    if raw is None or not math.isfinite(raw) or raw < MIN_ODDS:
        return None
    quantized = Decimal(str(raw)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized < Decimal(str(MIN_ODDS)):
        return None
    return float(quantized)


def _resolve_stake(
        mode: str,
        stake_amount: object,
        stake_units: object,
        unit_size: float) -> float:
    """Return stake money after converting units when needed."""
    if mode not in ALLOWED_STAKE_MODES:
        raise TipsterUnprocessableError("Invalid stake_input_mode")
    if unit_size <= 0:
        raise TipsterValidationError("unit_size must be greater than 0")
    if mode == "money":
        return _quantized_positive_stake(stake_amount)
    units = _require_positive_stake(stake_units)
    return _quantized_positive_stake(units * unit_size)


def _combined_odds(legs: list[dict[str, Any]]) -> float:
    """Return the product of per-leg odds, ignoring events inside a combined."""
    product = Decimal("1")
    for leg in legs:
        product *= Decimal(str(leg["odds"]))
    return float(product)


def _create_coupon_for_loaded_user(
        user: dict[str, Any],
        request: dict[str, Any]) -> dict[str, Any]:
    if not user.get("is_active"):
        raise TipsterForbiddenError("User account is inactive")
    user_id = _user_id(user)
    bankroll = repo.get_bankroll(user_id)
    if bankroll is None:
        raise TipsterValidationError("Bankroll not configured")
    mode = str(request.get("stake_input_mode") or "")
    legs = _validated_legs(request.get("legs"))
    stake_amount = _resolve_stake(
        mode,
        request.get("stake_amount"),
        request.get("stake_units"),
        float(bankroll["unit_size"]))
    stake_units = _persisted_stake_units(
        mode,
        stake_amount,
        request.get("stake_units"),
        float(bankroll["unit_size"]))
    return repo.insert_coupon(
        user_id,
        stake_amount,
        stake_units,
        mode,
        legs,
        combined_odds=_combined_odds(legs))


def _validated_legs(raw_legs: object) -> list[dict[str, Any]]:
    if not isinstance(raw_legs, list):
        raise TipsterUnprocessableError(
            "Coupon must have between 1 and 8 legs")
    if not MIN_LEGS <= len(raw_legs) <= MAX_LEGS:
        raise TipsterUnprocessableError(
            "Coupon must have between 1 and 8 legs")
    open_match_ids, settleable_events = _open_catalog()
    legs = [
        _validated_leg(raw, open_match_ids, settleable_events)
        for raw in raw_legs]
    _assert_unique_matches(legs)
    return legs


def _open_catalog() -> tuple[set[int], dict[int, str]]:
    # picker i walidacja kuponu dzielą to samo okno: przyszłe + settleable
    catalog = repo.fetch_catalog_matches(None, None, None)
    match_ids = {int(row["id"]) for row in catalog["matches"]}
    events = {
        int(row["id"]): str(row["name"])
        for row in catalog["events"]}
    return match_ids, events


def _validated_leg(
        raw: object,
        open_match_ids: set[int],
        settleable_events: dict[int, str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TipsterUnprocessableError("Invalid coupon leg")
    try:
        match_id = int(raw["match_id"])
        odds = float(raw["odds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TipsterUnprocessableError("Invalid coupon leg") from exc
    if match_id not in open_match_ids:
        raise TipsterUnprocessableError(
            "Match is finished or not open for betting")
    source = str(raw.get("source") or "")
    if source not in ALLOWED_SOURCES:
        raise TipsterUnprocessableError("Invalid leg source")
    if odds < MIN_ODDS:
        raise TipsterUnprocessableError("Odds must be at least 1.01")
    return {
        "match_id": match_id,
        "event_ids": _validated_event_ids(
            raw.get("event_ids"), settleable_events),
        "odds": odds,
        "bookmaker_id": _validated_bookmaker_id(
            raw.get("bookmaker_id")),
        "source": source
    }


def _validated_event_ids(
        raw_ids: object,
        settleable_events: dict[int, str]) -> list[int]:
    if not isinstance(raw_ids, list) or not raw_ids:
        raise TipsterUnprocessableError(
            "Each leg must have at least one event")
    event_ids: list[int] = []
    for raw_id in raw_ids:
        try:
            event_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise TipsterUnprocessableError("Invalid event_id") from exc
        name = settleable_events.get(event_id)
        if name is None or not is_settleable_event(event_id, name):
            raise TipsterUnprocessableError("Event is not settleable")
        event_ids.append(event_id)
    if len(event_ids) != len(set(event_ids)):
        raise TipsterUnprocessableError("Duplicate event_id on a leg")
    return event_ids


def _assert_unique_matches(legs: list[dict[str, Any]]) -> None:
    match_ids = [int(leg["match_id"]) for leg in legs]
    if len(match_ids) != len(set(match_ids)):
        raise TipsterUnprocessableError("Duplicate match on coupon")


def _persisted_stake_units(
        mode: str,
        stake_amount: float,
        stake_units: object,
        unit_size: float) -> float:
    if mode == "units":
        return float(stake_units)
    return float(Decimal(str(stake_amount)) / Decimal(str(unit_size)))


def _assert_initial_capital_unchanged(
        existing: dict[str, Any] | None, capital: float) -> None:
    if existing is None:
        return
    if capital != float(existing["initial_capital"]):
        raise TipsterConflictError(
            "Initial capital cannot be changed after onboarding")


def _assert_currency_change_allowed(
        existing: dict[str, Any] | None, currency: str) -> None:
    if existing is None:
        return
    if existing["currency"] == currency:
        return
    _items, total = repo.fetch_coupons(
        int(existing["user_id"]), None, 1, 1)
    if total > 0:
        raise TipsterConflictError(
            "Currency cannot be changed after the first coupon")


def _validated_bookmaker_id(value: object) -> int | None:
    if value is None:
        return None
    # bool jest podklasą int — True/False nie jest id bukmachera
    if isinstance(value, bool) or not isinstance(value, int):
        raise TipsterUnprocessableError("Invalid bookmaker_id")
    return value


def _apply_top_up(user_id: int, amount: float) -> dict[str, Any]:
    value = _require_positive(amount, "amount")
    if repo.get_bankroll(user_id) is None:
        raise TipsterValidationError("Bankroll not configured")
    document = repo.add_to_initial_capital(user_id, value)
    if document is None:
        raise TipsterValidationError("Bankroll not configured")
    return document


def _validated_currency(currency: str) -> str:
    code = currency.strip().upper()
    if code not in ALLOWED_CURRENCIES:
        raise TipsterValidationError("Unsupported currency")
    return code


def _require_positive(value: object, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TipsterValidationError(
            f"{field_name} must be greater than 0") from exc
    if number <= 0:
        raise TipsterValidationError(
            f"{field_name} must be greater than 0")
    quantized = _money(number)
    if quantized <= 0:
        raise TipsterValidationError(
            f"{field_name} must be greater than 0")
    return quantized


def _require_positive_stake(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TipsterUnprocessableError(
            "Stake must be greater than 0") from exc
    if number <= 0:
        raise TipsterUnprocessableError("Stake must be greater than 0")
    return number


def _quantized_positive_stake(value: object) -> float:
    amount = _money(_require_positive_stake(value))
    if amount <= 0:
        raise TipsterUnprocessableError("Stake must be greater than 0")
    return amount


def _coupon_page(
        user_id: int,
        settled: int | None,
        page: int,
        page_size: int,
        apply_tax: bool = False) -> dict[str, Any]:
    items, total = repo.fetch_coupons(
        user_id, settled, page, page_size, apply_tax=apply_tax)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


def _money(value: float) -> float:
    quantized = Decimal(str(value)).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP)
    return float(quantized)


def _can_view_coupons(
        target: dict[str, Any],
        viewer: dict[str, Any] | None) -> bool:
    if int(target.get("is_system") or 0) == 1:
        return True
    return _is_owner(target, viewer)


def _is_owner(
        target: dict[str, Any],
        viewer: dict[str, Any] | None) -> bool:
    if viewer is None:
        return False
    return _user_id(viewer) == int(target["id"])


def _visible_bankroll(
        bankroll: dict[str, Any] | None,
        target: dict[str, Any],
        viewer: dict[str, Any] | None) -> dict[str, Any] | None:
    if bankroll is None:
        return None
    if _is_owner(target, viewer):
        return bankroll
    # unit i kapitał startowy to ustawienia stawki — nie dla obcego
    return {
        "currency": bankroll["currency"],
        "current_balance": bankroll["current_balance"]
    }


def _reject_system_me(user: dict[str, Any]) -> None:
    if int(user.get("is_system") or 0) == 1:
        raise TipsterForbiddenError(
            "System accounts cannot use /me mutations")


def _user_id(user: dict[str, Any]) -> int:
    return int(user["id"])
