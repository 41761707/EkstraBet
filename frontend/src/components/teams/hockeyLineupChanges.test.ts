import { describe, expect, it } from "vitest";

import {
  lineShiftLabel,
  lineShiftMarker,
} from "@/components/teams/lineupChangeLabels";
import type { HockeyLineupMove } from "@/types/api";

function move(overrides: Partial<HockeyLineupMove> = {}): HockeyLineupMove {
  return {
    player_id: 1,
    common_name: "Center A.",
    previous_position: "C",
    previous_line: 2,
    position: "C",
    line: 1,
    ...overrides,
  };
}

describe("line shift marker", () => {
  it("marks a move onto a higher line with the previous line number", () => {
    const marker = lineShiftMarker(move({ previous_line: 4, line: 1 }));

    expect(marker).toEqual({ direction: "up", previousLine: 4 });
    expect(lineShiftLabel(marker!)).toBe("Awans z 4. linii");
  });

  it("marks a move onto a lower line", () => {
    const marker = lineShiftMarker(
      move({
        previous_position: "D",
        previous_line: 1,
        position: "D",
        line: 2,
      }),
    );

    expect(marker).toEqual({ direction: "down", previousLine: 1 });
    expect(lineShiftLabel(marker!)).toBe("Spadek z 1. linii");
  });

  it("ignores a wing swap on the same line", () => {
    expect(
      lineShiftMarker(
        move({ previous_position: "LW", position: "RW", previous_line: 1, line: 1 }),
      ),
    ).toBeNull();
  });

  it("ignores a move between a forward line and a defence pair", () => {
    expect(
      lineShiftMarker(
        move({ previous_position: "D", previous_line: 2, position: "C", line: 1 }),
      ),
    ).toBeNull();
  });
});
