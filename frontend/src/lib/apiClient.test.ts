import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addFavoriteLeague,
  getLeagueRatingProgress,
  getSeasonProjectionModes,
  getUserPreferences,
  putUserPreferences,
  removeFavoriteLeague,
} from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";

describe("apiClient first-login gate", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("redirects to /first-login on 403 first_login_required", async () => {
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        origin: "http://localhost:3000",
        replace,
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "first_login_required" }), {
          status: 403,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(getSeasonProjectionModes(1, 2)).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(replace).toHaveBeenCalledWith("/first-login");
  });
});

describe("getLeagueRatingProgress", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("calls the BFF rating-progress path with season and metric", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          league_id: 1,
          league_name: "Test",
          season_id: 13,
          season_years: "2026/27",
          metric: "elo",
          last_played_match_id: null,
          last_played_at: null,
          teams: [],
          biggest_rise: null,
          biggest_fall: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("window", {
      location: { origin: "http://localhost:3000", replace: vi.fn() },
    });
    vi.stubGlobal("fetch", fetchMock);

    await getLeagueRatingProgress(7, 13);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain("/api/backend/leagues/7/rating-progress");
    expect(requested).toContain("season_id=13");
    expect(requested).toContain("metric=elo");
  });
});

describe("favorite league mutations", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function stubBrowserFetch(fetchMock: ReturnType<typeof vi.fn>) {
    vi.stubGlobal("window", {
      location: { origin: "http://localhost:3000", replace: vi.fn() },
    });
    vi.stubGlobal("fetch", fetchMock);
  }

  it("PUTs a favorite league through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ league_id: 4, is_favorite: true }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    stubBrowserFetch(fetchMock);

    await expect(addFavoriteLeague(4)).resolves.toEqual({
      league_id: 4,
      is_favorite: true,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/users/me/favorite-leagues/4");
    expect(init.method).toBe("PUT");
  });

  it("DELETEs a favorite league through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ league_id: 4, is_favorite: false }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    stubBrowserFetch(fetchMock);

    await expect(removeFavoriteLeague(4)).resolves.toEqual({
      league_id: 4,
      is_favorite: false,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/users/me/favorite-leagues/4");
    expect(init.method).toBe("DELETE");
  });
});

describe("user preferences", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function stubBrowserFetch(fetchMock: ReturnType<typeof vi.fn>) {
    vi.stubGlobal("window", {
      location: { origin: "http://localhost:3000", replace: vi.fn() },
    });
    vi.stubGlobal("fetch", fetchMock);
  }

  it("GETs preferences through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ theme: "light", team_name_display: "full" }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    stubBrowserFetch(fetchMock);

    await expect(getUserPreferences()).resolves.toEqual({
      theme: "light",
      team_name_display: "full",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain("/api/backend/users/me/preferences");
  });

  it("PUTs a theme patch through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ theme: "dark", team_name_display: "full" }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    stubBrowserFetch(fetchMock);

    await expect(putUserPreferences({ theme: "dark" })).resolves.toEqual({
      theme: "dark",
      team_name_display: "full",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/users/me/preferences");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({ theme: "dark" });
  });

  it("PUTs a team_name_display patch through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ theme: "light", team_name_display: "shortcut" }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    stubBrowserFetch(fetchMock);

    await expect(
      putUserPreferences({ team_name_display: "shortcut" }),
    ).resolves.toEqual({
      theme: "light",
      team_name_display: "shortcut",
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({
      team_name_display: "shortcut",
    });
  });
});
