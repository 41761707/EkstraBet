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
