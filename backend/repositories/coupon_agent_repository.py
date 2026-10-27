"""Future settleable prediction-odds pairs for the coupon agent."""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from backend.database import get_db_connection
from backend.repositories.tipster_repository import FOOTBALL_SPORT_ID
from backend.repositories.tipster_repository import _FINISHED_RESULTS
from backend.services import coupon_agent_config as agent_config
from backend.services.probability_service import to_unit_probability
from backend.sports.football.event_settlement_registry import (
    is_settleable_event)


logger = logging.getLogger(__name__)
_FINGERPRINT_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


MAX_CANDIDATES = 200
_EDGE_POINTS = 100.0
CANDIDATE_COLUMNS = (
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "odds",
    "model_probability",
    "implied_probability",
    "value_edge_pp",
    "kickoff",
    "league_id",
    "league_tier",
    "event_family")
_SQL_COLUMNS = (
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "odds",
    "probability_pct",
    "kickoff",
    "league_id",
    "league_tier",
    "event_name",
    "event_family")
_NULLABLE_COLUMNS = ("league_id", "league_tier", "event_family")

# Katalog kuponu przyjmuje tylko piłkę; inny sport odpada przy zapisie.
# Predykat rezultatu jest ten sam: 1/X/2 nie wchodzi do puli.
# Limit jest po filtrze rejestru, żeby niesettleable nie zjadł slotu.
_CANDIDATE_SQL = """
    WITH window_matches AS (
        SELECT
            mk.id,
            mk.game_date,
            mk.league
        FROM matches mk
        WHERE mk.game_date >= %s
            AND mk.game_date < %s
            AND mk.sport_id = %s
            AND (
                mk.result IS NULL
                OR mk.result NOT IN (%s, %s, %s)
            )
    )
    SELECT
        p.match_id AS match_id,
        p.event_id AS event_id,
        p.model_id AS model_id,
        bo.bookmaker_id AS bookmaker_id,
        bo.odds AS odds,
        p.value AS probability_pct,
        wm.game_date AS kickoff,
        wm.league AS league_id,
        l.tier AS league_tier,
        e.name AS event_name,
        ef.name AS event_family
    FROM final_predictions fp
    INNER JOIN predictions p
        ON p.id = fp.predictions_id
    INNER JOIN window_matches wm
        ON wm.id = p.match_id
    INNER JOIN (
        SELECT
            ranked.match_id,
            ranked.event_id,
            ranked.bookmaker_id,
            ranked.odds
        FROM (
            SELECT
                o.match_id,
                o.event AS event_id,
                o.bookmaker AS bookmaker_id,
                o.odds,
                ROW_NUMBER() OVER (
                    PARTITION BY o.match_id, o.event
                    ORDER BY o.odds DESC, o.id ASC
                ) AS rn
            FROM odds o
            INNER JOIN window_matches wm_odds
                ON wm_odds.id = o.match_id
            WHERE o.odds > 1
        ) ranked
        WHERE ranked.rn = 1
    ) bo
        ON bo.match_id = p.match_id
        AND bo.event_id = p.event_id
    INNER JOIN events e
        ON e.id = p.event_id
    LEFT JOIN leagues l
        ON l.id = wm.league
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one
        ON efm_one.event_id = e.id
    LEFT JOIN event_families ef
        ON ef.id = efm_one.event_family_id
    ORDER BY
        wm.game_date,
        p.match_id,
        p.event_id,
        p.model_id,
        p.id
"""
_READY_SQL_COLUMNS = (
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "odds",
    "calibrated_probability",
    "kickoff",
    "league_id",
    "league_tier",
    "event_name",
    "event_family")
