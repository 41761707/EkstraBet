import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const cookieStore = { token: undefined as string | undefined };

const COMPLETE_BODY = {
  username: "alice",
  display_name: "Alice",
  new_password: "newpass",
  new_password_confirm: "newpass",
};

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

describe("POST /api/auth/complete-first-login", () => {
  beforeEach(() => {
    cookieStore.token = undefined;
    vi.stubEnv("ENVIRONMENT", "development");
    vi.stubEnv("API_BASE_URL", "http://api:8000");
    vi.stubEnv("AUTH_COOKIE_NAME", "ekstrabet_token");
    vi.stubEnv("AUTH_ENABLED", "true");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns 401 when auth is enabled and the cookie is missing", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import(
      "@/app/api/auth/complete-first-login/route"
    );
    const response = await POST(
      new Request("http://localhost:3000/api/auth/complete-first-login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(COMPLETE_BODY),
      }),
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      detail: "Not authenticated",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("proxies the cookie as Bearer and returns ok on success", async () => {
    cookieStore.token = "jwt-token";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          user: { uuid: "u1", username: "alice", first_login: false },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import(
      "@/app/api/auth/complete-first-login/route"
    );
    const response = await POST(
      new Request("http://localhost:3000/api/auth/complete-first-login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(COMPLETE_BODY),
      }),
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [upstreamUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(upstreamUrl).toBe("http://api:8000/auth/complete-first-login");
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer jwt-token",
    );
    expect(JSON.parse(String(init.body))).toEqual({
      username: "alice",
      display_name: "Alice",
      new_password: "newpass",
      new_password_confirm: "newpass",
    });
  });

  it("forwards a 409 username conflict from FastAPI", async () => {
    cookieStore.token = "jwt-token";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Username already taken" }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    const { POST } = await import(
      "@/app/api/auth/complete-first-login/route"
    );
    const response = await POST(
      new Request("http://localhost:3000/api/auth/complete-first-login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          username: "taken",
          display_name: "Taken",
          new_password: "newpass",
          new_password_confirm: "newpass",
        }),
      }),
    );

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toEqual({
      detail: "Username already taken",
    });
  });
});
