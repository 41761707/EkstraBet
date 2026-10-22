"""Pre-match features for one prediction-odds candidate."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

import pandas as pd

from backend.sports.football.markets import market_family


NUMERIC_FEATURE_COLUMNS = (
    "model_probability",
    "implied_probability",
    "devig_probability",
    "edge",
    "ev",
    "kickoff_weekday_sin",
    "kickoff_weekday_cos",
    "kickoff_hour_sin",
    "kickoff_hour_cos")
CATEGORICAL_FEATURE_COLUMNS = (
    "model_id",
    "market_family",
    "league_id")
FEATURE_COLUMNS = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS

# Kolumny wyniku i oceny po meczu. Nie wchodzą do macierzy cech.
POST_MATCH_DENYLIST = frozenset({
    "result",
    "outcome",
    "label",
    "home_goals",
    "away_goals",
    "home_team_goals",
    "away_team_goals",
    "home_team_xg",
    "away_team_xg",
    "assessment",
    "final_assessment"})
_POST_MATCH_TOKENS = ("result", "goal", "outcome", "assessment", "xg")
_WEEKDAY_CYCLE = 7.0
_HOUR_CYCLE = 24.0

_REQUIRED_COLUMNS = (
    "value_pct",
    "odds",
    "kickoff",
    "match_id",
    "bookmaker_id",
    "event_id",
    "model_id",
    "league_id",
    "devig_probability")


def build_candidate_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the pre-match feature matrix for candidate rows.

    The index of rows that pass the pair checks is preserved. Odds at
    most 1, a probability outside 0-100, and a missing pair are dropped.
    Post-match columns on the input are ignored. ``devig_probability``
    is copied from the candidate row. This function does not rebuild an
    overround from the selected prices.
    """
    _require_columns(frame)
    _reject_denied_feature_names()
    usable = _usable_rows(frame)
    return _feature_frame(usable)


