import vm from "node:vm";

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  PREFERENCES_VERSION,
  THEME_PREFERENCES,
} from "@/lib/preferences";
import {
  applyResolvedTheme,
  buildThemeBootstrapScript,
  COLOR_SCHEME_DARK_QUERY,
  getSystemPrefersDark,
  resolveTheme,
} from "@/lib/theme";

const RESOLVE_CASES = [
  ["system", true, "dark"],
  ["system", false, "light"],
  ["dark", true, "dark"],
  ["dark", false, "dark"],
  ["light", true, "light"],
  ["light", false, "light"],
] as const;

describe("resolveTheme", () => {
  it.each(RESOLVE_CASES)(
    "preference %s with systemPrefersDark=%s resolves to %s",
    (preference, systemPrefersDark, expected) => {
      expect(resolveTheme(preference, systemPrefersDark)).toBe(expected);
    },
  );
});

describe("getSystemPrefersDark", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("falls back to dark when window is missing", () => {
    expect(getSystemPrefersDark()).toBe(true);
  });

  it("falls back to dark when matchMedia is missing", () => {
    vi.stubGlobal("window", {});
    expect(getSystemPrefersDark()).toBe(true);
  });

  it("reads prefers-color-scheme from matchMedia", () => {
    vi.stubGlobal("window", {
      matchMedia(query: string) {
        expect(query).toBe(COLOR_SCHEME_DARK_QUERY);
        return { matches: false };
      },
    });
    expect(getSystemPrefersDark()).toBe(false);
  });

  it("falls back to dark when matchMedia throws", () => {
    vi.stubGlobal("window", {
      matchMedia() {
        throw new Error("blocked");
      },
    });
    expect(getSystemPrefersDark()).toBe(true);
  });
});

describe("applyResolvedTheme", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sets data-theme and color-scheme on the document root", () => {
    const root = {
      dataset: {} as { theme?: string },
      style: {} as { colorScheme?: string },
    };
    vi.stubGlobal("document", { documentElement: root });

    applyResolvedTheme("light");

    expect(root.dataset.theme).toBe("light");
    expect(root.style.colorScheme).toBe("light");
  });

  it("no-ops when document is unavailable", () => {
    expect(() => applyResolvedTheme("dark")).not.toThrow();
  });
});

interface BootstrapRoot {
  dataset: { theme?: string };
  style: { colorScheme?: string };
}

function runBootstrap(options: {
  stored?: string | null;
  systemPrefersDark?: boolean;
  storageThrows?: boolean;
  matchMediaThrows?: boolean;
}): BootstrapRoot {
  const root: BootstrapRoot = { dataset: {}, style: {} };
  const sandbox = {
    document: { documentElement: root },
    localStorage: {
      getItem(): string | null {
        if (options.storageThrows) {
          throw new Error("blocked");
        }
        return options.stored === undefined ? null : options.stored;
      },
    },
    window: {
      matchMedia() {
        if (options.matchMediaThrows) {
          throw new Error("no matchMedia");
        }
        return { matches: options.systemPrefersDark ?? true };
      },
    },
  };
  vm.runInNewContext(buildThemeBootstrapScript(), sandbox);
  return root;
}

describe("buildThemeBootstrapScript", () => {
  it("embeds the shared storage key, version and allowlist", () => {
    const script = buildThemeBootstrapScript();

    expect(script).toContain(JSON.stringify(PREFERENCES_STORAGE_KEY));
    expect(script).toContain(JSON.stringify(PREFERENCES_VERSION));
    expect(script).toContain(JSON.stringify([...THEME_PREFERENCES]));
    expect(script).toContain(JSON.stringify(DEFAULT_PREFERENCES.theme));
    expect(script).toContain(JSON.stringify(COLOR_SCHEME_DARK_QUERY));
    expect(script).toContain("dataset.theme");
    expect(script).toContain("colorScheme");
    expect(script).not.toContain("React");
    // Next 15 RSC payload zamienia & na \u0026 i psuje IIFE przy hydratacji
    expect(script).not.toContain("&");
  });

  it("applies system+dark when storage is empty", () => {
    const root = runBootstrap({ systemPrefersDark: true });
    expect(root.dataset.theme).toBe("dark");
    expect(root.style.colorScheme).toBe("dark");
  });

  it("applies system+light when storage is empty and the OS is light", () => {
    const root = runBootstrap({ systemPrefersDark: false });
    expect(root.dataset.theme).toBe("light");
    expect(root.style.colorScheme).toBe("light");
  });

  it("honors an explicit light document regardless of the OS", () => {
    const stored = JSON.stringify({ version: 1, theme: "light" });
    const root = runBootstrap({ stored, systemPrefersDark: true });
    expect(root.dataset.theme).toBe("light");
  });

  it("honors an explicit dark document regardless of the OS", () => {
    const stored = JSON.stringify({ version: 1, theme: "dark" });
    const root = runBootstrap({ stored, systemPrefersDark: false });
    expect(root.dataset.theme).toBe("dark");
  });

  it("resolves a stored system preference against the OS", () => {
    const stored = JSON.stringify({ version: 1, theme: "system" });
    expect(runBootstrap({ stored, systemPrefersDark: false }).dataset.theme).toBe(
      "light",
    );
    expect(runBootstrap({ stored, systemPrefersDark: true }).dataset.theme).toBe(
      "dark",
    );
  });

  it("falls back to system defaults for damaged JSON", () => {
    const root = runBootstrap({ stored: "{not-json", systemPrefersDark: false });
    expect(root.dataset.theme).toBe("light");
  });

  it("falls back to system defaults for an unsupported version", () => {
    const stored = JSON.stringify({ version: 2, theme: "light" });
    const root = runBootstrap({ stored, systemPrefersDark: true });
    expect(root.dataset.theme).toBe("dark");
  });

  it("falls back to system defaults for a disallowed theme", () => {
    const stored = JSON.stringify({ version: 1, theme: "sepia" });
    const root = runBootstrap({ stored, systemPrefersDark: false });
    expect(root.dataset.theme).toBe("light");
  });

  it("falls back to system defaults when storage throws", () => {
    const root = runBootstrap({ storageThrows: true, systemPrefersDark: true });
    expect(root.dataset.theme).toBe("dark");
  });

  it("falls back to dark when matchMedia throws for system", () => {
    const root = runBootstrap({ matchMediaThrows: true });
    expect(root.dataset.theme).toBe("dark");
  });
});
