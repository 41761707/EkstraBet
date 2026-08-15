import { afterEach, describe, expect, it, vi } from "vitest";

import { getSeasonProjectionModes } from "@/lib/apiClient";
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
