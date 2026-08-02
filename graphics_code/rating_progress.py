"""CLI export of seasonal team rating-progress PNG charts.

Thin wrapper over the rating-progress service and PNG renderer.
Does not read CSV Elo snapshots and never opens an interactive plot window.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.rating_progress_renderer import (  # noqa: E402
    render_rating_progress_png)
from backend.services.rating_progress_service import (  # noqa: E402
    RatingProgressFilterError)
from backend.services.rating_progress_service import (  # noqa: E402
    NonFootballLeagueError)
from backend.services.rating_progress_service import (  # noqa: E402
    get_country_rating_progress)
from backend.services.rating_progress_service import (  # noqa: E402
    get_rating_progress)
from backend.services.rating_progress_service import (  # noqa: E402
    select_teams)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI arguments for league or country PNG export."""
    parser = argparse.ArgumentParser(
        description=(
            "Export seasonal team rating-progress chart as PNG"))
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--league",
        type=int,
        help="League id (single league chart)")
    scope.add_argument(
        "--country",
        type=int,
        help="Country id (all football leagues in that country)")
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season id")
    parser.add_argument(
        "--metric",
        type=str,
        default="elo",
        help="Rating metric (default: elo)")
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Keep top N teams by current rating (1-24)")
    parser.add_argument(
        "--teams",
        type=str,
        default=None,
        help="Comma-separated participant team ids (max 24)")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Output PNG path")
    return parser


def parse_team_ids(raw: str | None) -> list[int] | None:
    """Parse ``1,2,3`` into unique-preserving integer ids."""
    if raw is None:
        return None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise ValueError("Parameter --teams must not be empty")
    try:
        return [int(part) for part in parts]
    except ValueError as exc:
        raise ValueError(
            "Parameter --teams must be a comma-separated list of integers"
        ) from exc


def export_rating_progress_png(
        *,
        league_id: int | None,
        country_id: int | None,
        season_id: int,
        metric: str,
        top: int | None,
        team_ids: list[int] | None,
        output_path: Path) -> Path:
    """Fetch progress, apply filters, render PNG and write ``output_path``."""
    if league_id is not None:
        result = get_rating_progress(league_id, season_id, metric=metric)
        scope = f"league={league_id}"
    elif country_id is not None:
        result = get_country_rating_progress(
            country_id,
            season_id,
            metric=metric)
        scope = f"country={country_id}"
    else:
        raise ValueError("Either league_id or country_id is required")
    if result is None:
        raise LookupError(
            f"No rating progress for {scope} season={season_id}")
    filtered = select_teams(result, team_ids=team_ids, top=top)
    png_bytes = render_rating_progress_png(filtered)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(png_bytes)
    return output_path


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args, export PNG and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        team_ids = parse_team_ids(args.teams)
        output = export_rating_progress_png(
            league_id=args.league,
            country_id=args.country,
            season_id=args.season,
            metric=args.metric,
            top=args.top,
            team_ids=team_ids,
            output_path=Path(args.output))
    except (
            ValueError,
            LookupError,
            NonFootballLeagueError,
            RatingProgressFilterError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Saved rating-progress chart to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
