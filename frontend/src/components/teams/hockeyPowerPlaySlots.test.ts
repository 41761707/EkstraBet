import { describe, expect, it } from "vitest";

import {
  placePowerPlayUnit,
  playersOnPowerPlay,
} from "@/components/teams/hockeyPowerPlaySlots";
import type { HockeyRosterPlayer, HockeyTeamRoster } from "@/types/api";

function skater(
  playerId: number,
  position: string,
  ppUnit: number | null,
): HockeyRosterPlayer {
  return {
    player_id: playerId,
    first_name: position,
    last_name: String(playerId),
    common_name: `${position}${playerId}`,
    country: "Canada",
    position,
    number: playerId,
    line: 1,
    pp_unit: ppUnit,
    is_injured: false,
    injury_status: null,
    injury_note: null,
    games_played: 1,
    goals: 0,
    assists: 0,
    points: 0,
    shots_on_goal: 0,
    average_toi: "02:00",
    save_percentage: null,
    goals_against_average: null,
    in_last_lineup: true,
  };
}

function names(slots: (HockeyRosterPlayer | null)[]): (string | null)[] {
  return slots.map((player) => player?.common_name ?? null);
}

describe("placePowerPlayUnit", () => {
  it("keeps a center on C when wings are listed first", () => {
    const sheet = placePowerPlayUnit([
      skater(1, "LW", 1),
      skater(2, "RW", 1),
      skater(3, "C", 1),
      skater(4, "C", 1),
      skater(5, "D", 1),
    ]);

    expect(names(sheet.wings)).toEqual(["LW1", "C3", "RW2"]);
    expect(names(sheet.back)).toEqual(["D5", "C4"]);
    expect(sheet.overflow).toEqual([]);
  });

  it("seats a defenseman on the back row even when listed last", () => {
    const sheet = placePowerPlayUnit([
      skater(1, "LW", 1),
      skater(2, "C", 1),
      skater(3, "RW", 1),
      skater(4, "C", 1),
      skater(5, "D", 1),
    ]);

    expect(names(sheet.wings)).toEqual(["LW1", "C2", "RW3"]);
    expect(names(sheet.back)).toEqual(["D5", "C4"]);
  });

  it("puts five forwards on the sheet when the unit has no defenseman", () => {
    const sheet = placePowerPlayUnit([
      skater(1, "LW", 1),
      skater(2, "C", 1),
      skater(3, "RW", 1),
      skater(4, "C", 1),
      skater(5, "RW", 1),
    ]);

    expect(names(sheet.wings)).toEqual(["LW1", "C2", "RW3"]);
    expect(names(sheet.back)).toEqual(["C4", "RW5"]);
  });

  it("uses both back slots for a three-forward pair of defensemen", () => {
    const sheet = placePowerPlayUnit([
      skater(1, "C", 1),
      skater(2, "D", 1),
      skater(3, "LW", 1),
      skater(4, "D", 1),
      skater(5, "RW", 1),
    ]);

    expect(names(sheet.wings)).toEqual(["LW3", "C1", "RW5"]);
    expect(names(sheet.back)).toEqual(["D2", "D4"]);
  });

  it("keeps a sixth skater when the sheet is already full", () => {
    const sheet = placePowerPlayUnit([
      skater(1, "LW", 1),
      skater(2, "C", 1),
      skater(3, "RW", 1),
      skater(4, "C", 1),
      skater(5, "D", 1),
      skater(6, "D", 1),
    ]);

    expect(names(sheet.wings)).toEqual(["LW1", "C2", "RW3"]);
    expect(names(sheet.back)).toEqual(["D5", "D6"]);
    expect(sheet.overflow.map((player) => player.common_name)).toEqual(["C4"]);
  });
});

describe("playersOnPowerPlay", () => {
  it("collects one unit from every roster group", () => {
    const roster: HockeyTeamRoster = {
      team_id: 1,
      team_name: "Ducks",
      goalkeepers: [],
      defensemen: [],
      forwards: [],
      injured_players: 1,
      groups: [
        {
          group_id: "F1",
          players: [skater(1, "C", 1), skater(2, "LW", null)],
        },
        {
          group_id: "D1",
          players: [skater(3, "D", 1)],
        },
        {
          group_id: "injured",
          players: [skater(4, "RW", 1)],
        },
        {
          group_id: "F2",
          players: [skater(5, "C", 2)],
        },
      ],
    };

    expect(playersOnPowerPlay(roster, 1).map((player) => player.player_id)).toEqual([
      1, 3, 4,
    ]);
    expect(playersOnPowerPlay(roster, 2).map((player) => player.player_id)).toEqual([
      5,
    ]);
  });
});
