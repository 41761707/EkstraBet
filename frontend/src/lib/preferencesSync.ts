import {
  toPreferencesPatch,
  type PreferencesApi,
  type PreferencesStorage,
  type ThemePreference,
  type UserPreferencesPatch,
  type UserPreferencesV1,
} from "@/lib/preferences";
import { applyResolvedTheme, resolveTheme } from "@/lib/theme";

export interface PreferencesWriteQueue {
  enqueue(task: () => Promise<void>): Promise<void>;
}

export interface PersistPreferencesPatchOptions {
  storage: PreferencesStorage;
  api: PreferencesApi;
  hasSession: boolean;
  systemPrefersDark: boolean;
  writeQueue?: PreferencesWriteQueue;
}

export interface PersistThemeOptions extends PersistPreferencesPatchOptions {
  theme: ThemePreference;
  current: UserPreferencesV1;
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

function definedPatch(update: UserPreferencesPatch): UserPreferencesPatch {
  const patch: UserPreferencesPatch = {};
  if (update.theme !== undefined) {
    patch.theme = update.theme;
  }
  if (update.teamNameDisplay !== undefined) {
    patch.teamNameDisplay = update.teamNameDisplay;
  }
  return patch;
}

function hasPatchFields(update: UserPreferencesPatch): boolean {
  return update.theme !== undefined || update.teamNameDisplay !== undefined;
}

/**
 * Merge a field patch into the current document, persist the full local
 * cache, and PUT only the changed field(s) when a session exists.
 */
export function persistPreferencesPatch(
  current: UserPreferencesV1,
  update: UserPreferencesPatch,
  options: PersistPreferencesPatchOptions,
): UserPreferencesV1 {
  const patch = definedPatch(update);
  const next: UserPreferencesV1 = {
    version: current.version,
    theme: patch.theme ?? current.theme,
    teamNameDisplay: patch.teamNameDisplay ?? current.teamNameDisplay,
  };
  options.storage.save(next);
  applyResolvedTheme(resolveTheme(next.theme, options.systemPrefersDark));
  if (options.hasSession && hasPatchFields(patch)) {
    void runAccountWrite(options.writeQueue, async () => {
      try {
        await options.api.put(patch);
      } catch {
        // sieć/5xx: UI i cache zostają przy nowym wyborze
      }
    });
  }
  return next;
}

/**
 * Write a theme choice by merging onto the in-memory document, not storage.
 * Storage save can no-op (quota / SecurityError); `current` is the source of
 * truth. With a session, fires `PUT { theme }` without rolling the UI back.
 */
export function persistThemePreference(
  options: PersistThemeOptions,
): UserPreferencesV1 {
  return persistPreferencesPatch(
    options.current,
    { theme: options.theme },
    options,
  );
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
      await api.put(toPreferencesPatch(storage.load()));
    });
  } catch {
    // sieć/5xx przy hydracji: zostajemy przy cache z localStorage
  }
}
