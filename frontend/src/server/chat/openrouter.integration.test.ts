import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/server/chat/tools/http", () => ({
  fetchReadOnly: vi.fn(),
  getEndpoint: (path: string) => `GET ${path}`,
  buildUrl: (path: string) => `http://localhost:8000${path}`,
}));

import { fetchReadOnly } from "@/server/chat/tools/http";
import { answerWithOpenRouter } from "@/server/chat/openrouter";

const mockedFetchReadOnly = vi.mocked(fetchReadOnly);

function openRouterJson(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

function sampleTeamProfile(team?: {
  id: number;
  name: string;
  shortcut: string;
}) {
  const resolved = team ?? { id: 11, name: "Argentyna", shortcut: "ARG" };
  return {
    team: {
      id: resolved.id,
      name: resolved.name,
      shortcut: resolved.shortcut,
      sport_id: 1,
    },
    season_id: 100,
    league_id: 1,
    form: [],
    overall_stats: {
      played: 2,
      wins: 2,
      draws: 0,
      losses: 0,
      goals_for: 3,
      goals_conceded: 1,
      points: 6,
    },
    home_stats: {
      played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      goals_for: 2,
      goals_conceded: 0,
      points: 3,
    },
    away_stats: {
      played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      goals_for: 1,
      goals_conceded: 1,
      points: 3,
    },
    recent_matches: [],
    season_matches: [
      {
        match_id: 1,
        game_date: "2024-06-01",
        is_home: true,
        home_goals: 2,
        away_goals: 0,
        total_goals: 2,
        opponent_name: "X",
        opponent_shortcut: "X",
        season_id: 100,
        team_shots_on_target: 5,
        opponent_shots_on_target: 1,
        total_shots_on_target: 6,
        team_shots: 10,
        opponent_shots: 4,
        total_shots: 14,
        team_corners: 3,
        opponent_corners: 2,
        total_corners: 5,
        team_cards: 1,
        opponent_cards: 2,
        total_cards: 3,
        team_offsides: 0,
        opponent_offsides: 0,
        total_offsides: 0,
        team_fouls: 8,
        opponent_fouls: 9,
        total_fouls: 17,
        team_penalty_minutes: 0,
        opponent_penalty_minutes: 0,
        total_penalty_minutes: 0,
        team_penalties: 0,
        opponent_penalties: 0,
        total_penalties: 0,
      },
      {
        match_id: 2,
        game_date: "2024-06-08",
        is_home: false,
        home_goals: 1,
        away_goals: 1,
        total_goals: 2,
        opponent_name: "Y",
        opponent_shortcut: "Y",
        season_id: 100,
        team_shots_on_target: 4,
        opponent_shots_on_target: 3,
        total_shots_on_target: 7,
        team_shots: 9,
        opponent_shots: 7,
        total_shots: 16,
        team_corners: 2,
        opponent_corners: 4,
        total_corners: 6,
        team_cards: 2,
        opponent_cards: 1,
        total_cards: 3,
        team_offsides: 1,
        opponent_offsides: 0,
        total_offsides: 1,
        team_fouls: 10,
        opponent_fouls: 8,
        total_fouls: 18,
        team_penalty_minutes: 0,
        opponent_penalty_minutes: 0,
        total_penalty_minutes: 0,
        team_penalties: 0,
        opponent_penalties: 0,
        total_penalties: 0,
      },
    ],
  };
}

afterEach(() => {
  mockedFetchReadOnly.mockReset();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("answerWithOpenRouter integration (mocked)", () => {
  it("happy path: Argentyna shots_on_target series → ChatAnswer with chart", async () => {
    vi.stubEnv("OPENROUTER_API_KEY", "test-key");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: null,
                tool_calls: [
                  {
                    id: "call_1",
                    type: "function",
                    function: {
                      name: "get_team_stat_series",
                      arguments: JSON.stringify({
                        query: "Argentyna",
                        stat: "shots_on_target",
                        perspective: "team",
                        limit: 2,
                      }),
                    },
                  },
                ],
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: "Dane pobrane, przygotowuję odpowiedź.",
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: JSON.stringify({
                  answerText:
                    "Argentyna miała 5 i 4 strzały celne w ostatnich dwóch meczach.",
                  warnings: [],
                }),
              },
            },
          ],
        }),
      );

    vi.stubGlobal("fetch", fetchMock);

    mockedFetchReadOnly
      .mockResolvedValueOnce({
        teams: [{ id: 11, name: "Argentyna", sport_name: "Football" }],
      })
      .mockResolvedValueOnce(sampleTeamProfile());

    const answer = await answerWithOpenRouter(
      [
        {
          role: "user",
          content:
            "Pokaż ostatnie 2 mecze Argentyny pod kątem strzałów celnych",
        },
      ],
      { sport_id: 1, label: "Piłka nożna" },
    );

    expect(answer.answerText).toMatch(/Argentyna/);
    expect(answer.chart?.type).toBe("bar");
    expect(answer.chart?.points.length).toBeGreaterThan(0);
    expect(answer.dataSources.length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(mockedFetchReadOnly).toHaveBeenCalled();
  });

  it("happy path: league table for Ekstraklasa season", async () => {
    vi.stubEnv("OPENROUTER_API_KEY", "test-key");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: null,
                tool_calls: [
                  {
                    id: "call_table",
                    type: "function",
                    function: {
                      name: "get_league_table",
                      arguments: JSON.stringify({
                        query: "Ekstraklasa",
                        season_years: "2024/2025",
                        scope: "overall",
                      }),
                    },
                  },
                ],
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: "Tabela gotowa.",
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: JSON.stringify({
                  answerText: "Tabela Ekstraklasy 2024/2025.",
                  warnings: [],
                }),
              },
            },
          ],
        }),
      );

    vi.stubGlobal("fetch", fetchMock);

    mockedFetchReadOnly
      .mockResolvedValueOnce({
        leagues: [
          {
            id: 5,
            name: "Ekstraklasa",
            slug: "ekstraklasa",
            sport_id: 1,
            sport_name: "Football",
            country_id: 1,
            country_name: "Poland",
            country_emoji: null,
            active: true,
            last_update: null,
          },
        ],
        total_count: 1,
      })
      .mockResolvedValueOnce({
        id: 5,
        name: "Ekstraklasa",
        slug: "ekstraklasa",
        sport_id: 1,
        sport_name: "Football",
        country_id: 1,
        country_name: "Poland",
        country_emoji: null,
        active: true,
        last_update: null,
        current_season_id: 20,
        tier: 1,
        has_player_stats: true,
        match_count: 100,
        seasons: [{ season_id: 20, years: "2024/2025", match_count: 100 }],
      })
      .mockResolvedValueOnce({
        standings: [
          {
            position: 1,
            team_id: 1,
            team_name: "Legia",
            played: 10,
            wins: 7,
            draws: 2,
            losses: 1,
            goals_for: 20,
            goals_against: 8,
            points: 23,
          },
        ],
        total_count: 1,
        scope: "overall",
      });

    const answer = await answerWithOpenRouter(
      [
        {
          role: "user",
          content: "Pokaż tabelę ligi Ekstraklasa za sezon 2024/2025",
        },
      ],
      { sport_id: 1, label: "Piłka nożna" },
    );

    expect(answer.answerText).toMatch(/Ekstraklas/);
    expect(answer.table?.title).toMatch(/Ekstraklas/i);
    expect(answer.table?.rows.length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("happy path: compare form of two teams via get_matchup_projection", async () => {
    vi.stubEnv("OPENROUTER_API_KEY", "test-key");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: null,
                tool_calls: [
                  {
                    id: "call_matchup",
                    type: "function",
                    function: {
                      name: "get_matchup_projection",
                      arguments: JSON.stringify({
                        team_a_query: "Legia",
                        team_b_query: "Lech",
                        target: "result",
                        limit: 5,
                      }),
                    },
                  },
                ],
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: "Projekcja gotowa.",
              },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        openRouterJson({
          choices: [
            {
              message: {
                role: "assistant",
                content: JSON.stringify({
                  answerText:
                    "Porównanie formy Legii i Lecha na podstawie ostatnich meczów.",
                  warnings: [],
                }),
              },
            },
          ],
        }),
      );

    vi.stubGlobal("fetch", fetchMock);

    mockedFetchReadOnly
      .mockResolvedValueOnce({
        teams: [{ id: 1, name: "Legia Warszawa", sport_name: "Football" }],
      })
      .mockResolvedValueOnce({
        teams: [{ id: 2, name: "Lech Poznań", sport_name: "Football" }],
      })
      .mockResolvedValueOnce(
        sampleTeamProfile({
          id: 1,
          name: "Legia Warszawa",
          shortcut: "LEG",
        }),
      )
      .mockResolvedValueOnce(
        sampleTeamProfile({
          id: 2,
          name: "Lech Poznań",
          shortcut: "LPO",
        }),
      );

    const answer = await answerWithOpenRouter(
      [
        {
          role: "user",
          content: "Porównaj formę dwóch drużyn Legia i Lech w ostatnich 5 meczach",
        },
      ],
      { sport_id: 1, label: "Piłka nożna" },
    );

    expect(answer.answerText).toMatch(/Legi|Lech/i);
    expect(answer.chart?.type).toBe("bar");
    expect(answer.chart?.points.length).toBe(2);
    expect(answer.table?.rows.length).toBeGreaterThan(0);
    expect(answer.dataSources.length).toBeGreaterThan(0);
    expect(answer.warnings.some((w) => /projekcja|statystyczna/i.test(w))).toBe(
      true,
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(mockedFetchReadOnly).toHaveBeenCalledTimes(4);
  });
});
