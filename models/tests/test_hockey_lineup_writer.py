"""MODEL writes replace a club's rows and leave a confirmed lineup."""

from unittest.mock import MagicMock

from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.persistence.hockey_lineup_writer import (
    write_probable_lineups)


def test_write_replaces_the_club_and_drops_omitted_players() -> None:
    connection, cursor = _connection([(4, "MODEL")])
    written = write_probable_lineups([_lineup(4, [1])], connection)
    delete = _statement(cursor, "DELETE")
    inserted = cursor.executemany.call_args.args[1]
    player_ids = {row[2] for row in inserted}
    assert written == 1
    assert delete.args[1] == (7,)
    assert player_ids == {1}
    assert 99 not in player_ids
    connection.commit.assert_called_once()


def test_model_does_not_overwrite_confirmed_for_the_same_match() -> None:
    connection, cursor = _connection([(4, "CONFIRMED")])
    written = write_probable_lineups([_lineup(4, [1])], connection)
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert written == 0
    assert not any(sql.strip().startswith("DELETE") for sql in statements)
    cursor.executemany.assert_not_called()
    connection.commit.assert_not_called()


def test_model_overwrites_a_confirmed_lineup_from_an_older_match() -> None:
    connection, cursor = _connection([(3, "CONFIRMED")])
    written = write_probable_lineups([_lineup(4, [1, 2])], connection)
    inserted = cursor.executemany.call_args.args[1]
    assert written == 2
    assert _statement(cursor, "DELETE") is not None
    assert {row[0] for row in inserted} == {4}
    assert {row[8] for row in inserted} == {"MODEL"}
    connection.commit.assert_called_once()


def _lineup(match_id: int, player_ids: list[int]) -> ProbableLineup:
    return ProbableLineup(
        match_id=match_id,
        team_id=7,
        players=[_player(player_id) for player_id in player_ids])


def _player(player_id: int) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="C",
        line=1,
        pp_unit=None,
        is_starting_goalie=None,
        confidence=0.8,
        source="MODEL")


def _connection(
        stored: list[tuple[int, str]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.fetchall.return_value = stored
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def _statement(cursor: MagicMock, prefix: str) -> MagicMock | None:
    for call in cursor.execute.call_args_list:
        if call.args[0].strip().startswith(prefix):
            return call
    return None
