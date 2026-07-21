"""Focused tests for future prediction mapping and persistence."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from models.pipeline.core.config import BttsPrediction
from models.pipeline.core.config import GoalsPoissonPrediction
from models.pipeline.core.config import PredictionWriteRow
from models.pipeline.core.config import ResultPrediction
from models.pipeline.persistence.prediction_writer import (
    map_predictions_to_rows,
    write_predictions)


def _event_ids() -> dict[str, int]:
    keys = [
        "result_home", "result_draw", "result_away",
        "btts_yes", "btts_no",
        "goals_0", "goals_1", "goals_2", "goals_3",
        "goals_4", "goals_5", "goals_6_plus",
        "over_25", "under_25"
    ]
    mapping = {key: index + 1 for index, key in enumerate(keys)}
    labels = ["0", "1", "2", "3", "4", "5+"]
    next_id = len(mapping) + 1
    for home in labels:
        for away in labels:
            mapping[f"exact:{home}:{away}"] = next_id
            next_id += 1
    return mapping


def _prediction() -> dict[str, object]:
    matrix = np.zeros((6, 6), dtype=float)
    matrix[2, 1] = 0.7
    matrix[0, 0] = 0.3
    return {
        "result": ResultPrediction(0.8, 0.1, 0.1),
        "btts": BttsPrediction(0.7, 0.3),
        "goals_poisson": GoalsPoissonPrediction(
            lambda_home=2.0,
            lambda_away=1.0,
            score_matrix=matrix,
            total_buckets={
                "0": 0.1,
                "1": 0.1,
                "2": 0.1,
                "3": 0.5,
                "4": 0.1,
                "5": 0.05,
                "6+": 0.05
            },
            over_25=0.7,
            under_25=0.3,
            top_exact_scores=[("2:1", 0.7)])
    }


def test_mapping_selects_exact_from_poisson_not_result() -> None:
    event_ids = _event_ids()
    rows = map_predictions_to_rows(
        100,
        _prediction(),
        {"result": 10, "btts": 11, "goals_poisson": 12},
        event_ids,
        select_finals=True)
    final_ids = {row.event_id for row in rows if row.is_final}

    assert event_ids["result_home"] in final_ids
    assert event_ids["exact:2:1"] in final_ids
    assert event_ids["exact:0:0"] not in final_ids
    assert len(final_ids) == 5


def test_mapping_supports_partial_result_family() -> None:
    rows = map_predictions_to_rows(
        100,
        {"result": ResultPrediction(0.5, 0.3, 0.2)},
        {"result": 10},
        {
            "result_home": 1,
            "result_draw": 2,
            "result_away": 3
        },
        select_finals=False)

    assert [row.event_id for row in rows] == [1, 2, 3]
    assert all(not row.is_final for row in rows)


def test_writer_converts_probability_to_percentage_and_upserts_final() -> None:
    cursor = MagicMock()
    cursor.lastrowid = 321
    connection = MagicMock()
    connection.cursor.return_value = cursor
    rows = [
        PredictionWriteRow(
            match_id=100,
            model_id=10,
            event_id=1,
            value=0.625,
            is_final=True)
    ]

    written = write_predictions(rows, connection)

    assert written == 1
    prediction_call = cursor.execute.call_args_list[0]
    assert "ON DUPLICATE KEY UPDATE" in prediction_call.args[0]
    assert prediction_call.args[1] == (100, 1, 10, 62.5)
    clear_call = cursor.execute.call_args_list[1]
    assert "DELETE" in clear_call.args[0]
    assert "final_predictions" in clear_call.args[0]
    assert clear_call.args[1] == (100, 10, 1)
    final_call = cursor.execute.call_args_list[2]
    assert "final_predictions" in final_call.args[0]
    assert "INSERT" in final_call.args[0]
    assert final_call.args[1] == (321,)
    connection.commit.assert_called_once()


def test_writer_clears_stale_family_finals_before_selecting_new() -> None:
    cursor = MagicMock()
    cursor.lastrowid = 0
    cursor.fetchone.side_effect = [{"id": 11}, {"id": 12}, {"id": 13}]
    connection = MagicMock()
    connection.cursor.return_value = cursor
    rows = [
        PredictionWriteRow(100, 10, 1, 0.2, False),
        PredictionWriteRow(100, 10, 2, 0.7, True),
        PredictionWriteRow(100, 10, 3, 0.1, False)
    ]

    write_predictions(rows, connection)

    sql_statements = [call.args[0] for call in cursor.execute.call_args_list]
    clear_calls = [
        call for call in cursor.execute.call_args_list
        if "DELETE" in call.args[0] and "final_predictions" in call.args[0]
    ]
    assert len(clear_calls) == 1
    assert clear_calls[0].args[1][:2] == (100, 10)
    assert set(clear_calls[0].args[1][2:]) == {1, 2, 3}
    insert_finals = [
        call for call in cursor.execute.call_args_list
        if "INSERT INTO final_predictions" in call.args[0]
    ]
    assert len(insert_finals) == 1
    assert insert_finals[0].args[1] == (12,)
    assert sum(1 for sql in sql_statements if "INSERT INTO predictions" in sql) == 3
