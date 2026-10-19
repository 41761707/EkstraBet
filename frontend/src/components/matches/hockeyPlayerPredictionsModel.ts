import {
  toRelativeBars,
  type ProbabilityBarPoint,
} from "@/components/predictions/predictionChartModel";
import {
  CHART_COLOR_DRAW,
  CHART_COLOR_POSITIVE,
  CHART_COLOR_SHOTS,
} from "@/lib/chartColors";
import type {
  HockeyPlayerPrediction,
  HockeyPlayerPredictionLine,
  HockeyPlayerPredictions,
} from "@/types/api";

const SOG_EVENT_ID = 190;
const POINTS_EVENT_ID = 192;
const ASSISTS_EVENT_ID = 194;
const GOALS_EVENT_ID = 196;
const SOG_DISPLAY_LINE = 2.5;
const SINGLE_COUNT_LINE = 0.5;
const TWO_POINTS_LINE = 1.5;
const LINE_EPSILON = 0.001;

export interface HockeyPlayerPropColumns {
  playerId: number;
  playerName: string;
  expectedShots: number | null;
  shotsOver25: number | null;
  goalProbability: number | null;
  assistProbability: number | null;
  pointProbability: number | null;
  twoPointProbability: number | null;
}

/** True when either club has at least one skater row. */
export function hasHockeyPlayerPredictions(
  predictions: HockeyPlayerPredictions | null,
): boolean {
  if (!predictions) {
    return false;
  }
  return predictions.home.length > 0 || predictions.away.length > 0;
}

/** Columns for the beta table. Expected shots come from any SOG line. */
export function toPropColumns(
  player: HockeyPlayerPrediction,
): HockeyPlayerPropColumns {
  const shots = matchingLine(player.lines, SOG_EVENT_ID, SOG_DISPLAY_LINE);
  const anyShots = player.lines.find((item) => item.event_id === SOG_EVENT_ID);
  return {
    playerId: player.player_id,
    playerName: player.player_name,
    expectedShots: anyShots?.expected_value ?? null,
    shotsOver25: shots?.probability ?? null,
    goalProbability: probabilityAt(player.lines, GOALS_EVENT_ID, SINGLE_COUNT_LINE),
    assistProbability: probabilityAt(
      player.lines,
      ASSISTS_EVENT_ID,
      SINGLE_COUNT_LINE,
    ),
    pointProbability: probabilityAt(
      player.lines,
      POINTS_EVENT_ID,
      SINGLE_COUNT_LINE,
    ),
    twoPointProbability: probabilityAt(
      player.lines,
      POINTS_EVENT_ID,
      TWO_POINTS_LINE,
    ),
  };
}

export type PlayerChartMetric = "goal" | "assist" | "point";

export interface ExpectedValueBarPoint {
  id: string;
  label: string;
  value: number;
  /** Relative bar length 0–100 against the highest player. */
  barPercent: number;
  color: string;
  isFavorite: boolean;
}

/** Horizontal bars for one counting stat, highest probability first. */
export function buildPlayerProbabilityBars(
  players: HockeyPlayerPrediction[],
  metric: PlayerChartMetric,
): ProbabilityBarPoint[] {
  const items = players.flatMap((player) => {
    const percent = metricPercent(toPropColumns(player), metric);
    if (percent == null || !Number.isFinite(percent)) {
      return [];
    }
    return [
      {
        id: String(player.player_id),
        label: player.player_name,
        probability: percent / 100,
        color: CHART_COLOR_POSITIVE,
      },
    ];
  });
  items.sort((left, right) => {
    if (right.probability !== left.probability) {
      return right.probability - left.probability;
    }
    return left.label.localeCompare(right.label, "pl");
  });
  return toRelativeBars(items);
}

/** Expected shots on goal from any SOG line, highest first. */
export function buildExpectedShotBars(
  players: HockeyPlayerPrediction[],
): ExpectedValueBarPoint[] {
  return buildExpectedValueBars(
    players,
    (player) => toPropColumns(player).expectedShots,
    CHART_COLOR_SHOTS,
  );
}

/** Expected goals from the goals-line Poisson mean, highest first. */
export function buildExpectedGoalBars(
  players: HockeyPlayerPrediction[],
): ExpectedValueBarPoint[] {
  return buildExpectedValueBars(players, expectedGoals, CHART_COLOR_DRAW);
}

function buildExpectedValueBars(
  players: HockeyPlayerPrediction[],
  readValue: (player: HockeyPlayerPrediction) => number | null,
  color: string,
): ExpectedValueBarPoint[] {
  const items = players.flatMap((player) => {
    const value = readValue(player);
    if (value == null || !Number.isFinite(value)) {
      return [];
    }
    return [
      {
        id: String(player.player_id),
        label: player.player_name,
        value,
      },
    ];
  });
  items.sort((left, right) => {
    if (right.value !== left.value) {
      return right.value - left.value;
    }
    return left.label.localeCompare(right.label, "pl");
  });
  const maxValue = Math.max(...items.map((item) => item.value), 0);
  return items.map((item) => ({
    id: item.id,
    label: item.label,
    value: item.value,
    barPercent: maxValue > 0 ? (item.value / maxValue) * 100 : 0,
    color,
    isFavorite: item.value === maxValue && maxValue > 0,
  }));
}

function expectedGoals(player: HockeyPlayerPrediction): number | null {
  const value = matchingLine(
    player.lines,
    GOALS_EVENT_ID,
    SINGLE_COUNT_LINE,
  )?.expected_value;
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return value;
}

function metricPercent(
  columns: HockeyPlayerPropColumns,
  metric: PlayerChartMetric,
): number | null {
  if (metric === "goal") {
    return columns.goalProbability;
  }
  if (metric === "assist") {
    return columns.assistProbability;
  }
  return columns.pointProbability;
}

export function formatExpectedShots(value: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return value.toFixed(2);
}

function probabilityAt(
  lines: HockeyPlayerPredictionLine[],
  eventId: number,
  line: number,
): number | null {
  return matchingLine(lines, eventId, line)?.probability ?? null;
}

function matchingLine(
  lines: HockeyPlayerPredictionLine[],
  eventId: number,
  line: number,
): HockeyPlayerPredictionLine | undefined {
  return lines.find(
    (item) => item.event_id === eventId && Math.abs(item.line - line) < LINE_EPSILON,
  );
}
