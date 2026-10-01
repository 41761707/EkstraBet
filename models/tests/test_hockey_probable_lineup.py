"""Stage priority for a stored probable lineup."""

import pandas as pd

from models.pipeline.lineups.hockey_probable_lineup import lineup_for_stage


def _rows(*sources: str) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player_id": 10 + index,
            "position": "C" if index == 0 else "G",
            "line": 1,
            "pp_unit": None,
            "is_starting_goalie": 1 if index else 0,
            "confidence": 0.8,
            "source": source}
        for index, source in enumerate(sources)])


def test_initial_prefers_confirmed_over_model() -> None:
    lineup = lineup_for_stage(7, 3, "initial", _rows("MODEL", "CONFIRMED"))
    assert lineup is not None
    assert {player.source for player in lineup.players} == {"CONFIRMED"}


def test_initial_uses_model_when_nothing_stronger_exists() -> None:
    lineup = lineup_for_stage(7, 3, "initial", _rows("MODEL"))
    assert lineup is not None
    assert lineup.players[0].source == "MODEL"
    assert lineup.players[0].start_probability is None


def test_final_ignores_a_model_lineup() -> None:
    assert lineup_for_stage(7, 3, "final", _rows("MODEL")) is None


def test_missing_rows_leave_the_club_without_a_lineup() -> None:
    empty = pd.DataFrame(columns=["source", "player_id", "position"])
    assert lineup_for_stage(7, 3, "initial", empty) is None
