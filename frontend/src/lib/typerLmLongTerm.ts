/** Presentation helpers for Typer LM long-term markets. */

import { ApiError } from "@/lib/apiShared";
import { hasWarsawNaiveDateTimePassed } from "@/lib/date";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import type {
  LongTermAutoResultResponse,
  LongTermDashboardResponse,
  LongTermMarketCard,
  LongTermPickChange,
  LongTermStandingTeam,
  LongTermTeam,
  SaveLongTermPicksResponse,
  SettleLongTermResponse,
} from "@/types/api";

export const LONG_TERM_SHORT_HISTORY_LIMIT = 3;

export type LongTermPickStatus = "hit" | "miss" | "pending";

export function formatLongTermSelectionCounter(
  selectedCount: number,
  selectionSize: number,
): string {
  return `${selectedCount}/${selectionSize}`;
}

export function formatLongTermTeamName(
  team: Pick<LongTermTeam, "team_name" | "team_shortcut">,
  teamNameDisplay: TeamNameDisplayPreference,
): string {
  return formatTeamName(team.team_name, team.team_shortcut, teamNameDisplay);
}

export function filterLongTermCandidates(
  candidates: readonly LongTermTeam[],
  query: string,
  teamNameDisplay: TeamNameDisplayPreference,
): LongTermTeam[] {
  const needle = query.trim().toLocaleLowerCase("pl");
  if (needle === "") {
    return [...candidates];
  }
  return candidates.filter((team) => {
    const label = formatLongTermTeamName(team, teamNameDisplay);
    const haystacks = [label, team.team_name, team.team_shortcut];
    return haystacks.some((value) =>
      value.toLocaleLowerCase("pl").includes(needle),
    );
  });
}

export function sortedTeamIds(teamIds: readonly number[]): number[] {
  return [...teamIds].sort((left, right) => left - right);
}

export function areTeamIdSetsEqual(
  left: readonly number[],
  right: readonly number[],
): boolean {
  const leftSorted = sortedTeamIds(left);
  const rightSorted = sortedTeamIds(right);
  if (leftSorted.length !== rightSorted.length) {
    return false;
  }
  return leftSorted.every((id, index) => id === rightSorted[index]);
}

export function toggleLongTermTeamId(
  selectedIds: readonly number[],
  teamId: number,
  selectionSize: number,
): number[] {
  if (selectedIds.includes(teamId)) {
    return selectedIds.filter((id) => id !== teamId);
  }
  if (selectedIds.length >= selectionSize) {
    return [...selectedIds];
  }
  return [...selectedIds, teamId];
}

export function isLongTermMarketLockedForUi(
  market: Pick<LongTermMarketCard, "is_locked" | "deadline_at">,
  nowMs?: number | null,
): boolean {
  if (market.is_locked) {
    return true;
  }
  if (nowMs == null || market.deadline_at == null) {
    return false;
  }
  return hasWarsawNaiveDateTimePassed(market.deadline_at, new Date(nowMs));
}

export function canSaveLongTermPicks(
  market: LongTermMarketCard,
  selectedIds: readonly number[],
  isPending: boolean,
  nowMs?: number | null,
): boolean {
  if (isLongTermMarketLockedForUi(market, nowMs) || isPending) {
    return false;
  }
  if (selectedIds.length !== market.selection_size) {
    return false;
  }
  return !areTeamIdSetsEqual(selectedIds, market.picked_team_ids);
}

export function classifyLongTermPick(
  teamId: number,
  resultTeamIds: readonly number[],
): LongTermPickStatus {
  if (resultTeamIds.length === 0) {
    return "pending";
  }
  return resultTeamIds.includes(teamId) ? "hit" : "miss";
}

export function countLongTermHits(
  pickedTeamIds: readonly number[],
  resultTeamIds: readonly number[],
): number {
  const resultSet = new Set(resultTeamIds);
  return pickedTeamIds.filter((id) => resultSet.has(id)).length;
}

