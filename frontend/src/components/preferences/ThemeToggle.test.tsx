import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  ThemeToggle,
  themeToggleLabel,
} from "@/components/preferences/ThemeToggle";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";

function silentStorage(): PreferencesStorage {
  return {
    load: () => ({ ...DEFAULT_PREFERENCES }),
    save: () => undefined,
  };
}

function silentApi(): PreferencesApi {
  return {
    get: async () => ({ status: "no-session" }),
    put: async (preferences) => preferences,
  };
}

describe("themeToggleLabel", () => {
  it("uses a generic label before mount to avoid hydration mismatch", () => {
    expect(themeToggleLabel(false, "dark")).toBe("Przełącz motyw");
    expect(themeToggleLabel(false, "light")).toBe("Przełącz motyw");
  });

  it("describes the action after mount", () => {
    expect(themeToggleLabel(true, "dark")).toBe("Przełącz na jasny motyw");
    expect(themeToggleLabel(true, "light")).toBe("Przełącz na ciemny motyw");
  });
});

describe("ThemeToggle", () => {
  it("throws outside PreferencesProvider", () => {
    expect(() => renderToStaticMarkup(<ThemeToggle />)).toThrow(
      "usePreferences must be used within PreferencesProvider",
    );
  });

  it("renders a button with a generic label before mount", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <ThemeToggle />
      </PreferencesProvider>,
    );

    expect(html).toContain("Przełącz motyw");
    expect(html).toContain('type="button"');
    expect(html).not.toContain("Przełącz na jasny motyw");
    expect(html).not.toContain("Przełącz na ciemny motyw");
  });
});
