import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AdminLeaguesPanel,
  AdminLeaguesStatus,
} from "@/components/admin/AdminLeaguesPanel";
import {
  ADMIN_LEAGUES_LOAD_ERROR_TITLE,
  ADMIN_LEAGUES_TITLE,
  ADMIN_LEAGUE_CREATE_ERROR_TITLE,
  ADMIN_LEAGUE_SEASONS_ERROR_TITLE,
  ADMIN_LEAGUE_TOGGLE_ERROR_TITLE,
  EMPTY_ADMIN_LEAGUES_TITLE,
  prependAdminLeague,
  replaceAdminLeague,
} from "@/components/admin/adminLeaguesModel";
import {
  submitCreateAdminLeague,
  submitToggleLeagueActive,
} from "@/components/admin/adminLeaguesMutations";
import { ADD_LEAGUE_FORM_TITLE } from "@/components/admin/AddLeagueForm";
import {
  createAdminLeague,
  setAdminLeagueActive,
} from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  CreateLeagueRequest,
} from "@/types/api";

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

const COUNTRIES: AdminCountry[] = [
  { id: 1, name: "Polska", short_name: "POL", emoji: "🇵🇱" },
];
const SPORTS: AdminSport[] = [{ id: 1, name: "Piłka nożna" }];
const SEASONS: AdminSeason[] = [{ id: 13, years: "2026/27" }];

const CREATE_REQUEST: CreateLeagueRequest = {
  name: "I liga",
  country_id: 1,
  sport_id: 1,
  current_season_id: 13,
  tier: 2,
  has_player_stats: false,
};

function renderPanel(
  leagues: AdminLeague[],
  extra: {
    leaguesError?: string | null;
    dictionariesError?: string | null;
    seasonsError?: string | null;
  } = {},
) {
  return renderToStaticMarkup(
    <AdminLeaguesPanel
      initialLeagues={leagues}
      countries={COUNTRIES}
      sports={SPORTS}
      seasons={SEASONS}
      leaguesError={extra.leaguesError}
      dictionariesError={extra.dictionariesError}
      seasonsError={extra.seasonsError}
    />,
  );
}

describe("AdminLeaguesPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the leagues list, create form and dropdown options", () => {
    const html = renderPanel([
      sampleLeague(),
      sampleLeague({ id: 49, name: "I liga", active: false }),
    ]);

    expect(html).toContain(ADMIN_LEAGUES_TITLE);
    expect(html).toContain(ADD_LEAGUE_FORM_TITLE);
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("I liga");
    expect(html).toContain("Polska");
    expect(html).toContain("Piłka nożna");
    expect(html).toContain("2026/27");
    expect(html).toContain('name="country_id"');
    expect(html).toContain('aria-busy="false"');
  });

  it("renders an empty state when there are no leagues", () => {
    const html = renderPanel([]);

    expect(html).toContain(EMPTY_ADMIN_LEAGUES_TITLE);
    expect(html).toContain(ADD_LEAGUE_FORM_TITLE);
  });

  it("renders a load error through StatusMessage", () => {
    const html = renderPanel([], { leaguesError: "Połączenie odrzucone." });

    expect(html).toContain(ADMIN_LEAGUES_LOAD_ERROR_TITLE);
    expect(html).toContain("Połączenie odrzucone.");
    expect(html).not.toContain(EMPTY_ADMIN_LEAGUES_TITLE);
  });

  it("shows a non-blocking seasons warning without hiding the form", () => {
    const html = renderPanel([sampleLeague()], { seasonsError: "Błąd sezonów" });

    expect(html).toContain(ADMIN_LEAGUE_SEASONS_ERROR_TITLE);
    expect(html).toContain("Błąd sezonów");
    expect(html).toContain(ADD_LEAGUE_FORM_TITLE);
    expect(html).toContain('name="country_id"');
    expect(html).toContain("Utwórz ligę");
  });
});

describe("AdminLeaguesPanel mutations", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates a league through apiClient and prepends the returned row", async () => {
    const existing = sampleLeague();
    const created = sampleLeague({ id: 49, name: "I liga", tier: 2 });
    createAdminLeagueMock.mockResolvedValue(created);

    const result = await submitCreateAdminLeague(CREATE_REQUEST);

    expect(createAdminLeagueMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result).toEqual({ ok: true, league: created });
    if (!result.ok) {
      throw new Error("expected create to succeed");
    }
    const html = renderPanel(prependAdminLeague([existing], result.league));
    expect(html.indexOf("I liga")).toBeLessThan(html.indexOf("Ekstraklasa"));
  });

  it("shows StatusMessage after a 422 FK create error", async () => {
    createAdminLeagueMock.mockRejectedValue(new ApiError(422, "Country not found"));

    const result = await submitCreateAdminLeague(CREATE_REQUEST);

    expect(createAdminLeagueMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected create to fail");
    }
    expect(result.errorTitle).toBe(ADMIN_LEAGUE_CREATE_ERROR_TITLE);
    const html = renderToStaticMarkup(
      <AdminLeaguesStatus title={result.errorTitle} message={result.errorMessage} />,
    );
    expect(html).toContain(ADMIN_LEAGUE_CREATE_ERROR_TITLE);
    expect(html).toContain("Nie znaleziono kraju");
    expect(html).toContain('role="status"');
  });

  it("toggles activity through apiClient and replaces the row", async () => {
    const league = sampleLeague();
    const deactivated = { ...league, active: false };
    setAdminLeagueActiveMock.mockResolvedValue(deactivated);

    const result = await submitToggleLeagueActive(league);

    expect(setAdminLeagueActiveMock).toHaveBeenCalledWith(league.id, false);
    expect(result).toEqual({ ok: true, league: deactivated });
    if (!result.ok) {
      throw new Error("expected toggle to succeed");
    }
    const html = renderPanel(replaceAdminLeague([league], result.league));
    expect(html).toContain("Nieaktywna");
    expect(html).toContain("Aktywuj");
  });

  it("shows StatusMessage after a 404 toggle", async () => {
    setAdminLeagueActiveMock.mockRejectedValue(new ApiError(404, "League not found"));

    const result = await submitToggleLeagueActive(sampleLeague());

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected toggle to fail");
    }
    expect(result.errorTitle).toBe(ADMIN_LEAGUE_TOGGLE_ERROR_TITLE);
    const html = renderToStaticMarkup(
      <AdminLeaguesStatus title={result.errorTitle} message={result.errorMessage} />,
    );
    expect(html).toContain(ADMIN_LEAGUE_TOGGLE_ERROR_TITLE);
    expect(html).toContain("Nie znaleziono ligi");
  });
});