export function scoreLongTerm(
  pickedTeamIds: readonly number[],
  resultTeamIds: readonly number[],
  pointsPerCorrect: number,
): number {
  return countLongTermHits(pickedTeamIds, resultTeamIds) * pointsPerCorrect;
}

export function isLongTermMarketSettled(
  market: Pick<LongTermMarketCard, "settled_at" | "result_team_ids">,
): boolean {
  return market.settled_at != null && market.result_team_ids.length > 0;
}

export function formatLongTermPointsLabel(market: LongTermMarketCard): string {
  if (!isLongTermMarketSettled(market) || market.points === null) {
    return "Punkty po zatwierdzeniu admina";
  }
  return `${formatOdds(market.points)} pkt`;
}

export function formatLongTermHitsLabel(market: LongTermMarketCard): string {
  if (!isLongTermMarketSettled(market)) {
    return "";
  }
  const hits = countLongTermHits(
    market.picked_team_ids,
    market.result_team_ids,
  );
  return `${hits}/${market.selection_size} trafień`;
}

export function formatLongTermChangeLine(change: LongTermPickChange): string {
  const when = formatMatchDateTime(change.changed_at);
  if (change.previous_team_ids === null) {
    return `${when}: pierwszy zapis`;
  }
  return `${when}: zmiana zestawu`;
}

export function takeRecentLongTermChanges(
  changes: readonly LongTermPickChange[],
  limit: number = LONG_TERM_SHORT_HISTORY_LIMIT,
): LongTermPickChange[] {
  if (changes.length <= limit) {
    return [...changes];
  }
  return changes.slice(-limit);
}

export function longTermSaveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Faza ligowa już się rozpoczęła. Typu nie można zmienić.";
    }
    if (error.status === 404) {
      return "Ten rynek długoterminowy nie istnieje.";
    }
    if (error.status === 422) {
      return "Wybierz dokładnie wymaganą liczbę różnych drużyn z fazy ligowej.";
    }
    if (error.status === 401) {
      return "Sesja wygasła. Zaloguj się ponownie.";
    }
  }
  return "Nie udało się zapisać typu. Spróbuj ponownie.";
}

export function longTermSettleErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Faza ligowa nie jest jeszcze kompletna. Rozliczenie jest zablokowane.";
    }
    if (error.status === 404) {
      return "Ten rynek długoterminowy nie istnieje.";
    }
    if (error.status === 422) {
      return "Wskaż dokładnie tyle drużyn, ile wymaga rynek.";
    }
    if (error.status === 403) {
      return "Brak uprawnień administratora.";
    }
  }
  return "Nie udało się zatwierdzić wyniku. Spróbuj ponownie.";
}

export function longTermAutoResultErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "Ten rynek długoterminowy nie istnieje.";
    }
    if (error.status === 403) {
      return "Brak uprawnień administratora.";
    }
  }
  return "Nie udało się wczytać propozycji TOP 8.";
}

export function lockLongTermMarket(
  market: LongTermMarketCard,
): LongTermMarketCard {
  return { ...market, is_locked: true };
}

export function formatAdminLongTermChangeLine(
  change: LongTermPickChange,
): string {
  const when = formatMatchDateTime(change.changed_at);
  const who = `${change.display_name} (${change.user_uuid})`;
  const market = `rynek ${change.market_id}`;
  const nextSet = change.new_team_ids.join(",");
  if (change.previous_team_ids === null) {
    return `${when}: ${who}, ${market}, pierwszy zapis (${nextSet})`;
  }
  const previousSet = change.previous_team_ids.join(",");
  return `${when}: ${who}, ${market}, zmiana zestawu (${previousSet} -> ${nextSet})`;
}

export function longTermAdminAuditErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return "Brak uprawnień administratora.";
    }
    if (error.status === 401) {
      return "Sesja wygasła. Zaloguj się ponownie.";
    }
    if (error.status === 404) {
      return longTermAuditNotFoundMessage(error.message);
    }
  }
  return "Nie udało się wczytać audytu. Spróbuj ponownie.";
}

