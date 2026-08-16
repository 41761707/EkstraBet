import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getLeagueRatingProgress,
  getSeasonProjectionModes,
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
