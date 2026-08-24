import {
  DEFAULT_PREFERENCES,
  parsePreferences,
  PREFERENCES_STORAGE_KEY,
  type PreferencesStorage,
  type UserPreferencesV1,
} from "@/lib/preferences";

interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function readBrowserLocalStorage(): StorageLike | null {
  try {
    const storage = (globalThis as { localStorage?: unknown }).localStorage;
    if (
      storage == null ||
      typeof storage !== "object" ||
      typeof (storage as StorageLike).getItem !== "function" ||
      typeof (storage as StorageLike).setItem !== "function"
    ) {
      return null;
    }
    return storage as StorageLike;
  } catch {
    // localStorage bywa zablokowany (iframe, tryb prywatny) i samo odczytanie rzuca
    return null;
  }
}

function loadFromStorage(storage: StorageLike | null): UserPreferencesV1 {
  if (storage == null) {
    return { ...DEFAULT_PREFERENCES };
  }
  try {
    const raw = storage.getItem(PREFERENCES_STORAGE_KEY);
    if (raw == null) {
      return { ...DEFAULT_PREFERENCES };
    }
    return parsePreferences(JSON.parse(raw) as unknown);
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function saveToStorage(
  storage: StorageLike | null,
  preferences: UserPreferencesV1,
): void {
  if (storage == null) {
    return;
  }
  try {
    storage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify(parsePreferences(preferences)),
    );
  } catch {
    // SecurityError / QuotaExceededError — sesja i tak trzyma bieżący dokument
  }
}

/**
 * localStorage adapter that never throws: missing window, blocked storage,
 * quota, and damaged JSON all fall back to in-memory defaults.
 *
 * Optional `storage` lets tests inject a fake without jsdom. Omit it to use
 * `localStorage` lazily (safe during SSR).
 */
export function createLocalPreferencesStorage(
  storage?: StorageLike | null,
): PreferencesStorage {
  const resolveStorage = (): StorageLike | null =>
    storage !== undefined ? storage : readBrowserLocalStorage();

  return {
    load(): UserPreferencesV1 {
      return loadFromStorage(resolveStorage());
    },
    save(preferences: UserPreferencesV1): void {
      saveToStorage(resolveStorage(), preferences);
    },
  };
}
