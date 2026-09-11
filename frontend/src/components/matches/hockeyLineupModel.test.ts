import { describe, expect, it } from "vitest";

import {
  HOCKEY_LINE_TABS,
  linePlayers,
  rinkMarkersForLine,
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
      ["RW", 33, 45],
      ["C", 20, 45],
      ["LW", 7, 45],
      ["D", 13.5, 25],
      ["D", 26.5, 25],
      ["G", 20, 11],
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
    expect(markers[0].y).toBe(45);
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
