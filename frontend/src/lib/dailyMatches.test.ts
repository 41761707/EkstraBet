import { describe, expect, it } from "vitest";

import { groupDailyMatches } from "@/lib/dailyMatches";
import type { DailyMatchSummary } from "@/types/api";

function dailyMatch(
  overrides: Partial<DailyMatchSummary> &
    Pick<
      DailyMatchSummary,
      "id" | "league_id" | "league_name" | "sport_id" | "sport_name" | "game_date"
    >,
): DailyMatchSummary {
  return {
    season_id: 1,
    round: 1,
    round_label: "1",
    home_team: { id: 1, name: "Home", shortcut: "HOM" },
    away_team: { id: 2, name: "Away", shortcut: "AWY" },
    home_goals: null,
    away_goals: null,
    result: "X",
    is_played: false,
    score_resolution: null,
    ...overrides,
  };
}

describe("groupDailyMatches", () => {
  it("returns an empty list for empty input", () => {
    expect(groupDailyMatches([])).toEqual([]);
  });

  it("groups by sport then league and sorts chronologically", () => {
    const matches = [
      dailyMatch({
        id: 3,
        league_id: 20,
        league_name: "NBA",
        sport_id: 3,
        sport_name: "Koszykówka",
        game_date: "2026-07-26T20:00:00",
      }),
      dailyMatch({
        id: 1,
        league_id: 10,
        league_name: "Ekstraklasa",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T18:00:00",
      }),
      dailyMatch({
        id: 4,
        league_id: 11,
        league_name: "La Liga",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T16:00:00",
      }),
      dailyMatch({
        id: 2,
        league_id: 10,
        league_name: "Ekstraklasa",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T15:00:00",
      }),
      dailyMatch({
        id: 5,
        league_id: 30,
        league_name: "NHL",
        sport_id: 2,
        sport_name: "Hokej",
        game_date: "2026-07-26T19:00:00",
      }),
    ];

    const groups = groupDailyMatches(matches);

    expect(groups.map((group) => group.sportName)).toEqual([
      "Hokej",
      "Koszykówka",
      "Piłka nożna",
    ]);
    expect(groups[2]?.leagues.map((league) => league.leagueName)).toEqual([
      "Ekstraklasa",
      "La Liga",
    ]);
    expect(
      groups[2]?.leagues[0]?.matches.map((match) => match.id),
    ).toEqual([2, 1]);
    expect(groups[0]?.leagues[0]?.matches[0]?.id).toBe(5);
    expect(groups[1]?.leagues[0]?.matches[0]?.id).toBe(3);
  });

  it("sorts Polish league names with locale pl", () => {
    const matches = [
      dailyMatch({
        id: 2,
        league_id: 2,
        league_name: "Łódzka",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T16:00:00",
      }),
      dailyMatch({
        id: 1,
        league_id: 1,
        league_name: "Ligowa",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T15:00:00",
      }),
    ];

    const leagues = groupDailyMatches(matches)[0]?.leagues ?? [];
    expect(leagues.map((league) => league.leagueName)).toEqual([
      "Ligowa",
      "Łódzka",
    ]);
  });

  it("does not mutate the input array or match order", () => {
    const matches = [
      dailyMatch({
        id: 2,
        league_id: 10,
        league_name: "Ekstraklasa",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T18:00:00",
      }),
      dailyMatch({
        id: 1,
        league_id: 10,
        league_name: "Ekstraklasa",
        sport_id: 1,
        sport_name: "Piłka nożna",
        game_date: "2026-07-26T15:00:00",
      }),
    ];
    const snapshot = matches.map((match) => match.id);

    groupDailyMatches(matches);

    expect(matches.map((match) => match.id)).toEqual(snapshot);
  });
});
