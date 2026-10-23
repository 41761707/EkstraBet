"""Store hockey player game ratings for one match or one season."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Parse the target, fill ratings and print one summary line."""
    # Uruchomienie z katalogu scripts nie widzi pakietu backend.
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.services.hockey_game_rating_fill import fill_match
    from backend.services.hockey_game_rating_fill import fill_season
    from backend.services.hockey_game_rating_fill import (
        resolve_fill_target)

    parser = argparse.ArgumentParser(
        description=(
            "Store hockey player game ratings for one match "
            "or one season"))
    parser.add_argument("--match-id", type=int)
    parser.add_argument("--season-id", type=int)
    args = parser.parse_args(argv)
    try:
        target, target_id = resolve_fill_target(
            args.match_id, args.season_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if target == "match":
        written = fill_match(target_id)
        print(f"matches=1 rows={written} skipped=0")
        return 0
    summary = fill_season(target_id)
    print(
        "matches="
        f"{summary['matches']} rows={summary['rows']} "
        f"skipped={summary['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
