/**
 * Pure geometry and selection helpers for the league rating-progress SVG.
 * Mirrors CLI PNG baseline/label rules so WWW and operators see the same series.
 */

import type { TeamRatingProgress } from "@/types/api";

export const DEFAULT_VISIBLE_TEAMS = 6;

export const CHART_WIDTH = 720;
export const CHART_HEIGHT = 360;
export const CHART_PAD_LEFT = 48;
export const CHART_PAD_RIGHT = 120;
export const CHART_PAD_TOP = 20;
export const CHART_PAD_BOTTOM = 40;

const LABEL_MIN_GAP_RATIO = 0.028;
const Y_PADDING_RATIO = 0.08;
const FLAT_SERIES_HALF_SPAN = 50;

/** Same palette as backend rating_progress_renderer (stable per team_id). */
export const TEAM_SERIES_COLORS: readonly string[] = [
  "#52b788",
  "#38bdf8",
  "#d9b44a",
  "#d95757",
  "#a78bfa",
  "#fb923c",
  "#22d3ee",
  "#f472b6",
  "#84cc16",
  "#64748b",
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
  "#d8b4fe",
];

export interface ChartPlotPoint {
  matchId: number | null;
  roundNumber: number | null;
  playedAt: string;
  rating: number;
  isBaseline: boolean;
  x: number;
  y: number;
}

export interface ChartEndLabel {
  x: number;
  markerY: number;
  labelY: number;
  text: string;
  showLeader: boolean;
}

export interface ChartSeriesView {
  teamId: number;
  label: string;
  color: string;
  currentRank: number;
  currentRating: number;
  change: number;
  startRating: number;
  pathD: string;
  points: ChartPlotPoint[];
  endLabel: ChartEndLabel | null;
}

export interface ChartTick {
  position: number;
  label: string;
}

export interface RatingProgressChartModel {
  width: number;
  height: number;
  series: ChartSeriesView[];
  yTicks: ChartTick[];
  xTicks: ChartTick[];
  plotLeft: number;
  plotRight: number;
  plotTop: number;
  plotBottom: number;
}

export function colorForTeam(teamId: number): string {
  return TEAM_SERIES_COLORS[teamId % TEAM_SERIES_COLORS.length] ?? "#64748b";
}

export function teamDisplayLabel(
  team: Pick<TeamRatingProgress, "team_name" | "team_shortcut">,
): string {
  const shortcut = team.team_shortcut?.trim();
  return shortcut ? shortcut : team.team_name;
}

export function sortTeamsByCurrentRating(
  teams: readonly TeamRatingProgress[],
): TeamRatingProgress[] {
  return [...teams].sort((left, right) => {
    if (right.current_rating !== left.current_rating) {
      return right.current_rating - left.current_rating;
    }
    return left.team_id - right.team_id;
  });
}

/** Default selection: top N by current rating (stable team_id tie-break). */
export function selectDefaultTeamIds(
  teams: readonly TeamRatingProgress[],
  top: number = DEFAULT_VISIBLE_TEAMS,
): number[] {
  return sortTeamsByCurrentRating(teams)
    .slice(0, Math.max(0, top))
    .map((team) => team.team_id);
}

/** Bottom N by current rating (lowest first in the returned id list order). */
export function selectBottomTeamIds(
  teams: readonly TeamRatingProgress[],
  bottom: number = DEFAULT_VISIBLE_TEAMS,
): number[] {
  const ranked = sortTeamsByCurrentRating(teams);
  const count = Math.max(0, bottom);
  return ranked.slice(Math.max(0, ranked.length - count)).map((team) => team.team_id);
}

export function filterTeamsByIds(
  teams: readonly TeamRatingProgress[],
  teamIds: readonly number[],
): TeamRatingProgress[] {
  const selected = new Set(teamIds);
  return sortTeamsByCurrentRating(teams).filter((team) =>
    selected.has(team.team_id),
  );
}

