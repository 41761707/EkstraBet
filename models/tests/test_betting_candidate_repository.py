"""SELECT contract for prediction-odds candidate pairs."""

from __future__ import annotations

import inspect
import math
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from backend.sports.football.markets import DEVIG_MARKETS
from backend.sports.football.markets import EXACT_GOALS_GROUP_EVENT_ID
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
        return pd.DataFrame(columns=list(repository._SQL_FRAME_COLUMNS))

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
    for column in repository._SQL_FRAME_COLUMNS:
        assert f"AS {column}" in text
    assert "AS devig_probability" not in text


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


def test_returns_candidates_with_fair_probability() -> None:
    raw = _raw_row(implied=0.5, implied_sum=7.0 / 6.0, priced_outcomes=3)
    incomplete = _raw_row(
        prediction_id=11,
        event_id=8,
        implied=0.5,
        implied_sum=1.2,
        priced_outcomes=1,
        market_size=2)

    def _read_sql(
            _query: str,
            _params: tuple[object, ...]) -> pd.DataFrame:
        return pd.DataFrame([raw, incomplete])

    with patch.object(repository, "_read_sql", side_effect=_read_sql):
        frame = fetch_candidates(_AS_OF, _HORIZON, _filters())
    assert list(frame.columns) == list(BETTING_CANDIDATE_COLUMNS)
    assert "implied_sum" not in frame.columns
    assert frame["league_id"].iloc[0] == 7
    assert frame["devig_probability"].iloc[0] == pytest.approx(3.0 / 7.0)
    assert math.isnan(frame["devig_probability"].iloc[1])


def test_fair_price_uses_one_book_before_the_ranking() -> None:
    query, _params = _capture()
    text = _sql(query)
    assert text.index("AS implied_sum") < text.index("WHERE ranked.rn = 1")
    assert "SUM(1.0 / o.odds) OVER (" in text
    assert "PARTITION BY o.match_id, o.bookmaker," in text
    assert "mk.league" in text
    assert "AS league_id" in text
    fair_window = text.split("SUM(1.0 / o.odds) OVER (", 1)[1]
    fair_window = fair_window.split(") AS implied_sum", 1)[0]
    assert "model_id" not in fair_window
    assert "p." not in fair_window
    for name, event_ids in DEVIG_MARKETS:
        listed = ", ".join(str(event_id) for event_id in sorted(event_ids))
        assert f"WHEN o.event IN ({listed}) THEN '{name}'" in text
    assert str(EXACT_GOALS_GROUP_EVENT_ID) not in text


def _raw_row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 7,
        "kickoff": _HORIZON,
        "value_pct": 55.0,
        "odds": 2.0,
        "implied": 0.5,
        "implied_sum": 7.0 / 6.0,
        "priced_outcomes": 3,
        "market_size": 3}
    payload.update(overrides)
    return payload


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
