"""Season rating lists from stored hockey game ratings."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from backend.sports.hockey.game_rating import _round_part


MIN_AVERAGE_GAMES = 5
LIST_LIMIT = 10
SEASON_WINDOW = 0


def build_hockey_rating_board(
    frame: pd.DataFrame,
    window: int) -> dict:
    """Build averages and the ten best and worst games.

    Window 0 keeps every rated game in the frame. 5 and 10 keep
    that many latest games per player. Averages need five games.
    Best and worst games ignore the window.
    """
    if frame.empty:
        return {
            "averages": [],
            "best_games": [],
            "worst_games": []
        }
    rows = [_plain_row(row) for _, row in frame.iterrows()]
    return {
        "averages": _averages(rows, window),
        "best_games": _extreme_games(rows, highest_first=True),
        "worst_games": _extreme_games(rows, highest_first=False)
    }


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
        "date_rank": float(stamp.timestamp())
    }


def _averages(rows: list[dict], window: int) -> list[dict]:
    """Return the ten highest averages that have five games."""
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["player_id"], []).append(row)
    ranked = []
    for games in grouped.values():
        chosen = _latest(games, window)
        if len(chosen) < MIN_AVERAGE_GAMES:
            continue
        ranked.append(_average_entry(chosen))
    ranked.sort(key=_average_sort_key)
    return [_public_average(item) for item in ranked[:LIST_LIMIT]]


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
