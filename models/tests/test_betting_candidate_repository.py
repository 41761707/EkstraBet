"""SELECT contract for prediction-odds candidate pairs."""

from __future__ import annotations

import inspect
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.data import betting_candidate_repository as repository
from models.pipeline.data.betting_candidate_repository import (
    BETTING_CANDIDATE_COLUMNS)
from models.pipeline.data.betting_candidate_repository import (
    fetch_candidates)

_AS_OF = datetime(2026, 8, 1, 0, 0)
_HORIZON = datetime(2026, 9, 1, 0, 0)
_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "TRUNCATE")
_ALLOWED_MODEL_NAMES = (
    "FOOTBALL_RESULT_V2",
    "FOOTBALL_BTTS_V2",
    "FOOTBALL_GOALS_POISSON_V1")


def _filters(**overrides: object) -> BettingStrategyConfig:
    payload: dict[str, object] = {
        "probability_threshold": 0.5,
        "football_sport_name": "Piłka nożna",
        "excluded_model_names": (
            "FOOTBALL_PLAYED_BETTER_V1",
            "FOOTBALL_PLAYED_BETTER_NOXG_V1"),
        "max_brier": 0.24,
        "max_reliability_error": 0.05,
        "min_roi": 0.0}
    payload.update(overrides)
    return BettingStrategyConfig.model_validate(payload)


def _capture(
        filters: BettingStrategyConfig | None = None
        ) -> tuple[str, tuple[object, ...]]:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            params: tuple[object, ...]) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame(columns=list(BETTING_CANDIDATE_COLUMNS))

    with patch.object(repository, "_read_sql", side_effect=_read_sql):
        fetch_candidates(_AS_OF, _HORIZON, filters or _filters())
    return str(captured["query"]), tuple(captured["params"])


def _sql(query: str) -> str:
    return " ".join(query.split())


def test_joins_prediction_to_odds_on_match_and_event() -> None:
    query, _params = _capture()
    text = _sql(query)
    assert "FROM predictions p" in text
    assert "o.event AS event_id" in text
    assert "ON bo.match_id = p.match_id" in text
    assert "AND bo.event_id = p.event_id" in text
    assert "FROM matches mk" in text
    assert "INNER JOIN models md" in text
    assert "INNER JOIN sports s" in text
    assert "wm.game_date AS kickoff" in text
    for column in BETTING_CANDIDATE_COLUMNS:
        assert f"AS {column}" in text


def test_keeps_one_bookmaker_by_price_then_id() -> None:
    query, _params = _capture()
    text = _sql(query)
    window = text.split("ROW_NUMBER() OVER (", 1)[1].split(") AS rn", 1)[0]
    assert "PARTITION BY o.match_id, o.event" in window
    assert "ORDER BY o.odds DESC, o.id ASC" in window
    assert "model_id" not in window
    assert "bookmaker" not in window
    assert "WHERE ranked.rn = 1" in text


def test_drops_a_row_without_prediction_or_odds() -> None:
    query, _params = _capture()
    text = _sql(query).upper()
    assert "LEFT JOIN" not in text
    assert "RIGHT JOIN" not in text
    assert "FULL JOIN" not in text
    assert "FROM PREDICTIONS P" in text
    assert "INNER JOIN" in text


def test_hockey_model_cannot_match_the_football_sport_name() -> None:
    query, params = _capture()
    text = _sql(query)
    assert "s.name = %s" in text
    assert "ON s.id = md.sport_id" in text
    assert params[2] == "Piłka nożna"
    assert "sport_id = 1" not in text
    assert "sport_id = 2" not in text
    assert "Hokej" not in text
    for name in _ALLOWED_MODEL_NAMES:
        assert name not in text


def test_inactive_model_is_excluded() -> None:
    query, _params = _capture()
    assert "md.active = 1" in _sql(query)


def test_excludes_both_played_better_names() -> None:
    query, params = _capture()
    text = _sql(query)
    assert "md.name NOT IN (%s, %s)" in text
    assert params == (
        _AS_OF,
        _HORIZON,
        "Piłka nożna",
        "FOOTBALL_PLAYED_BETTER_V1",
        "FOOTBALL_PLAYED_BETTER_NOXG_V1")
    assert "FOOTBALL_PLAYED_BETTER_V1" not in text
    assert "FOOTBALL_PLAYED_BETTER_NOXG_V1" not in text


def test_rejects_odds_at_most_one_and_probability_outside_percent() -> None:
    query, _params = _capture()
    text = _sql(query)
    assert "WHERE o.odds > 1" in text
    assert "p.value >= 0" in text
    assert "p.value <= 100" in text
    assert "mk.game_date >= %s" in text
    assert "mk.game_date < %s" in text


def test_query_and_module_are_select_only() -> None:
    query, _params = _capture()
    text = _sql(query).upper()
    source = inspect.getsource(repository).upper()
    assert text.startswith("WITH")
    assert "SELECT" in text
    assert ";" not in text
    for word in _WRITE_WORDS:
        assert word not in text
        assert word not in source
    assert "READ_SQL" in source


def test_returns_the_frame_from_the_select() -> None:
    expected = pd.DataFrame([{
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "kickoff": _HORIZON,
        "value_pct": 55.0,
        "odds": 1.9}])

    def _read_sql(
            _query: str,
            _params: tuple[object, ...]) -> pd.DataFrame:
        return expected

    with patch.object(repository, "_read_sql", side_effect=_read_sql):
        frame = fetch_candidates(_AS_OF, _HORIZON, _filters())
    assert list(frame.columns) == list(BETTING_CANDIDATE_COLUMNS)
    assert frame.equals(expected)


def test_rejects_a_window_that_cannot_contain_a_kickoff() -> None:
    filters = _filters()
    with patch.object(repository, "_read_sql") as read_sql:
        with pytest.raises(ValueError, match="earlier than horizon_end"):
            fetch_candidates(_HORIZON, _AS_OF, filters)
        with pytest.raises(ValueError, match="as_of_at must be a datetime"):
            fetch_candidates("2026-08-01", _HORIZON, filters)
        with pytest.raises(
                ValueError,
                match="horizon_end must be a datetime"):
            fetch_candidates(_AS_OF, "2026-09-01", filters)
    read_sql.assert_not_called()