function longTermAuditNotFoundMessage(detail: string): string {
  const normalized = detail.toLowerCase();
  if (normalized.includes("user not found")) {
    return "Nie znaleziono użytkownika o podanym UUID.";
  }
  if (normalized.includes("season not found")) {
    return "Nie znaleziono sezonu.";
  }
  if (normalized.includes("market not found")) {
    return "Nie znaleziono rynku długoterminowego.";
  }
  return "Nie znaleziono użytkownika, rynku albo sezonu.";
}

export function applySavedLongTermPicks(
  market: LongTermMarketCard,
  saved: SaveLongTermPicksResponse,
  changes?: LongTermPickChange[],
): LongTermMarketCard {
  return {
    ...market,
    picked_team_ids: saved.team_ids,
    changes: changes ?? market.changes,
  };
}

export function applySettledLongTermResult(
  market: LongTermMarketCard,
  settled: SettleLongTermResponse,
): LongTermMarketCard {
  const resultTeamIds = settled.result_team_ids;
  const hasPicks = market.picked_team_ids.length > 0;
  return {
    ...market,
    result_team_ids: resultTeamIds,
    settled_at: settled.settled_at,
    points: hasPicks
      ? scoreLongTerm(
          market.picked_team_ids,
          resultTeamIds,
          market.points_per_correct,
        )
      : 0,
  };
}

export function updateLongTermDashboardMarket(
  dashboard: LongTermDashboardResponse,
  marketId: number,
  updater: (market: LongTermMarketCard) => LongTermMarketCard,
): LongTermDashboardResponse {
  return {
    ...dashboard,
    markets: dashboard.markets.map((market) =>
      market.market_id === marketId ? updater(market) : market,
    ),
  };
}

export function formatLongTermCompleteness(
  result: LongTermAutoResultResponse,
): string {
  if (result.is_complete) {
    return (
      `Faza ligowa jest kompletna (${result.participant_count} drużyn, ` +
      `${result.settled_match_count} meczów). TOP 8 to propozycja — ` +
      "dalsze kryteria UEFA nie są uwzględnione."
    );
  }
  return (
    `Faza ligowa nie jest kompletna: drużyn ${result.participant_count}/` +
    `${result.required_participant_count}, min. meczów na drużynę ` +
    `${result.min_matches_per_team}/${result.required_matches_per_team}, ` +
    `spotkań ${result.settled_match_count}/` +
    `${result.required_settled_match_count}.`
  );
}

export function formatLongTermStandingLine(
  team: LongTermStandingTeam,
  teamNameDisplay: TeamNameDisplayPreference,
): string {
  const name = formatLongTermTeamName(team, teamNameDisplay);
  const signedDifference =
    team.goal_difference > 0
      ? `+${team.goal_difference}`
      : String(team.goal_difference);
  return `${name} · ${team.points} pkt · ${signedDifference} · ${team.goals_for} bramek`;
}

export function defaultAdminResultIds(
  autoResult: LongTermAutoResultResponse | null,
): number[] {
  if (autoResult === null) {
    return [];
  }
  if (autoResult.result_team_ids.length > 0) {
    return [...autoResult.result_team_ids];
  }
  return [...autoResult.proposed_team_ids];
}

export function canSettleLongTermSelection(
  autoResult: LongTermAutoResultResponse,
  selectedIds: readonly number[],
): boolean {
  if (!autoResult.is_complete) {
    return false;
  }
  return selectedIds.length === autoResult.selection_size;
}

export function teamsById(
  candidates: readonly LongTermTeam[],
): Map<number, LongTermTeam> {
  return new Map(candidates.map((team) => [team.team_id, team]));
}

export function selectedTeams(
  candidates: readonly LongTermTeam[],
  selectedIds: readonly number[],
): LongTermTeam[] {
  const index = teamsById(candidates);
  return selectedIds.flatMap((id) => {
    const team = index.get(id);
    return team ? [team] : [];
  });
}
