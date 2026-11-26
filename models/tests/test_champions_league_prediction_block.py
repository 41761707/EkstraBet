"""Champions League stays out of prediction batches and offline scores."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from models.pipeline.data.match_history_repository import (
    CHAMPIONS_LEAGUE_ID)
from models.pipeline.evaluation.candidates import _drop_champions_league
from models.pipeline.evaluation.candidates import _test_positions
from models.pipeline.data.match_history_repository import (
    ensure_predictions_allowed)
from models.pipeline.data.match_history_repository import (
    fetch_upcoming_matches)

_REPOSITORY = "models.pipeline.data.match_history_repository"


def test_champions_league_predictions_are_forbidden() -> None:
    with pytest.raises(ValueError, match="league_id=42"):
        ensure_predictions_allowed(CHAMPIONS_LEAGUE_ID)


def test_fetch_upcoming_matches_excludes_champions_league() -> None:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame()

    context = MagicMock()
    context.__enter__.return_value = MagicMock()
    context.__exit__.return_value = False
    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=context), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        fetch_upcoming_matches(1, date(2026, 9, 1), league_id=1)

    query = str(captured["query"])
    params = captured["params"]
    assert "m.league <> %s" in query
    assert isinstance(params, tuple)
    assert params[-1] == CHAMPIONS_LEAGUE_ID


def test_fetch_upcoming_matches_rejects_champions_league_filter() -> None:
    with pytest.raises(ValueError, match="league_id=42"):
        fetch_upcoming_matches(
            1, date(2026, 9, 1), league_id=CHAMPIONS_LEAGUE_ID)


def test_offline_score_skips_champions_league() -> None:
    payload = _window_payload()
    positions = _test_positions(
        payload["dates"], date(2026, 9, 1), "result_v2_champion")
    kept = _drop_champions_league(
        payload, positions, "result_v2_champion")
    assert kept.tolist() == [0, 2]


def test_offline_score_rejects_only_champions_league() -> None:
    payload = _window_payload()
    payload["league_ids"] = np.full(3, CHAMPIONS_LEAGUE_ID)
    positions = _test_positions(
        payload["dates"], date(2026, 9, 1), "result_v2_champion")
    with pytest.raises(ValueError, match="Champions League"):
        _drop_champions_league(
            payload, positions, "result_v2_champion")


def _window_payload() -> dict[str, object]:
    return {
        "dates": np.array(
            ["2026-09-01", "2026-09-02", "2026-09-03"],
            dtype="datetime64[ns]"),
        "league_ids": np.array([1, CHAMPIONS_LEAGUE_ID, 7])}