export function seasonBaselineIso(
  teams: readonly TeamRatingProgress[],
  lastPlayedAt: string | null,
): string | null {
  let earliest: string | null = null;
  for (const team of teams) {
    const first = team.points[0]?.played_at;
    if (!first) {
      continue;
    }
    if (earliest === null || Date.parse(first) < Date.parse(earliest)) {
      earliest = first;
    }
  }
  return earliest ?? lastPlayedAt;
}

export function buildSeriesSourcePoints(
  team: TeamRatingProgress,
  baselineIso: string | null,
): Omit<ChartPlotPoint, "x" | "y">[] {
  if (team.points.length === 0) {
    return [];
  }
  const startAt = baselineIso ?? team.points[0]?.played_at;
  if (!startAt) {
    return [];
  }
  const points: Omit<ChartPlotPoint, "x" | "y">[] = [
    {
      matchId: null,
      roundNumber: null,
      playedAt: startAt,
      rating: team.start_rating,
      isBaseline: true,
    },
  ];
  for (const point of team.points) {
    points.push({
      matchId: point.match_id,
      roundNumber: point.round_number,
      playedAt: point.played_at,
      rating: point.rating,
      isBaseline: false,
    });
  }
  return points;
}

export function computeRatingExtent(
  teams: readonly TeamRatingProgress[],
  baselineIso: string | null,
): { min: number; max: number } {
  const values: number[] = [];
  for (const team of teams) {
    for (const point of buildSeriesSourcePoints(team, baselineIso)) {
      values.push(point.rating);
    }
  }
  if (values.length === 0) {
    return { min: 0, max: 1 };
  }
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= FLAT_SERIES_HALF_SPAN;
    max += FLAT_SERIES_HALF_SPAN;
  } else {
    const pad = (max - min) * Y_PADDING_RATIO;
    min -= pad;
    max += pad;
  }
  return { min, max };
}

export function resolveEndLabelYs(
  ratings: readonly number[],
  minGap: number,
): number[] {
  if (ratings.length === 0) {
    return [];
  }
  const order = [...ratings.keys()].sort(
    (left, right) =>
      (ratings[right] ?? 0) - (ratings[left] ?? 0) || left - right,
  );
  const positions = [...ratings];
  for (let index = 1; index < order.length; index += 1) {
    const higher = order[index - 1]!;
    const lower = order[index]!;
    if ((positions[higher] ?? 0) - (positions[lower] ?? 0) < minGap) {
      positions[lower] = (positions[higher] ?? 0) - minGap;
    }
  }
  return positions;
}

function formatAxisDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleDateString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
  });
}

function formatRatingTick(value: number): string {
  return String(Math.round(value));
}

function buildLinearScale(
  domainMin: number,
  domainMax: number,
  rangeMin: number,
  rangeMax: number,
): (value: number) => number {
  const span = domainMax - domainMin;
  if (span === 0) {
    const mid = (rangeMin + rangeMax) / 2;
    return () => mid;
  }
  return (value: number) =>
    rangeMin + ((value - domainMin) / span) * (rangeMax - rangeMin);
}

function buildYTicks(
  min: number,
  max: number,
  yAt: (value: number) => number,
): ChartTick[] {
  const steps = 4;
  const ticks: ChartTick[] = [];
  for (let index = 0; index <= steps; index += 1) {
    const value = min + ((max - min) * index) / steps;
    ticks.push({ position: yAt(value), label: formatRatingTick(value) });
  }
  return ticks;
}

function buildXTicks(
  minMs: number,
  maxMs: number,
  xAt: (ms: number) => number,
): ChartTick[] {
  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs)) {
    return [];
  }
  const steps = minMs === maxMs ? 1 : 3;
  const ticks: ChartTick[] = [];
  for (let index = 0; index <= steps; index += 1) {
    const ms = minMs + ((maxMs - minMs) * index) / steps;
    ticks.push({
      position: xAt(ms),
      label: formatAxisDate(new Date(ms).toISOString()),
    });
  }
  return ticks;
}

