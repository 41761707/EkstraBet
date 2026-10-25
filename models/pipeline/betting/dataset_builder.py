"""Walk-forward dataset for one betting meta-model.

The feature matrix is the pre-match allowlist. The label is the
football settlement of the same row and is not a column of that matrix.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from typing import cast

import pandas as pd

from backend.sports.football.markets import market_family
from backend.sports.football.outcome_evaluator import EventFamily
from backend.sports.football.outcome_evaluator import (
    InvalidMatchResultError)
from backend.sports.football.outcome_evaluator import SettlementCandidate
from backend.sports.football.outcome_evaluator import (
    UnsupportedFootballEventError)
from backend.sports.football.outcome_evaluator import (
    evaluate_football_outcome)
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import POST_MATCH_DENYLIST
from models.pipeline.betting.features import build_candidate_features
from models.pipeline.betting.features import feature_schema_fingerprint


SplitRole = Literal["train", "calibration", "test"]
_SPLIT_ROLES: tuple[SplitRole, ...] = ("train", "calibration", "test")
_FOOTBALL_SPORT_ID = 1
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")
_SETTLEMENT_ERRORS = (
    InvalidMatchResultError,
    UnsupportedFootballEventError)
# Kolumny wyniku. Macierz cech ich nie dostaje.
_OUTCOME_COLUMNS = (
    "result",
    "home_team_goals",
    "away_team_goals",
    "event_name")
_IDENTITY_COLUMNS = (
    "prediction_id",
    "odds_id",
    "match_id",
    "event_id")


@dataclass(frozen=True)
class TemporalSplit:
    """One chronological block of whole matches.

    ``match_ids`` follow kickoff. ``row_labels`` are the index labels
    of those matches, in the input order. ``kickoff_from`` and
    ``kickoff_to`` are the earliest and latest kickoff in the block.
    """

    role: SplitRole
    match_ids: tuple[int, ...]
    row_labels: tuple[object, ...]
    kickoff_from: datetime
    kickoff_to: datetime
    match_count: int
    row_count: int

    def __post_init__(self) -> None:
        _validate_split(self)


@dataclass(frozen=True, eq=False)
class BettingDataset:
    """Features, labels and the identity of each kept pair.

    ``features`` omit the score. ``labels`` are 1 when the candidate
    won and 0 otherwise. ``odds`` stays beside the matrix so a later
    report can price a unit stake. The price is not a model column.
    """

    features: pd.DataFrame
    labels: pd.Series
    prediction_id: pd.Series
    odds_id: pd.Series
    match_id: pd.Series
    kickoff: pd.Series
    odds: pd.Series

    def __post_init__(self) -> None:
        _validate_dataset(self)

    def split_frame(self) -> pd.DataFrame:
        """Return the match id and kickoff used to assign splits."""
        return pd.DataFrame({
            "match_id": self.match_id.to_numpy(),
            "kickoff": list(self.kickoff)},
            index=self.features.index)


@dataclass(frozen=True)
class DatasetManifest:
    """Ranges, counts and the feature-schema fingerprint.

    ``splits`` are train, then calibration, then test.
    """

    feature_schema_fingerprint: str
    splits: tuple[TemporalSplit, ...]

    def __post_init__(self) -> None:
        _require_fingerprint(self.feature_schema_fingerprint)
        _require_chronology(self.splits)


def build_betting_dataset(frame: pd.DataFrame) -> BettingDataset:
    """Return pre-match features and a post-match label.

    ``frame`` is a candidate row plus ``result``, ``home_team_goals``,
    ``away_team_goals`` and ``event_name``. The label is
    ``evaluate_football_outcome``. Unfinished, unsupported and invalid
    pairs are left out. Feature columns are the pre-match allowlist.
    """
    checked = _require_frame(frame)
    _require_columns(checked, _IDENTITY_COLUMNS + _OUTCOME_COLUMNS)
    features = build_candidate_features(checked)
    labels = _label_column(checked)
    kept = _kept_index(features, labels)
    return _assemble(checked, features, labels, kept)


def build_walk_forward_splits(
        frame: pd.DataFrame,
        config: BettingTrainingConfig) -> list[TemporalSplit]:
    """Split matches into train, calibration and test by kickoff.

    Every row of a match stays in one block. Shares are rounded on
    the match count, then each cut moves forward to a kickoff change
    so one kickoff stays in the earlier block. The next block starts
    strictly later. ``random_state`` is not used.
    """
    checked = _require_frame(frame)
    _require_columns(checked, ("match_id", "kickoff"))
    _require_config(config)
    ordered = _ordered_matches(checked)
    sizes = _split_sizes(len(ordered), config)
    splits = _assign_splits(checked, ordered, sizes)
    _require_partition(checked, splits)
    _require_chronology(tuple(splits))
    return splits


def build_dataset_manifest(
        features: pd.DataFrame,
        splits: Sequence[TemporalSplit]) -> DatasetManifest:
    """Record split ranges, counts and the feature-column fingerprint.

    ``features`` must be the candidate allowlist. ``splits`` must be
    train, calibration and test, cover each feature row once, and
    share no match.
    """
    _require_feature_matrix(features)
    split_tuple = _split_tuple(splits)
    _require_chronology(split_tuple)
    _require_coverage(features, split_tuple)
    digest = feature_schema_fingerprint(list(features.columns))
    return DatasetManifest(
        feature_schema_fingerprint=digest,
        splits=split_tuple)


def _validate_split(split: TemporalSplit) -> None:
    """Reject a block whose counts and kickoffs disagree."""
    if split.role not in _SPLIT_ROLES:
        raise ValueError("role must be train, calibration or test")
    _require_match_ids(split.match_ids)
    _require_row_labels(split.row_labels)
    if split.match_count != len(split.match_ids):
        raise ValueError("match_count must equal len(match_ids)")
    if split.row_count != len(split.row_labels):
        raise ValueError("row_count must equal len(row_labels)")
    if split.row_count < split.match_count:
        raise ValueError("every match in a split needs a row")
    _require_kickoff_pair(split.kickoff_from, split.kickoff_to)


def _validate_dataset(dataset: BettingDataset) -> None:
    """Reject a table whose columns or indexes disagree."""
    _require_feature_matrix(dataset.features)
    _require_aligned(dataset)
    _require_label_values(dataset.labels)
    _require_id_series(dataset.prediction_id, "prediction_id")
    _require_id_series(dataset.odds_id, "odds_id")
    _require_id_series(dataset.match_id, "match_id")
    _require_kickoff_series(dataset.kickoff)
    _require_price_series(dataset.odds)


def _assemble(
        frame: pd.DataFrame,
        features: pd.DataFrame,
        labels: pd.Series,
        kept: pd.Index) -> BettingDataset:
    """Copy the kept rows into a dataset aligned on one index."""
    selected = features.loc[list(kept)].copy()
    return BettingDataset(
        features=selected,
        labels=_labels_kept(labels, kept),
        prediction_id=_id_series(frame, kept, "prediction_id"),
        odds_id=_id_series(frame, kept, "odds_id"),
        match_id=_id_series(frame, kept, "match_id"),
        kickoff=_kickoff_series(frame, kept),
        odds=_price_series(frame, kept))


def _label_column(frame: pd.DataFrame) -> pd.Series:
    """Settle each row. Missing and unsupported scores stay empty."""
    # Etykieta jest rozliczeniem po meczu i nie wchodzi do macierzy.
    values = [
        _label_value(row)
        for row in frame.itertuples(index=False)]
    return pd.Series(values, index=frame.index, dtype="object")


def _label_value(row: object) -> int | None:
    """Return 1 or 0, or None when the row cannot be settled."""
    candidate = _candidate_or_none(row)
    if candidate is None:
        return None
    try:
        return evaluate_football_outcome(candidate)
    except _SETTLEMENT_ERRORS:
        return None


def _candidate_or_none(row: object) -> SettlementCandidate | None:
    """Build a settlement candidate, or None when the match is open."""
    prediction_id = _field_id(row, "prediction_id")
    _field_id(row, "odds_id")
    match_id = _field_id(row, "match_id")
    event_id = _field_id(row, "event_id")
    family_name = market_family(event_id)
    result = _result_code(_field(row, "result"))
    home_goals = _goals(_field(row, "home_team_goals"))
    away_goals = _goals(_field(row, "away_team_goals"))
    event_name = _event_name(_field(row, "event_name"))
    if family_name is None or result is None or event_name is None:
        return None
    if home_goals is None or away_goals is None:
        return None
    # Modele goli nie są rynkiem kuponu, więc idą ścieżką predykcji.
    return SettlementCandidate(
        record_id=prediction_id,
        target="final_prediction",
        event_id=event_id,
        event_name=event_name,
        family=cast(EventFamily, family_name),
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        match_id=match_id,
        sport_id=_FOOTBALL_SPORT_ID)


def _kept_index(features: pd.DataFrame, labels: pd.Series) -> pd.Index:
    """Keep rows that have both features and a settled label."""
    finished = labels.dropna().index
    return features.index[features.index.isin(finished)]


def _labels_kept(labels: pd.Series, kept: pd.Index) -> pd.Series:
    """Return settled labels aligned to the kept index."""
    values = [int(labels.loc[label]) for label in kept]
    return pd.Series(values, index=kept, dtype="int64", name="label")


def _id_series(
        frame: pd.DataFrame,
        kept: pd.Index,
        name: str) -> pd.Series:
    """Return positive ids aligned to the kept index."""
    values = [
        _positive_id(name, frame.at[label, name])
        for label in kept]
    return pd.Series(values, index=kept, dtype="int64", name=name)


def _kickoff_series(frame: pd.DataFrame, kept: pd.Index) -> pd.Series:
    """Return kickoffs aligned to the kept index."""
    values = [
        _as_kickoff(frame.at[label, "kickoff"])
        for label in kept]
    return pd.Series(values, index=kept, dtype="object", name="kickoff")


def _price_series(frame: pd.DataFrame, kept: pd.Index) -> pd.Series:
    """Return prices above 1 aligned to the kept index."""
    values = [
        _positive_price(frame.at[label, "odds"])
        for label in kept]
    return pd.Series(values, index=kept, dtype="float64", name="odds")


def _ordered_matches(
        frame: pd.DataFrame) -> list[tuple[int, datetime]]:
    """Return one kickoff per match, earliest kickoff first."""
    # Ten sam mecz ma wiele zdarzeń. Okno dostaje go w całości.
    by_match: dict[int, datetime] = {}
    for match_id, kickoff in zip(frame["match_id"], frame["kickoff"]):
        parsed_id = _positive_id("match_id", match_id)
        parsed_kickoff = _as_kickoff(kickoff)
        previous = by_match.get(parsed_id)
        if previous is None:
            by_match[parsed_id] = parsed_kickoff
            continue
        if previous != parsed_kickoff:
            raise ValueError("match_id has more than one kickoff")
    return _sort_matches(by_match)


def _sort_matches(
        by_match: dict[int, datetime]) -> list[tuple[int, datetime]]:
    """Sort matches by kickoff, then by match id."""
    try:
        ordered = sorted(
            by_match.items(),
            key=lambda item: (item[1], item[0]))
    except TypeError as exc:
        raise ValueError("kickoff values must be comparable") from exc
    return ordered


def _split_sizes(
        count: int,
        config: BettingTrainingConfig) -> tuple[int, int, int]:
    """Return train, calibration and test sizes that sum to count."""
    # Cięcie jest po meczach, nie po wierszach. Pusty blok jest błędem.
    if count < 1:
        raise ValueError(
            "not enough matches for train, calibration and test")
    fractions = (
        config.train_fraction,
        config.calibration_fraction,
        config.test_fraction)
    cuts = _cumulative_cuts(count, fractions)
    if cuts != sorted(set(cuts)) or cuts[0] < 1:
        raise ValueError(
            "not enough matches for train, calibration and test")
    sizes = (cuts[0], cuts[1] - cuts[0], count - cuts[1])
    if any(size < 1 for size in sizes):
        raise ValueError(
            "not enough matches for train, calibration and test")
    return sizes


def _cumulative_cuts(
        count: int,
        fractions: tuple[float, float, float]) -> list[int]:
    """Return match indexes after each cumulative share."""
    cuts: list[int] = []
    consumed = 0.0
    for fraction in fractions:
        consumed += fraction
        cuts.append(int(round(consumed * count)))
    cuts[-1] = count
    return cuts


def _assign_splits(
        frame: pd.DataFrame,
        ordered: list[tuple[int, datetime]],
        sizes: tuple[int, int, int]) -> list[TemporalSplit]:
    """Cut the ordered match list into the three roles."""
    cuts = _snap_cuts(ordered, _cumulative_ends(sizes))
    splits: list[TemporalSplit] = []
    start = 0
    for role, end in zip(_SPLIT_ROLES, cuts):
        chunk = ordered[start:end]
        start = end
        splits.append(_make_split(role, chunk, frame))
    return splits


def _cumulative_ends(sizes: tuple[int, int, int]) -> list[int]:
    """Return the match index after each quantile block."""
    ends: list[int] = []
    total = 0
    for size in sizes:
        total += size
        ends.append(total)
    return ends


def _snap_cuts(
        ordered: list[tuple[int, datetime]],
        cuts: list[int]) -> list[int]:
    """Pull each quantile cut forward onto a kickoff change."""
    # Wyniki jednego terminu są znane razem, więc cały kickoff
    # zostaje we wcześniejszym bloku.
    last = len(ordered)
    snapped: list[int] = []
    previous = 0
    for cut in cuts[:-1]:
        boundary = _kickoff_boundary(ordered, cut, previous, last)
        if boundary <= previous or boundary >= last:
            raise ValueError(
                "not enough matches for train, calibration and test")
        snapped.append(boundary)
        previous = boundary
    snapped.append(last)
    return snapped


def _kickoff_boundary(
        ordered: list[tuple[int, datetime]],
        cut: int,
        previous: int,
        last: int) -> int:
    """Return a cut that does not divide one kickoff."""
    if cut <= previous:
        return _end_of_kickoff(ordered, previous, last)
    if cut >= last:
        return cut
    if ordered[cut - 1][1] == ordered[cut][1]:
        return _end_of_kickoff(ordered, cut, last)
    return cut


def _end_of_kickoff(
        ordered: list[tuple[int, datetime]],
        start: int,
        last: int) -> int:
    """Return the index after the kickoff group containing ``start``."""
    if start >= last:
        return start
    kickoff = ordered[start][1]
    index = start + 1
    while index < last and ordered[index][1] == kickoff:
        index += 1
    return index


def _make_split(
        role: SplitRole,
        chunk: list[tuple[int, datetime]],
        frame: pd.DataFrame) -> TemporalSplit:
    """Build one block from a contiguous list of matches."""
    match_ids = tuple(match_id for match_id, _kickoff in chunk)
    row_labels = _row_labels(frame, set(match_ids))
    return TemporalSplit(
        role=role,
        match_ids=match_ids,
        row_labels=row_labels,
        kickoff_from=chunk[0][1],
        kickoff_to=chunk[-1][1],
        match_count=len(match_ids),
        row_count=len(row_labels))


def _row_labels(
        frame: pd.DataFrame,
        match_ids: set[int]) -> tuple[object, ...]:
    """Return index labels of the matches, in input order."""
    labels = []
    for index, match_id in zip(frame.index, frame["match_id"]):
        if _positive_id("match_id", match_id) in match_ids:
            labels.append(index)
    return tuple(labels)


def _require_partition(
        frame: pd.DataFrame,
        splits: Sequence[TemporalSplit]) -> None:
    """Require every input row to belong to exactly one block."""
    labels: list[object] = []
    for split in splits:
        labels.extend(split.row_labels)
    covered = set(labels)
    if len(labels) != len(covered) or covered != set(frame.index):
        raise ValueError("splits must cover each row once")


def _require_chronology(splits: Sequence[TemporalSplit]) -> None:
    """Require the three roles, disjoint matches and kickoff order."""
    if tuple(split.role for split in splits) != _SPLIT_ROLES:
        raise ValueError("splits must be train, calibration, then test")
    seen: list[int] = []
    for split in splits:
        if not isinstance(split, TemporalSplit):
            raise ValueError("splits must contain TemporalSplit values")
        seen.extend(split.match_ids)
    if len(seen) != len(set(seen)):
        raise ValueError("a match appears in two splits")
    for left, right in zip(splits, splits[1:]):
        if not _kickoff_is_before(left.kickoff_to, right.kickoff_from):
            raise ValueError("splits must follow kickoff order")


def _require_coverage(
        features: pd.DataFrame,
        splits: Sequence[TemporalSplit]) -> None:
    """Require the blocks to cover each feature row once."""
    labels: list[object] = []
    for split in splits:
        labels.extend(split.row_labels)
    covered = set(labels)
    if len(labels) != len(covered) or covered != set(features.index):
        raise ValueError("splits must cover each feature row once")


def _split_tuple(
        splits: Sequence[TemporalSplit]) -> tuple[TemporalSplit, ...]:
    """Return the split sequence as a tuple."""
    if isinstance(splits, str) or not isinstance(splits, Sequence):
        raise ValueError("splits must be a sequence")
    return tuple(splits)


def _require_frame(frame: object) -> pd.DataFrame:
    """Reject a value that is not a uniquely indexed frame."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("frame must be a DataFrame")
    if frame.columns.has_duplicates:
        raise ValueError("frame columns must be unique")
    if frame.index.has_duplicates:
        raise ValueError("frame index must be unique")
    return frame


