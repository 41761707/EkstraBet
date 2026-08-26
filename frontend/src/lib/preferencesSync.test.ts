import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
  type UserPreferencesPatch,
  type UserPreferencesV1,
} from "@/lib/preferences";
import {
  createPreferencesWriteQueue,
  hydrateAccountPreferences,
  persistPreferencesPatch,
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

function createNoOpStorage(initial: UserPreferencesV1): PreferencesStorage {
  return {
    load(): UserPreferencesV1 {
      return { ...initial };
    },
    save(): void {
      // quota / SecurityError — dokument zostaje tylko w pamięci sesji
    },
  };
}

function documentWith(
  overrides: Partial<Pick<UserPreferencesV1, "theme" | "teamNameDisplay">> = {},
): UserPreferencesV1 {
  return { ...DEFAULT_PREFERENCES, ...overrides };
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
      put: vi.fn().mockResolvedValue(documentWith({ theme: "light" })),
    };

    const next = persistThemePreference({
      current: storage.load(),
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
    });

    expect(next).toEqual(documentWith({ theme: "light" }));
    expect(storage.load()).toEqual(documentWith({ theme: "light" }));
    expect(root.theme).toBe("light");
    expect(root.colorScheme).toBe("light");
    expect(api.put).toHaveBeenCalledWith({ theme: "light" });
  });

  it("does not PUT without a session", () => {
    stubDocumentRoot();
    const api: PreferencesApi = { get: vi.fn(), put: vi.fn() };

    persistThemePreference({
      current: DEFAULT_PREFERENCES,
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
      current: storage.load(),
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
    });

    await Promise.resolve();

    expect(storage.load()).toEqual(documentWith({ theme: "light" }));
    expect(root.theme).toBe("light");
  });

  it("does not reset teamNameDisplay when only theme changes", () => {
    stubDocumentRoot();
    const storage = createMemoryStorage(
      documentWith({ theme: "dark", teamNameDisplay: "shortcut" }),
    );
    const api: PreferencesApi = {
      get: vi.fn(),
      put: vi.fn().mockResolvedValue(
        documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
      ),
    };

    const next = persistThemePreference({
      current: storage.load(),
      theme: "light",
      storage,
      api,
      hasSession: true,
      systemPrefersDark: true,
    });

    expect(next).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
    expect(storage.load()).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
    expect(api.put).toHaveBeenCalledWith({ theme: "light" });
    expect(api.put).not.toHaveBeenCalledWith(
      expect.objectContaining({ teamNameDisplay: expect.anything() }),
    );
  });

  it("keeps in-memory shortcut when storage save is a no-op", () => {
    stubDocumentRoot();
    const stored = documentWith({ theme: "dark", teamNameDisplay: "full" });
    const inMemory = documentWith({
      theme: "dark",
      teamNameDisplay: "shortcut",
    });
    const storage = createNoOpStorage(stored);
    const api: PreferencesApi = { get: vi.fn(), put: vi.fn() };

    const next = persistThemePreference({
      current: inMemory,
      theme: "light",
      storage,
      api,
      hasSession: false,
      systemPrefersDark: true,
    });

    expect(next).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
    expect(storage.load()).toEqual(stored);
  });
});

describe("persistPreferencesPatch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("PUTs only teamNameDisplay and keeps the current theme", () => {
    stubDocumentRoot();
    const current = documentWith({ theme: "light", teamNameDisplay: "full" });
    const storage = createMemoryStorage(current);
    const api: PreferencesApi = {
      get: vi.fn(),
      put: vi.fn().mockResolvedValue(
        documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
      ),
    };

    const next = persistPreferencesPatch(
      current,
      { teamNameDisplay: "shortcut" },
      {
        storage,
        api,
        hasSession: true,
        systemPrefersDark: true,
      },
    );

    expect(next).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
    expect(storage.load()).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
    expect(api.put).toHaveBeenCalledWith({ teamNameDisplay: "shortcut" });
    expect(api.put).not.toHaveBeenCalledWith(
      expect.objectContaining({ theme: expect.anything() }),
    );
  });
});

describe("hydrateAccountPreferences", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("overwrites storage and DOM when GET returns a row", async () => {
    stubDocumentRoot();
    const storage = createMemoryStorage(documentWith({ theme: "dark" }));
    const remote = documentWith({ theme: "light", teamNameDisplay: "shortcut" });
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

  it("PUTs the full local document when GET returns missing (no row)", async () => {
    const local = documentWith({ theme: "light", teamNameDisplay: "shortcut" });
    const storage = createMemoryStorage(local);
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "missing" }),
      put: vi.fn().mockResolvedValue(local),
    };

    await hydrateAccountPreferences({ storage, api, apply: vi.fn() });

    expect(api.put).toHaveBeenCalledWith({
      theme: "light",
      teamNameDisplay: "shortcut",
    });
  });

  it("skips applying a remote row when shouldApply is false", async () => {
    const storage = createMemoryStorage(documentWith({ theme: "dark" }));
    const apply = vi.fn();
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({
        status: "found",
        preferences: documentWith({ theme: "light" }),
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
    expect(storage.load()).toEqual(documentWith({ theme: "dark" }));
    expect(api.put).not.toHaveBeenCalled();
  });

  it("does not first-save PUT when GET is no-session (401/403)", async () => {
    const local = documentWith({ theme: "light" });
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
    const storage = createMemoryStorage(documentWith({ theme: "dark" }));
    const apply = vi.fn();
    let remainingAllows = 1;
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({
        status: "found",
        preferences: documentWith({ theme: "light" }),
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
    expect(storage.load()).toEqual(documentWith({ theme: "dark" }));
  });

  it("skips first-save PUT when shouldApply becomes false after GET", async () => {
    const local = documentWith({ theme: "system" });
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
    const local = documentWith({ theme: "system", teamNameDisplay: "shortcut" });
    const storage = createMemoryStorage(local);
    const writeQueue = createPreferencesWriteQueue();
    let releaseFirstPut: (() => void) | undefined;
    const firstPutGate = new Promise<void>((resolve) => {
      releaseFirstPut = resolve;
    });
    const putOrder: UserPreferencesPatch[] = [];
    const api: PreferencesApi = {
      get: vi.fn().mockResolvedValue({ status: "missing" }),
      put: vi.fn().mockImplementation(async (update: UserPreferencesPatch) => {
        putOrder.push({ ...update });
        if (putOrder.length === 1) {
          await firstPutGate;
        }
        return documentWith({
          theme: update.theme ?? local.theme,
          teamNameDisplay: update.teamNameDisplay ?? local.teamNameDisplay,
        });
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
    expect(putOrder).toEqual([
      { theme: "system", teamNameDisplay: "shortcut" },
    ]);

    epoch = 1;
    persistThemePreference({
      current: storage.load(),
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
      { theme: "system", teamNameDisplay: "shortcut" },
      { theme: "light" },
    ]);
    expect(storage.load()).toEqual(
      documentWith({ theme: "light", teamNameDisplay: "shortcut" }),
    );
  });

  it("keeps the local cache when GET throws", async () => {
    const local = documentWith({ theme: "light" });
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
