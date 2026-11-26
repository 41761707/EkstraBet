"""Tests for season-format segments and the per-league table."""

from __future__ import annotations

import math
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from models.pipeline.data.evaluation_repository import fetch_league_names
from models.pipeline.data.evaluation_repository import fetch_season_years
from models.pipeline.evaluation.segments import SEASON_FORMAT_CALENDAR_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_SPLIT_YEAR
from models.pipeline.evaluation.segments import SEASON_FORMAT_UNKNOWN
from models.pipeline.evaluation.segments import league_table
from models.pipeline.evaluation.segments import median_within_league_std
from models.pipeline.evaluation.segments import season_format_segments
from models.pipeline.evaluation.segments import weighted_level_error


_REPOSITORY = "models.pipeline.data.evaluation_repository"


def test_season_format_uses_the_slash_and_keeps_order() -> None:
    labels = season_format_segments(
        np.array([11, 12, 13, 14]),
        {11: "2026/2027", 12: "2026", 14: "2025/26"})
    assert list(labels) == [
        SEASON_FORMAT_SPLIT_YEAR,
        SEASON_FORMAT_CALENDAR_YEAR,
        SEASON_FORMAT_UNKNOWN,
        SEASON_FORMAT_SPLIT_YEAR]


def test_season_format_rejects_a_non_integer_id() -> None:
    with pytest.raises(ValueError, match="integers"):
        season_format_segments(np.array([1.5]), {})


def test_league_table_matches_the_hand_formula() -> None:
    rows = league_table(
        np.array([3, 7, 3]),
        np.array([0.2, 0.8, 0.6]),
        np.array([0, 0, 1]),
        np.array([1, 0, 1]),
        {3: "Ekstraklasa"})
    assert [row["league_id"] for row in rows] == [3, 7]
    first = rows[0]
    mean_p = (0.2 + 0.6) / 2.0
    std_p = math.sqrt(
        ((0.2 - mean_p) ** 2 + (0.6 - mean_p) ** 2) / 2.0)
    assert first["league_name"] == "Ekstraklasa"
    assert first["n"] == 2
    assert first["mean_p"] == pytest.approx(mean_p)
    assert first["std_p"] == pytest.approx(std_p)
    assert first["share_final_yes"] == pytest.approx(1.0)
    assert first["actual"] == pytest.approx(0.5)
    assert first["level_error"] == pytest.approx(mean_p - 0.5)
    second = rows[1]
    assert second["league_name"] == "7"
    assert second["n"] == 1
    assert second["mean_p"] == pytest.approx(0.8)
    assert second["std_p"] == pytest.approx(0.0)
    assert second["share_final_yes"] == pytest.approx(0.0)
    assert second["actual"] == pytest.approx(0.0)
    assert second["level_error"] == pytest.approx(0.8)


def test_league_table_rejects_a_different_length() -> None:
    with pytest.raises(ValueError, match="same length"):
        league_table(
            np.array([1, 1]),
            np.array([0.4]),
            np.array([1, 0]),
            np.array([1, 0]),
            {})


def test_weighted_level_error_weights_absolute_errors_by_count() -> None:
    table = league_table(
        np.array([3, 7, 3]),
        np.array([0.2, 0.8, 0.6]),
        np.array([0, 0, 1]),
        np.array([1, 0, 1]),
        {3: "Ekstraklasa"})
    # |0.4 - 0.5| * 2 + |0.8 - 0| * 1, dzielone przez 3 mecze.
    assert weighted_level_error(table) == pytest.approx(1.0 / 3.0)


def test_median_within_league_std_ignores_small_leagues() -> None:
    table = [
        {"n": 30, "std_p": 0.1, "level_error": 0.0},
        {"n": 10, "std_p": 0.9, "level_error": 0.0},
        {"n": 40, "std_p": 0.3, "level_error": 0.0},
        {"n": 50, "std_p": 0.2, "level_error": 0.0}]
    assert median_within_league_std(table) == pytest.approx(0.2)
    assert median_within_league_std(
        table, min_matches=40) == pytest.approx(0.25)


def test_median_within_league_std_rejects_an_empty_selection() -> None:
    table = [{"n": 29, "std_p": 0.2, "level_error": 0.0}]
    with pytest.raises(ValueError, match="at least 30"):
        median_within_league_std(table)


def test_fetch_season_years_reads_labels_and_skips_nulls() -> None:
    captured: dict[str, object] = {}
    frame = pd.DataFrame({
        "id": [11, 12, 13],
        "label": ["2025/26", None, "2026"]})

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[int, ...] = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return frame

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_season_years([12, 11, 11])
    query = str(captured["query"])
    assert "FROM seasons" in query
    assert "years" in query
    assert captured["params"] == (12, 11)
    assert loaded == {11: "2025/26", 13: "2026"}


def test_fetch_league_names_reads_the_league_table() -> None:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[int, ...] = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame({"id": [3], "label": ["Ekstraklasa"]})

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_league_names(np.array([3]))
    query = str(captured["query"])
    assert "FROM leagues" in query
    assert "name" in query
    assert captured["params"] == (3,)
    assert loaded == {3: "Ekstraklasa"}


def test_fetch_season_years_skips_the_database_when_empty() -> None:
    with patch(f"{_REPOSITORY}.get_db_connection") as connect:
        assert fetch_season_years([]) == {}
    connect.assert_not_called()


def _db_context() -> MagicMock:
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return context