# Werdykt wskazuje konkretny wiersz kursu. Najlepsza cena z puli
# bazowej mogłaby być inną kwotą niż ta, którą ocenił meta-model.
_READY_BET_SQL = """
    WITH window_matches AS (
        SELECT
            mk.id,
            mk.game_date,
            mk.league
        FROM matches mk
        WHERE mk.game_date >= %s
            AND mk.game_date < %s
            AND mk.sport_id = %s
            AND (
                mk.result IS NULL
                OR mk.result NOT IN (%s, %s, %s)
            )
    )
    SELECT
        p.match_id AS match_id,
        p.event_id AS event_id,
        p.model_id AS model_id,
        o.bookmaker AS bookmaker_id,
        o.odds AS odds,
        br.calibrated_probability AS calibrated_probability,
        wm.game_date AS kickoff,
        wm.league AS league_id,
        l.tier AS league_tier,
        e.name AS event_name,
        ef.name AS event_family
    FROM betting_recommendations br
    INNER JOIN predictions p
        ON p.id = br.prediction_id
    INNER JOIN odds o
        ON o.id = br.odds_id
        AND o.match_id = p.match_id
        AND o.event = p.event_id
    INNER JOIN window_matches wm
        ON wm.id = p.match_id
    INNER JOIN events e
        ON e.id = p.event_id
    LEFT JOIN leagues l
        ON l.id = wm.league
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one
        ON efm_one.event_id = e.id
    LEFT JOIN event_families ef
        ON ef.id = efm_one.event_family_id
    WHERE br.decision = %s
        AND br.model_fingerprint = %s
        AND o.odds > 1
    ORDER BY
        wm.game_date,
        p.match_id,
        p.event_id,
        p.model_id,
        p.id
"""


def ready_model_fingerprint(allow_unready: bool = False) -> str | None:
    """Return the artifact digest, or None for the baseline pool.

    Readiness is the EB-18 gate on ``metrics.json``: Brier, reliability
    and ROI against the strategy file. The digest is ``meta.json`` of
    that same directory. A missing report or a JSON error returns None.
    A failed gate also returns None, unless ``allow_unready`` is true,
    in which case the stored digest is used. The model file is not
    opened. A failed gate does not read ``meta.json`` when readiness
    is required, so an older digest cannot leak into the baseline path.
    """
    if not isinstance(allow_unready, bool):
        raise ValueError("allow_unready must be a bool")
    try:
        fingerprint = _fingerprint_when_ready(allow_unready)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        logger.warning(
            "Coupon agent could not read the betting artifact; "
            "using the prediction-odds pool")
        return None
    if fingerprint is None:
        logger.warning(
            "Coupon agent artifact is not ready; "
            "using the prediction-odds pool")
        return None
    return fingerprint


def fetch_ready_bets(
        model_fingerprint: str,
        now: datetime,
        horizon_days: int = 7) -> pd.DataFrame:
    """Return settleable ``bet`` rows for one ready model digest.

    The window matches ``fetch_candidates``. ``model_probability`` is
    ``calibrated_probability`` on the unit scale, not the stored
    prediction percentage. The price is the odds row named by the
    verdict. ``now`` is the same clock as the baseline pool.
    """
    digest = _require_fingerprint(model_fingerprint)
    horizon_end = _horizon_end(now, horizon_days)
    frame = _read_sql(
        _READY_BET_SQL,
        (
            now,
            horizon_end,
            FOOTBALL_SPORT_ID,
            *_FINISHED_RESULTS,
            "bet",
            digest))
    return _to_candidates(frame, _READY_SQL_COLUMNS)


def fetch_candidates(
        now: datetime,
        horizon_days: int = 7) -> pd.DataFrame:
    """Return settleable published prediction-odds pairs in the window.

    Kickoff is ``matches.game_date`` in the half-open interval
    ``[now, now + horizon_days)``. The window is football only, and a
    final result of 1, X or 2 is omitted, the same rule as the tipster
    catalog. One bookmaker survives per match and event: the highest
    price, then the lowest odds id. Probability is the published
    percentage on the unit scale. Implied probability is ``1 / odds``
    without removing the bookmaker margin. At most ``MAX_CANDIDATES``
    rows are kept, earliest kickoff first. ``event_family`` is the
    catalog family name, not its id.
    """
    horizon_end = _horizon_end(now, horizon_days)
    frame = _read_sql(
        _CANDIDATE_SQL,
        (
            now,
            horizon_end,
            FOOTBALL_SPORT_ID,
            *_FINISHED_RESULTS))
    return _to_candidates(frame)


