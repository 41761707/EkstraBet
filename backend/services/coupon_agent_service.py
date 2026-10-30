"""Publish one daily coupon per configured system agent."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from backend.repositories.coupon_agent_repository import fetch_candidates
from backend.repositories.coupon_agent_repository import fetch_ready_bets
from backend.repositories.coupon_agent_repository import (
    ready_model_fingerprint)
from backend.repositories.tipster_repository import (
    fetch_coupon_leg_sets_between)
from backend.repositories.tipster_repository import get_by_username
from backend.services import coupon_agent_config as agent_config
from backend.services.coupon_agent_selector import AgentCandidate
from backend.services.coupon_agent_selector import CouponSelection
from backend.services.coupon_agent_selector import select_coupon
from backend.services.tipster_service import create_coupon_for_user
from backend.services.tipster_service import quantize_catalog_odds
from backend.timezone import WARSAW_TIME_ZONE


logger = logging.getLogger(__name__)
_WARSAW = ZoneInfo(WARSAW_TIME_ZONE)

_STATUS_PUBLISHED = "published"
_STATUS_ALREADY = "already_published"
_STATUS_NO_BET = "no_bet"
_STATUS_MISSING = "missing_user"
_REASON_DAY = "Coupon already published for this calendar day"
_REASON_SAME_LEGS = "Coupon with the same legs already exists today"


class CouponAgentServiceError(Exception):
    """A named agent cannot be published."""


@dataclass(frozen=True)
class PublishReport:
    """Outcome of one agent on one calendar day."""

    username: str
    status: str
    coupon_id: int | None
    candidate_count: int
    skipped_reason: str | None


@dataclass(frozen=True)
class PublishBatchReport:
    """One publication result per configured agent."""

    reports: list[PublishReport]


class _CandidatePool:
    """Load the shared candidate frame at most once per call."""

    def __init__(self, now: datetime, allow_unready: bool) -> None:
        self._now = now
        self._allow_unready = allow_unready
        self._rows: list[AgentCandidate] | None = None

    def load(self) -> list[AgentCandidate]:
        """Return candidates, fetching them on the first call only."""
        if self._rows is None:
            frame = _selector_frame(self._now, self._allow_unready)
            self._rows = _candidates_from_frame(frame)
        return self._rows


def publish_daily(
        as_of: datetime,
        username: str | None = None,
        dry_run: bool = False,
        allow_unready: bool = False) -> PublishBatchReport:
    """Publish one coupon per configured agent for the Warsaw day.

    ``username`` None publishes every entry in ``AGENTS``. A name
    publishes that agent and raises ``CouponAgentServiceError`` when
    the account or its bankroll is missing, or when the name is not
    configured. The batch path records ``missing_user`` and continues.
    ``dry_run`` logs legs and score and does not insert. ``as_of``
    only confirms the current Warsaw day. The candidate pool, the
    idempotency window and the stored stamp all use the same clock.
    A ready EB-18 artifact narrows that pool to stored ``bet`` rows.
    ``allow_unready`` uses those rows even when the report fails the
    gate. Stake stays ``stake_units`` from the agent config.
    """
    if not isinstance(allow_unready, bool):
        raise ValueError("allow_unready must be a bool")
    wall = _warsaw_wall_time(as_of)
    _require_current_warsaw_day(wall)
    # Pula startuje od teraz, nie od godziny as_of. Katalog zapisu
    # i created_at też idą tym zegarem, więc mecz już rozegrany
    # nie wchodzi w kupon i nie urywa reszty agentów.
    now = _warsaw_now()
    specs = _specs_for(username)
    pool = _CandidatePool(now, allow_unready)
    day_start, day_end = _calendar_day_bounds(now)
    strict = username is not None
    reports = [
        _publish_agent(
            spec, pool, day_start, day_end, dry_run, strict)
        for spec in specs]
    return PublishBatchReport(reports=reports)


def _selector_frame(
        now: datetime,
        allow_unready: bool) -> pd.DataFrame:
    """Return bet verdicts when the artifact may be used.

    ``None`` means the report failed or could not be read. That path
    does not query verdicts. ``allow_unready`` still reads the stored
    digest after a failed gate.
    """
    fingerprint = ready_model_fingerprint(allow_unready=allow_unready)
    if fingerprint is None:
        return fetch_candidates(now)
    logger.info(
        "coupon agent pool=betting_recommendations fingerprint=%s",
        fingerprint)
    return fetch_ready_bets(fingerprint, now)


def _specs_for(username: str | None) -> list[agent_config.AgentSpec]:
    """Return every agent, or the one named entry."""
    agents = list(agent_config.AGENTS)
    if username is None:
        return agents
    matched = [
        spec for spec in agents
        if spec.username == username]
    if not matched:
        raise CouponAgentServiceError(
            f"Unknown coupon agent {username}")
    return matched


def _publish_agent(
        spec: agent_config.AgentSpec,
        pool: _CandidatePool,
        day_start: datetime,
        day_end: datetime,
        dry_run: bool,
        strict: bool) -> PublishReport:
    """Place one agent's coupon or return the reason it was skipped."""
    # INNER JOIN: brak usera i brak bankrolla dają ten sam wynik.
    account = get_by_username(spec.username)
    if account is None:
        return _missing_report(spec.username, dry_run, strict)
    user_id = int(account["user_id"])
    existing = fetch_coupon_leg_sets_between(
        user_id, day_start, day_end)
    if len(existing) >= agent_config.MAX_COUPONS_PER_DAY:
        return _finish(
            spec.username, _STATUS_ALREADY, 0, _REASON_DAY, dry_run)
    candidates = pool.load()
    cfg = _selector_config(spec)
    selection = select_coupon(candidates, cfg)
    count = len(candidates)
    _log_selection(spec.username, selection, dry_run)
    if selection.reason != _STATUS_PUBLISHED:
        return _finish(spec.username, _STATUS_NO_BET, count, None, dry_run)
    if _leg_set(selection) in existing:
        return _finish(
            spec.username, _STATUS_ALREADY, count, _REASON_SAME_LEGS,
            dry_run)
    if dry_run:
        return _finish(
            spec.username, _STATUS_PUBLISHED, count, None, dry_run)
    document = create_coupon_for_user(
        user_id, _coupon_request(selection, cfg))
    return _finish(
        spec.username,
        _STATUS_PUBLISHED,
        count,
        None,
        dry_run,
        coupon_id=int(document["id"]))


