import { describe, expect, it } from "vitest";

import {
  ADMIN_LEAGUE_CREATE_ERROR_TITLE,
  GENERIC_ADMIN_LEAGUE_ERROR,
  MAX_LEAGUE_NAME_LENGTH,
  buildCreateLeagueRequest,
  leagueCountryLabel,
  leagueSeasonLabel,
  mapAdminLeagueApiDetail,
  mapAdminLeagueError,
  prependAdminLeague,
  replaceAdminLeague,
  validateAddLeagueForm,
} from "@/components/admin/adminLeaguesModel";
import { ApiError } from "@/lib/apiShared";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
} from "@/types/api";

function sampleLeague(overrides: Partial<AdminLeague> = {}): AdminLeague {
  return {
    id: 48,
    name: "Ekstraklasa",
    country_id: 1,
    country_name: "Polska",
    country_emoji: "🇵🇱",
    sport_id: 1,
    sport_name: "Piłka nożna",
    active: true,
    last_update: "2026-09-01",
    current_season_id: 13,
    tier: 1,
    has_player_stats: false,
    ...overrides,
  };
}

const COUNTRIES: AdminCountry[] = [
  { id: 1, name: "Polska", short_name: "POL", emoji: "🇵🇱" },
];
const SPORTS: AdminSport[] = [{ id: 1, name: "Piłka nożna" }];
const SEASONS: AdminSeason[] = [{ id: 13, years: "2026/27" }];

const VALID_FORM = {
  name: " Ekstraklasa ",
  countryId: "1",
  sportId: "1",
  currentSeasonId: "13",
  tier: "1",
  hasPlayerStats: false,
};

describe("validateAddLeagueForm", () => {
  it("accepts a named league with dictionary ids", () => {
    expect(validateAddLeagueForm(VALID_FORM, COUNTRIES, SPORTS, SEASONS)).toBeNull();
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, currentSeasonId: "", tier: "" },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBeNull();
  });

  it("rejects an empty name after trim", () => {
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, name: "   " },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe("Nazwa ligi jest wymagana");
  });

  it("rejects a name longer than the backend limit", () => {
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, name: "x".repeat(MAX_LEAGUE_NAME_LENGTH + 1) },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe(`Nazwa ligi może mieć maksymalnie ${MAX_LEAGUE_NAME_LENGTH} znaków`);
  });

  it("rejects a missing or unknown country, sport or season", () => {
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, countryId: "" },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe("Wybierz kraj");
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, sportId: "99" },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe("Wybierz sport");
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, currentSeasonId: "99" },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe("Wybierz sezon");
  });

  it("rejects a non-integer tier", () => {
    expect(
      validateAddLeagueForm(
        { ...VALID_FORM, tier: "1.5" },
        COUNTRIES,
        SPORTS,
        SEASONS,
      ),
    ).toBe("Poziom ligi musi być liczbą całkowitą");
  });
});

describe("buildCreateLeagueRequest", () => {
  it("trims the name and maps empty optional fields to null", () => {
    expect(
      buildCreateLeagueRequest({
        ...VALID_FORM,
        currentSeasonId: "",
        tier: "  ",
        hasPlayerStats: true,
      }),
    ).toEqual({
      name: "Ekstraklasa",
      country_id: 1,
      sport_id: 1,
      current_season_id: null,
      tier: null,
      has_player_stats: true,
    });
  });

  it("throws when a required dictionary id is missing", () => {
    expect(() =>
      buildCreateLeagueRequest({ ...VALID_FORM, countryId: "" }),
    ).toThrow("country_id is required");
    expect(() =>
      buildCreateLeagueRequest({ ...VALID_FORM, sportId: "0" }),
    ).toThrow("sport_id is required");
  });
});

describe("admin league list updates", () => {
  it("prepends a created league and replaces a toggled row", () => {
    const existing = sampleLeague();
    const created = sampleLeague({ id: 49, name: "I liga" });
    const prepended = prependAdminLeague([existing], created);
    expect(prepended.map((league) => league.name)).toEqual(["I liga", "Ekstraklasa"]);

    const deactivated = sampleLeague({ id: 49, name: "I liga", active: false });
    expect(replaceAdminLeague(prepended, deactivated)[0]?.active).toBe(false);
  });
});

describe("league labels", () => {
  it("joins country emoji with the name and resolves season years", () => {
    expect(leagueCountryLabel(sampleLeague())).toBe("🇵🇱 Polska");
    expect(leagueCountryLabel(sampleLeague({ country_emoji: null }))).toBe(
      "Polska",
    );
    expect(leagueSeasonLabel(SEASONS, 13)).toBe("2026/27");
    expect(leagueSeasonLabel(SEASONS, null)).toBe("—");
    expect(leagueSeasonLabel(SEASONS, 99)).toBe("99");
  });
});

describe("mapAdminLeagueError", () => {
  it("maps FK, missing-row and name validation details", () => {
    expect(mapAdminLeagueApiDetail("Country not found")).toBe("Nie znaleziono kraju");
    expect(mapAdminLeagueApiDetail("Sport not found")).toBe("Nie znaleziono sportu");
    expect(mapAdminLeagueApiDetail("Season not found")).toBe("Nie znaleziono sezonu");
    expect(mapAdminLeagueApiDetail("League name is required")).toBe(
      "Nazwa ligi jest wymagana",
    );
    expect(
      mapAdminLeagueError(new ApiError(422, "Country not found")),
    ).toBe("Nie znaleziono kraju");
    expect(mapAdminLeagueError(new ApiError(500, ""))).toBe(
      GENERIC_ADMIN_LEAGUE_ERROR,
    );
    expect(ADMIN_LEAGUE_CREATE_ERROR_TITLE).toContain("utworzyć");
  });
});
