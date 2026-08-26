import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  TEAM_NAME_DISPLAY_LABEL,
  TEAM_NAME_DISPLAY_OPTION_LABELS,
  TeamNameDisplayControl,
} from "@/components/preferences/TeamNameDisplayControl";
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
    put: async () => ({ ...DEFAULT_PREFERENCES }),
  };
}

function renderControl(): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <TeamNameDisplayControl />
    </PreferencesProvider>,
  );
}

function radioInput(html: string, value: string): string {
  return html.match(new RegExp(`<input[^>]*value="${value}"[^>]*>`))?.[0] ?? "";
}

describe("TeamNameDisplayControl", () => {
  it("throws outside PreferencesProvider", () => {
    expect(() => renderToStaticMarkup(<TeamNameDisplayControl />)).toThrow(
      "usePreferences must be used within PreferencesProvider",
    );
  });

  it("renders a labelled radio group with both Polish options", () => {
    const html = renderControl();

    expect(html).toContain(TEAM_NAME_DISPLAY_LABEL);
    expect(html).toContain(TEAM_NAME_DISPLAY_OPTION_LABELS.full);
    expect(html).toContain(TEAM_NAME_DISPLAY_OPTION_LABELS.shortcut);
    expect(html).toContain('type="radio"');
  });

  it("checks the full option on first paint and leaves shortcut unchecked", () => {
    // SSR używa domyślnego dokumentu (full), więc first-paint nie rozjeżdża się
    // z hydracją — analogicznie do ThemeToggle i jego etykiety przed mountem
    const html = renderControl();

    expect(radioInput(html, "full")).toContain("checked");
    expect(radioInput(html, "shortcut")).not.toContain("checked");
  });

  it("groups both radios under one name for arrow-key navigation", () => {
    const html = renderControl();
    const full = radioInput(html, "full");
    const shortcut = radioInput(html, "shortcut");

    const fullName = full.match(/name="([^"]+)"/)?.[1];
    const shortcutName = shortcut.match(/name="([^"]+)"/)?.[1];

    expect(fullName).toBeTruthy();
    expect(fullName).toBe(shortcutName);
  });

  it("does not render color-scheme content", () => {
    // kontrolka nazw nie dotyka pola theme
    expect(renderControl()).not.toContain("Schemat kolorów");
  });
});
