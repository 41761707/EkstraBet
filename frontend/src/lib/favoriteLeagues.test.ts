import { describe, expect, it } from "vitest";

import {
  nextFavoriteIds,
  orderLeaguesByFavorites,
} from "@/lib/favoriteLeagues";
import type { LeagueSummary } from "@/types/api";

function sampleLeague(
  id: number,
  name: string,
  overrides: Partial<LeagueSummary> = {},
): LeagueSummary {
  return {
    id,
    name,
    country_id: id,
    country_name: "Country",
    country_emoji: null,
    sport_id: 1,
    sport_name: "Football",
    active: true,
    last_update: null,
    slug: name.toLowerCase().replace(/ /g, "-"),
    ...overrides,
  };
}

const austria = sampleLeague(1, "Bundesliga", {
  country_name: "Austria",
});
const poland = sampleLeague(2, "Ekstraklasa", {
  country_name: "Poland",
});
const england = sampleLeague(3, "Premier League", {
  country_name: "England",
});
const spain = sampleLeague(4, "La Liga", {
  country_name: "Spain",
});

const catalog = [austria, england, poland, spain];

describe("orderLeaguesByFavorites", () => {
  it("keeps the input order when there are no favorites", () => {
    expect(orderLeaguesByFavorites(catalog, [])).toEqual(catalog);
  });

  it("lifts several favorites while preserving order in both groups", () => {
    expect(orderLeaguesByFavorites(catalog, [4, 2])).toEqual([
      poland,
      spain,
      austria,
      england,
    ]);
  });

  it("ignores favorite ids that are not in the catalog", () => {
    expect(orderLeaguesByFavorites(catalog, [99, 3])).toEqual([
      england,
      austria,
      poland,
      spain,
    ]);
  });

  it("keeps relative order when every league is a favorite", () => {
    expect(orderLeaguesByFavorites(catalog, [1, 2, 3, 4])).toEqual(catalog);
  });

  it("does not reorder leagues inside the non-favorite group", () => {
    const ordered = orderLeaguesByFavorites(catalog, [3]);
    expect(ordered.slice(1).map((league) => league.id)).toEqual([1, 2, 4]);
  });
});

describe("nextFavoriteIds", () => {
  it("adds a missing id and ignores a duplicate add", () => {
    expect(nextFavoriteIds([1], 4, true)).toEqual([1, 4]);
    expect(nextFavoriteIds([1, 4], 4, true)).toEqual([1, 4]);
  });

  it("removes an existing id and ignores a missing remove", () => {
    expect(nextFavoriteIds([1, 4], 1, false)).toEqual([4]);
    expect(nextFavoriteIds([4], 1, false)).toEqual([4]);
  });
});
