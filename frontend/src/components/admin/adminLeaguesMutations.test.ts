import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ADMIN_LEAGUE_CREATE_ERROR_TITLE,
  ADMIN_LEAGUE_TOGGLE_ERROR_TITLE,
} from "@/components/admin/adminLeaguesModel";
import {
  submitCreateAdminLeague,
  submitToggleLeagueActive,
} from "@/components/admin/adminLeaguesMutations";
import {
  createAdminLeague,
  setAdminLeagueActive,
} from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";
import type { AdminLeague, CreateLeagueRequest } from "@/types/api";

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return {
    ...actual,
    createAdminLeague: vi.fn(),
    setAdminLeagueActive: vi.fn(),
  };
});

const createAdminLeagueMock = vi.mocked(createAdminLeague);
const setAdminLeagueActiveMock = vi.mocked(setAdminLeagueActive);

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

const CREATE_REQUEST: CreateLeagueRequest = {
  name: "I liga",
  country_id: 1,
  sport_id: 1,
  current_season_id: 13,
  tier: 2,
  has_player_stats: false,
};

describe("admin league mutations", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates a league through apiClient", async () => {
    const created = sampleLeague({ id: 49, name: "I liga", tier: 2 });
    createAdminLeagueMock.mockResolvedValue(created);

    const result = await submitCreateAdminLeague(CREATE_REQUEST);

    expect(createAdminLeagueMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result).toEqual({ ok: true, league: created });
  });

  it("returns the create error title when the API rejects the country", async () => {
    createAdminLeagueMock.mockRejectedValue(
      new ApiError(422, "Country not found"),
    );

    const result = await submitCreateAdminLeague(CREATE_REQUEST);

    expect(createAdminLeagueMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected create to fail");
    }
    expect(result.errorTitle).toBe(ADMIN_LEAGUE_CREATE_ERROR_TITLE);
  });

  it("toggles activity through apiClient", async () => {
    const league = sampleLeague();
    const deactivated = { ...league, active: false };
    setAdminLeagueActiveMock.mockResolvedValue(deactivated);

    const result = await submitToggleLeagueActive(league);

    expect(setAdminLeagueActiveMock).toHaveBeenCalledWith(league.id, false);
    expect(result).toEqual({ ok: true, league: deactivated });
  });

  it("returns the toggle error title when the API cannot find the league", async () => {
    setAdminLeagueActiveMock.mockRejectedValue(
      new ApiError(404, "League not found"),
    );

    const result = await submitToggleLeagueActive(sampleLeague());

    expect(setAdminLeagueActiveMock).toHaveBeenCalledWith(48, false);
    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected toggle to fail");
    }
    expect(result.errorTitle).toBe(ADMIN_LEAGUE_TOGGLE_ERROR_TITLE);
  });
});
