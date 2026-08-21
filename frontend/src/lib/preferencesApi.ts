import { getUserPreferences, putUserPreferences } from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";
import {
  parsePreferences,
  PREFERENCES_VERSION,
  type PreferencesApi,
  type UserPreferencesV1,
} from "@/lib/preferences";

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
  });
}

/**
 * Account preferences adapter. 401/403 behave like no session; GET 404 is
 * "no row yet". Network and 5xx errors propagate to the caller.
 */
export function createPreferencesApi(): PreferencesApi {
  return {
    async get(): Promise<UserPreferencesV1 | null> {
      try {
        return fromApiPayload(await getUserPreferences());
      } catch (error) {
        if (isNoSessionError(error) || isMissingRowError(error)) {
          return null;
        }
        throw error;
      }
    },
    async put(preferences: UserPreferencesV1): Promise<UserPreferencesV1> {
      const document = parsePreferences(preferences);
      try {
        const payload = await putUserPreferences({ theme: document.theme });
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
