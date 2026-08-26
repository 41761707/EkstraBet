import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PlayerPanel } from "@/components/players/PlayerPanel";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import { FOOTBALL_SPORT_ID } from "@/lib/playerFilterParams";
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

const panelProps = {
  sportId: FOOTBALL_SPORT_ID,
  playerId: 12,
  playerName: "Robert Lewandowski",
  playerPosition: "F",
  seasonId: 2024,
  matchLimit: 10,
  selectedStats: ["goals"] as const,
  thresholdLines: {},
};

describe("PlayerPanel", () => {
  it("throws outside PreferencesProvider", () => {
    expect(() =>
      renderToStaticMarkup(
        <PlayerPanel
          sportId={panelProps.sportId}
          playerId={panelProps.playerId}
          playerName={panelProps.playerName}
          playerPosition={panelProps.playerPosition}
          seasonId={panelProps.seasonId}
          matchLimit={panelProps.matchLimit}
          selectedStats={[...panelProps.selectedStats]}
          thresholdLines={panelProps.thresholdLines}
        />,
      ),
    ).toThrow("usePreferences must be used within PreferencesProvider");
  });

  it("renders the player name inside PreferencesProvider", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <PlayerPanel
          sportId={panelProps.sportId}
          playerId={panelProps.playerId}
          playerName={panelProps.playerName}
          playerPosition={panelProps.playerPosition}
          seasonId={panelProps.seasonId}
          matchLimit={panelProps.matchLimit}
          selectedStats={[...panelProps.selectedStats]}
          thresholdLines={panelProps.thresholdLines}
        />
      </PreferencesProvider>,
    );

    expect(html).toContain("Robert Lewandowski");
  });
});
