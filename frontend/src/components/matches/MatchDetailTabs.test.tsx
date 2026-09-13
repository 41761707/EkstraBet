import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MatchDetailTabs } from "@/components/matches/MatchDetailTabs";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type HeadToHeadSummary,
  type MatchDetails,
} from "@/types/api";

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

function emptyHeadToHead(): HeadToHeadSummary {
  return {
    team_id: 1,
    opponent_id: 2,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_conceded: 0,
    btts_count: 0,
    btts_percentage: 0,
    avg_goals_per_match: 0,
    meetings: [],
  };
}

function minimalMatchDetails(sportId: number): MatchDetails {
  return {
    id: 116122,
    league_id: 45,
    season_id: 10,
    sport_id: sportId,
    round: 1,
    round_label: "1",
    game_date: "2026-01-29T01:30:00",
    home_team: { id: 1, name: "Columbus Blue Jackets", shortcut: "CBJ" },
    away_team: { id: 2, name: "Philadelphia Flyers", shortcut: "PHI" },
    home_goals: null,
    away_goals: null,
    result: "0",
    is_played: false,
    score_resolution: null,
    final_predictions: [],
    prediction_analysis: null,
    odds: [],
    stats: null,
    hockey_stats: null,
    has_player_stats: false,
    head_to_head: emptyHeadToHead(),
    home_team_history: [],
    away_team_history: [],
    boxscore: null,
    hockey_boxscore: null,
    hockey_lineups: null,
    model_assessments: [],
  };
}

function renderTabs(sportId: number): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <MatchDetailTabs match={minimalMatchDetails(sportId)} />
    </PreferencesProvider>,
  );
}

describe("MatchDetailTabs", () => {
  it("shows the Składy tab for hockey matches", () => {
    const html = renderTabs(HOCKEY_SPORT_ID);

    expect(html).toContain("Składy");
  });

  it("hides the Składy tab for football matches", () => {
    const html = renderTabs(FOOTBALL_SPORT_ID);

    expect(html).not.toContain("Składy");
  });
});
