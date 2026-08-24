import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/apiShared";
import { createPreferencesApi } from "@/lib/preferencesApi";

function stubBrowserFetch(fetchMock: ReturnType<typeof vi.fn>): ReturnType<
  typeof vi.fn
> {
  vi.stubGlobal("window", {
    location: { origin: "http://localhost:3000", replace: vi.fn() },
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("createPreferencesApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps GET with a row onto a v1 document", async () => {
    const fetchMock = stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(200, { theme: "light" })),
    );
    const api = createPreferencesApi();

    await expect(api.get()).resolves.toEqual({
      status: "found",
      preferences: { version: 1, theme: "light" },
    });

    const requested = String(fetchMock.mock.calls[0]?.[0]);
    expect(requested).toContain("/api/backend/users/me/preferences");
  });

  it("maps GET 404 to missing (no account row)", async () => {
    stubBrowserFetch(
      vi.fn().mockResolvedValue(
        jsonResponse(404, { detail: "Preferences not found" }),
      ),
    );
    await expect(createPreferencesApi().get()).resolves.toEqual({
      status: "missing",
    });
  });

  it("maps GET 401 to no-session", async () => {
    stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(401, { detail: "Not authenticated" })),
    );
    await expect(createPreferencesApi().get()).resolves.toEqual({
      status: "no-session",
    });
  });

  it("maps GET 403 to no-session without redirecting to first-login", async () => {
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { origin: "http://localhost:3000", replace },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(403, { detail: "first_login_required" }),
      ),
    );

    await expect(createPreferencesApi().get()).resolves.toEqual({
      status: "no-session",
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("PUTs only theme and maps the response onto a v1 document", async () => {
    const fetchMock = stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(200, { theme: "dark" })),
    );
    const api = createPreferencesApi();

    await expect(api.put({ version: 1, theme: "dark" })).resolves.toEqual({
      version: 1,
      theme: "dark",
    });

    const [requested, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(requested).toContain("/api/backend/users/me/preferences");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({ theme: "dark" });
  });

  it("treats PUT 401 as no session and returns the local document", async () => {
    stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(401, { detail: "Not authenticated" })),
    );
    const api = createPreferencesApi();

    await expect(api.put({ version: 1, theme: "light" })).resolves.toEqual({
      version: 1,
      theme: "light",
    });
  });

  it("propagates GET 5xx", async () => {
    stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(500, { detail: "boom" })),
    );
    await expect(createPreferencesApi().get()).rejects.toBeInstanceOf(ApiError);
  });

  it("propagates PUT 5xx", async () => {
    stubBrowserFetch(
      vi.fn().mockResolvedValue(jsonResponse(502, { detail: "upstream" })),
    );
    await expect(
      createPreferencesApi().put({ version: 1, theme: "light" }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});
