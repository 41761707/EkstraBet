import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
  type UserPreferencesV1,
} from "@/lib/preferences";
import {
  createPreferencesWriteQueue,
  hydrateAccountPreferences,
  persistThemePreference,
} from "@/lib/preferencesSync";

function createMemoryStorage(
  initial: UserPreferencesV1 = { ...DEFAULT_PREFERENCES },
): PreferencesStorage {
  let document: UserPreferencesV1 = { ...initial };
  return {
    load(): UserPreferencesV1 {
      return { ...document };
    },
    save(preferences: UserPreferencesV1): void {
      document = { ...preferences };
    },
  };
}

function stubDocumentRoot(): { theme?: string; colorScheme?: string } {
  const root = {
    dataset: {} as { theme?: string },
    style: {} as { colorScheme?: string },
  };
  vi.stubGlobal("document", { documentElement: root });
  return {
    get theme() {
      return root.dataset.theme;
    },
    get colorScheme() {
      return root.style.colorScheme;
    },
  };
}

describe("persistThemePreference", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("saves locally, applies the theme, and PUTs when a session exists", () => {
    const root = stubDocumentRoot();
    const storage = createMemoryStorage();
    const api: PreferencesApi = {
      get: vi.fn(),
      put: vi.fn().mockResolvedValue({ version: 1, theme: "light" }),
    };

    const next = persistThemePreference({
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
    });

    expect(next).toEqual({ version: 1, theme: "light" });
    expect(storage.load()).toEqual({ version: 1, theme: "light" });
    expect(root.theme).toBe("light");
    expect(root.colorScheme).toBe("light");
    expect(api.put).toHaveBeenCalledWith({ version: 1, theme: "light" });
  });

  it("does not PUT without a session", () => {
    stubDocumentRoot();
    const api: PreferencesApi = { get: vi.fn(), put: vi.fn() };

    persistThemePreference({
      theme: "dark",
      storage: createMemoryStorage(),
      api,
      hasSession: false,
      systemPrefersDark: false,
    });

    expect(api.put).not.toHaveBeenCalled();
  });

  it("keeps the local choice when PUT rejects", async () => {
    const root = stubDocumentRoot();
    const storage = createMemoryStorage();
    const api: PreferencesApi = {
      get: vi.fn(),
      put: vi.fn().mockRejectedValue(new Error("network")),
    };

    persistThemePreference({
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
    });

    await Promise.resolve();

    expect(storage.load()).toEqual({ version: 1, theme: "light" });
    expect(root.theme).toBe("light");
  });
});

describe("hydrateAccountPreferences", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("overwrites storage and DOM when GET returns a row", async () => {
    stubDocumentRoot();
    const storage = createMemoryStorage({ version: 1, theme: "dark" });
    const remote: UserPreferencesV1 = { version: 1, theme: "light" };
    const apply = vi.fn();
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({
        status: "found",
        preferences: remote,
      }),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({ storage, api, apply });

    expect(storage.load()).toEqual(remote);
    expect(apply).toHaveBeenCalledWith(remote);
    expect(api.put).not.toHaveBeenCalled();
  });

  it("PUTs the local document when GET returns missing (no row)", async () => {
    const local: UserPreferencesV1 = { version: 1, theme: "light" };
    const storage = createMemoryStorage(local);
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "missing" }),
      put: vi.fn().mockResolvedValue(local),
    };

    await hydrateAccountPreferences({ storage, api, apply: vi.fn() });

    expect(api.put).toHaveBeenCalledWith(local);
  });

  it("skips applying a remote row when shouldApply is false", async () => {
    const storage = createMemoryStorage({ version: 1, theme: "dark" });
    const apply = vi.fn();
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({
        status: "found",
        preferences: { version: 1, theme: "light" },
      }),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({
      storage,
      api,
      apply,
      shouldApply: () => false,
    });

    expect(apply).not.toHaveBeenCalled();
    expect(storage.load()).toEqual({ version: 1, theme: "dark" });
    expect(api.put).not.toHaveBeenCalled();
  });

  it("does not first-save PUT when GET is no-session (401/403)", async () => {
    const local: UserPreferencesV1 = { version: 1, theme: "light" };
    const storage = createMemoryStorage(local);
    const apply = vi.fn();
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "no-session" }),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({ storage, api, apply });

    expect(api.put).not.toHaveBeenCalled();
    expect(apply).not.toHaveBeenCalled();
    expect(storage.load()).toEqual(local);
  });

  it("skips save when shouldApply becomes false after GET", async () => {
    const storage = createMemoryStorage({ version: 1, theme: "dark" });
    const apply = vi.fn();
    let remainingAllows = 1;
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({
        status: "found",
        preferences: { version: 1, theme: "light" },
      }),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({
      storage,
      api,
      apply,
      shouldApply: () => {
        if (remainingAllows === 0) {
          return false;
        }
        remainingAllows -= 1;
        return true;
      },
    });

    expect(apply).not.toHaveBeenCalled();
    expect(storage.load()).toEqual({ version: 1, theme: "dark" });
  });

  it("skips first-save PUT when shouldApply becomes false after GET", async () => {
    const local: UserPreferencesV1 = { version: 1, theme: "system" };
    const storage = createMemoryStorage(local);
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "missing" }),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({
      storage,
      api,
      apply: vi.fn(),
      shouldApply: () => false,
    });

    expect(api.put).not.toHaveBeenCalled();
  });

  it("lets a newer persist PUT win over an in-flight first-save", async () => {
    stubDocumentRoot();
    const local: UserPreferencesV1 = { version: 1, theme: "system" };
    const storage = createMemoryStorage(local);
    const writeQueue = createPreferencesWriteQueue();
    let releaseFirstPut: (() => void) | undefined;
    const firstPutGate = new Promise<void>((resolve) => {
      releaseFirstPut = resolve;
    });
    const putOrder: UserPreferencesV1[] = [];
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "missing" }),
      put: vi.fn().mockImplementation(async (document: UserPreferencesV1) => {
        putOrder.push({ ...document });
        if (putOrder.length === 1) {
          await firstPutGate;
        }
        return document;
      }),
    };

    let epoch = 0;
    const hydratePromise = hydrateAccountPreferences({
      storage,
      api,
      apply: vi.fn(),
      writeQueue,
      shouldApply: () => epoch === 0,
    });

    for (let i = 0; i < 10 && putOrder.length === 0; i += 1) {
      await Promise.resolve();
    }
    expect(putOrder).toEqual([{ version: 1, theme: "system" }]);

    epoch = 1;
    persistThemePreference({
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
      writeQueue,
    });
    expect(putOrder).toHaveLength(1);

    releaseFirstPut?.();
    await hydratePromise;
    await writeQueue.enqueue(async () => undefined);

    expect(putOrder).toEqual([
      { version: 1, theme: "system" },
      { version: 1, theme: "light" },
    ]);
    expect(storage.load()).toEqual({ version: 1, theme: "light" });
  });

  it("keeps the local cache when GET throws", async () => {
    const local: UserPreferencesV1 = { version: 1, theme: "light" };
    const storage = createMemoryStorage(local);
    const apply = vi.fn();
    const api: PreferencesApi = {
      get: vi.fn().mockRejectedValue(new Error("500")),
      put: vi.fn(),
    };

    await hydrateAccountPreferences({ storage, api, apply });

    expect(storage.load()).toEqual(local);
    expect(apply).not.toHaveBeenCalled();
    expect(api.put).not.toHaveBeenCalled();
  });
});
