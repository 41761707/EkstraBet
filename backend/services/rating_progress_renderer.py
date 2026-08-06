"""Render rating-progress DTOs to PNG bytes without a GUI.

Uses the Matplotlib Agg backend and an in-memory buffer so API/CLI
exports never open an interactive window. Colors are defined locally
to mirror the frontend chart palette on a dark branded background.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure

from backend.sports.football.rating_progress import RatingProgressResult
from backend.sports.football.rating_progress import TeamRatingProgress

# Rozmiar bazowy; wysokość rośnie z liczbą drużyn (limit pamięci).
FIGURE_WIDTH = 14.0
FIGURE_HEIGHT_MIN = 8.0
FIGURE_HEIGHT_MAX = 20.0
FIGURE_HEIGHT_BASE = 7.0
INCHES_PER_EXTRA_TEAM = 0.42
DENSE_SPAN_PER_TEAM = 20.0
FIGURE_DPI = 150
LABEL_MIN_GAP_RATIO = 0.012
LABEL_TARGET_PIXELS = 12.0
LABEL_MAX_EXTRA_SPAN_RATIO = 0.4
LEADER_OFFSET_THRESHOLD = 2.5
LABEL_FONTSIZE_BASE = 11
LABEL_FONTSIZE_MID = 10
LABEL_FONTSIZE_MIN = 9
RIGHT_MARGIN_FRACTION = 0.16
LEADER_X_FRACTION = 0.012
# Napisy blisko osi — bez dużych pustych pasów.
TITLE_Y = 0.965
SUBTITLE_Y = 0.925
FOOTER_Y = 0.02
X_LABEL_PAD = 8
SAVE_PAD_INCHES = 0.25
# [left, bottom, right, top]
TIGHT_LAYOUT_RECT = (0.04, 0.11, 0.98, 0.88)

BACKGROUND_COLOR = "#0b1120"
AXES_FACE_COLOR = "#111827"
FOREGROUND_COLOR = "#e2e8f0"
GRID_COLOR = "#334155"
SPINE_COLOR = "#475569"

# Semantyczne kolory odpowiadające frontend/src/lib/chartColors.ts.
CHART_COLOR_NEGATIVE = "#d95757"
CHART_COLOR_POSITIVE = "#52b788"
CHART_COLOR_DRAW = "#d9b44a"
CHART_COLOR_NEUTRAL = "#64748b"

# Paleta serii do 24 drużyn; stała per team_id poprzez modulo.
TEAM_SERIES_COLORS: tuple[str, ...] = (
    CHART_COLOR_POSITIVE,
    "#38bdf8",
    CHART_COLOR_DRAW,
    CHART_COLOR_NEGATIVE,
    "#a78bfa",
    "#fb923c",
    "#22d3ee",
    "#f472b6",
    "#84cc16",
    CHART_COLOR_NEUTRAL,
    "#2dd4bf",
    "#f87171",
    "#60a5fa",
    "#c084fc",
    "#fbbf24",
    "#4ade80",
    "#e879f9",
    "#94a3b8",
    "#fdba74",
    "#67e8f9",
    "#bef264",
    "#fca5a5",
    "#93c5fd",
    "#d8b4fe")

FOOTER_TEXT = "Wygenerowano przez EkstraBet"
METRIC_LABELS = {"elo": "ELO (pipeline ML)"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def color_for_team(team_id: int) -> str:
    """Return a stable series color for ``team_id``."""
    return TEAM_SERIES_COLORS[team_id % len(TEAM_SERIES_COLORS)]


def figure_height_for(
        team_count: int,
        rating_span: float) -> float:
    """Return PNG height in inches from team count and rating spread.

    More teams or a tight final cluster get a taller figure so end labels
    stay readable. Height is capped to avoid unbounded memory use.
    """
    extra_teams = max(0, team_count - 6)
    height = FIGURE_HEIGHT_BASE + extra_teams * INCHES_PER_EXTRA_TEAM
    if team_count > 1 and rating_span > 0:
        span_per_team = rating_span / (team_count - 1)
        if span_per_team < DENSE_SPAN_PER_TEAM:
            # Wąski klaster końcowy — dołóż wysokość na rozsunięcie etykiet.
            crowding = 1.0 - (span_per_team / DENSE_SPAN_PER_TEAM)
            height += crowding * team_count * 0.12
    return min(FIGURE_HEIGHT_MAX, max(FIGURE_HEIGHT_MIN, height))


def _rating_span(teams: list[TeamRatingProgress]) -> float:
    """Return max-min rating across start values and all series points."""
    values: list[float] = []
    for team in teams:
        values.append(team.start_rating)
        values.extend(point.rating for point in team.points)
    if not values:
        return 0.0
    return max(values) - min(values)


def render_rating_progress_png(result: RatingProgressResult) -> bytes:
    """Render ``result`` to PNG bytes and always close the figure.

    The returned buffer starts with a PNG signature. Filtering of teams
    is the caller's responsibility (``select_teams``); this function
    draws whatever series are present on the DTO.
    """
    fig: Figure | None = None
    try:
        height = figure_height_for(
            team_count=len(result.teams),
            rating_span=_rating_span(result.teams))
        fig, ax = plt.subplots(
            figsize=(FIGURE_WIDTH, height),
            dpi=FIGURE_DPI)
        _style_figure(fig, ax)
        _draw_series(ax, result)
        _configure_axes(ax, result)
        _add_end_labels(ax, result.teams, fig_height=height)
        _add_legend(ax, result.teams)
        # Layout osi w zarezerwowanym prostokącie, napisy poza nim.
        fig.tight_layout(rect=list(TIGHT_LAYOUT_RECT))
        _place_figure_captions(fig, result)
        buffer = BytesIO()
        fig.savefig(
            buffer,
            format="png",
            facecolor=fig.get_facecolor(),
            bbox_inches="tight",
            pad_inches=SAVE_PAD_INCHES)
        return buffer.getvalue()
    finally:
        if fig is not None:
            plt.close(fig)


def _style_figure(fig: Figure, ax: plt.Axes) -> None:
    """Apply dark branded colors to the figure and axes."""
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    ax.set_facecolor(AXES_FACE_COLOR)
    ax.tick_params(colors=FOREGROUND_COLOR, labelsize=9)
    ax.yaxis.label.set_color(FOREGROUND_COLOR)
    ax.xaxis.label.set_color(FOREGROUND_COLOR)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.45, linewidth=0.8)


def _draw_series(ax: plt.Axes, result: RatingProgressResult) -> None:
    """Plot one line per team on match dates, from seasonal baseline."""
    baseline = _season_baseline_date(result)
    for team in result.teams:
        dates, ratings = _series_plot_points(team, baseline)
        if not dates:
            continue
        color = color_for_team(team.team_id)
        label = _series_legend_label(team)
        ax.plot(
            dates,
            ratings,
            color=color,
            linewidth=2.0,
            marker="o",
            markersize=3.5,
            label=label)


def _season_baseline_date(
        result: RatingProgressResult) -> datetime | None:
    """Earliest first-match date across teams; else ``last_played_at``."""
    first_dates = [
        team.points[0].played_at
        for team in result.teams
        if team.points]
    if first_dates:
        return min(first_dates)
    return result.last_played_at


def _series_plot_points(
        team: TeamRatingProgress,
        baseline_date: datetime | None
) -> tuple[list[datetime], list[float]]:
    """Build date X/Y including a synthetic season-start baseline point.

    DTO ``points`` stay post-match only; the renderer prepends
    ``(baseline_date, start_rating)`` so the first-match delta is visible.
    X uses chronological match dates to avoid round-order zigzags.
    """
    if not team.points:
        return [], []
    # Wspólna data startu sezonu; fallback na pierwszy mecz drużyny.
    start_at = baseline_date or team.points[0].played_at
    dates = [start_at]
    ratings = [team.start_rating]
    for point in team.points:
        dates.append(point.played_at)
        ratings.append(point.rating)
    return dates, ratings


def _configure_axes(ax: plt.Axes, result: RatingProgressResult) -> None:
    """Set date ticks, metric Y label and room for end labels."""
    ax.set_xlabel("Data", labelpad=X_LABEL_PAD)
    ax.set_ylabel(_metric_axis_label(result.metric))
    locator = AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    for label in ax.get_xticklabels():
        label.set_rotation(35)
        label.set_ha("right")
    # Zapas z prawej na etykiety końcowe.
    xlim = ax.get_xlim()
    span = xlim[1] - xlim[0]
    if span > 0:
        ax.set_xlim(xlim[0], xlim[1] + span * RIGHT_MARGIN_FRACTION)


def _add_end_labels(
        ax: plt.Axes,
        teams: list[TeamRatingProgress],
        *,
        fig_height: float) -> None:
    """Place end labels near markers; nudge on collision with leader lines."""
    label_rows = [
        team for team in teams if team.points]
    if not label_rows:
        return
    raw_y = [team.points[-1].rating for team in label_rows]
    ylim = ax.get_ylim()
    y_span = max(ylim[1] - ylim[0], 1.0)
    min_gap = _label_min_gap(
        y_span=y_span,
        team_count=len(label_rows),
        fig_height=fig_height)
    adjusted = _resolve_label_y_positions(raw_y, min_gap)
    pad = max(y_span * 0.03, min_gap)
    low = min(adjusted + list(raw_y) + [ylim[0]]) - pad
    high = max(adjusted + list(raw_y) + [ylim[1]]) + pad
    ax.set_ylim(low, high)
    xlim = ax.get_xlim()
    x_span = max(xlim[1] - xlim[0], 1e-9)
    leader_dx = x_span * LEADER_X_FRACTION
    fontsize = _label_fontsize(len(label_rows))
    for team, true_y, label_y in zip(label_rows, raw_y, adjusted):
        last = team.points[-1]
        color = color_for_team(team.team_id)
        x_end = last.played_at
        # Matplotlib miesza daty i floaty osi — leader w jednostkach osi.
        x_num = float(ax.convert_xunits(x_end))
        x_text = x_num + leader_dx
        if abs(label_y - true_y) >= LEADER_OFFSET_THRESHOLD:
            ax.plot(
                [x_num, x_text],
                [true_y, label_y],
                color=color,
                linewidth=0.9,
                alpha=0.75,
                solid_capstyle="round",
                zorder=3)
        ax.text(
            x_text,
            label_y,
            f" {team.current_rank}. {_display_name(team)}",
            color=color,
            fontsize=fontsize,
            fontweight="bold",
            va="center",
            ha="left",
            clip_on=False,
            zorder=4)


def _label_min_gap(
        y_span: float,
        team_count: int,
        fig_height: float) -> float:
    """Minimum label gap in rating units from figure pixel budget.

    Prefer staying close to true marker Y. Absolute ELO gaps are avoided
    so labels are not pushed into empty space below the series.
    """
    axes_height = max(fig_height * 0.72, 1.0)
    pixels_for_span = axes_height * FIGURE_DPI
    gap_from_pixels = (LABEL_TARGET_PIXELS / pixels_for_span) * y_span
    ratio_gap = y_span * LABEL_MIN_GAP_RATIO
    gap = max(gap_from_pixels, ratio_gap)
    if team_count <= 1:
        return gap
    # Limit łącznego rozsunięcia, żeby etykiety trzymały się kul.
    max_gap = (y_span * LABEL_MAX_EXTRA_SPAN_RATIO) / (team_count - 1)
    return min(gap, max(max_gap, ratio_gap))


def _label_fontsize(team_count: int) -> int:
    """Pick end-label font size; stay readable even for dense charts."""
    if team_count <= 14:
        return LABEL_FONTSIZE_BASE
    if team_count <= 20:
        return LABEL_FONTSIZE_MID
    return LABEL_FONTSIZE_MIN


def _resolve_label_y_positions(
        ratings: list[float],
        min_gap: float) -> list[float]:
    """Spread Y positions top-down so consecutive labels keep ``min_gap``."""
    if not ratings:
        return []
    order = sorted(
        range(len(ratings)),
        key=lambda index: (-ratings[index], index))
    positions = list(ratings)
    for sequence_index in range(1, len(order)):
        higher = order[sequence_index - 1]
        lower = order[sequence_index]
        if positions[higher] - positions[lower] < min_gap:
            positions[lower] = positions[higher] - min_gap
    return positions


def _add_legend(ax: plt.Axes, teams: list[TeamRatingProgress]) -> None:
    """Draw a compact legend for all plotted series."""
    if not teams:
        return
    team_count = len(teams)
    fontsize = 8 if team_count <= 14 else 7
    columns = 1 if team_count <= 12 else 2
    legend = ax.legend(
        loc="upper left",
        fontsize=fontsize,
        ncol=columns,
        framealpha=0.85,
        facecolor=AXES_FACE_COLOR,
        edgecolor=SPINE_COLOR,
        labelcolor=FOREGROUND_COLOR)
    if legend is not None:
        for text in legend.get_texts():
            text.set_color(FOREGROUND_COLOR)


def _place_figure_captions(
        fig: Figure,
        result: RatingProgressResult) -> None:
    """Draw title, subtitle and footer outside the axes rect."""
    title = (
        f"Progres siły drużyn — {result.league_name} "
        f"({result.season_years})")
    fig.text(
        0.5,
        TITLE_Y,
        title,
        ha="center",
        va="top",
        color=FOREGROUND_COLOR,
        fontsize=14,
        fontweight="bold")
    subtitle = _build_subtitle(result)
    if subtitle:
        fig.text(
            0.5,
            SUBTITLE_Y,
            subtitle,
            ha="center",
            va="top",
            color=CHART_COLOR_NEUTRAL,
            fontsize=8)
    method = METRIC_LABELS.get(result.metric, result.metric.upper())
    fig.text(
        0.5,
        FOOTER_Y,
        f"Metoda: {method}  ·  {FOOTER_TEXT}",
        ha="center",
        va="bottom",
        color=CHART_COLOR_NEUTRAL,
        fontsize=8)


def _build_subtitle(result: RatingProgressResult) -> str:
    """Build a compact date/round range description."""
    dates: list[datetime] = []
    rounds: list[int] = []
    for team in result.teams:
        for point in team.points:
            dates.append(point.played_at)
            if point.round_number is not None:
                rounds.append(point.round_number)
    parts: list[str] = []
    if dates:
        start = min(dates).strftime("%Y-%m-%d")
        end = max(dates).strftime("%Y-%m-%d")
        parts.append(f"Zakres dat: {start} – {end}")
    if rounds:
        parts.append(f"Kolejki: {min(rounds)}–{max(rounds)}")
    if result.last_played_at is not None:
        stamp = result.last_played_at.strftime("%Y-%m-%d")
        parts.append(f"Ostatni mecz: {stamp}")
    return "  ·  ".join(parts)


def _series_legend_label(team: TeamRatingProgress) -> str:
    """Legend entry with league rank and display name."""
    return f"{team.current_rank}. {_display_name(team)}"


def _display_name(team: TeamRatingProgress) -> str:
    """Prefer shortcut when present, otherwise full team name."""
    if team.team_shortcut:
        return team.team_shortcut
    return team.team_name


def _metric_axis_label(metric: str) -> str:
    """Human-readable Y-axis label for the selected metric."""
    if metric == "elo":
        return "Rating ELO"
    return f"Rating ({metric})"
