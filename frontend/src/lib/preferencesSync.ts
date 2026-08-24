import {
  PREFERENCES_VERSION,
  type PreferencesApi,
  type PreferencesStorage,
  type ThemePreference,
  type UserPreferencesV1,
} from "@/lib/preferences";
import { applyResolvedTheme, resolveTheme } from "@/lib/theme";

export interface PreferencesWriteQueue {
  enqueue(task: () => Promise<void>): Promise<void>;
}

export interface PersistThemeOptions {
  theme: ThemePreference;
  storage: PreferencesStorage;
  api: PreferencesApi;
  hasSession: boolean;
  systemPrefersDark: boolean;
  writeQueue?: PreferencesWriteQueue;
}

export interface HydrateAccountPreferencesOptions {
  storage: PreferencesStorage;
  api: PreferencesApi;
  apply: (preferences: UserPreferencesV1) => void;
  shouldApply?: () => boolean;
  writeQueue?: PreferencesWriteQueue;
}

/**
 * Serializes account PUTs so an in-flight first-save cannot finish after a
 * newer `setTheme` write and win last-write-wins on the server.
 */
export function createPreferencesWriteQueue(): PreferencesWriteQueue {
  let tail: Promise<void> = Promise.resolve();

  return {
    enqueue(task: () => Promise<void>): Promise<void> {
      const run = tail.then(task, task);
      tail = run.then(
        () => undefined,
        () => undefined,
      );
      return run;
    },
  };
}

function isWriteStillCurrent(shouldApply?: () => boolean): boolean {
  return shouldApply == null || shouldApply();
}

async function runAccountWrite(
  writeQueue: PreferencesWriteQueue | undefined,
  task: () => Promise<void>,
): Promise<void> {
  if (writeQueue == null) {
    await task();
    return;
  }
  await writeQueue.enqueue(task);
}

/**
 * Write a theme choice to the in-memory document, localStorage and the DOM.
 * With a session, fires `PUT { theme }` without rolling the UI back on error.
 */
export function persistThemePreference(
  options: PersistThemeOptions,
): UserPreferencesV1 {
  const next: UserPreferencesV1 = {
    version: PREFERENCES_VERSION,
    theme: options.theme,
  };
  options.storage.save(next);
  applyResolvedTheme(resolveTheme(next.theme, options.systemPrefersDark));
  if (options.hasSession) {
    void runAccountWrite(options.writeQueue, async () => {
      try {
        await options.api.put(next);
      } catch {
        // sieć/5xx: UI i cache zostają przy nowym wyborze
      }
    });
  }
  return next;
}

function applyRemoteIfCurrent(
  storage: PreferencesStorage,
  apply: (preferences: UserPreferencesV1) => void,
  preferences: UserPreferencesV1,
  shouldApply?: () => boolean,
): void {
  // tuż przed zapisem — toggle mógł podbić epoch po GET
  if (!isWriteStillCurrent(shouldApply)) {
    return;
  }
  storage.save(preferences);
  apply(preferences);
}

/**
 * After mount with a session: GET wins over localStorage when a row exists;
 * a missing row pushes the current local document as the first save.
 * 401/403 (`no-session`) leave the cache alone and do not PUT.
 */
export async function hydrateAccountPreferences(
  options: HydrateAccountPreferencesOptions,
): Promise<void> {
  const { storage, api, apply, shouldApply, writeQueue } = options;
  try {
    const lookup = await api.get();
    if (!isWriteStillCurrent(shouldApply)) {
      return;
    }
    if (lookup.status === "found") {
      applyRemoteIfCurrent(storage, apply, lookup.preferences, shouldApply);
      return;
    }
    if (lookup.status === "no-session") {
      return;
    }
    await runAccountWrite(writeQueue, async () => {
      if (!isWriteStillCurrent(shouldApply)) {
        return;
      }
      await api.put(storage.load());
    });
  } catch {
    // sieć/5xx przy hydracji: zostajemy przy cache z localStorage
  }
}
