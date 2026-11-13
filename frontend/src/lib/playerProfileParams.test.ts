import { describe, expect, it } from "vitest";

import {
  buildPlayerProfileHref,
  buildPlayerProfileQuery,
  canSelectTeammate,
  parsePlayerProfileParams,
  playerProfilePanelHref,
  type PlayerProfileParams,
} from "@/lib/playerProfileParams";
import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/types/api";

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

describe("canSelectTeammate", () => {
  it("rejects the same id", () => {
    expect(canSelectTeammate(15, 15)).toBe(false);
    expect(canSelectTeammate(15, 3)).toBe(true);
  });
});

describe("playerProfilePanelHref", () => {
  it("links a hockey player to the profile with the list season", () => {
    expect(playerProfilePanelHref(HOCKEY_SPORT_ID, 15, 7)).toBe(
      "/players/15?season_id=7",
    );
  });

  it("returns no link for football", () => {
    expect(playerProfilePanelHref(FOOTBALL_SPORT_ID, 15, 7)).toBeNull();
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