function pathFromPoints(points: ChartPlotPoint[]): string {
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
}

function attachEndLabels(
  plotted: ChartSeriesView[],
  extent: { min: number; max: number },
  yAtRating: (value: number) => number,
): ChartSeriesView[] {
  // Kolizje rozsuwamy w przestrzeni ratingu (jak CLI), potem mapujemy na Y SVG.
  const labelCandidates = plotted.filter((series) => series.points.length > 0);
  const markerRatings = labelCandidates.map((series) => series.currentRating);
  const ratingSpan = Math.max(extent.max - extent.min, 1);
  const minGapRating = ratingSpan * LABEL_MIN_GAP_RATIO;
  const adjustedRatings = resolveEndLabelYs(markerRatings, minGapRating);

  return plotted.map((entry) => {
    const candidateIndex = labelCandidates.findIndex(
      (candidate) => candidate.teamId === entry.teamId,
    );
    if (candidateIndex < 0) {
      return entry;
    }
    const last = entry.points[entry.points.length - 1];
    if (!last) {
      return entry;
    }
    const labelY = yAtRating(
      adjustedRatings[candidateIndex] ?? entry.currentRating,
    );
    return {
      ...entry,
      endLabel: {
        x: last.x + 8,
        markerY: last.y,
        labelY,
        text: `${entry.currentRank}. ${entry.label}`,
        showLeader: Math.abs(labelY - last.y) >= 2.5,
      },
    };
  });
}

export function buildRatingProgressChartModel(
  teams: readonly TeamRatingProgress[],
  options?: {
    lastPlayedAt?: string | null;
    width?: number;
    height?: number;
  },
): RatingProgressChartModel {
  const width = options?.width ?? CHART_WIDTH;
  const height = options?.height ?? CHART_HEIGHT;
  const plotLeft = CHART_PAD_LEFT;
  const plotRight = width - CHART_PAD_RIGHT;
  const plotTop = CHART_PAD_TOP;
  const plotBottom = height - CHART_PAD_BOTTOM;
  const baselineIso = seasonBaselineIso(teams, options?.lastPlayedAt ?? null);
  const extent = computeRatingExtent(teams, baselineIso);
  const yAtRating = buildLinearScale(
    extent.min,
    extent.max,
    plotBottom,
    plotTop,
  );

  const rawSeries = teams.map((team) => {
    const source = buildSeriesSourcePoints(team, baselineIso);
    return {
      team,
      source,
      times: source.map((point) => Date.parse(point.playedAt)),
    };
  });

  const allTimes = rawSeries.flatMap((entry) =>
    entry.times.filter((time) => Number.isFinite(time)),
  );
  const minMs = allTimes.length > 0 ? Math.min(...allTimes) : 0;
  const maxMs = allTimes.length > 0 ? Math.max(...allTimes) : 1;
  const xAtMs = buildLinearScale(minMs, maxMs, plotLeft, plotRight);

  const plotted: ChartSeriesView[] = rawSeries.map(({ team, source }) => {
    const points: ChartPlotPoint[] = source.map((point) => {
      const ms = Date.parse(point.playedAt);
      return {
        ...point,
        x: xAtMs(Number.isFinite(ms) ? ms : minMs),
        y: yAtRating(point.rating),
      };
    });
    return {
      teamId: team.team_id,
      label: teamDisplayLabel(team),
      color: colorForTeam(team.team_id),
      currentRank: team.current_rank,
      currentRating: team.current_rating,
      change: team.change,
      startRating: team.start_rating,
      pathD: pathFromPoints(points),
      points,
      endLabel: null,
    };
  });

  return {
    width,
    height,
    series: attachEndLabels(plotted, extent, yAtRating),
    yTicks: buildYTicks(extent.min, extent.max, yAtRating),
    xTicks: buildXTicks(minMs, maxMs, xAtMs),
    plotLeft,
    plotRight,
    plotTop,
    plotBottom,
  };
}
