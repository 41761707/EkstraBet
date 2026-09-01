import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addFavoriteLeague,
  deleteTyperPublication,
  getLeagueRatingProgress,
  getSeasonProjectionModes,
  getTyperAdminCandidates,
  getTyperAdminPredictionHistory,
  getTyperLongTermAutoResult,
  getTyperLongTermHistory,
  getTyperLongTermAdminHistory,
  getUserPreferences,
  publishTyperMatches,
  putUserPreferences,
  removeFavoriteLeague,
  saveTyperLongTermPicks,
  saveTyperPrediction,
  settleTyperLongTermMarket,
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

describe("typer LM participant client", () => {
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

  it("PUTs a 1X2 pick through the BFF", async () => {
    const payload = {
      match_id: 101,
      outcome: "X",
      previous_outcome: "1",
      audit_written: true,
      created_at: "2026-09-11T18:00:00",
      updated_at: "2026-09-11T19:00:00",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(saveTyperPrediction(101, "X")).resolves.toEqual(payload);

    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/typer-lm/predictions/101");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({ outcome: "X" });
  });
});

describe("typer LM admin client", () => {
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

  it("GETs admin candidates through the BFF", async () => {
    const payload = {
      season_id: 13,
      round_number: 1,
      candidates: [],
      total_count: 0,
      group_match_count: 9,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(getTyperAdminCandidates(13, 1)).resolves.toEqual(payload);
    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain("/api/backend/typer-lm/admin/candidates");
    expect(requested).toContain("season_id=13");
    expect(requested).toContain("round_number=1");
  });

  it("POSTs an atomic publication set without odds in the body", async () => {
    const payload = { publications: [], total_count: 9 };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    const matchIds = [101, 102, 103, 104, 105, 106, 107, 108, 109];
    await expect(publishTyperMatches(13, 1, matchIds)).resolves.toEqual(
      payload,
    );
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/typer-lm/admin/publications");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      season_id: 13,
      round_number: 1,
      match_ids: matchIds,
    });
  });

  it("DELETEs a publication and accepts 204 without a JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    stubBrowserFetch(fetchMock);

    await expect(deleteTyperPublication(101)).resolves.toBeUndefined();
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain(
      "/api/backend/typer-lm/admin/publications/101",
    );
    expect(init.method).toBe("DELETE");
  });

  it("GETs another user's prediction audit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(
      getTyperAdminPredictionHistory({
        userUuid: "user-2",
        matchId: 101,
        seasonId: 13,
      }),
    ).resolves.toEqual([]);
    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain(
      "/api/backend/typer-lm/admin/prediction-history",
    );
    expect(requested).toContain("user_uuid=user-2");
    expect(requested).toContain("match_id=101");
    expect(requested).toContain("season_id=13");
  });
});

describe("typer LM long-term client", () => {
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

  it("PUTs a long-term pick set through the BFF", async () => {
    const payload = {
      market_id: 1,
      team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      previous_team_ids: null,
      audit_written: true,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(
      saveTyperLongTermPicks(1, [1, 2, 3, 4, 5, 6, 7, 8]),
    ).resolves.toEqual(payload);
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain("/api/backend/typer-lm/long-term/markets/1/picks");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({
      team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    });
  });

  it("GETs own long-term history through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(getTyperLongTermHistory(1)).resolves.toEqual([]);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/api/backend/typer-lm/long-term/markets/1/history",
    );
  });

  it("GETs another user's long-term audit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(
      getTyperLongTermAdminHistory({
        userUuid: "user-2",
        marketId: 1,
        seasonId: 13,
      }),
    ).resolves.toEqual([]);
    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain(
      "/api/backend/typer-lm/long-term/admin/prediction-history",
    );
    expect(requested).toContain("user_uuid=user-2");
    expect(requested).toContain("market_id=1");
    expect(requested).toContain("season_id=13");
  });

  it("GETs the admin auto-result through the BFF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ market_id: 1, is_complete: false }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(getTyperLongTermAutoResult(1)).resolves.toEqual({
      market_id: 1,
      is_complete: false,
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/api/backend/typer-lm/long-term/admin/markets/1/auto-result",
    );
  });

  it("POSTs a long-term settlement through the BFF", async () => {
    const payload = {
      market_id: 1,
      team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      settled_by_uuid: "admin-1",
      settled_by_display_name: "Admin",
      settled_at: "2027-01-30T12:00:00",
      result_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    stubBrowserFetch(fetchMock);

    await expect(
      settleTyperLongTermMarket(1, [1, 2, 3, 4, 5, 6, 7, 8]),
    ).resolves.toEqual(payload);
    const [requested, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(requested).toContain(
      "/api/backend/typer-lm/long-term/admin/markets/1/settle",
    );
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    });
  });
});
