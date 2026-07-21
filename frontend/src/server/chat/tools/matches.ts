import type { ChatTableSpec, MatchDetails } from "@/types/api";

import { numberArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import type { ToolResult } from "./types";

function formatMatchScore(details: MatchDetails): string {
  if (details.home_goals != null && details.away_goals != null) {
    return `${details.home_goals}:${details.away_goals}`;
  }
  return details.result || "brak wyniku";
}

function buildMatchDetailsTable(details: MatchDetails): ChatTableSpec {
  const score = formatMatchScore(details);
  const date = String(details.game_date).slice(0, 10);
  return {
    title: `${details.home_team.name} vs ${details.away_team.name}`,
    columns: ["Pole", "Wartość"],
    rows: [
      ["Data", date],
      ["Wynik", score],
      ["Status", details.is_played ? "Rozegrany" : "Nierozgrany"],
      ["Runda", details.round_label ?? details.round ?? "-"],
      ["Liga (id)", details.league_id],
      ["Sezon (id)", details.season_id],
      ["Predykcje", details.final_predictions?.length ?? 0],
      ["Kursy", details.odds?.length ?? 0],
      ["Oceny modeli", details.model_assessments?.length ?? 0],
      [
        "H2H (rozegrane)",
        details.head_to_head?.played ?? 0,
      ],
      [
        "Historia gospodarzy",
        details.home_team_history?.length ?? 0,
      ],
      ["Historia gości", details.away_team_history?.length ?? 0],
    ],
  };
}

/** Skraca odpowiedź API — bez pełnych tablic kursów/predykcji/historii. */
function summarizeMatchDetails(details: MatchDetails) {
  const h2h = details.head_to_head;
  return {
    id: details.id,
    league_id: details.league_id,
    season_id: details.season_id,
    sport_id: details.sport_id,
    round: details.round,
    round_label: details.round_label,
    game_date: details.game_date,
    home_team: details.home_team,
    away_team: details.away_team,
    home_goals: details.home_goals,
    away_goals: details.away_goals,
    result: details.result,
    is_played: details.is_played,
    score_resolution: details.score_resolution,
    stats: details.stats,
    hockey_stats: details.hockey_stats,
    has_player_stats: details.has_player_stats,
    head_to_head: h2h
      ? {
          played: h2h.played,
          wins: h2h.wins,
          draws: h2h.draws,
          losses: h2h.losses,
          goals_for: h2h.goals_for,
          goals_conceded: h2h.goals_conceded,
          btts_percentage: h2h.btts_percentage,
          avg_goals_per_match: h2h.avg_goals_per_match,
          meetings_count: h2h.meetings?.length ?? 0,
        }
      : null,
    odds_count: details.odds?.length ?? 0,
    predictions_count: details.final_predictions?.length ?? 0,
    model_assessments_count: details.model_assessments?.length ?? 0,
    home_history_count: details.home_team_history?.length ?? 0,
    away_history_count: details.away_team_history?.length ?? 0,
    has_boxscore: Boolean(details.boxscore?.length),
    has_hockey_boxscore: Boolean(details.hockey_boxscore),
  };
}

export async function getMatchDetails(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const matchId = numberArg(args, "match_id", { required: true, min: 1 })!;
  const details = await fetchReadOnly<MatchDetails>(
    `/matches/${matchId}/details`,
  );
  const score = formatMatchScore(details);
  const date = String(details.game_date).slice(0, 10);

  return {
    name: "get_match_details",
    summary: `${details.home_team.name} vs ${details.away_team.name}: ${score} (${date}).`,
    data: summarizeMatchDetails(details),
    table: buildMatchDetailsTable(details),
    dataSources: [
      {
        label: "Szczegóły meczu",
        endpoint: getEndpoint(`/matches/${matchId}/details`),
        params: { match_id: matchId },
      },
    ],
    warnings: [],
  };
}
