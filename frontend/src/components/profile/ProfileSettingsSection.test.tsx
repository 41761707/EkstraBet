import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  COLOR_SCHEME_DESCRIPTION,
  COLOR_SCHEME_LABEL,
  PROFILE_SETTINGS_DESCRIPTION,
  PROFILE_SETTINGS_TITLE,
  ProfileSettingsSection,
} from "@/components/profile/ProfileSettingsSection";
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

function renderSettingsSection(): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <ProfileSettingsSection />
    </PreferencesProvider>,
  );
}

describe("ProfileSettingsSection", () => {
  it("renders the settings card with a color-scheme row and theme toggle", () => {
    const html = renderSettingsSection();

    expect(html).toContain(PROFILE_SETTINGS_TITLE);
    expect(html).toContain(PROFILE_SETTINGS_DESCRIPTION);
    expect(html).toContain(COLOR_SCHEME_LABEL);
    expect(html).toContain(COLOR_SCHEME_DESCRIPTION);
    expect(html).toContain("Przełącz motyw");
    expect(html).toContain('type="button"');
  });

  it("does not offer a third system option or favorite-leagues content", () => {
    const html = renderSettingsSection();

    expect(html).not.toContain("system");
    expect(html).not.toContain("Ulubione ligi");
  });
});
