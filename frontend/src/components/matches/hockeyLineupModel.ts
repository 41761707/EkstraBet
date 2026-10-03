import type {
  HockeyLineupPlayer,
  HockeyLineupStatus,
  HockeyPredictionStage,
  HockeyTeamLineup,
} from "@/types/api";

export const HOCKEY_LINE_TABS: readonly {
  line: 1 | 2 | 3 | 4;
  label: string;
}[] = [
  { line: 1, label: "Pierwsza linia" },
  { line: 2, label: "Druga linia" },
  { line: 3, label: "Trzecia linia" },
  { line: 4, label: "Czwarta linia" },
];

export interface HockeyRinkMarker {
  playerId: number;
  name: string;
  number: number | null;
  position: string;
  x: number;
  y: number;
}

const FORWARD_SLOT_ORDER = ["RW", "C", "LW"] as const;
const FORWARD_SLOT_X = [33, 20, 7] as const;
const FORWARD_SLOT_Y = 43;
const DEFENSE_SLOT_X = [13.5, 26.5] as const;
const DEFENSE_SLOT_Y = 23;
const GOALIE_SLOT_X = 20;
// Streamlit miało y=11; podnosimy G, żeby podpis pod kółkiem nie wchodził w pole bramkowe.
const GOALIE_SLOT_Y = 12;
const LINE_1_TABLE_ORDER = ["G", "D", "LW", "C", "RW"] as const;
const SKATER_LINE_TABLE_ORDER = ["D", "LW", "C", "RW"] as const;
const GOALIE_POSITION = "G";

function toMarker(
  player: HockeyLineupPlayer,
  x: number,
  y: number,
): HockeyRinkMarker {
  return {
    playerId: player.player_id,
    name: player.player_name,
    number: player.number,
    position: player.position,
    x,
    y,
  };
}

function playersWithPosition(
  players: HockeyLineupPlayer[],
  position: string,
): HockeyLineupPlayer[] {
  return players.filter((player) => player.position === position);
}

function markersForSlots(
  players: HockeyLineupPlayer[],
  slotX: readonly number[],
  slotY: number,
): HockeyRinkMarker[] {
  return players
    .slice(0, slotX.length)
    .map((player, index) => toMarker(player, slotX[index], slotY));
}

/** Players of one line, or an empty list when that line is missing. */
export function linePlayers(
  team: HockeyTeamLineup,
  line: number,
): HockeyLineupPlayer[] {
  const lineupLine = team.lines.find((item) => item.line === line);
  return lineupLine?.players ?? [];
}

/** Table order: line 1 is G, D, D, LW, C, RW; other lines omit G. */
export function sortPlayersForLineTable(
  players: HockeyLineupPlayer[],
  line: number,
): HockeyLineupPlayer[] {
  const order = line === 1 ? LINE_1_TABLE_ORDER : SKATER_LINE_TABLE_ORDER;
  const used = new Set<string>(order);
  return [
    ...order.flatMap((position) => playersWithPosition(players, position)),
    ...players.filter((player) => !used.has(player.position)),
  ];
}

/**
 * Map a line's roster onto rink slots. Extra players and unknown positions
 * stay in the table only — they do not get a marker.
 */
export function rinkMarkersForLine(
  players: HockeyLineupPlayer[],
): HockeyRinkMarker[] {
  // napastnicy w kolejności RW -> C -> LW, potem kolejne x ze Streamlit
  const forwards = FORWARD_SLOT_ORDER.flatMap((position) =>
    playersWithPosition(players, position),
  );
  const defensemen = playersWithPosition(players, "D");
  const goalies = playersWithPosition(players, "G");

  return [
    ...markersForSlots(forwards, FORWARD_SLOT_X, FORWARD_SLOT_Y),
    ...markersForSlots(defensemen, DEFENSE_SLOT_X, DEFENSE_SLOT_Y),
    ...markersForSlots(goalies, [GOALIE_SLOT_X], GOALIE_SLOT_Y),
  ];
}

const LINEUP_STATUS_LABELS: Record<HockeyLineupStatus, string> = {
  probable: "Przewidywany skład",
  confirmed: "Skład potwierdzony",
};

const LINEUP_SOURCE_LABELS: Record<string, string> = {
  MODEL: "model",
  EXTERNAL: "zewnętrzny",
  CONFIRMED: "potwierdzony",
};

const PREDICTION_STAGE_LABELS: Record<HockeyPredictionStage, string> = {
  initial: "Predykcja pierwotna",
  final: "Predykcja ostateczna",
};

/** Badge for a projected or official sheet. Played box scores have none. */
export function lineupStatusLabel(
  status: HockeyLineupStatus | null | undefined,
): string | null {
  if (status == null) {
    return null;
  }
  return LINEUP_STATUS_LABELS[status] ?? null;
}

/** Polish source name. An unknown stored value is shown as-is. */
export function lineupSourceLabel(
  source: string | null | undefined,
): string | null {
  if (source == null) {
    return null;
  }
  const trimmed = source.trim();
  if (!trimmed) {
    return null;
  }
  return LINEUP_SOURCE_LABELS[trimmed.toUpperCase()] ?? trimmed;
}

/** Stage label from the latest team-model snapshot, or null when absent. */
export function predictionStageLabel(
  stage: HockeyPredictionStage | null | undefined,
): string | null {
  if (stage == null) {
    return null;
  }
  return PREDICTION_STAGE_LABELS[stage] ?? null;
}

/** Goalie start weight as a whole percent. Skaters and missing weights are null. */
export function formatGoalieStartPercent(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value) || value < 0 || value > 1) {
    return null;
  }
  return `${Math.round(value * 100)}%`;
}

export interface GoalieStartLabel {
  playerId: number;
  playerName: string;
  percent: string;
}

/** Every goalie with a stored start weight, starter's line first. */
export function goalieStartLabels(team: HockeyTeamLineup): GoalieStartLabel[] {
  const labels: GoalieStartLabel[] = [];
  const lines = [...team.lines].sort((left, right) => left.line - right.line);
  for (const lineupLine of lines) {
    for (const player of lineupLine.players) {
      const label = goalieStartLabel(player);
      if (label !== null) {
        labels.push(label);
      }
    }
  }
  return labels;
}

/**
 * Players drawn for one line. Line 1 keeps the starter. Lines 2-4 drop
 * goalies, because a backup is stored on line 2 only so the sheet has a row.
 */
export function playersOnLineSheet(
  players: HockeyLineupPlayer[],
  line: number,
): HockeyLineupPlayer[] {
  if (line <= 1) {
    return players;
  }
  return players.filter((player) => player.position !== GOALIE_POSITION);
}

function goalieStartLabel(player: HockeyLineupPlayer): GoalieStartLabel | null {
  if (player.position !== GOALIE_POSITION) {
    return null;
  }
  const percent = formatGoalieStartPercent(player.start_probability);
  if (percent === null) {
    return null;
  }
  return {
    playerId: player.player_id,
    playerName: player.player_name,
    percent,
  };
}
