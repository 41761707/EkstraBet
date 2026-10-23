import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PlayerGameLogTable } from "@/components/players/PlayerGameLogTable";
import {
  PlayerPanel,
  PlayersStatConfig,
  buildChartLabel,
  averageStoredRating,
  playerChartPoints,
  playerPlayedAway,
} from "@/components/players/PlayerPanel";
import { getConfigurablePlayerStats } from "@/components/players/playerStatsConfig";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/types/api";
import type { HockeyPlayerMatchStat } from "@/types/api";

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

  it("offers Ocena and skips a match that has no stored rating", () => {
    const html = renderToStaticMarkup(
      <PlayersStatConfig
        stats={getConfigurablePlayerStats(HOCKEY_SPORT_ID)}
        selectedStats={["rating"]}
        thresholdLines={{}}
        onSelectedStatsChange={() => undefined}
        onThresholdLineChange={() => undefined}
      />,
    );
    const rated = hockeyMatch(1, -1.4);
    const missing = hockeyMatch(2, null);
    const points = playerChartPoints(
      [missing, rated],
      "rating",
      "full",
    );

    expect(html).toContain("Ocena");
    expect(points).toHaveLength(1);
    expect(points[0]?.value).toBe(-1.4);
    expect(averageStoredRating([missing, rated])).toBe(-1.4);
    expect(averageStoredRating([missing])).toBeNull();

    const log = renderToStaticMarkup(
      <PlayerGameLogTable
        sportId={HOCKEY_SPORT_ID}
        playerRole="skater"
        matches={[missing, rated]}
        selectedStats={["rating"]}
      />,
    );
    expect(log).toContain("—");
    expect(log).toContain("\u22121.4");
    expect(log).not.toContain(">0<");
  });
});

function hockeyMatch(
  matchId: number,
  rating: number | null,
): HockeyPlayerMatchStat {
  return {
    match_id: matchId,
    home_team: "Los Angeles Kings",
    away_team: "Ottawa Senators",
    match_date: "02.01",
    opponent_shortcut: "OTT",
    opponent_name: "Ottawa Senators",
    toi: "18:00",
    toi_minutes: 18,
    points: 1,
    goals: 0,
    assists: 1,
    plus_minus: 1,
    penalty_minutes: 0,
    sog: 2,
    shots_against: null,
    shots_saved: null,
    saves_acc: null,
    rating,
  };
}