def feature_schema_fingerprint(columns: Sequence[str]) -> str:
    """Return the SHA-256 hex digest of the sorted column names.

    Names are joined with newlines and encoded as UTF-8. Order of the
    input does not change the digest.
    """
    payload = "\n".join(_sorted_column_names(columns)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(frame: pd.DataFrame) -> None:
    """Reject a frame that is not the candidate contract."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("frame must be a DataFrame")
    missing = [
        name for name in _REQUIRED_COLUMNS
        if name not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"frame is missing columns: {joined}")
    if frame.columns.has_duplicates:
        raise ValueError("frame columns must be unique")


def _reject_denied_feature_names() -> None:
    """Stop if the allowlist itself contains a post-match name."""
    if not set(FEATURE_COLUMNS).isdisjoint(POST_MATCH_DENYLIST):
        raise RuntimeError("feature allowlist contains a post-match name")
    for name in FEATURE_COLUMNS:
        lowered = name.lower()
        for token in _POST_MATCH_TOKENS:
            if token in lowered:
                raise RuntimeError(
                    f"feature name {name} looks post-match")


def _usable_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep pairs with a percent probability and a price above 1."""
    value = pd.to_numeric(frame["value_pct"], errors="coerce")
    odds = pd.to_numeric(frame["odds"], errors="coerce")
    valid = _valid_pair(value, odds)
    usable = frame.loc[valid, list(_REQUIRED_COLUMNS)].copy()
    usable["value_pct"] = value.loc[valid].astype("float64")
    usable["odds"] = odds.loc[valid].astype("float64")
    return usable


def _valid_pair(value: pd.Series, odds: pd.Series) -> pd.Series:
    """Mark rows whose probability and price can form a candidate."""
    finite_value = value.map(_finite_number)
    finite_odds = odds.map(_finite_number)
    return (
        finite_value
        & finite_odds
        & value.ge(0.0)
        & value.le(100.0)
        & odds.gt(1.0))


def _feature_frame(usable: pd.DataFrame) -> pd.DataFrame:
    """Assemble allowlisted columns for the rows that remain."""
    if usable.empty:
        return _empty_features()
    probability = usable["value_pct"] / 100.0
    odds = usable["odds"]
    implied = 1.0 / odds
    weekday_sin, weekday_cos = _cyclic_clock(usable["kickoff"], "weekday")
    hour_sin, hour_cos = _cyclic_clock(usable["kickoff"], "hour")
    features = pd.DataFrame(index=usable.index)
    features["model_probability"] = probability
    features["implied_probability"] = implied
    features["devig_probability"] = _devig_column(usable["devig_probability"])
    features["edge"] = probability - implied
    features["ev"] = probability * odds - 1.0
    features["kickoff_weekday_sin"] = weekday_sin
    features["kickoff_weekday_cos"] = weekday_cos
    features["kickoff_hour_sin"] = hour_sin
    features["kickoff_hour_cos"] = hour_cos
    features["model_id"] = _id_labels(usable["model_id"])
    features["market_family"] = _family_labels(usable["event_id"])
    features["league_id"] = _id_labels(usable["league_id"])
    return features.loc[:, list(FEATURE_COLUMNS)]


def _empty_features() -> pd.DataFrame:
    """Return a zero-row matrix with the stable feature schema."""
    features = pd.DataFrame(columns=list(FEATURE_COLUMNS))
    for name in NUMERIC_FEATURE_COLUMNS:
        features[name] = features[name].astype("float64")
    return features


def _cyclic_clock(
        kickoff: pd.Series,
        part: str) -> tuple[pd.Series, pd.Series]:
    """Return sine and cosine of the kickoff weekday or clock time.

    Monday is 0. The hour angle is hours plus minutes, over 24.
    A missing kickoff leaves both parts empty.
    """
    # Predykcja i kurs nie mają czasu kwotowania, więc nie ma godzin
    # do meczu. Sinus i cosinus składają niedzielę z poniedziałkiem.
    parsed = pd.to_datetime(kickoff, errors="coerce")
    if part == "weekday":
        values = parsed.dt.dayofweek.astype("float64")
        cycle = _WEEKDAY_CYCLE
    else:
        # Minuta przesuwa kąt, więc 18:30 nie wpada w punkt 18:00.
        hour = parsed.dt.hour.astype("float64")
        minute = parsed.dt.minute.astype("float64")
        values = hour + minute / 60.0
        cycle = _HOUR_CYCLE
    return _cyclic_pair(values, cycle)


def _cyclic_pair(
        values: pd.Series,
        cycle: float) -> tuple[pd.Series, pd.Series]:
    """Map a linear clock onto one full turn."""
    angle = 2.0 * math.pi * values / cycle
    sine = angle.map(_sine).astype("float64")
    cosine = angle.map(_cosine).astype("float64")
    return sine, cosine


def _devig_column(values: pd.Series) -> pd.Series:
    """Keep a fair probability in (0, 1] and clear every other value."""
    numbers = pd.to_numeric(values, errors="coerce")
    valid = numbers.map(_finite_number) & numbers.gt(0.0) & numbers.le(1.0)
    return numbers.where(valid).astype("float64")


def _family_labels(event_ids: pd.Series) -> pd.Series:
    """Map event ids to family names. Unknown ids stay empty."""
    labels = []
    for event_id in event_ids.tolist():
        parsed = _integral(event_id)
        if parsed is None:
            labels.append(None)
            continue
        labels.append(market_family(parsed))
    return pd.Series(labels, index=event_ids.index, dtype="object")


def _id_labels(values: pd.Series) -> pd.Series:
    """Render ids as categorical labels. Missing ids stay empty."""
    labels = []
    for value in values.tolist():
        parsed = _integral(value)
        labels.append(None if parsed is None else str(parsed))
    return pd.Series(labels, index=values.index, dtype="object")


def _sorted_column_names(columns: Sequence[str]) -> list[str]:
    """Return column names sorted for a stable digest."""
    if isinstance(columns, str):
        raise ValueError("columns must be a sequence of names")
    names: list[str] = []
    for name in columns:
        if not isinstance(name, str) or name != name.strip() or not name:
            raise ValueError("column names must be non-empty strings")
        if "\n" in name:
            raise ValueError("column names must not contain newlines")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("column names must be unique")
    names.sort()
    return names


def _sine(value: object) -> float:
    """Return sine, or NaN when the angle is missing."""
    if not _finite_number(value):
        return math.nan
    return math.sin(float(value))


def _cosine(value: object) -> float:
    """Return cosine, or NaN when the angle is missing."""
    if not _finite_number(value):
        return math.nan
    return math.cos(float(value))


def _finite_number(value: object) -> bool:
    """Return whether the value is a finite int or float."""
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _integral(value: object) -> int | None:
    """Return an int when the value is a whole number."""
    if not _finite_number(value):
        return None
    if isinstance(value, bool) or not float(value).is_integer():
        return None
    return int(value)
