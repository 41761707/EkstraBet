"""Season rating lists from stored hockey game ratings."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from backend.sports.hockey.game_rating import (
    GROUP_DEFENSE,
    GROUP_FORWARD,
    GROUP_GOALIE,
    _round_part,
    player_group)


MIN_AVERAGE_GAMES = 5
LIST_LIMIT = 10
SEASON_WINDOW = 0


def build_hockey_rating_board(
    frame: pd.DataFrame,
    window: int) -> dict:
    """Build average charts and the best and worst nights by position.

    Window 0 keeps every rated game. 5 and 10 keep that many
    latest games per player. Averages need five games.
    Best and worst nights ignore the window and stay inside
    one position group.
    """
    if frame.empty:
        return _empty_board()
    rows = [_plain_row(row) for _, row in frame.iterrows()]
    ranked = _ranked_averages(rows, window)
    board = _empty_board()
    board["averages"] = _take_averages(ranked, _average_sort_key)
    board["worst_averages"] = _take_averages(
        ranked,
        _worst_average_sort_key)
    for group in (GROUP_FORWARD, GROUP_DEFENSE, GROUP_GOALIE):
        chosen = [row for row in rows if row["player_group"] == group]
        board[group] = {
            "best_games": _extreme_games(chosen, highest_first=True),
            "worst_games": _extreme_games(chosen, highest_first=False)
        }
    return board


def _plain_row(row: pd.Series) -> dict:
    """Normalize one frame row for sorting and display."""
    stamp = pd.Timestamp(row["game_date"])
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_name": str(row["team_name"]),
        "match_id": int(row["match_id"]),
        "match_date": stamp.strftime("%d.%m.%Y"),
        "opponent_name": str(row["opponent_name"]),
        "total": float(row["total"]),
        "date_rank": float(stamp.timestamp()),
        "player_group": _group_of(row)
    }


def _empty_position() -> dict:
    """Best and worst lists before any night is classified."""
    return {"best_games": [], "worst_games": []}


def _empty_board() -> dict:
    """Board with every chart present and empty."""
    return {
        "averages": [],
        "worst_averages": [],
        "forward": _empty_position(),
        "defense": _empty_position(),
        "goalie": _empty_position()
    }


def _group_of(row: pd.Series) -> str:
    """Classify the night the same way as the match rating charts."""
    shots = row["shots_against"] if "shots_against" in row.index else None
    if shots is None or pd.isna(shots):
        shot_count = None
    else:
        shot_count = int(shots)
    return player_group(
        _optional_text(row, "roster_position"),
        _optional_text(row, "player_position"),
        shot_count)


def _optional_text(row: pd.Series, column: str) -> str | None:
    """Return a position cell, or None when it is missing."""
    if column not in row.index or pd.isna(row[column]):
        return None
    text = str(row[column]).strip()
    if text == "":
        return None
    return text


def _ranked_averages(rows: list[dict], window: int) -> list[dict]:
    """Return every average that has five games."""
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["player_id"], []).append(row)
    ranked = []
    for games in grouped.values():
        chosen = _latest(games, window)
        if len(chosen) < MIN_AVERAGE_GAMES:
            continue
        ranked.append(_average_entry(chosen))
    return ranked


def _take_averages(ranked: list[dict], key) -> list[dict]:
    """Keep ten averages in the order of ``key``."""
    ordered = sorted(ranked, key=key)
    return [_public_average(item) for item in ordered[:LIST_LIMIT]]


def _latest(games: list[dict], window: int) -> list[dict]:
    """Keep the newest games. Window 0 keeps the whole list."""
    ordered = sorted(games, key=_newest_first)
    if window == SEASON_WINDOW:
        return ordered
    return ordered[:window]


def _newest_first(row: dict) -> tuple:
    """Later date first, then the smaller player id."""
    return (-row["date_rank"], row["player_id"], row["match_id"])


def _average_entry(chosen: list[dict]) -> dict:
    """Average ``total`` and keep the name from the latest game."""
    latest = chosen[0]
    raw = sum(
        (Decimal(str(row["total"])) for row in chosen),
        Decimal("0"))
    average = float(_round_part(raw / Decimal(len(chosen))))
    return {
        "player_id": latest["player_id"],
        "player_name": latest["player_name"],
        "team_name": latest["team_name"],
        "games": len(chosen),
        "average": average,
        "date_rank": latest["date_rank"]
    }


def _average_sort_key(item: dict) -> tuple:
    """Higher average, then the later night, then player id."""
    return (-item["average"], -item["date_rank"], item["player_id"])


def _worst_average_sort_key(item: dict) -> tuple:
    """Lower average, then the later night, then player id."""
    return (item["average"], -item["date_rank"], item["player_id"])


def _public_average(item: dict) -> dict:
    """Drop the sort key before the row leaves this module."""
    return {
        "player_id": item["player_id"],
        "player_name": item["player_name"],
        "team_name": item["team_name"],
        "games": item["games"],
        "average": item["average"]
    }


def _extreme_games(rows: list[dict], highest_first: bool) -> list[dict]:
    """Return ten games, best first or worst first."""
    ordered = sorted(rows, key=lambda row: _game_sort_key(row, highest_first))
    return [_public_game(row) for row in ordered[:LIST_LIMIT]]


def _game_sort_key(row: dict, highest_first: bool) -> tuple:
    """Total, then the later date, then player id."""
    total = -row["total"] if highest_first else row["total"]
    return (total, -row["date_rank"], row["player_id"])


def _public_game(row: dict) -> dict:
    """One player-night for the best and worst lists."""
    return {
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "match_id": row["match_id"],
        "match_date": row["match_date"],
        "opponent_name": row["opponent_name"],
        "total": row["total"]
    }
