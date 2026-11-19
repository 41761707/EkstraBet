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
  teammateId: null,
  matchLimit: null,
  teammateLabel: null,
};

describe("parsePlayerProfileParams", () => {
  it("reads season, opponent, club, teammate and label", () => {
    expect(
      parsePlayerProfileParams({
        season_id: "7",
        opponent_team_id: "4",
        teammate_id: "3",
        teammate_label: "  Jan Kowalski  ",
        match_limit: "10",
      }),
    ).toEqual({
      seasonId: 7,
      opponentTeamId: 4,
      teammateId: 3,
      matchLimit: 10,
      teammateLabel: "Jan Kowalski",
    });
  });

  it("turns a garbage number into null and drops a blank label", () => {
    expect(
      parsePlayerProfileParams({
        season_id: "abc",
        opponent_team_id: "1.5",
        teammate_id: "-3",
        teammate_label: "   ",
        match_limit: "20",
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
        matchLimit: 5,
        teammateLabel: "Jan Kowalski",
      }),
    ).toBe(
      "season_id=7&teammate_id=3&match_limit=5&teammate_label=Jan+Kowalski",
    );
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
