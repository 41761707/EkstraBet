import type {
  ChatTableSpec,
  MatchDetails,
  MatchPredictionItem,
  MatchSearchResponse,
  MatchSummary,
  OddsItem,
  PredictionPreviewResponse,
} from "@/types/api";

import { booleanArg, numberArg, stringArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import type { ToolResult } from "./types";

// Limit poniżej 25 z planu: dataPreview ma 4k znaków; top-N musi się zmieścić w LLM.
const MATCH_DETAILS_PREDICTIONS_LIMIT = 12;
const MATCH_DETAILS_ODDS_LIMIT = 12;

interface SummarizedMatchPrediction {
  event_name: string;
  model_name: string | null;
  value: number | null;
  event_family: string | null;
}

interface SummarizedMatchOdds {
  event_name: string;
  bookmaker_name: string;
  odds: number;
}

function formatMatchScore(details: MatchDetails): string {
  if (details.home_goals != null && details.away_goals != null) {
    return `${details.home_goals}:${details.away_goals}`;
  }
  return details.result || "brak wyniku";
}

function formatProbabilityPct(value: number | null): string {
  if (value == null) {
    return "—";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function pickTopPrediction(
  predictions: MatchPredictionItem[],
): MatchPredictionItem | null {
  if (predictions.length === 0) {
    return null;
  }
  return [...predictions].sort(
    (left, right) => (right.value ?? -Infinity) - (left.value ?? -Infinity),
  )[0]!;
}

function formatTopPredictionLabel(
  prediction: MatchPredictionItem | null,
): string {
  if (!prediction) {
    return "-";
  }
  const model = prediction.model_name ?? `model ${prediction.model_id}`;
  return `${prediction.event_name} (${formatProbabilityPct(prediction.value)}, ${model})`;
}

function summarizePredictions(
  predictions: MatchPredictionItem[],
): {
  items: SummarizedMatchPrediction[];
  truncated: boolean;
  total: number;
} {
  const total = predictions.length;
  // Najwyższe prawdopodobieństwa pierwsze — przy obcięciu model widzi top-N.
  const items = [...predictions]
    .sort(
      (left, right) => (right.value ?? -Infinity) - (left.value ?? -Infinity),
    )
    .slice(0, MATCH_DETAILS_PREDICTIONS_LIMIT)
    .map((prediction) => ({
      event_name: prediction.event_name,
      model_name: prediction.model_name,
      value: prediction.value,
      event_family: prediction.event_family?.name ?? null,
    }));
  return {
    items,
    truncated: total > MATCH_DETAILS_PREDICTIONS_LIMIT,
    total,
  };
}

function summarizeOdds(odds: OddsItem[]): {
  items: SummarizedMatchOdds[];
  truncated: boolean;
  total: number;
} {
  const total = odds.length;
  // Grupuj po evencie, w grupie najwyższy kurs; potem top-N po kursie.
  const sorted = [...odds].sort((left, right) => {
    const byEvent = left.event_name.localeCompare(right.event_name, "pl");
    if (byEvent !== 0) {
      return byEvent;
    }
    return right.odds - left.odds;
  });
  const items = sorted.slice(0, MATCH_DETAILS_ODDS_LIMIT).map((row) => ({
    event_name: row.event_name,
    bookmaker_name: row.bookmaker_name,
    odds: row.odds,
  }));
  return {
    items,
    truncated: total > MATCH_DETAILS_ODDS_LIMIT,
    total,
  };
}

function buildMatchDetailsTable(
  details: MatchDetails,
  topPrediction: MatchPredictionItem | null,
): ChatTableSpec {
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
      ["Top predykcja", formatTopPredictionLabel(topPrediction)],
      ["Predykcje", details.final_predictions?.length ?? 0],
      ["Kursy", details.odds?.length ?? 0],
      ["Oceny modeli", details.model_assessments?.length ?? 0],
      ["H2H (rozegrane)", details.head_to_head?.played ?? 0],
      ["Historia gospodarzy", details.home_team_history?.length ?? 0],
      ["Historia gości", details.away_team_history?.length ?? 0],
    ],
  };
}

/** Skraca odpowiedź API — zachowuje skrót rynków, bez pełnej historii. */
function summarizeMatchDetails(details: MatchDetails) {
  const h2h = details.head_to_head;
  const predictions = summarizePredictions(details.final_predictions ?? []);
  const odds = summarizeOdds(details.odds ?? []);
  const predictionAnalysis: PredictionPreviewResponse | null =
    details.prediction_analysis ?? null;

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
    prediction_analysis: predictionAnalysis,
    final_predictions: predictions.items,
    odds: odds.items,
    predictions_count: predictions.total,
    odds_count: odds.total,
    predictions_truncated: predictions.truncated,
    odds_truncated: odds.truncated,
    model_assessments_count: details.model_assessments?.length ?? 0,
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
  const summarized = summarizeMatchDetails(details);
  const topPrediction = pickTopPrediction(details.final_predictions ?? []);
  const topLabel = formatTopPredictionLabel(topPrediction);
  const summaryBase = `${details.home_team.name} vs ${details.away_team.name}: ${score} (${date}).`;
  const summary =
    topPrediction != null
      ? `${summaryBase} Top predykcja: ${topLabel}.`
      : summaryBase;

  return {
    name: "get_match_details",
    summary,
    data: summarized,
    // Jeden slot table: szczegóły z Top predykcją; pełniejsza lista w data.
    table: buildMatchDetailsTable(details, topPrediction),
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

/**
 * Search fixtures by one or two team names (upcoming by default).
 */
export async function searchMatches(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const teamAQuery = stringArg(args, "team_a_query", {
    required: true,
    maxLength: 80,
  })!;
  const teamBQuery = stringArg(args, "team_b_query", { maxLength: 80 });
  const fromNow = booleanArg(args, "from_now") ?? true;
  const played = booleanArg(args, "played");
  const dateFrom = stringArg(args, "date_from", { maxLength: 10 });
  const dateTo = stringArg(args, "date_to", { maxLength: 10 });
  const pageSize = numberArg(args, "page_size", { min: 1, max: 20 }) ?? 10;
  const sportId = numberArg(args, "sport_id", { min: 1 });

  const params = {
    team_a_query: teamAQuery,
    team_b_query: teamBQuery,
    sport_id: sportId,
    from_now: fromNow,
    played,
    date_from: dateFrom,
    date_to: dateTo,
    page_size: pageSize,
  };

  const response = await fetchReadOnly<MatchSearchResponse>(
    "/matches/search",
    params,
  );
  const warnings = [...(response.filters_applied?.warnings ?? [])];
  const matches = response.matches;

  return {
    name: "search_matches",
    summary:
      matches.length === 0
        ? `Brak meczów dla zapytania "${teamAQuery}"${teamBQuery ? ` / "${teamBQuery}"` : ""}.`
        : `Znaleziono ${matches.length} mecz(ów) dla "${teamAQuery}"${teamBQuery ? ` / "${teamBQuery}"` : ""}.`,
    data: {
      matches,
      total_count: response.total_count,
      filters_applied: response.filters_applied,
    },
    table: buildSearchMatchesTable(matches),
    dataSources: [
      {
        label: "Wyszukiwanie meczów",
        endpoint: getEndpoint("/matches/search"),
        params: {
          team_a_query: teamAQuery,
          team_b_query: teamBQuery ?? null,
          sport_id: sportId ?? null,
          from_now: fromNow,
          played: played ?? null,
          date_from: dateFrom ?? null,
          date_to: dateTo ?? null,
          page_size: pageSize,
        },
      },
    ],
    warnings,
  };
}

function buildSearchMatchesTable(matches: MatchSummary[]): ChatTableSpec {
  return {
    title: "Znalezione mecze",
    columns: ["Data", "Gospodarz", "Gość", "Status", "match_id"],
    rows: matches.map((match) => [
      String(match.game_date).slice(0, 10),
      match.home_team.name,
      match.away_team.name,
      match.is_played ? "Rozegrany" : "Nierozgrany",
      match.id,
    ]),
  };
}
