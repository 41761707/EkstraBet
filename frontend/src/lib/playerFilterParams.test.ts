import { describe, expect, it } from "vitest";

import {
  FOOTBALL_SPORT_ID,
  selectCountryFilter,
  teamsForCountry,
  type PlayersFilterValues,
} from "@/lib/playerFilterParams";
import type { PlayerTeamOption } from "@/types/api";

const TEAMS: PlayerTeamOption[] = [
  { id: 10, name: "Arsenal", country_id: 1 },
  { id: 11, name: "Liverpool", country_id: 1 },
  { id: 20, name: "Bayern Monachium", country_id: 2 },
  { id: 21, name: "Borussia Dortmund", country_id: 2 },
];

const FILTERS: PlayersFilterValues = {
  sportId: FOOTBALL_SPORT_ID,
  countryId: 1,
  teamId: 10,
  seasonId: 13,
  matchLimit: 50,
  search: "",
};

describe("teamsForCountry", () => {
  it("returns only teams from the selected country", () => {
    expect(teamsForCountry(TEAMS, 2).map((team) => team.name)).toEqual([
      "Bayern Monachium",
      "Borussia Dortmund",
    ]);
  });

  it("returns all teams when no country is selected", () => {
    expect(teamsForCountry(TEAMS, null)).toEqual(TEAMS);
  });
});

describe("selectCountryFilter", () => {
  it("switches the team to the first club of the new country", () => {
    expect(selectCountryFilter(FILTERS, 2, TEAMS)).toEqual({
      ...FILTERS,
      countryId: 2,
      teamId: 20,
    });
  });

  it("clears the team when the country has no clubs", () => {
    expect(selectCountryFilter(FILTERS, 99, TEAMS).teamId).toBeNull();
  });
});
