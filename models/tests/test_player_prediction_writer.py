"""Player-prop rows map lines to event ids and upsert."""

from unittest.mock import MagicMock

import pytest

from models.pipeline.persistence.player_prediction_writer import (
    build_player_prediction_rows)
from models.pipeline.persistence.player_prediction_writer import (
    write_player_predictions)


_EVENTS = {
    "sog_over": 190,
    "points_over": 192,
    "assists_over": 194,
    "goals_over": 196}
_RATES = {
    "sog": 3.0,
    "goals": 0.4,
    "assists": 0.5,
    "points": 0.9}


def test_seven_lines_map_to_over_events_and_shrink_as_the_line_grows() -> None:
    rows = build_player_prediction_rows(
        8, 21, 3, 13, _RATES, _EVENTS)
    assert len(rows) == 7
    by_line = {(row.event_id, row.line): row for row in rows}
    assert set(by_line) == {
        (190, 1.5),
        (190, 2.5),
        (190, 3.5),
        (196, 0.5),
        (194, 0.5),
        (192, 0.5),
        (192, 1.5)}
    shots = [
        by_line[(190, line)].probability for line in (1.5, 2.5, 3.5)]
    assert shots[0] > shots[1] > shots[2]
    assert by_line[(192, 0.5)].probability > by_line[(192, 1.5)].probability
    assert by_line[(190, 2.5)].expected_value == pytest.approx(3.0)
    assert all(0.0 <= row.probability <= 100.0 for row in rows)


def test_write_upserts_every_bound_row() -> None:
    rows = build_player_prediction_rows(
        8, 21, 3, 13, _RATES, _EVENTS)
    connection, cursor = _connection()
    written = write_player_predictions(rows, connection)
    statement, bound = cursor.executemany.call_args.args
    assert written == 7
    assert "ON DUPLICATE KEY UPDATE" in statement
    assert "player_predictions" in statement
    assert len(bound) == 7
    assert bound[0][0:5] == (8, 21, 3, 13, 190)
    assert bound[0][5] == pytest.approx(1.5)
    connection.commit.assert_called_once()


def test_write_drops_skaters_absent_from_the_stage_lineup() -> None:
    rows = build_player_prediction_rows(
        8, 21, 3, 13, _RATES, _EVENTS)
    connection, cursor = _connection()
    written = write_player_predictions(
        rows,
        connection,
        match_id=8,
        model_id=13,
        dressed_player_ids={3: {21, 22}, 4: set()})
    assert written == 7
    deletes = [
        call for call in cursor.execute.call_args_list
        if "DELETE FROM player_predictions" in call.args[0]]
    assert len(deletes) == 2
    kept_sql, kept_params = deletes[0].args
    assert "player_id NOT IN" in kept_sql
    assert kept_params == (8, 13, 3, 21, 22)
    dropped_sql, dropped_params = deletes[1].args
    assert "NOT IN" not in dropped_sql
    assert dropped_params == (8, 13, 4)
    connection.commit.assert_called_once()
    cursor.executemany.assert_called_once()


def test_write_rejects_a_probability_above_100() -> None:
    rows = build_player_prediction_rows(
        8, 21, 3, 13, _RATES, _EVENTS)
    broken = rows[0].__class__(
        match_id=8,
        player_id=21,
        team_id=3,
        model_id=13,
        event_id=190,
        line=1.5,
        expected_value=3.0,
        probability=140.0)
    connection, _cursor = _connection()
    with pytest.raises(ValueError, match="0 and 100"):
        write_player_predictions([broken], connection)
    connection.commit.assert_not_called()


def _connection() -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor
