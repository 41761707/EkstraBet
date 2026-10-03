import { describe, expect, it } from "vitest";

import {
  formatGoalieStartPercent,
  goalieStartLabels,
  HOCKEY_LINE_TABS,
  linePlayers,
  lineupSourceLabel,
  lineupStatusLabel,
  playersOnLineSheet,
  predictionStageLabel,
  rinkMarkersForLine,
  sortPlayersForLineTable,
} from "@/components/matches/hockeyLineupModel";
import type { HockeyLineupPlayer, HockeyTeamLineup } from "@/types/api";

function samplePlayer(
  overrides: Partial<HockeyLineupPlayer> = {},
): HockeyLineupPlayer {
  return {
    player_id: 1,
    player_name: "Player",
    team_id: 10,
    position: "C",
    number: 19,
    line: 1,
    ...overrides,
  };
}

function sampleTeam(
  lines: HockeyTeamLineup["lines"],
): HockeyTeamLineup {
  return {
    team_id: 10,
    team_name: "Columbus Blue Jackets",
    lines,
  };
}

describe("HOCKEY_LINE_TABS", () => {
  it("lists four Polish line labels", () => {
    expect(HOCKEY_LINE_TABS.map((tab) => tab.line)).toEqual([1, 2, 3, 4]);
    expect(HOCKEY_LINE_TABS.map((tab) => tab.label)).toEqual([
      "Pierwsza linia",
      "Druga linia",
      "Trzecia linia",
      "Czwarta linia",
    ]);
  });
});

describe("linePlayers", () => {
  it("returns players of the requested line", () => {
    const team = sampleTeam([
      { line: 1, players: [samplePlayer({ player_id: 1, player_name: "A" })] },
      { line: 2, players: [samplePlayer({ player_id: 2, line: 2 })] },
    ]);

    expect(linePlayers(team, 1).map((player) => player.player_id)).toEqual([1]);
  });

  it("returns an empty list when the line is missing", () => {
    const team = sampleTeam([{ line: 1, players: [samplePlayer()] }]);

    expect(linePlayers(team, 4)).toEqual([]);
  });
});

describe("sortPlayersForLineTable", () => {
  const scrambled = [
    samplePlayer({ player_id: 1, position: "C", player_name: "C" }),
    samplePlayer({ player_id: 2, position: "RW", player_name: "RW" }),
    samplePlayer({ player_id: 3, position: "D", player_name: "D1" }),
    samplePlayer({ player_id: 4, position: "G", player_name: "G" }),
    samplePlayer({ player_id: 5, position: "LW", player_name: "LW" }),
    samplePlayer({ player_id: 6, position: "D", player_name: "D2" }),
    samplePlayer({ player_id: 7, position: "NN", player_name: "NN" }),
  ];

  it("orders line 1 as G, D, D, LW, C, RW, then unknown positions", () => {
    expect(
      sortPlayersForLineTable(scrambled, 1).map((player) => player.position),
    ).toEqual(["G", "D", "D", "LW", "C", "RW", "NN"]);
  });

  it("orders other lines as D, D, LW, C, RW, then leftover positions", () => {
    expect(
      sortPlayersForLineTable(scrambled, 2).map((player) => player.position),
    ).toEqual(["D", "D", "LW", "C", "RW", "G", "NN"]);
  });
});

describe("rinkMarkersForLine", () => {
  it("places a full first line on six Streamlit slots", () => {
    const markers = rinkMarkersForLine([
      samplePlayer({
        player_id: 1,
        player_name: "Fantilli",
        position: "C",
        number: 19,
      }),
      samplePlayer({
        player_id: 2,
        player_name: "Marchment",
        position: "LW",
        number: 17,
      }),
      samplePlayer({
        player_id: 3,
        player_name: "Marchenko",
        position: "RW",
        number: 86,
      }),
      samplePlayer({
        player_id: 4,
        player_name: "Werenski",
        position: "D",
        number: 8,
      }),
      samplePlayer({
        player_id: 5,
        player_name: "Severson",
        position: "D",
        number: 78,
      }),
      samplePlayer({
        player_id: 6,
        player_name: "Merzlikins",
        position: "G",
        number: 90,
      }),
    ]);

    expect(markers).toHaveLength(6);
    expect(markers.map((marker) => [marker.position, marker.x, marker.y])).toEqual([
      ["RW", 33, 43],
      ["C", 20, 43],
      ["LW", 7, 43],
      ["D", 13.5, 23],
      ["D", 26.5, 23],
      ["G", 20, 12],
    ]);
    expect(markers.map((marker) => marker.name)).toEqual([
      "Marchenko",
      "Fantilli",
      "Marchment",
      "Werenski",
      "Severson",
      "Merzlikins",
    ]);
  });

  it("places a lone RW at x=33", () => {
    const markers = rinkMarkersForLine([
      samplePlayer({ player_id: 3, player_name: "Marchenko", position: "RW" }),
    ]);

    expect(markers).toHaveLength(1);
    expect(markers[0].x).toBe(33);
    expect(markers[0].y).toBe(43);
    expect(markers[0].position).toBe("RW");
  });

  it("keeps only two defense markers when a third D is present", () => {
    const markers = rinkMarkersForLine([
      samplePlayer({ player_id: 4, player_name: "Werenski", position: "D" }),
      samplePlayer({ player_id: 5, player_name: "Severson", position: "D" }),
      samplePlayer({ player_id: 7, player_name: "Extra", position: "D" }),
    ]);

    expect(markers).toHaveLength(2);
    expect(markers.map((marker) => marker.playerId)).toEqual([4, 5]);
    expect(markers.map((marker) => marker.x)).toEqual([13.5, 26.5]);
  });

  it("does not create a marker for NN", () => {
    const markers = rinkMarkersForLine([
      samplePlayer({ player_id: 8, player_name: "Unknown", position: "NN" }),
    ]);

    expect(markers).toHaveLength(0);
  });
});

describe("lineup labels", () => {
  it("names a projected sheet and its source", () => {
    expect(lineupStatusLabel("probable")).toBe("Przewidywany skład");
    expect(lineupStatusLabel("confirmed")).toBe("Skład potwierdzony");
    expect(lineupStatusLabel(null)).toBeNull();
    expect(lineupSourceLabel("MODEL")).toBe("model");
    expect(lineupSourceLabel(" external ")).toBe("zewnętrzny");
    expect(lineupSourceLabel("CONFIRMED")).toBe("potwierdzony");
  });

  it("names the prediction stage", () => {
    expect(predictionStageLabel("initial")).toBe("Predykcja pierwotna");
    expect(predictionStageLabel("final")).toBe("Predykcja ostateczna");
    expect(predictionStageLabel(null)).toBeNull();
  });

  it("formats a goalie start weight as a whole percent", () => {
    expect(formatGoalieStartPercent(0.62)).toBe("62%");
    expect(formatGoalieStartPercent(1)).toBe("100%");
    expect(formatGoalieStartPercent(null)).toBeNull();
    expect(formatGoalieStartPercent(1.2)).toBeNull();
  });
});

describe("goalie placement", () => {
  const starter = samplePlayer({
    player_id: 11,
    player_name: "Merzlikins E.",
    position: "G",
    line: 1,
    start_probability: 0.62,
  });
  const backup = samplePlayer({
    player_id: 12,
    player_name: "Greaves J.",
    position: "G",
    line: 2,
    start_probability: 0.38,
  });
  const secondLineForward = samplePlayer({
    player_id: 13,
    player_name: "Marchenko K.",
    position: "RW",
    line: 2,
  });

  function teamWithSplitGoalies(): HockeyTeamLineup {
    return sampleTeam([
      { line: 1, players: [starter] },
      { line: 2, players: [backup, secondLineForward] },
    ]);
  }

  it("lists every goalie start weight, line 1 before line 2", () => {
    expect(goalieStartLabels(teamWithSplitGoalies())).toEqual([
      { playerId: 11, playerName: "Merzlikins E.", percent: "62%" },
      { playerId: 12, playerName: "Greaves J.", percent: "38%" },
    ]);
  });

  it("keeps the starter on line 1 and drops the backup from line 2", () => {
    const team = teamWithSplitGoalies();
    const lineOne = playersOnLineSheet(linePlayers(team, 1), 1);
    const lineTwo = playersOnLineSheet(linePlayers(team, 2), 2);

    expect(lineOne.map((player) => player.player_id)).toEqual([11]);
    expect(lineTwo.map((player) => player.player_id)).toEqual([13]);
    expect(rinkMarkersForLine(lineTwo).map((marker) => marker.position)).toEqual([
      "RW",
    ]);
    expect(rinkMarkersForLine(lineOne).map((marker) => marker.position)).toEqual([
      "G",
    ]);
  });
});
