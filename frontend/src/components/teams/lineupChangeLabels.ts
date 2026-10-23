import type { HockeyLineupChanges, HockeyLineupMove } from "@/types/api";

const FORWARD_POSITIONS = new Set(["LW", "C", "RW"]);

export type LineShiftDirection = "up" | "down";

export interface LineShiftMarker {
  direction: LineShiftDirection;
  previousLine: number;
}

/** Line move inside one position group. A wing swap on the same line is ignored. */
export function lineShiftMarker(move: HockeyLineupMove): LineShiftMarker | null {
  if (!samePositionFamily(move.previous_position, move.position)) {
    return null;
  }
  if (move.previous_line === move.line) {
    return null;
  }
  return {
    direction: move.previous_line > move.line ? "up" : "down",
    previousLine: move.previous_line,
  };
}

export function lineShiftsByPlayer(
  changes: HockeyLineupChanges,
): Map<number, LineShiftMarker> {
  const shifts = new Map<number, LineShiftMarker>();
  for (const move of changes.moves) {
    const marker = lineShiftMarker(move);
    if (marker) {
      shifts.set(move.player_id, marker);
    }
  }
  return shifts;
}

export function lineShiftLabel(marker: LineShiftMarker): string {
  const verb = marker.direction === "up" ? "Awans" : "Spadek";
  return `${verb} z ${marker.previousLine}. linii`;
}

function samePositionFamily(previous: string, current: string): boolean {
  if (previous === "D" && current === "D") {
    return true;
  }
  if (previous === "G" && current === "G") {
    return true;
  }
  return FORWARD_POSITIONS.has(previous) && FORWARD_POSITIONS.has(current);
}
