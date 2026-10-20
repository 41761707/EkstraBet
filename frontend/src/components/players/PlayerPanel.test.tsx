import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  PlayerPanel,
  buildChartLabel,
  playerPlayedAway,
} from "@/components/players/PlayerPanel";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import { FOOTBALL_SPORT_ID } from "@/types/api";

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

describe("buildChartLabel", () => {
  it("glues @ to the opponent when that club hosted the match", () => {
    expect(
      buildChartLabel(
        {
          opponent_name: "Vegas Golden Knights",
          opponent_shortcut: "VGK",
          home_team: "Vegas Golden Knights",
          match_date: "03.10",
        },
        "shortcut",
      ),
    ).toBe("@VGK 03.10");
  });

  it("leaves a home-game opponent unmarked", () => {
    expect(
      buildChartLabel(
        {
          opponent_name: "Florida Panthers",
          opponent_shortcut: "FLA",
          home_team: "Anaheim Ducks",
          match_date: "05.10",
        },
        "shortcut",
      ),
    ).toBe("FLA 05.10");
  });
});

describe("playerPlayedAway", () => {
  it("marks the opponent when that club hosted the match", () => {
    expect(
      playerPlayedAway({
        opponent_name: "Los Angeles Kings",
        home_team: "Los Angeles Kings",
      }),
    ).toBe(true);
  });

  it("leaves the opponent unmarked when the player's club was home", () => {
    expect(
      playerPlayedAway({
        opponent_name: "Toronto Maple Leafs",
        home_team: "San Jose Sharks",
      }),
    ).toBe(false);
  });

  it("does not mark a match with an empty opponent name", () => {
    expect(
      playerPlayedAway({
        opponent_name: "",
        home_team: "",
      }),
    ).toBe(false);
  });
});
