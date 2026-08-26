/**
 * Pure geometry and selection helpers for the league rating-progress SVG.
 * Mirrors CLI PNG baseline/label rules so WWW and operators see the same series.
 */

import { CHART_COLOR_NEUTRAL } from "@/lib/chartColors";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
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
  /** Position on the match-index X axis (0 = season baseline). */
  axisIndex: number;
  x: number;
  y: number;
}

/**
 * One column on the X axis. Index 0 is the synthetic season start;
 * index N is each team's N-th played match (sorted by date, not round_number).
 */
export interface MatchAxisSlot {
  index: number;
  label: string;
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
  return TEAM_SERIES_COLORS[teamId % TEAM_SERIES_COLORS.length] ?? CHART_COLOR_NEUTRAL;
}

export function teamDisplayLabel(
  team: Pick<TeamRatingProgress, "team_name" | "team_shortcut">,
  preference: TeamNameDisplayPreference,
): string {
  return formatTeamName(team.team_name, team.team_shortcut, preference);
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

function sortPointsByPlayedAt<T extends { played_at: string; match_id: number }>(
  points: readonly T[],
): T[] {
  return [...points].sort((left, right) => {
    const leftMs = Date.parse(left.played_at);
    const rightMs = Date.parse(right.played_at);
    if (leftMs !== rightMs) {
      return leftMs - rightMs;
    }
    return left.match_id - right.match_id;
  });
}

/**
 * Shared X domain: 0 = baseline, then 1..maxMatches where N is each team's
 * N-th played match in chronological order (postponements included by date).
 */
export function buildMatchAxisSlots(
  teams: readonly TeamRatingProgress[],
): MatchAxisSlot[] {
  let maxMatches = 0;
  for (const team of teams) {
    maxMatches = Math.max(maxMatches, team.points.length);
  }
  const slots: MatchAxisSlot[] = [{ index: 0, label: "0" }];
  for (let index = 1; index <= maxMatches; index += 1) {
    slots.push({ index, label: String(index) });
  }
  return slots;
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
      axisIndex: 0,
    },
  ];
  const ordered = sortPointsByPlayedAt(team.points);
  ordered.forEach((point, offset) => {
    points.push({
      matchId: point.match_id,
      roundNumber: point.round_number,
      playedAt: point.played_at,
      rating: point.rating,
      isBaseline: false,
      axisIndex: offset + 1,
    });
  });
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
  slots: readonly MatchAxisSlot[],
  xAtIndex: (index: number) => number,
): ChartTick[] {
  // Skip synthetic baseline (0); tick labels are match/round indices.
  const matchSlots = slots.filter((slot) => slot.index > 0);
  if (matchSlots.length === 0) {
    return [];
  }
  if (matchSlots.length === 1) {
    const only = matchSlots[0]!;
    return [{ position: xAtIndex(only.index), label: only.label }];
  }
  const steps = Math.min(3, matchSlots.length - 1);
  const ticks: ChartTick[] = [];
  const seen = new Set<number>();
  for (let step = 0; step <= steps; step += 1) {
    const pick = Math.round((step * (matchSlots.length - 1)) / steps);
    const slot = matchSlots[pick];
    if (!slot || seen.has(slot.index)) {
      continue;
    }
    seen.add(slot.index);
    ticks.push({ position: xAtIndex(slot.index), label: slot.label });
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
    teamNameDisplay?: TeamNameDisplayPreference;
  },
): RatingProgressChartModel {
  const width = options?.width ?? CHART_WIDTH;
  const height = options?.height ?? CHART_HEIGHT;
  const plotLeft = CHART_PAD_LEFT;
  const plotRight = width - CHART_PAD_RIGHT;
  const plotTop = CHART_PAD_TOP;
  const plotBottom = height - CHART_PAD_BOTTOM;
  const baselineIso = seasonBaselineIso(teams, options?.lastPlayedAt ?? null);
  const axisSlots = buildMatchAxisSlots(teams);
  const extent = computeRatingExtent(teams, baselineIso);
  const yAtRating = buildLinearScale(
    extent.min,
    extent.max,
    plotBottom,
    plotTop,
  );
  const maxAxisIndex = Math.max(0, ...axisSlots.map((slot) => slot.index));
  const xAtIndex = buildLinearScale(0, Math.max(maxAxisIndex, 1), plotLeft, plotRight);

  const teamNameDisplay = options?.teamNameDisplay ?? "full";
  const plotted: ChartSeriesView[] = teams.map((team) => {
    const source = buildSeriesSourcePoints(team, baselineIso);
    const points: ChartPlotPoint[] = source.map((point) => ({
      ...point,
      x: xAtIndex(point.axisIndex),
      y: yAtRating(point.rating),
    }));
    return {
      teamId: team.team_id,
      label: teamDisplayLabel(team, teamNameDisplay),
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
    xTicks: buildXTicks(axisSlots, xAtIndex),
    plotLeft,
    plotRight,
    plotTop,
    plotBottom,
  };
}
