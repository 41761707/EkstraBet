import { describe, expect, it } from "vitest";

import {
  DEFAULT_PREFERENCES,
  parsePreferences,
  PREFERENCES_STORAGE_KEY,
  toPreferencesPatch,
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

function documentWith(
  overrides: Partial<Pick<UserPreferencesV1, "theme" | "teamNameDisplay">> = {},
): UserPreferencesV1 {
  return { ...DEFAULT_PREFERENCES, ...overrides };
}

describe("parsePreferences", () => {
  it("returns defaults for missing or empty input", () => {
    expect(parsePreferences(undefined)).toEqual(DEFAULT_PREFERENCES);
    expect(parsePreferences(null)).toEqual(DEFAULT_PREFERENCES);
    expect(parsePreferences({})).toEqual(DEFAULT_PREFERENCES);
  });

  it("accepts a valid v1 document", () => {
    expect(
      parsePreferences({
        version: 1,
        theme: "light",
        teamNameDisplay: "shortcut",
      }),
    ).toEqual(documentWith({ theme: "light", teamNameDisplay: "shortcut" }));
    expect(
      parsePreferences({
        version: 1,
        theme: "dark",
        teamNameDisplay: "full",
      }),
    ).toEqual(documentWith({ theme: "dark", teamNameDisplay: "full" }));
    expect(
      parsePreferences({
        version: 1,
        theme: "system",
        teamNameDisplay: "full",
      }),
    ).toEqual(documentWith({ theme: "system" }));
  });

  it("migrates a valid legacy v1 document without teamNameDisplay to full", () => {
    expect(parsePreferences({ version: 1, theme: "light" })).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "full" }),
    );
    expect(parsePreferences({ version: 1, theme: "dark" })).toEqual(
      documentWith({ theme: "dark", teamNameDisplay: "full" }),
    );
    expect(parsePreferences({ version: 1, theme: "system" })).toEqual(
      documentWith({ theme: "system", teamNameDisplay: "full" }),
    );
  });

  it("keeps only allowlisted fields from a valid v1 document", () => {
    expect(
      parsePreferences({
        version: 1,
        theme: "light",
        teamNameDisplay: "shortcut",
        odds_format: "american",
        extra: true,
      }),
    ).toEqual(documentWith({ theme: "light", teamNameDisplay: "shortcut" }));
  });

  it("returns defaults for an unsupported version", () => {
    expect(parsePreferences({ version: 2, theme: "light" })).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences({ version: "1", theme: "light" })).toEqual(
      DEFAULT_PREFERENCES,
    );
  });

  it("falls back to the default theme without resetting a valid teamNameDisplay", () => {
    expect(
      parsePreferences({
        version: 1,
        theme: "sepia",
        teamNameDisplay: "shortcut",
      }),
    ).toEqual(documentWith({ theme: "system", teamNameDisplay: "shortcut" }));
    expect(parsePreferences({ version: 1, theme: "" })).toEqual(
      DEFAULT_PREFERENCES,
    );
    expect(parsePreferences({ version: 1, theme: 0 })).toEqual(
      DEFAULT_PREFERENCES,
    );
  });

  it("falls back to full without resetting a valid theme", () => {
    expect(
      parsePreferences({
        version: 1,
        theme: "light",
        teamNameDisplay: "abbreviation",
      }),
    ).toEqual(documentWith({ theme: "light", teamNameDisplay: "full" }));
    expect(
      parsePreferences({
        version: 1,
        theme: "dark",
        teamNameDisplay: "",
      }),
    ).toEqual(documentWith({ theme: "dark", teamNameDisplay: "full" }));
    expect(
      parsePreferences({
        version: 1,
        theme: "system",
        teamNameDisplay: 1,
      }),
    ).toEqual(documentWith({ theme: "system", teamNameDisplay: "full" }));
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

describe("toPreferencesPatch", () => {
  it("maps both fields from a full local document", () => {
    expect(
      toPreferencesPatch(
        documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
      ),
    ).toEqual({ theme: "light", teamNameDisplay: "shortcut" });
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
    const document = documentWith({
      theme: "light",
      teamNameDisplay: "shortcut",
    });

    storage.save(document);

    expect(JSON.parse(backend.getItem(PREFERENCES_STORAGE_KEY) ?? "")).toEqual(
      document,
    );
    expect(storage.load()).toEqual(document);
  });

  it("migrates a stored legacy v1 document on load", () => {
    const storage = createLocalPreferencesStorage(
      createMemoryStorage({
        [PREFERENCES_STORAGE_KEY]: JSON.stringify({
          version: 1,
          theme: "dark",
        }),
      }),
    );
    expect(storage.load()).toEqual(
      documentWith({ theme: "dark", teamNameDisplay: "full" }),
    );
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
    expect(() =>
      storage.save(documentWith({ theme: "dark" })),
    ).not.toThrow();
  });

  it("no-ops when storage is unavailable", () => {
    const storage = createLocalPreferencesStorage(null);

    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
    expect(() =>
      storage.save(documentWith({ theme: "light" })),
    ).not.toThrow();
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
  });

  it("loads defaults in Node when window/localStorage is missing", () => {
    const storage = createLocalPreferencesStorage();
    expect(storage.load()).toEqual(DEFAULT_PREFERENCES);
    expect(() =>
      storage.save(documentWith({ theme: "dark" })),
    ).not.toThrow();
  });
});
