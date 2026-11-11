import { afterEach, describe, expect, it, vi } from "vitest";

import { loadPlayerProfilePage } from "@/app/players/[playerId]/loadPlayerProfilePage";
import {
  getPlayerProfile,
  getPlayerSeasons,
  getPlayerTeams,
} from "@/lib/api";
import type { PlayerProfileQuery } from "@/lib/playerProfileParams";
import { ApiError } from "@/lib/apiShared";
import { HOCKEY_SPORT_ID, type PlayerProfileResponse } from "@/types/api";

vi.mock("@/lib/api", () => ({
  getPlayerProfile: vi.fn(),
  getPlayerSeasons: vi.fn(),
  getPlayerTeams: vi.fn(),
}));

const getPlayerProfileMock = vi.mocked(getPlayerProfile);
const getPlayerSeasonsMock = vi.mocked(getPlayerSeasons);
const getPlayerTeamsMock = vi.mocked(getPlayerTeams);

const QUERY: PlayerProfileQuery = {
  seasonId: 7,
  opponentTeamId: null,
  ownTeamId: null,
  teammateId: null,
};

function sampleProfile(): PlayerProfileResponse {
  return {
    player_id: 15,
    player_name: "Leon Draisaitl",
    sport_id: HOCKEY_SPORT_ID,
    filters: {
      player_id: 15,
      season_id: 7,
      opponent_team_id: null,
      own_team_id: null,
      teammate_id: null,
    },
    match_count: 2,
    truncated: false,
    body: {
      sport_id: HOCKEY_SPORT_ID,
      player_role: "skater",
      summary: {
        is_goalie: false,
        points: 3,
        goals: 1,
        assists: 2,
        plus_minus: 1,
        penalty_minutes: 0,
        average_penalty_minutes: 0,
        average_sog: 2,
        average_toi: "18:00",
        shots_against: null,
        shots_saved: null,
        saves_acc: null,
      },
      event_split: {
        goals: 1,
        power_play_goals: 0,
        empty_net_goals: 0,
        goals_period_1: 1,
        goals_period_2: 0,
        goals_period_3: 0,
        goals_overtime: 0,
        shootout_goals: 0,
        minor_penalties: 0,
        major_penalties: 0,
        misconduct_penalties: 0,
        unsportsmanlike_penalties: 0,
        disallowed_goals: 0,
      },
      matches: [],
    },
  };
}

describe("loadPlayerProfilePage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns notFound for an unknown player and does not load dictionaries", async () => {
    getPlayerProfileMock.mockRejectedValue(new ApiError(404, "Player not found"));

    await expect(loadPlayerProfilePage(15, QUERY)).resolves.toEqual({
      kind: "notFound",
    });
    expect(getPlayerProfileMock).toHaveBeenCalledWith(15, QUERY);
    expect(getPlayerSeasonsMock).not.toHaveBeenCalled();
    expect(getPlayerTeamsMock).not.toHaveBeenCalled();
  });

  it("returns notFound when the sport has no profile source", async () => {
    getPlayerProfileMock.mockRejectedValue(
      new ApiError(404, "Player profile is not available for this sport"),
    );

    await expect(loadPlayerProfilePage(15, QUERY)).resolves.toEqual({
      kind: "notFound",
    });
    expect(getPlayerSeasonsMock).not.toHaveBeenCalled();
  });

  it("returns sliceError for a profile failure other than 404", async () => {
    getPlayerProfileMock.mockRejectedValue(new ApiError(422, "Unknown season"));

    await expect(loadPlayerProfilePage(15, QUERY)).resolves.toEqual({
      kind: "error",
      sliceError: "Unknown season",
    });
    expect(getPlayerSeasonsMock).not.toHaveBeenCalled();
  });

  it("loads seasons and teams with the sport id from the profile", async () => {
    const profile = sampleProfile();
    const seasons = [{ season_id: 7, years: "2025/26" }];
    const teams = [{ id: 9, name: "Edmonton Oilers", country_id: null }];
    getPlayerProfileMock.mockResolvedValue(profile);
    getPlayerSeasonsMock.mockResolvedValue({ seasons, total_count: 1 });
    getPlayerTeamsMock.mockResolvedValue({ teams, total_count: 1 });

    await expect(loadPlayerProfilePage(15, QUERY)).resolves.toEqual({
      kind: "ready",
      profile,
      seasons,
      teams,
      dictionariesError: null,
    });
    expect(getPlayerProfileMock).toHaveBeenCalledWith(15, QUERY);
    expect(getPlayerSeasonsMock).toHaveBeenCalledWith(profile.sport_id);
    expect(getPlayerTeamsMock).toHaveBeenCalledWith(profile.sport_id);
  });

  it("keeps the profile when a dictionary fails", async () => {
    const profile = sampleProfile();
    getPlayerProfileMock.mockResolvedValue(profile);
    getPlayerSeasonsMock.mockRejectedValue(new ApiError(500, "Błąd sezonów"));
    getPlayerTeamsMock.mockResolvedValue({
      teams: [{ id: 9, name: "Edmonton Oilers", country_id: null }],
      total_count: 1,
    });

    await expect(loadPlayerProfilePage(15, QUERY)).resolves.toEqual({
      kind: "ready",
      profile,
      seasons: [],
      teams: [{ id: 9, name: "Edmonton Oilers", country_id: null }],
      dictionariesError: "Błąd sezonów",
    });
  });
});
