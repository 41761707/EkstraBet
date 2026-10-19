import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyTeamPrematchPanel } from "@/components/matches/HockeyTeamPrematchPanel";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import type { HockeyScheduleSide } from "@/types/api";

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

function renderPanel(schedule: HockeyScheduleSide | null): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <HockeyTeamPrematchPanel
        teamName="Columbus Blue Jackets"
        history={[]}
        lookback={5}
        ouLine={5.5}
        schedule={schedule}
      />
    </PreferencesProvider>,
  );
}

describe("HockeyTeamPrematchPanel schedule context", () => {
  it("shows rest, back-to-back and games in seven days", () => {
    const html = renderPanel({
      rest_days: 1,
      is_b2b: true,
      games_last_7_days: 3,
    });

    expect(html).toContain("Dni odpoczynku");
    expect(html).toContain("1 dzień");
    expect(html).toContain("Back-to-back");
    expect(html).toContain(">Tak<");
    expect(html).toContain("Mecze w ostatnich 7 dniach");
    expect(html).toContain(">2<");
    expect(html).not.toContain(">3<");
  });

  it("treats zero rest without a back-to-back as no previous game", () => {
    const html = renderPanel({
      rest_days: 0,
      is_b2b: false,
      games_last_7_days: 1,
    });

    expect(html).toContain("brak poprzedniego meczu");
    expect(html).toContain(">Nie<");
    expect(html).toContain(">0<");
  });

  it("omits the schedule card when context is missing", () => {
    const html = renderPanel(null);

    expect(html).not.toContain("Back-to-back");
    expect(html).toContain("Brak historii meczów");
  });
});