def _horizon_end(now: datetime, horizon_days: int) -> datetime:
    """Return the exclusive end of a positive day window."""
    if not isinstance(now, datetime):
        raise ValueError("now must be a datetime")
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int):
        raise ValueError("horizon_days must be a positive integer")
    if horizon_days < 1:
        raise ValueError("horizon_days must be a positive integer")
    return now + timedelta(days=horizon_days)


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    """Run one SELECT and return its rows."""
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)


def _to_candidates(
        frame: pd.DataFrame,
        columns: tuple[str, ...] = _SQL_COLUMNS) -> pd.DataFrame:
    """Keep rows the settlement registry and the unit scale accept."""
    _require_sql_columns(frame, columns)
    if frame.empty:
        return _empty_frame()
    records = [
        candidate
        for row in frame.to_dict(orient="records")
        if (candidate := _candidate_or_none(row)) is not None]
    records.sort(key=_sort_key)
    if not records:
        return _empty_frame()
    return _frame_from_records(records[:MAX_CANDIDATES])


def _require_sql_columns(
        frame: pd.DataFrame,
        columns: tuple[str, ...]) -> None:
    """Reject a read that does not match the candidate SELECT."""
    missing = [
        name for name in columns
        if name not in frame.columns]
    if not missing:
        return
    joined = ", ".join(missing)
    raise ValueError(f"candidate rows are missing columns: {joined}")


def _candidate_or_none(row: dict[str, object]) -> dict[str, object] | None:
    """Map one SQL row, or return None when it cannot be a leg."""
    event_id = _optional_int(row.get("event_id"))
    event_name = _optional_str(row.get("event_name"))
    if event_id is None or event_name is None:
        return None
    if not is_settleable_event(event_id, event_name):
        return None
    probability = _stored_probability(row)
    odds = _odds_above_one(row.get("odds"))
    identity = _required_identity(row)
    kickoff = row.get("kickoff")
    if probability is None or odds is None or identity is None:
        return None
    if _is_missing(kickoff):
        return None
    implied = 1.0 / odds
    # implied bez de-vig: marża zostaje w kursie (świadoma decyzja v1)
    return {
        "match_id": identity[0],
        "event_id": event_id,
        "model_id": identity[1],
        "bookmaker_id": identity[2],
        "odds": odds,
        "model_probability": probability,
        "implied_probability": implied,
        "value_edge_pp": (probability - implied) * _EDGE_POINTS,
        "kickoff": kickoff,
        "league_id": _optional_int(row.get("league_id")),
        "league_tier": _optional_int(row.get("league_tier")),
        "event_family": _optional_str(row.get("event_family"))}


def _required_identity(
        row: dict[str, object]) -> tuple[int, int, int] | None:
    """Return match, model and bookmaker ids, or None if one is missing."""
    match_id = _optional_int(row.get("match_id"))
    model_id = _optional_int(row.get("model_id"))
    bookmaker_id = _optional_int(row.get("bookmaker_id"))
    if match_id is None or model_id is None or bookmaker_id is None:
        return None
    return (match_id, model_id, bookmaker_id)


def _sort_key(row: dict[str, object]) -> tuple[object, int, int, int]:
    """Order the pool by kickoff, then by stable ids."""
    return (
        row["kickoff"],
        int(row["match_id"]),
        int(row["event_id"]),
        int(row["model_id"]))


def _stored_probability(row: dict[str, object]) -> float | None:
    """Return the unit probability stored on this candidate row.

    A verdict already uses the unit scale. Dividing that number by
    100 would turn a real chance into a fraction of a percent.
    """
    if "calibrated_probability" in row:
        return _open_unit_value(row.get("calibrated_probability"))
    return _open_unit_probability(row.get("probability_pct"))


def _open_unit_probability(value: object) -> float | None:
    """Convert a DB percentage and keep only the open unit interval."""
    number = _finite_float(value)
    if number is None:
        return None
    unit = to_unit_probability(number)
    if unit <= 0.0 or unit >= 1.0:
        return None
    return unit


def _open_unit_value(value: object) -> float | None:
    """Keep a finite probability inside the open unit interval."""
    number = _finite_float(value)
    if number is None or number <= 0.0 or number >= 1.0:
        return None
    return number


