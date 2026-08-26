/** Versioned user preferences contract (local cache and account API). */

export const PREFERENCES_STORAGE_KEY = "ekstrabet.preferences";
export const PREFERENCES_VERSION = 1;

export const THEME_PREFERENCES = ["system", "dark", "light"] as const;
export const TEAM_NAME_DISPLAY_PREFERENCES = ["full", "shortcut"] as const;

export type ThemePreference = (typeof THEME_PREFERENCES)[number];
export type TeamNameDisplayPreference =
  (typeof TEAM_NAME_DISPLAY_PREFERENCES)[number];
export type ResolvedTheme = "dark" | "light";

export interface UserPreferencesV1 {
  version: 1;
  theme: ThemePreference;
  teamNameDisplay: TeamNameDisplayPreference;
}

/** Local camelCase patch; HTTP mapping lives in `preferencesApi.ts`. */
export interface UserPreferencesPatch {
  theme?: ThemePreference;
  teamNameDisplay?: TeamNameDisplayPreference;
}

export interface PreferencesStorage {
  load(): UserPreferencesV1;
  save(preferences: UserPreferencesV1): void;
}

/**
 * Account GET outcome. `missing` is a 404 (no row yet); `no-session` is
 * 401/403 (unauthenticated or first-login gate).
 */
export type PreferencesLookupResult =
  | { status: "found"; preferences: UserPreferencesV1 }
  | { status: "missing" }
  | { status: "no-session" };

/** HTTP boundary; implemented in `preferencesApi.ts`. */
export interface PreferencesApi {
  get(): Promise<PreferencesLookupResult>;
  put(update: UserPreferencesPatch): Promise<UserPreferencesV1>;
}

export interface PreferencesContextValue {
  preferences: UserPreferencesV1;
  resolvedTheme: ResolvedTheme;
  setTheme(theme: ThemePreference): void;
  toggleTheme(): void;
}

export const DEFAULT_PREFERENCES: UserPreferencesV1 = Object.freeze({
  version: PREFERENCES_VERSION,
  theme: "system",
  teamNameDisplay: "full",
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

function isTeamNameDisplayPreference(
  value: unknown,
): value is TeamNameDisplayPreference {
  return (
    typeof value === "string" &&
    (TEAM_NAME_DISPLAY_PREFERENCES as readonly string[]).includes(value)
  );
}

/**
 * Parse unknown input into a v1 preferences document.
 * Unknown versions or shapes fall back to defaults. Theme and team-name
 * fields validate independently so a missing `teamNameDisplay` migrates
 * to `full` without resetting a valid theme.
 */
export function parsePreferences(value: unknown): UserPreferencesV1 {
  if (!isRecord(value) || value.version !== PREFERENCES_VERSION) {
    return { ...DEFAULT_PREFERENCES };
  }
  return {
    version: PREFERENCES_VERSION,
    theme: isThemePreference(value.theme)
      ? value.theme
      : DEFAULT_PREFERENCES.theme,
    teamNameDisplay: isTeamNameDisplayPreference(value.teamNameDisplay)
      ? value.teamNameDisplay
      : DEFAULT_PREFERENCES.teamNameDisplay,
  };
}

/** Map a full local document onto a two-field account patch (first save). */
export function toPreferencesPatch(
  document: UserPreferencesV1,
): UserPreferencesPatch {
  return {
    theme: document.theme,
    teamNameDisplay: document.teamNameDisplay,
  };
}
