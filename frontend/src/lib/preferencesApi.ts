import { getUserPreferences, putUserPreferences } from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";
import {
  parsePreferences,
  PREFERENCES_VERSION,
  type PreferencesApi,
  type PreferencesLookupResult,
  type UserPreferencesPatch,
  type UserPreferencesV1,
} from "@/lib/preferences";
import type { UserPreferencesUpdate } from "@/types/api";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNoSessionError(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 401 || error.status === 403)
  );
}

function isMissingRowError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** Map the HTTP document (no version) onto the local v1 cache shape. */
function fromApiPayload(payload: unknown): UserPreferencesV1 {
  if (!isRecord(payload)) {
    return parsePreferences(undefined);
  }
  return parsePreferences({
    version: PREFERENCES_VERSION,
    theme: payload.theme,
    teamNameDisplay: payload.team_name_display,
  });
}

function toApiUpdate(update: UserPreferencesPatch): UserPreferencesUpdate {
  const body: UserPreferencesUpdate = {};
  if (update.theme !== undefined) {
    body.theme = update.theme;
  }
  if (update.teamNameDisplay !== undefined) {
    body.team_name_display = update.teamNameDisplay;
  }
  return body;
}

/**
 * Account preferences adapter. 401/403 are `no-session`; GET 404 is
 * `missing` (first save). Network and 5xx errors propagate to the caller.
 */
export function createPreferencesApi(): PreferencesApi {
  return {
    async get(): Promise<PreferencesLookupResult> {
      try {
        return {
          status: "found",
          preferences: fromApiPayload(await getUserPreferences()),
        };
      } catch (error) {
        if (isNoSessionError(error)) {
          return { status: "no-session" };
        }
        if (isMissingRowError(error)) {
          return { status: "missing" };
        }
        throw error;
      }
    },
    async put(update: UserPreferencesPatch): Promise<UserPreferencesV1> {
      const document = parsePreferences({
        version: PREFERENCES_VERSION,
        ...update,
      });
      try {
        const payload = await putUserPreferences(toApiUpdate(update));
        return fromApiPayload(payload);
      } catch (error) {
        if (isNoSessionError(error)) {
          return document;
        }
        throw error;
      }
    },
  };
}
