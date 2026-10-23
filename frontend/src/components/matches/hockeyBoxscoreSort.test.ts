import { describe, expect, it } from "vitest";

import {
  goalieSortValue,
  nextBoxscoreSort,
  skaterSortValue,
  sortBoxscoreRows,
  timeOnIceSeconds,
} from "@/components/matches/hockeyBoxscoreSort";
import type {
  HockeyGoalieBoxscoreRow,
  HockeySkaterBoxscoreRow,
} from "@/types/api";

function goalie(
  overrides: Partial<HockeyGoalieBoxscoreRow> & Pick<HockeyGoalieBoxscoreRow, "player_id">,
): HockeyGoalieBoxscoreRow {
  return {
    player_name: "Goalie A.",
    team_id: 1,
    team_name: "Tampa Bay Lightning",
    points: 0,
    penalty_minutes: 0,
    time_on_ice: "59:57",
    shots_against: 30,
    shots_saved: 28,
    saves_accuracy: 93.33,
    ...overrides,
  };
}

function skater(
  overrides: Partial<HockeySkaterBoxscoreRow> & Pick<HockeySkaterBoxscoreRow, "player_id">,
): HockeySkaterBoxscoreRow {
  return {
    player_name: "Skater A.",
    team_id: 1,
    team_name: "Tampa Bay Lightning",
    goals: 0,
    assists: 0,
    points: 0,
    plus_minus: 0,
    penalty_minutes: 0,
    shots_on_goal: 0,
    time_on_ice: "10:00",
    ...overrides,
  };
}

describe("nextBoxscoreSort", () => {
  it("starts stat columns at the highest value and names at A-Z", () => {
    expect(nextBoxscoreSort(null, "time_on_ice")).toEqual({
      key: "time_on_ice",
      direction: "desc",
    });
    expect(nextBoxscoreSort(null, "player_name")).toEqual({
      key: "player_name",
      direction: "asc",
    });
  });

  it("flips direction when the same header is clicked again", () => {
    const first = nextBoxscoreSort(null, "points");
    expect(nextBoxscoreSort(first, "points").direction).toBe("asc");
    expect(nextBoxscoreSort(nextBoxscoreSort(first, "points"), "points").direction).toBe(
      "desc",
    );
  });
});

describe("timeOnIceSeconds", () => {
  it("parses minutes and seconds and rejects empty or broken values", () => {
    expect(timeOnIceSeconds("59:57")).toBe(59 * 60 + 57);
    expect(timeOnIceSeconds(" 9:05 ")).toBe(9 * 60 + 5);
    expect(timeOnIceSeconds(null)).toBeNull();
    expect(timeOnIceSeconds("")).toBeNull();
    expect(timeOnIceSeconds("18:5")).toBeNull();
  });
});

describe("sortBoxscoreRows", () => {
  it("orders skaters by ice time with missing values last", () => {
    const rows = [
      skater({ player_id: 1, player_name: "Short A.", time_on_ice: "09:30" }),
      skater({ player_id: 2, player_name: "Missing B.", time_on_ice: null }),
      skater({ player_id: 3, player_name: "Long C.", time_on_ice: "21:00" }),
    ];
    const desc = nextBoxscoreSort(null, "time_on_ice");
    const asc = nextBoxscoreSort(desc, "time_on_ice");

    expect(sortBoxscoreRows(rows, desc, skaterSortValue).map((row) => row.player_id)).toEqual([
      3, 1, 2,
    ]);
    expect(sortBoxscoreRows(rows, asc, skaterSortValue).map((row) => row.player_id)).toEqual([
      1, 3, 2,
    ]);
  });

  it("keeps a zero plus-minus and drops a missing one to the bottom", () => {
    const rows = [
      skater({ player_id: 1, plus_minus: null }),
      skater({ player_id: 2, plus_minus: -2 }),
      skater({ player_id: 3, plus_minus: 0 }),
      skater({ player_id: 4, plus_minus: 3 }),
    ];
    const desc = nextBoxscoreSort(null, "plus_minus");

    expect(sortBoxscoreRows(rows, desc, skaterSortValue).map((row) => row.player_id)).toEqual([
      4, 3, 2, 1,
    ]);
  });

  it("breaks equal ice time by player id", () => {
    const rows = [
      skater({ player_id: 9, time_on_ice: "18:00" }),
      skater({ player_id: 4, time_on_ice: "18:00" }),
    ];
    const desc = nextBoxscoreSort(null, "time_on_ice");

    expect(sortBoxscoreRows(rows, desc, skaterSortValue).map((row) => row.player_id)).toEqual([
      4, 9,
    ]);
  });

  it("sorts a higher rating above a lower one and keeps a missing rating last", () => {
    const rows = [
      { ...skater({ player_id: 1 }), rating: 0.4 },
      { ...skater({ player_id: 2 }), rating: null },
      { ...skater({ player_id: 3 }), rating: 3.3 },
    ];
    const desc = nextBoxscoreSort(null, "rating");

    expect(desc.direction).toBe("desc");
    expect(sortBoxscoreRows(rows, desc, skaterSortValue).map((row) => row.player_id)).toEqual([
      3, 1, 2,
    ]);
  });

  it("sorts goalies by save percentage and names in Polish order", () => {
    const rows = [
      goalie({
        player_id: 2,
        player_name: "Łukasz L.",
        saves_accuracy: 71.4,
        time_on_ice: "59:46",
      }),
      goalie({
        player_id: 1,
        player_name: "Adam A.",
        saves_accuracy: null,
        time_on_ice: "12:00",
      }),
      goalie({
        player_id: 3,
        player_name: "Zbigniew Z.",
        saves_accuracy: 94.1,
        time_on_ice: "59:57",
      }),
    ];
    const bySaves = nextBoxscoreSort(null, "saves_accuracy");
    const byName = nextBoxscoreSort(null, "player_name");

    expect(sortBoxscoreRows(rows, bySaves, goalieSortValue).map((row) => row.player_id)).toEqual([
      3, 2, 1,
    ]);
    expect(sortBoxscoreRows(rows, byName, goalieSortValue).map((row) => row.player_name)).toEqual([
      "Adam A.",
      "Łukasz L.",
      "Zbigniew Z.",
    ]);
  });
});