def _require_columns(
        frame: pd.DataFrame,
        columns: tuple[str, ...]) -> None:
    """Reject a frame that lacks the named columns."""
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"frame is missing columns: {joined}")


def _require_config(config: object) -> None:
    """Reject a split config from outside the training contract."""
    if not isinstance(config, BettingTrainingConfig):
        raise ValueError("config must be a BettingTrainingConfig")


def _require_feature_matrix(features: object) -> None:
    """Reject a matrix that is not the pre-match allowlist."""
    if not isinstance(features, pd.DataFrame):
        raise ValueError("features must be a DataFrame")
    columns = list(features.columns)
    if columns != list(FEATURE_COLUMNS):
        raise ValueError("features must use the candidate feature columns")
    denied = set(columns) & (POST_MATCH_DENYLIST | set(_OUTCOME_COLUMNS))
    if denied or "label" in columns:
        raise ValueError("features must not include a post-match column")


def _require_aligned(dataset: BettingDataset) -> None:
    """Require every series to share the feature index."""
    expected = dataset.features.index
    series = (
        ("labels", dataset.labels),
        ("prediction_id", dataset.prediction_id),
        ("odds_id", dataset.odds_id),
        ("match_id", dataset.match_id),
        ("kickoff", dataset.kickoff),
        ("odds", dataset.odds))
    for name, values in series:
        if not isinstance(values, pd.Series):
            raise ValueError(f"{name} must be a Series")
        if not values.index.equals(expected):
            raise ValueError(f"{name} index must match features")


