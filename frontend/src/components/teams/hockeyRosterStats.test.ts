import { describe, expect, it } from "vitest";

import {
  countingFor,
  formatRosterStat,
  nextRosterSortState,
  sortRosterPlayers,
} from "@/components/teams/hockeyRosterStats";
import type { HockeyPlayerCountingStats, HockeyRosterPlayer } from "@/types/api";

function counting(
  overrides: Partial<HockeyPlayerCountingStats> = {},
): HockeyPlayerCountingStats {
  return {
    games_played: 10,
    goals: 4,
    assists: 6,
    points: 10,
    shots_on_goal: 28,
    shots_per_game: 2.8,
    average_toi: "18:12",
    save_percentage: null,
    goals_against_average: null,
    ...overrides,
  };
}

function player(
  overrides: Partial<HockeyRosterPlayer> = {},
): HockeyRosterPlayer {
  const season = counting();
  const lastFive = counting({
    games_played: 5,
    shots_on_goal: 50,
    shots_per_game: 9.99,
  });
  return {
    player_id: 1,
    first_name: "Adam",
    last_name: "Center",
    common_name: "Center A.",
    country: "Canada",
    position: "C",
    number: 19,
    line: 1,
    pp_unit: null,
    is_injured: false,
    injury_status: null,
    injury_note: null,
    ...season,
    in_last_lineup: true,
    stat_windows: {
      season,
      last_5: lastFive,
      last_10: season,
    },
    ...overrides,
  };
}

describe("formatRosterStat", () => {
  it("formats shots per game and hides goalie rates for a skater", () => {
    const skater = player();
    const season = countingFor(skater, "season");

    expect(formatRosterStat(skater, season, "shots_per_game")).toBe("2.80");
    expect(formatRosterStat(skater, countingFor(skater, "last_5"), "shots_per_game")).toBe(
      "9.99",
    );
    expect(formatRosterStat(skater, counting({ shots_per_game: null }), "shots_per_game")).toBe(
      "—",
    );
    expect(formatRosterStat(skater, season, "save_percentage")).toBe("—");
  });

  it("formats goalie rates from the selected window", () => {
    const goalie = player({
      position: "G",
      stat_windows: {
        season: counting({ save_percentage: 90, goals_against_average: 2 }),
        last_5: counting({ save_percentage: 80, goals_against_average: 3.1 }),
        last_10: counting({ save_percentage: 90, goals_against_average: 2 }),
      },
    });

    expect(formatRosterStat(goalie, countingFor(goalie, "last_5"), "save_percentage")).toBe(
      "80.00%",
    );
    expect(
      formatRosterStat(goalie, countingFor(goalie, "last_5"), "goals_against_average"),
    ).toBe("3.10");
  });
});

function rankedPlayer(
  playerId: number,
  name: string,
  season: Partial<HockeyPlayerCountingStats>,
  lastFive?: Partial<HockeyPlayerCountingStats>,
): HockeyRosterPlayer {
  const seasonStats = counting(season);
  const recentStats = counting(lastFive ?? season);
  return player({
    player_id: playerId,
    common_name: name,
    stat_windows: {
      season: seasonStats,
      last_5: recentStats,
      last_10: seasonStats,
    },
  });
}

describe("sortRosterPlayers", () => {
  it("puts the highest shots per game first and leaves an empty sample last", () => {
    const low = rankedPlayer(1, "Low L.", { shots_per_game: 1.2, shots_on_goal: 12 });
    const high = rankedPlayer(2, "High H.", { shots_per_game: 4.5, shots_on_goal: 45 });
    const empty = rankedPlayer(3, "Empty E.", {
      games_played: 0,
      shots_on_goal: 0,
      shots_per_game: null,
      average_toi: null,
    });
    const sort = nextRosterSortState(null, "shots_per_game");

    expect(sort.direction).toBe("desc");
    expect(sortRosterPlayers([low, empty, high], "season", sort).map((item) => item.player_id)).toEqual([
      2, 1, 3,
    ]);
    const flipped = nextRosterSortState(sort, "shots_per_game");
    expect(flipped.direction).toBe("asc");
    expect(sortRosterPlayers([low, empty, high], "season", flipped).map((item) => item.player_id)).toEqual([
      1, 2, 3,
    ]);
  });

  it("sorts the selected window and keeps a skater below a goalie on save percentage", () => {
    const cold = rankedPlayer(
      1,
      "Cold C.",
      { shots_per_game: 4 },
      { shots_per_game: 1 },
    );
    const hot = rankedPlayer(
      2,
      "Hot H.",
      { shots_per_game: 1 },
      { shots_per_game: 5 },
    );
    const goalie = player({
      player_id: 9,
      common_name: "Goalie G.",
      position: "G",
      stat_windows: {
        season: counting({ save_percentage: 91 }),
        last_5: counting({ save_percentage: 91 }),
        last_10: counting({ save_percentage: 91 }),
      },
    });
    const skater = rankedPlayer(4, "Skater S.", { shots_per_game: 3 });
    const shots = nextRosterSortState(null, "shots_per_game");
    const saves = nextRosterSortState(null, "save_percentage");

    expect(sortRosterPlayers([cold, hot], "last_5", shots).map((item) => item.player_id)).toEqual([
      2, 1,
    ]);
    expect(
      sortRosterPlayers([skater, goalie], "season", saves).map((item) => item.player_id),
    ).toEqual([9, 4]);
  });

  it("sorts time on ice by duration and names from A to Z", () => {
    const short = rankedPlayer(2, "Zorro Z.", { average_toi: "09:30" });
    const long = rankedPlayer(1, "Adam A.", { average_toi: "21:00" });
    const toi = nextRosterSortState(null, "average_toi");
    const name = nextRosterSortState(null, "name");

    expect(name.direction).toBe("asc");
    expect(sortRosterPlayers([short, long], "season", toi).map((item) => item.player_id)).toEqual([
      1, 2,
    ]);
    expect(sortRosterPlayers([short, long], "season", name).map((item) => item.common_name)).toEqual([
      "Adam A.",
      "Zorro Z.",
    ]);
  });
});