def _selector_config(
        spec: agent_config.AgentSpec) -> agent_config.SelectorConfig:
    """Return the agent override or the shared defaults."""
    if spec.selector is None:
        return agent_config.SelectorConfig()
    return spec.selector


def _missing_report(
        username: str,
        dry_run: bool,
        strict: bool) -> PublishReport:
    """Record a missing account. A named publish raises instead."""
    reason = f"System user {username} is missing"
    report = _finish(username, _STATUS_MISSING, 0, reason, dry_run)
    if strict:
        raise CouponAgentServiceError(reason)
    return report


def _finish(
        username: str,
        status: str,
        candidate_count: int,
        skipped_reason: str | None,
        dry_run: bool,
        coupon_id: int | None = None) -> PublishReport:
    """Log one agent outcome and return it."""
    report = PublishReport(
        username=username,
        status=status,
        coupon_id=coupon_id,
        candidate_count=candidate_count,
        skipped_reason=skipped_reason)
    logger.info(
        "coupon agent username=%s status=%s coupon_id=%s "
        "candidate_count=%s dry_run=%s",
        report.username,
        report.status,
        report.coupon_id,
        report.candidate_count,
        dry_run)
    return report


def _coupon_request(
        selection: CouponSelection,
        cfg: agent_config.SelectorConfig) -> dict[str, object]:
    """Map selected legs onto the shared EB-11 coupon payload.

    Each agent leg is one catalog event. Combined prices are out of
    scope, so ``event_ids`` always has length 1.
    """
    legs = [
        {
            "match_id": leg.match_id,
            "event_ids": [leg.event_id],
            # FLOAT 1.01 wraca tuż poniżej progu walidacji zdarzeń.
            "odds": quantize_catalog_odds(leg.odds),
            "bookmaker_id": leg.bookmaker_id,
            "source": "catalog"
        }
        for leg in selection.legs]
    return {
        "stake_input_mode": "units",
        "stake_units": cfg.stake_units,
        "legs": legs
    }


def _leg_set(
        selection: CouponSelection) -> frozenset[tuple[int, int]]:
    """Return the slip identity used by the same-day duplicate lock."""
    return frozenset(
        (leg.match_id, leg.event_id) for leg in selection.legs)