def _require_label_values(labels: pd.Series) -> None:
    """Require every label to be 0 or 1."""
    if labels.name != "label":
        raise ValueError("labels must be named label")
    for value in labels.tolist():
        if isinstance(value, bool) or value not in (0, 1):
            raise ValueError("labels must be 0 or 1")


def _require_id_series(values: pd.Series, name: str) -> None:
    """Require every id in the series to be a positive integer."""
    for value in values.tolist():
        _positive_id(name, value)


def _require_kickoff_series(values: pd.Series) -> None:
    """Require every kickoff to be a datetime."""
    for value in values.tolist():
        if not isinstance(value, datetime):
            raise ValueError("kickoff must be a datetime")


def _require_price_series(values: pd.Series) -> None:
    """Require every stored price to be greater than 1."""
    for value in values.tolist():
        _positive_price(value)


def _require_match_ids(match_ids: tuple[int, ...]) -> None:
    """Reject an empty or repeated match list."""
    if not isinstance(match_ids, tuple) or not match_ids:
        raise ValueError("match_ids must be a non-empty tuple")
    parsed = [_positive_id("match_id", match_id) for match_id in match_ids]
    if len(parsed) != len(set(parsed)):
        raise ValueError("match_ids must be unique")


def _require_row_labels(row_labels: tuple[object, ...]) -> None:
    """Reject an empty or repeated row-label list."""
    if not isinstance(row_labels, tuple) or not row_labels:
        raise ValueError("row_labels must be a non-empty tuple")
    if len(row_labels) != len(set(row_labels)):
        raise ValueError("row_labels must be unique")


