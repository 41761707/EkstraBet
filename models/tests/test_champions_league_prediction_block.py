"""Champions League stays out of model prediction batches."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
import pytest

from models.pipeline.data.match_history_repository import (
    CHAMPIONS_LEAGUE_ID)
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