def _log_selection(
        username: str,
        selection: CouponSelection,
        dry_run: bool) -> None:
    """Log legs and score. Dry-run has no other record of the slip."""
    parts = [
        f"{leg.match_id}:{leg.event_id}@{leg.odds}"
        for leg in selection.legs]
    logger.info(
        "coupon agent username=%s dry_run=%s reason=%s score=%s "
        "combined_odds=%s legs=%s",
        username,
        dry_run,
        selection.reason,
        selection.score,
        selection.combined_odds,
        ",".join(parts))


def _warsaw_now() -> datetime:
    """Return the process clock as naive Warsaw wall time."""
    return datetime.now(_WARSAW).replace(tzinfo=None)


def _require_current_warsaw_day(wall: datetime) -> None:
    """Raise when ``wall`` is not today's Warsaw calendar day."""
    # created_at i katalog idą zegarem bazy. Obce as_of sprawdziłoby
    # inną dobę i wstawiło drugi kupon ze stemplem teraźniejszym.
    if wall.date() == _warsaw_now().date():
        return
    raise CouponAgentServiceError(
        "as_of must fall on the current Warsaw day")


def _warsaw_wall_time(as_of: datetime) -> datetime:
    """Return ``as_of`` as a naive Europe/Warsaw clock reading.

    A naive value is already that clock. An aware value is converted,
    because ``matches.game_date`` is stored as Warsaw wall time.
    """
    if not isinstance(as_of, datetime):
        raise ValueError("as_of must be a datetime")
    if as_of.tzinfo is None:
        return as_of
    return as_of.astimezone(_WARSAW).replace(tzinfo=None)


def _calendar_day_bounds(
        wall: datetime) -> tuple[datetime, datetime]:
    """Return ``[midnight, next midnight)`` in Warsaw wall time.

    The end is the next calendar midnight, not ``+ 24h``, so a DST
    change does not merge or split a publishing day.
    """
    aware = wall.replace(tzinfo=_WARSAW)
    start = aware.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.replace(tzinfo=None), end.replace(tzinfo=None)


def _candidates_from_frame(frame: pd.DataFrame) -> list[AgentCandidate]:
    """Copy repository rows into selector legs."""
    if frame.empty:
        return []
    rows = frame.to_dict(orient="records")
    return [_candidate_from_row(row) for row in rows]


def _candidate_from_row(row: dict[str, object]) -> AgentCandidate:
    """Build one leg. Ids and prices are plain Python numbers."""
    return AgentCandidate(
        match_id=_required_int(row, "match_id"),
        event_id=_required_int(row, "event_id"),
        model_id=_required_int(row, "model_id"),
        bookmaker_id=_required_int(row, "bookmaker_id"),
        odds=_required_float(row, "odds"),
        model_probability=_required_float(row, "model_probability"),
        implied_probability=_required_float(row, "implied_probability"),
        value_edge_pp=_required_float(row, "value_edge_pp"),
        kickoff=_as_datetime(row.get("kickoff")),
        league_id=_optional_int(row.get("league_id")),
        league_tier=_optional_int(row.get("league_tier")),
        event_family=_optional_str(row.get("event_family")))


def _required_int(row: dict[str, object], name: str) -> int:
    """Return a required id, or raise when the cell is blank."""
    value = row.get(name)
    if _is_blank(value):
        raise ValueError(f"candidate {name} is missing")
    return int(value)  # type: ignore[arg-type]


def _required_float(row: dict[str, object], name: str) -> float:
    """Return a required number, or raise when the cell is blank."""
    value = row.get(name)
    if _is_blank(value):
        raise ValueError(f"candidate {name} is missing")
    return float(value)  # type: ignore[arg-type]


def _optional_int(value: object) -> int | None:
    """Return an id, or None when the repository left the cell empty."""
    if _is_blank(value):
        return None
    return int(value)  # type: ignore[arg-type]


def _optional_str(value: object) -> str | None:
    """Return a family name, or None when the cell is empty."""
    if _is_blank(value):
        return None
    return str(value)


def _as_datetime(value: object) -> datetime:
    """Return a stdlib datetime. Pandas timestamps are unwrapped."""
    if isinstance(value, pd.Timestamp):
        converted = value.to_pydatetime()
        if isinstance(converted, datetime):
            return converted
    if isinstance(value, datetime):
        return value
    raise ValueError("candidate kickoff must be a datetime")


def _is_blank(value: object) -> bool:
    """Return True for None, NaN and NaT. False for numbers and text."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
