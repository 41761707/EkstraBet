import { describe, expect, it } from "vitest";

import {
  BASKETBALL_STARTER_SLOT_COUNT,
  BASKETBALL_STARTER_SLOTS,
  courtMarkersForStarters,
  starterPlayers,
} from "@/components/matches/basketballLineupModel";
import type {
  BasketballLineupPlayer,
  BasketballTeamLineup,
} from "@/types/api";

function player(
  overrides: Partial<BasketballLineupPlayer> &
    Pick<BasketballLineupPlayer, "player_id" | "player_name">,
): BasketballLineupPlayer {
  return {
    team_id: 917,
    number: null,
    starter: true,
    ...overrides,
  };
}

function team(players: BasketballLineupPlayer[]): BasketballTeamLineup {
  return {
    team_id: 917,
    team_name: "New Orleans Pelicans",
    players,
  };
}

describe("starterPlayers", () => {
  it("keeps payload order and drops bench players", () => {
    const roster = team([
      player({ player_id: 1, player_name: "Bey", number: 41, starter: true }),
      player({ player_id: 2, player_name: "Poole", number: 3, starter: false }),
      player({ player_id: 3, player_name: "Fears", number: 0, starter: true }),
    ]);

    expect(starterPlayers(roster).map((item) => item.player_name)).toEqual([
      "Bey",
      "Fears",
    ]);
  });
});

describe("courtMarkersForStarters", () => {
  it("places five starters on 2-1-2 slots sorted by number including 0", () => {
    const markers = courtMarkersForStarters([
      player({ player_id: 41, player_name: "Bey", number: 41 }),
      player({ player_id: 22, player_name: "Queen", number: 22 }),
      player({ player_id: 1, player_name: "Fears", number: 0 }),
      player({ player_id: 25, player_name: "Murphy", number: 25 }),
      player({ player_id: 2, player_name: "Jones", number: 2 }),
    ]);

    expect(markers).toHaveLength(BASKETBALL_STARTER_SLOT_COUNT);
    expect(markers.map((item) => [item.x, item.y])).toEqual(
      BASKETBALL_STARTER_SLOTS.map((slot) => [slot.x, slot.y]),
    );
    expect(markers.map((item) => item.number)).toEqual([0, 2, 22, 25, 41]);
    expect(markers[0].x).toBe(12);
    expect(markers[1].x).toBe(38);
    expect(markers[2].x).toBe(25);
    expect(markers[3].x).toBe(14);
    expect(markers[4].x).toBe(36);
  });

  it("omits a sixth starter from markers", () => {
    const markers = courtMarkersForStarters([
      player({ player_id: 1, player_name: "A", number: 1 }),
      player({ player_id: 2, player_name: "B", number: 2 }),
      player({ player_id: 3, player_name: "C", number: 3 }),
      player({ player_id: 4, player_name: "D", number: 4 }),
      player({ player_id: 5, player_name: "E", number: 5 }),
      player({ player_id: 6, player_name: "F", number: 6 }),
    ]);

    expect(markers).toHaveLength(5);
    expect(markers.map((item) => item.name)).not.toContain("F");
  });

  it("does not place bench players even with a low number", () => {
    const markers = courtMarkersForStarters([
      player({
        player_id: 1,
        player_name: "Starter",
        number: 22,
        starter: true,
      }),
      player({
        player_id: 2,
        player_name: "Poole",
        number: 3,
        starter: false,
      }),
    ]);

    expect(markers).toHaveLength(1);
    expect(markers[0].name).toBe("Starter");
  });

  it("sorts by jersey number regardless of input order", () => {
    const markers = courtMarkersForStarters([
      player({ player_id: 10, player_name: "High", number: 33 }),
      player({ player_id: 11, player_name: "Low", number: 8 }),
    ]);

    expect(markers.map((item) => item.name)).toEqual(["Low", "High"]);
  });

  it("puts null numbers last and tie-breaks by player_id", () => {
    const markers = courtMarkersForStarters([
      player({ player_id: 30, player_name: "NoNumber", number: null }),
      player({ player_id: 20, player_name: "SameB", number: 10 }),
      player({ player_id: 10, player_name: "SameA", number: 10 }),
    ]);

    expect(markers.map((item) => item.name)).toEqual([
      "SameA",
      "SameB",
      "NoNumber",
    ]);
  });
});