def _fingerprint_when_ready(allow_unready: bool) -> str | None:
    """Return the current digest when the report may be used.

    A failed gate stops before ``meta.json`` unless the caller asked
    to keep the stored verdicts anyway.
    """
    directory = agent_config.BETTING_ARTIFACT_DIR
    metrics = _read_json_object(directory / "metrics.json")
    passed = _metrics_pass(metrics, _strategy_limits())
    if not passed and not allow_unready:
        return None
    # Nieudana bramka nie sięga po meta.json, dopóki caller nie
    # poprosi o werdykty mimo raportu.
    meta = _read_json_object(directory / "meta.json")
    fingerprint = _valid_fingerprint(meta.get("model_fingerprint"))
    if fingerprint is None or passed:
        return fingerprint
    logger.warning(
        "Coupon agent artifact failed the readiness gate; "
        "using stored bet rows anyway")
    return fingerprint


def _read_json_object(path: Path) -> dict[str, object]:
    """Load one JSON object. A missing file or a bad body raises."""
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("artifact JSON must be an object")
    return payload


def _strategy_limits() -> tuple[float, float, float]:
    """Return Brier, reliability and ROI caps from the strategy file."""
    payload = _read_json_object(agent_config.BETTING_STRATEGY_PATH)
    max_brier = _json_number(payload.get("max_brier"))
    max_reliability = _json_number(payload.get("max_reliability_error"))
    min_roi = _json_number(payload.get("min_roi"))
    if max_brier is None or max_reliability is None or min_roi is None:
        raise ValueError("betting strategy gate is incomplete")
    return (max_brier, max_reliability, min_roi)


def _metrics_pass(
        metrics: dict[str, object],
        limits: tuple[float, float, float]) -> bool:
    """Return whether the out-of-sample report meets the EB-18 gate."""
    max_brier, max_reliability, min_roi = limits
    brier = _json_number(metrics.get("brier"))
    reliability = _json_number(metrics.get("reliability"))
    roi = _json_number(metrics.get("roi"))
    if brier is None or reliability is None or roi is None:
        return False
    if brier < 0.0 or brier > 1.0:
        return False
    if reliability < 0.0 or reliability > 1.0:
        return False
    if roi < -1.0:
        return False
    if brier > max_brier or reliability > max_reliability:
        return False
    return roi >= min_roi


def _json_number(value: object) -> float | None:
    """Return a finite JSON number. Text and booleans are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _valid_fingerprint(value: object) -> str | None:
    """Return a SHA-256 hex digest, or None when the text is not one."""
    if not isinstance(value, str):
        return None
    if _FINGERPRINT_HEX.fullmatch(value) is None:
        return None
    return value


def _require_fingerprint(value: str) -> str:
    """Reject a digest that cannot be a stored model file id."""
    digest = _valid_fingerprint(value)
    if digest is None:
        raise ValueError(
            "model_fingerprint must be a 64-character SHA-256 hex string")
    return digest


def _odds_above_one(value: object) -> float | None:
    """Keep a price that can be inverted into an implied probability."""
    number = _finite_float(value)
    if number is None or number <= 1.0:
        return None
    return number


def _finite_float(value: object) -> float | None:
    """Return a finite float, or None for a blank or non-numeric value."""
    if isinstance(value, bool) or _is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _optional_int(value: object) -> int | None:
    """Return an int, or None when the SQL value is blank."""
    if isinstance(value, bool) or _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    """Return a stripped string, or None when the SQL value is blank."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _is_missing(value: object) -> bool:
    """Return True for None, NaN, NaT and a blank string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)


def _frame_from_records(records: list[dict[str, object]]) -> pd.DataFrame:
    """Build the public frame and keep nullable fields as None."""
    columns = {
        name: [row[name] for row in records]
        for name in CANDIDATE_COLUMNS}
    frame = pd.DataFrame(columns)
    for name in _NULLABLE_COLUMNS:
        frame[name] = [
            None if _is_missing(value) else value
            for value in frame[name].tolist()]
    return frame.loc[:, list(CANDIDATE_COLUMNS)]


def _empty_frame() -> pd.DataFrame:
    """Return a zero-row frame with the public candidate columns."""
    return pd.DataFrame(columns=list(CANDIDATE_COLUMNS))
