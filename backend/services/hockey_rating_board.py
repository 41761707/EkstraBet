"""Read the stored hockey rating board for one season."""

from backend.repositories.hockey_game_rating_repository import (
    fetch_hockey_rating_rows)
from backend.sports.hockey.rating_board import build_hockey_rating_board


def get_hockey_rating_board(season_id: int, window: int) -> dict:
    """Return averages and extreme games for a season window."""
    frame = fetch_hockey_rating_rows(season_id)
    board = build_hockey_rating_board(frame, window)
    return {
        "season_id": season_id,
        "window": window,
        "averages": board["averages"],
        "worst_averages": board["worst_averages"],
        "forward": board["forward"],
        "defense": board["defense"],
        "goalie": board["goalie"]
    }
