import { describe, expect, it } from "vitest";

import {
  DEFAULT_PREFERENCES,
  parsePreferences,
  PREFERENCES_STORAGE_KEY,
  type UserPreferencesV1,
} from "@/lib/preferences";
import { createLocalPreferencesStorage } from "@/lib/preferencesStorage";

interface MemoryStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function createMemoryStorage(
  initial: Record<string, string> = {},
): MemoryStorage {
  const data: Record<string, string> = { ...initial };
  return {
    getItem(key: string): string | null {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key: string, value: string): void {
      data[key] = value;
    },
  };
}

function createThrowingStorage(error: Error): MemoryStorage {
  return {
    getItem(): string | null {
      throw error;
    },
    setItem(): void {
      throw error;
    },
  };
}

describe("parsePreferences", () => {
  it("returns defaults for missing or empty input", () => {
    expect(parsePreferences(undefined)).toEqual(DEFAULT_PREFERENCES);
    expect(parsePreferences(null)).toEqual(DEFAULT_PREFERENCES);
    expect(parsePreferences({})).toEqual(DEFAULT_PREFERENCES);
  });

  it("accepts a valid v1 document", () => {
    expect(parsePreferences({ version: 1, theme: "light" })).toEqual({
      version: 1,
      theme: "light",
    });
    expect(parsePreferences({ version: 1, theme: "dark" })).toEqual({
      version: 1,
      theme: "dark",
    });
    expect(parsePreferences({ version: 1, theme: "system" })).toEqual({
      version: 1,
      theme: "system",
    });
  });

  it("keeps only allowlisted fields from a valid v1 document", () => {
    expect(
      parsePreferences({
        version: 1,
        theme: "light",
        odds_format: "american",
        extra: true,
      }),
    ).toEqual({ version: 1, theme: "light" });
  });

  it("returns defaults for an unsupported version", () => {
    expect(parsePreferences({ version: 2, theme: "light" })).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences({ version: "1", theme: "light" })).toEqual(
      DEFAULT_PREFERENCES,
    );
  });

  it("returns defaults for a disallowed theme value", () => {
    expect(parsePreferences({ version: 1, theme: "sepia" })).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences({ version: 1, theme: "" })).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences({ version: 1, theme: 0 })).toEqual(
      DEFAULT_PREFERENCES,
    );
  });

  it("returns defaults for non-object input", () => {
    expect(parsePreferences("{\"version\":1,\"theme\":\"light\"}")).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences([{ version: 1, theme: "light" }])).toEqual(
      DEFAULT_PREFERENCES,
    );
  });
});

describe("createLocalPreferencesStorage", () => {
  it("loads defaults when the key is missing", () => {
    const storage = createLocalPreferencesStorage(createMemoryStorage());
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
  });

  it("round-trips a valid v1 document", () => {
    const backend = createMemoryStorage();
    const storage = createLocalPreferencesStorage(backend);
    const document: UserPreferencesV1 = { version: 1, theme: "light" };

    storage.save(document);

    expect(JSON.parse(backend.getItem(PREFERENCES_STORAGE_KEY) ?? "")).toEqual(
      document,
    );
    expect(storage.load()).toEqual(document);
  });

  it("falls back to defaults for damaged JSON", () => {
    const storage = createLocalPreferencesStorage(
      createMemoryStorage({ [PREFERENCES_STORAGE_KEY]: "{not-json" }),
    );
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
  });

  it("falls back to defaults when storage throws", () => {
    const securityError = new Error("blocked");
    securityError.name = "SecurityError";
    const storage = createLocalPreferencesStorage(
      createThrowingStorage(securityError),
    );

    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
    expect(() => storage.save({ version: 1, theme: "dark" })).not.toThrow();
  });

  it("no-ops when storage is unavailable", () => {
    const storage = createLocalPreferencesStorage(null);

    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
    expect(() => storage.save({ version: 1, theme: "light" })).not.toThrow();
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
  });

  it("loads defaults in Node when window/localStorage is missing", () => {
    const storage = createLocalPreferencesStorage();
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
    expect(() => storage.save({ version: 1, theme: "dark" })).not.toThrow();
  });
});
