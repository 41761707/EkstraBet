import { describe, expect, it } from "vitest";

import {
  formatRating,
  groupRatingRows,
  ratingScale,
  ratingTooltip,
} from "@/components/matches/hockeyGameRatingModel";
import type { HockeyRatedPlayer, HockeyRatingParts } from "@/types/api";

function parts(
  overrides: Partial<HockeyRatingParts> = {},
): HockeyRatingParts {
  return {
    production: 0,
    empty_net: 0,
    shots: 0,
    teammate_goals: 0,
    faceoffs: 0,
    goals_against: 0,
    penalties: 0,
    blocks: 0,
    goaltending: 0,
    ...overrides,
  };
}

function player(
  overrides: Pick<HockeyRatedPlayer, "player_id" | "player_name" | "group"> &
    Partial<HockeyRatedPlayer>,
): HockeyRatedPlayer {
  return {
    offense: 0,
    defense: 0,
    total: 0,
    parts: parts(),
    ...overrides,
  };
}

describe("groupRatingRows", () => {
  const low = player({
    player_id: 1,
    player_name: "Low A.",
    group: "forward",
    offense: 0.2,
    defense: 2,
    total: 2.2,
  });
  const high = player({
    player_id: 2,
    player_name: "High B.",
    group: "forward",
    offense: 3,
    defense: 0.1,
    total: 3.1,
  });
  const mid = player({
    player_id: 3,
    player_name: "Mid C.",
    group: "forward",
    offense: 1,
    defense: 1,
    total: 2,
  });
  const defender = player({
    player_id: 4,
    player_name: "Def D.",
    group: "defense",
    offense: 4,
    defense: 0.5,
    total: 4.5,
  });
  const roster = [low, high, mid, defender];

  it("sorts forwards by offense and keeps a hotter defender in defense", () => {
    const grouped = groupRatingRows(roster, "offense");

    expect(grouped.forward.map((row) => row.player_name)).toEqual([
      "High B.",
      "Mid C.",
      "Low A.",
    ]);
    expect(grouped.defense.map((row) => row.player_name)).toEqual(["Def D."]);
    expect(grouped.goalie).toEqual([]);
    expect(roster.map((row) => row.player_name)).toEqual([
      "Low A.",
      "High B.",
      "Mid C.",
      "Def D.",
    ]);
  });

  it("sorts the same forwards by defense on the defense chart", () => {
    const grouped = groupRatingRows(roster, "defense");

    expect(grouped.forward.map((row) => row.player_name)).toEqual([
      "Low A.",
      "Mid C.",
      "High B.",
    ]);
    expect(grouped.defense.map((row) => row.offense)).toEqual([4]);
  });

  it("breaks a tie by player name ascending", () => {
    const zetterberg = player({
      player_id: 10,
      player_name: "Zetterberg H.",
      group: "forward",
      offense: 1.5,
    });
    const aho = player({
      player_id: 11,
      player_name: "Aho S.",
      group: "forward",
      offense: 1.5,
    });
    const grouped = groupRatingRows([zetterberg, aho], "offense");

    expect(grouped.forward.map((row) => row.player_name)).toEqual([
      "Aho S.",
      "Zetterberg H.",
    ]);
  });
});

describe("ratingScale", () => {
  it("stays at 1 when every absolute value is below 1", () => {
    const players = [
      player({
        player_id: 1,
        player_name: "A",
        group: "forward",
        total: 0.4,
        offense: -0.2,
        defense: 0.1,
      }),
      player({
        player_id: 2,
        player_name: "B",
        group: "defense",
        total: 0.1,
        offense: 0.4,
        defense: -0.3,
      }),
    ];

    expect(ratingScale(players)).toBe(1);
    expect(ratingScale([])).toBe(1);
  });

  it("uses the largest absolute total, offense or defense", () => {
    const players = [
      player({
        player_id: 1,
        player_name: "A",
        group: "goalie",
        total: -3.2,
        offense: 0,
        defense: -3.2,
      }),
    ];

    expect(ratingScale(players)).toBe(3.2);
  });
});

describe("formatRating", () => {
  it("prints a plus, a unicode minus, or an unsigned zero", () => {
    expect(formatRating(3.2)).toBe("+3.2");
    expect(formatRating(-1.4)).toBe("\u22121.4");
    expect(formatRating(0)).toBe("0.0");
    expect(formatRating(-0)).toBe("0.0");
  });
});

describe("ratingTooltip", () => {
  it("skips zero leaves and keeps production and goals against", () => {
    const text = ratingTooltip(
      parts({ production: 3, shots: 0.2, goals_against: -1.4 }),
    );

    expect(text).toBe("Produkcja +3.0, strzały +0.2, bramki stracone \u22121.4");
    expect(text).not.toContain("wznowienia");
    expect(text).not.toContain("bramkarz");
  });

  it("is empty when every leaf is zero", () => {
    expect(ratingTooltip(parts())).toBe("");
  });
});
