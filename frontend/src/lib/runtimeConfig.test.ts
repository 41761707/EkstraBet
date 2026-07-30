import { afterEach, describe, expect, it, vi } from "vitest";

import {
  assertSafeRuntimeConfig,
  collectProductionConfigErrors,
  getApiBaseUrl,
} from "@/lib/runtimeConfig";
import { buildClientProxyPath } from "@/lib/apiShared";

describe("collectProductionConfigErrors", () => {
  const validProduction = {
    ENVIRONMENT: "production",
    AUTH_ENABLED: "true",
    APP_ORIGIN: "https://ekstrabet.example",
    API_BASE_URL: "http://api:8000",
    AUTH_COOKIE_NAME: "ekstrabet_token",
  };

  it("accepts a complete production configuration", () => {
    expect(collectProductionConfigErrors(validProduction)).toEqual([]);
  });

  it("rejects disabled auth, missing origin/API URL, and public API URL", () => {
    expect(
      collectProductionConfigErrors({
        ...validProduction,
        AUTH_ENABLED: "false",
        APP_ORIGIN: "",
        API_BASE_URL: "",
        NEXT_PUBLIC_API_BASE_URL: "http://public-api.example",
      }),
    ).toEqual(
      expect.arrayContaining([
        "AUTH_ENABLED must be true in production",
        "APP_ORIGIN is required in production",
        "API_BASE_URL is required in production",
        "NEXT_PUBLIC_API_BASE_URL must not be set in production (use BFF only)",
      ]),
    );
  });

  it("throws from assertSafeRuntimeConfig on unsafe production env", () => {
    expect(() =>
      assertSafeRuntimeConfig({
        ENVIRONMENT: "production",
        AUTH_ENABLED: "false",
      }),
    ).toThrow(/Unsafe production configuration/);
  });

  it("rejects Cursor chat flags in production", () => {
    expect(
      collectProductionConfigErrors({
        ...validProduction,
        CHAT_ENABLE_CURSOR: "true",
        NEXT_PUBLIC_CHAT_ENABLE_CURSOR: "1",
      }),
    ).toEqual(
      expect.arrayContaining([
        "CHAT_ENABLE_CURSOR must be false in production",
        "NEXT_PUBLIC_CHAT_ENABLE_CURSOR must be false in production",
      ]),
    );
  });
});

describe("getApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses only API_BASE_URL in production", () => {
    vi.stubEnv("ENVIRONMENT", "production");
    vi.stubEnv("API_BASE_URL", "http://api:8000/");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://should-be-ignored");
    expect(getApiBaseUrl()).toBe("http://api:8000");
  });
});

describe("buildClientProxyPath", () => {
  it("routes browser traffic through the BFF, not a public API host", () => {
    const path = buildClientProxyPath("/leagues", { active: true });
    expect(path).toBe("/api/backend/leagues?active=true");
    expect(path).not.toContain("8000");
    expect(path).not.toContain("api:");
  });
});

describe("apiClient module boundary", () => {
  it("does not import server-only runtimeConfig", async () => {
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile(new URL("./apiClient.ts", import.meta.url), "utf8"),
    );
    expect(source).not.toMatch(
      /from ["']@\/lib\/runtimeConfig["']|from ["']server-only["']|API_BASE_URL|localhost:8000/,
    );
  });
});