def _require_kickoff_pair(start: object, end: object) -> None:
    """Reject a block whose kickoffs are missing or reversed."""
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError("kickoff must be a datetime")
    if _kickoff_is_after(start, end):
        raise ValueError("kickoff_from must not be later than kickoff_to")


def _require_fingerprint(value: object) -> None:
    """Reject a digest that is not lowercase SHA-256 hex."""
    if (
            not isinstance(value, str)
            or len(value) != _SHA256_HEX_LENGTH
            or value != value.lower()
            or any(char not in _HEX_DIGITS for char in value)):
        raise ValueError(
            "feature_schema_fingerprint must be a SHA-256 hex digest")


def _kickoff_is_after(left: datetime, right: datetime) -> bool:
    """Return whether left is strictly later than right."""
    try:
        return left > right
    except TypeError as exc:
        raise ValueError("kickoff values must be comparable") from exc


def _kickoff_is_before(left: datetime, right: datetime) -> bool:
    """Return whether left is strictly earlier than right."""
    try:
        return left < right
    except TypeError as exc:
        raise ValueError("kickoff values must be comparable") from exc


def _field(row: object, name: str) -> object:
    """Return one attribute from a candidate tuple."""
    if not hasattr(row, name):
        raise ValueError(f"frame is missing columns: {name}")
    return getattr(row, name)


