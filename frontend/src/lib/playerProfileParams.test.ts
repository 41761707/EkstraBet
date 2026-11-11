import { describe, expect, it } from "vitest";

import {
  buildPlayerProfileHref,
  buildPlayerProfileQuery,
  parsePlayerProfileParams,
  type PlayerProfileParams,
} from "@/lib/playerProfileParams";

const EMPTY: PlayerProfileParams = {
  seasonId: null,
  opponentTeamId: null,
  ownTeamId: null,
  teammateId: null,
  teammateLabel: null,
};

describe("parsePlayerProfileParams", () => {
  it("reads season, opponent, club, teammate and label", () => {
    expect(
      parsePlayerProfileParams({
        season_id: "7",
        opponent_team_id: "4",
        own_team_id: "9",
        teammate_id: "3",
        teammate_label: "  Jan Kowalski  ",
      }),
    ).toEqual({
      seasonId: 7,
      opponentTeamId: 4,
      ownTeamId: 9,
      teammateId: 3,
      teammateLabel: "Jan Kowalski",
    });
  });

  it("turns a garbage number into null and drops a blank label", () => {
    expect(
      parsePlayerProfileParams({
        season_id: "abc",
        opponent_team_id: "1.5",
        own_team_id: "0",
        teammate_id: "-3",
        teammate_label: "   ",
      }),
    ).toEqual(EMPTY);
  });
});

describe("buildPlayerProfileQuery", () => {
  it("omits empty filters", () => {
    expect(buildPlayerProfileQuery(EMPTY)).toBe("");
    expect(
      buildPlayerProfileQuery({
        ...EMPTY,
        seasonId: 7,
        teammateId: 3,
        teammateLabel: "Jan Kowalski",
      }),
    ).toBe("season_id=7&teammate_id=3&teammate_label=Jan+Kowalski");
  });
});

describe("buildPlayerProfileHref", () => {
  it("builds the profile path with the list season", () => {
    expect(buildPlayerProfileHref(15, 7)).toBe("/players/15?season_id=7");
  });

  it("omits the query when the list has no season", () => {
    expect(buildPlayerProfileHref(15, null)).toBe("/players/15");
  });
});
