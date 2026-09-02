import { afterEach, describe, expect, it, vi } from "vitest";

import { loadAdminPage } from "@/app/admin/loadAdminPage";
import {
  getAdminCountries,
  getAdminLeagues,
  getAdminSeasons,
  getAdminSports,
  getAdminUsers,
  getCurrentUser,
} from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  AdminUser,
  UserPublic,
} from "@/types/api";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminUsers: vi.fn(),
  getAdminLeagues: vi.fn(),
  getAdminCountries: vi.fn(),
  getAdminSports: vi.fn(),
  getAdminSeasons: vi.fn(),
}));

const getCurrentUserMock = vi.mocked(getCurrentUser);
const getAdminUsersMock = vi.mocked(getAdminUsers);
const getAdminLeaguesMock = vi.mocked(getAdminLeagues);
const getAdminCountriesMock = vi.mocked(getAdminCountries);
const getAdminSportsMock = vi.mocked(getAdminSports);
const getAdminSeasonsMock = vi.mocked(getAdminSeasons);

function sampleUser(overrides: Partial<UserPublic> = {}): UserPublic {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    first_login: false,
    is_admin: false,
    ...overrides,
  };
}

function sampleAdminUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    is_active: true,
    is_admin: true,
    first_login: false,
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

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
    last_update: null,
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

function mockAdminCollections(options?: {
  users?: AdminUser[];
  leagues?: AdminLeague[];
  countries?: AdminCountry[];
  sports?: AdminSport[];
  seasons?: AdminSeason[];
}) {
  getAdminUsersMock.mockResolvedValue(options?.users ?? [sampleAdminUser()]);
  getAdminLeaguesMock.mockResolvedValue(options?.leagues ?? [sampleLeague()]);
  getAdminCountriesMock.mockResolvedValue(options?.countries ?? COUNTRIES);
  getAdminSportsMock.mockResolvedValue(options?.sports ?? SPORTS);
  getAdminSeasonsMock.mockResolvedValue(options?.seasons ?? SEASONS);
}

describe("loadAdminPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns forbidden for a signed-in non-admin", async () => {
    getCurrentUserMock.mockResolvedValue(sampleUser({ is_admin: false }));

    await expect(loadAdminPage()).resolves.toEqual({ kind: "forbidden" });
    expect(getAdminUsersMock).not.toHaveBeenCalled();
    expect(getAdminLeaguesMock).not.toHaveBeenCalled();
  });

  it("returns unauthenticated when the session is missing", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(401, "Unauthorized"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "unauthenticated",
    });
  });

  it("returns ok with bootstrapped users, leagues and dropdowns", async () => {
    const currentUser = sampleUser({ is_admin: true });
    const users = [sampleAdminUser()];
    const leagues = [sampleLeague()];
    getCurrentUserMock.mockResolvedValue(currentUser);
    mockAdminCollections({ users, leagues });

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "ok",
      currentUser,
      users,
      usersError: null,
      leagues,
      leaguesError: null,
      countries: COUNTRIES,
      sports: SPORTS,
      seasons: SEASONS,
      dictionariesError: null,
      seasonsError: null,
    });
  });

  it("keeps the page available when the users list fails to load", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);
    mockAdminCollections();
    getAdminUsersMock.mockRejectedValue(new ApiError(500, "Błąd serwera"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "ok",
      currentUser,
      users: [],
      usersError: "Błąd serwera",
      leagues: [sampleLeague()],
      leaguesError: null,
      countries: COUNTRIES,
      sports: SPORTS,
      seasons: SEASONS,
      dictionariesError: null,
      seasonsError: null,
    });
  });

  it("keeps the page available when the leagues list fails to load", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);
    mockAdminCollections();
    getAdminLeaguesMock.mockRejectedValue(new ApiError(500, "Błąd lig"));

    const result = await loadAdminPage();
    expect(result).toMatchObject({
      kind: "ok",
      users: [sampleAdminUser()],
      usersError: null,
      leagues: [],
      leaguesError: "Błąd lig",
      dictionariesError: null,
      seasonsError: null,
    });
  });

  it("keeps the page available when a dictionary dropdown fails", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);
    mockAdminCollections();
    getAdminCountriesMock.mockRejectedValue(new ApiError(500, "Błąd krajów"));

    const result = await loadAdminPage();
    expect(result).toMatchObject({
      kind: "ok",
      countries: [],
      dictionariesError: "Błąd krajów",
    });
  });

  it("keeps the create form available when only seasons fail to load", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);
    mockAdminCollections();
    getAdminSeasonsMock.mockRejectedValue(new ApiError(500, "Błąd sezonów"));

    const result = await loadAdminPage();
    expect(result).toMatchObject({
      kind: "ok",
      seasons: [],
      dictionariesError: null,
      seasonsError: "Błąd sezonów",
    });
  });

  it("treats a 403 from /auth/me as forbidden", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(403, "Forbidden"));

    await expect(loadAdminPage()).resolves.toEqual({ kind: "forbidden" });
  });

  it("treats a 403 from an admin collection as forbidden", async () => {
    getCurrentUserMock.mockResolvedValue(sampleUser({ is_admin: true }));
    mockAdminCollections();
    getAdminLeaguesMock.mockRejectedValue(new ApiError(403, "Forbidden"));

    await expect(loadAdminPage()).resolves.toEqual({ kind: "forbidden" });
  });

  it("returns an error payload when the current-user lookup fails", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(500, "Błąd serwera"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "error",
      message: "Błąd serwera",
    });
  });
});