def _field_id(row: object, name: str) -> int:
    """Return one positive id from a candidate tuple."""
    return _positive_id(name, _field(row, name))


def _result_code(value: object) -> str | None:
    """Return a result code, or None when the match is not finished."""
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        raise ValueError("result must be a match result code")
    if isinstance(value, int):
        if value in (1, 2):
            return str(value)
        raise ValueError("result must be a match result code")
    if not isinstance(value, str):
        raise ValueError("result must be a match result code")
    code = value.strip()
    if code in ("", "0"):
        return None
    return code


def _goals(value: object) -> int | None:
    """Return a goal count, or None when the score is missing."""
    if _is_missing(value):
        return None
    parsed = _integral(value)
    if parsed is None:
        raise ValueError("goals must be integers")
    return parsed


def _event_name(value: object) -> str | None:
    """Return the event label, or None when it is missing."""
    if _is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError("event_name must be a string")
    return value.strip()


def _positive_id(name: str, value: object) -> int:
    """Return a positive integer id."""
    parsed = _integral(value)
    if parsed is None or parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _positive_price(value: object) -> float:
    """Return a price strictly above 1."""
    if isinstance(value, bool) or _finite(value) is None:
        raise ValueError("odds must be greater than 1")
    number = float(value)
    if number <= 1.0:
        raise ValueError("odds must be greater than 1")
    return number


def _as_kickoff(value: object) -> datetime:
    """Return a datetime kickoff."""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            raise ValueError("kickoff must be a datetime")
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if not isinstance(parsed, pd.Timestamp) or pd.isna(parsed):
        raise ValueError("kickoff must be a datetime")
    return parsed.to_pydatetime()


def _is_missing(value: object) -> bool:
    """Return whether a cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing) if missing is not None else False


def _integral(value: object) -> int | None:
    """Return an int when the value is a whole number."""
    number = _finite(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _finite(value: object) -> float | None:
    """Return a finite float, or None when the value is not one."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number
