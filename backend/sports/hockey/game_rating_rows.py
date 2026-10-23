"""Flatten a hockey rating payload into table rows."""

from __future__ import annotations

from decimal import Decimal

from backend.sports.hockey.game_rating import _round_part


_PLAYER_GROUPS = ("forward", "defense", "goalie")
_PART_FIELDS = (
    "production",
    "empty_net",
    "shots",
    "teammate_goals",
    "faceoffs",
    "goals_against",
    "penalties",
    "blocks",
    "goaltending")


def _one_decimal(value: object) -> Decimal:
    """Round one stored number the same way as a rating leaf."""
    return _round_part(Decimal(str(value)))


def _player_row(team_id: int, player: dict) -> dict:
    """Copy one player's stored numbers. Totals are not summed again."""
    group = player["group"]
    if group not in _PLAYER_GROUPS:
        raise ValueError(f"Unsupported player group: {group}")
    parts = player["parts"]
    row = {
        "player_id": int(player["player_id"]),
        "team_id": team_id,
        "player_group": group,
        "offense": _one_decimal(player["offense"]),
        "defense": _one_decimal(player["defense"]),
        "total": _one_decimal(player["total"])
    }
    for field in _PART_FIELDS:
        row[field] = _one_decimal(parts[field])
    return row


def rows_from_rating(payload: dict) -> list[dict]:
    """Build one insert row per player in the rating payload.

    ``team_id`` comes from the team. An empty player list yields no
    rows. A group outside the three known groups, or the same
    ``player_id`` twice in the payload, raises ``ValueError``.
    """
    seen: set[int] = set()
    rows: list[dict] = []
    for team in payload["teams"]:
        team_id = int(team["team_id"])
        for player in team["players"]:
            player_id = int(player["player_id"])
            if player_id in seen:
                raise ValueError(
                    "Duplicate player_id in rating payload: "
                    f"{player_id}")
            seen.add(player_id)
            rows.append(_player_row(team_id, player))
    return rows
