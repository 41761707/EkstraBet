import type { HockeyLineupPlayer, HockeyTeamLineup } from "@/types/api";

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
const FORWARD_SLOT_Y = 45;
const DEFENSE_SLOT_X = [13.5, 26.5] as const;
const DEFENSE_SLOT_Y = 25;
const GOALIE_SLOT_X = 20;
const GOALIE_SLOT_Y = 11;

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
