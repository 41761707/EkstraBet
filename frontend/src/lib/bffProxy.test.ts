import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildUpstreamUrl,
  isAllowedMutatingOrigin,
  isMethodAllowedForPath,
  isMutatingMethod,
  normalizeBffPath,
} from "@/lib/bffProxy";

const cookieStore = { token: undefined as string | undefined };

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      if (name === "ekstrabet_token" && cookieStore.token) {
        return { value: cookieStore.token };
      }
      return undefined;
    },
  }),
}));

describe("normalizeBffPath", () => {
  it("accepts relative allowlisted-style paths", () => {
    expect(normalizeBffPath(["leagues", "1", "matches"])).toEqual({
      ok: true,
      path: "leagues/1/matches",
    });
  });

  it("rejects empty paths", () => {
    expect(normalizeBffPath([])).toEqual({ ok: false, reason: "empty" });
  });

  it("rejects absolute URLs and protocol-relative targets", () => {
    expect(normalizeBffPath(["https://evil.example/secret"])).toMatchObject({
      ok: false,
      reason: "absolute",
    });
    expect(normalizeBffPath(["//evil.example/secret"])).toMatchObject({
      ok: false,
      reason: "absolute",
    });
  });

  it("rejects backslashes and traversal segments", () => {
    expect(normalizeBffPath(["leagues", "..", "teams"])).toMatchObject({
      ok: false,
      reason: "traversal",
    });
    expect(normalizeBffPath(["leagues\\..\\teams"])).toMatchObject({
      ok: false,
      reason: "backslash",
    });
  });

  it("rejects encoded separators used for SSRF/traversal", () => {
    expect(normalizeBffPath(["leagues%2f..%2fteams"])).toMatchObject({
      ok: false,
      reason: "encoded-separator",
    });
    expect(normalizeBffPath(["..%2fauth%2flogin"])).toMatchObject({
      ok: false,
      reason: "encoded-separator",
    });
    expect(normalizeBffPath(["leagues%5c..%5cteams"])).toMatchObject({
      ok: false,
      reason: "encoded-separator",
    });
  });
});

describe("isMethodAllowedForPath", () => {
  it("allows GET for leagues and POST for predictions", () => {
    expect(isMethodAllowedForPath("leagues/1", "GET")).toBe(true);
    expect(isMethodAllowedForPath("leagues/1/rating-progress", "GET")).toBe(
      true,
    );
    expect(isMethodAllowedForPath("predictions/preview", "POST")).toBe(true);
  });

  it("rejects disallowed methods and prefixes", () => {
    expect(isMethodAllowedForPath("leagues/1", "DELETE")).toBe(false);
    expect(isMethodAllowedForPath("auth/login", "POST")).toBe(false);
    expect(isMethodAllowedForPath("admin/users", "GET")).toBe(false);
    expect(isMethodAllowedForPath("odds/match/1", "GET")).toBe(false);
    expect(isMethodAllowedForPath("helper/seasons", "GET")).toBe(false);
  });
});

describe("mutating origin checks", () => {
  it("detects mutating methods", () => {
    expect(isMutatingMethod("POST")).toBe(true);
    expect(isMutatingMethod("get")).toBe(false);
  });

  it("requires Origin to match APP_ORIGIN", () => {
    expect(
      isAllowedMutatingOrigin("http://localhost:3000", "http://localhost:3000"),
    ).toBe(true);
    expect(
      isAllowedMutatingOrigin("https://evil.example", "http://localhost:3000"),
    ).toBe(false);
    expect(isAllowedMutatingOrigin(null, "http://localhost:3000")).toBe(false);
    expect(isAllowedMutatingOrigin("http://localhost:3000", null)).toBe(false);
  });
});

describe("buildUpstreamUrl", () => {
  it("keeps the request under the API base URL", () => {
    const url = buildUpstreamUrl(
      "http://api:8000",
      "leagues/1",
      "?active=true",
    );
    expect(url.toString()).toBe("http://api:8000/leagues/1?active=true");
  });
});

describe("BFF route handler", () => {
  beforeEach(() => {
    cookieStore.token = undefined;
    vi.stubEnv("ENVIRONMENT", "development");
    vi.stubEnv("API_BASE_URL", "http://api:8000");
    vi.stubEnv("APP_ORIGIN", "http://localhost:3000");
    vi.stubEnv("AUTH_COOKIE_NAME", "ekstrabet_token");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("rejects traversal before calling upstream", async () => {
    vi.stubEnv("AUTH_ENABLED", "false");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { GET } = await import("@/app/api/backend/[...path]/route");
    const response = await GET(new Request("http://localhost:3000/api/backend/x"), {
      params: Promise.resolve({ path: ["..", "auth", "login"] }),
    });

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects disallowed methods", async () => {
    vi.stubEnv("AUTH_ENABLED", "false");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { DELETE } = await import("@/app/api/backend/[...path]/route");
    const response = await DELETE(
      new Request("http://localhost:3000/api/backend/leagues/1", {
        method: "DELETE",
      }),
      { params: Promise.resolve({ path: ["leagues", "1"] }) },
    );

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects mutating requests with a foreign Origin", async () => {
    vi.stubEnv("AUTH_ENABLED", "false");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import("@/app/api/backend/[...path]/route");
    const response = await POST(
      new Request("http://localhost:3000/api/backend/predictions/preview", {
        method: "POST",
        headers: {
          origin: "https://evil.example",
          "content-type": "application/json",
        },
        body: "{}",
      }),
      { params: Promise.resolve({ path: ["predictions", "preview"] }) },
    );

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 401 when auth is enabled and cookie is missing", async () => {
    vi.stubEnv("AUTH_ENABLED", "true");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { GET } = await import("@/app/api/backend/[...path]/route");
    const response = await GET(
      new Request("http://localhost:3000/api/backend/leagues"),
      { params: Promise.resolve({ path: ["leagues"] }) },
    );

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("proxies an allowlisted GET with Authorization from the cookie", async () => {
    vi.stubEnv("AUTH_ENABLED", "true");
    cookieStore.token = "jwt-token";

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ leagues: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { GET } = await import("@/app/api/backend/[...path]/route");
    const response = await GET(
      new Request("http://localhost:3000/api/backend/leagues?active=true", {
        headers: { accept: "application/json" },
      }),
      { params: Promise.resolve({ path: ["leagues"] }) },
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [upstreamUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(upstreamUrl).toBe("http://api:8000/leagues?active=true");
    expect((init.headers as Headers).get("authorization")).toBe(
      "Bearer jwt-token",
    );
  });

  it("proxies an allowlisted POST when Origin matches APP_ORIGIN", async () => {
    vi.stubEnv("AUTH_ENABLED", "true");
    cookieStore.token = "jwt-token";

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import("@/app/api/backend/[...path]/route");
    const response = await POST(
      new Request("http://localhost:3000/api/backend/predictions/preview", {
        method: "POST",
        headers: {
          origin: "http://localhost:3000",
          "content-type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({ home_team_id: 1, away_team_id: 2 }),
      }),
      { params: Promise.resolve({ path: ["predictions", "preview"] }) },
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [upstreamUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(upstreamUrl).toBe("http://api:8000/predictions/preview");
    expect(init.method).toBe("POST");
    expect((init.headers as Headers).get("authorization")).toBe(
      "Bearer jwt-token",
    );
    expect((init.headers as Headers).get("content-type")).toBe(
      "application/json",
    );
  });
});
