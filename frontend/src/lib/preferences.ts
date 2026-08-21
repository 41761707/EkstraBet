/** Versioned user preferences contract (local cache and account API). */

export const PREFERENCES_STORAGE_KEY = "ekstrabet.preferences";
export const PREFERENCES_VERSION = 1;

export const THEME_PREFERENCES = ["system", "dark", "light"] as const;

export type ThemePreference = (typeof THEME_PREFERENCES)[number];
export type ResolvedTheme = "dark" | "light";

export interface UserPreferencesV1 {
  version: 1;
  theme: ThemePreference;
}

export interface PreferencesStorage {
  load(): UserPreferencesV1;
  save(preferences: UserPreferencesV1): void;
}

/** HTTP boundary; implemented in SZP-117 (`preferencesApi.ts`). */
export interface PreferencesApi {
  get(): Promise<UserPreferencesV1 | null>;
  put(preferences: UserPreferencesV1): Promise<UserPreferencesV1>;
}

export const DEFAULT_PREFERENCES: UserPreferencesV1 = Object.freeze({
  version: PREFERENCES_VERSION,
  theme: "system",
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isThemePreference(value: unknown): value is ThemePreference {
  return (
    typeof value === "string" &&
    (THEME_PREFERENCES as readonly string[]).includes(value)
  );
}

/**
 * Parse unknown input into a v1 preferences document.
 * Unknown versions, shapes, or theme values fall back to defaults.
 */
export function parsePreferences(value: unknown): UserPreferencesV1 {
  if (!isRecord(value) || value.version !== PREFERENCES_VERSION) {
    return { ...DEFAULT_PREFERENCES };
  }
  if (!isThemePreference(value.theme)) {
    return { ...DEFAULT_PREFERENCES };
  }
  return {
    version: PREFERENCES_VERSION,
    theme: value.theme,
  };
}
