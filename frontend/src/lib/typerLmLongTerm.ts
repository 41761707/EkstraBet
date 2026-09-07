/** Presentation helpers for Typer LM long-term markets. */

import { ApiError } from "@/lib/apiShared";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import {
  normalizeSubjectText,
  scoreExactSubject,
} from "@/lib/typerLmLongTermExact";
import {
  areTeamIdSequencesEqual,
  isLongTermMarketLockedForUi,
  MARKET_KIND_FREE_TEXT,
  MARKET_KIND_SINGLE_TEAM,
  MARKET_KIND_YES_NO,
  SCORING_KIND_EXACT_SUBJECT,
  SCORING_KIND_ZONE_AND_POSITION,
  scoreZoneAndPosition,
} from "@/lib/typerLmLongTermRanking";
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

export { isLongTermMarketLockedForUi };

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
  // kolejność jest częścią typu tabeli — zbiór id nie steruje zapisem
  return !areTeamIdSequencesEqual(selectedIds, market.picked_team_ids);
}

export function hasSavedRankedPick(
  market: Pick<LongTermMarketCard, "picked_team_ids" | "selection_size">,
): boolean {
  return market.picked_team_ids.length === market.selection_size;
}

export function hasSavedLongTermPick(
  market: Pick<
    LongTermMarketCard,
    | "market_kind"
    | "picked_team_ids"
    | "selection_size"
    | "picked_subject_text"
    | "picked_is_text_correct"
  >,
): boolean {
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    return (market.picked_subject_text ?? "").trim() !== "";
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    return market.picked_is_text_correct != null;
  }
  if (market.market_kind === MARKET_KIND_SINGLE_TEAM) {
    return market.picked_team_ids.length === 1;
  }
  return hasSavedRankedPick(market);
}

export function rankingIdsForMarket(market: LongTermMarketCard): number[] {
  if (hasSavedRankedPick(market)) {
    return [...market.picked_team_ids];
  }
  return market.candidates.map((team) => team.team_id);
}

export const LONG_TERM_UNSAVED_PICK_STATUS = "Nie zapisano typu";

export function longTermUnsavedPickStatus(
  market: Pick<
    LongTermMarketCard,
    | "market_kind"
    | "picked_team_ids"
    | "selection_size"
    | "picked_subject_text"
    | "picked_is_text_correct"
  >,
  isReadOnly: boolean,
): string | null {
  if (!isReadOnly || hasSavedLongTermPick(market)) {
    return null;
  }
  return LONG_TERM_UNSAVED_PICK_STATUS;
}

/**
 * Saved pick after lock/settle; official table if settled without a pick;
 * local draft only while typing is open.
 */
export function displayedRankedTeamIds(
  market: LongTermMarketCard,
  draftIds: readonly number[],
  isReadOnly: boolean,
): number[] {
  if (!isReadOnly) {
    return [...draftIds];
  }
  if (hasSavedRankedPick(market)) {
    return [...market.picked_team_ids];
  }
  if (isLongTermMarketSettled(market)) {
    return [...market.result_team_ids];
  }
  return rankingIdsForMarket(market);
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
  market: Pick<
    LongTermMarketCard,
    | "settled_at"
    | "result_team_ids"
    | "result_subject_texts"
    | "result_is_text_correct"
    | "market_kind"
  >,
): boolean {
  if (market.settled_at == null) {
    return false;
  }
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    return market.result_subject_texts.length > 0;
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    return market.result_is_text_correct != null;
  }
  return market.result_team_ids.length > 0;
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
  return `${when}: ${longTermChangeActionLabel(change)}`;
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

export function longTermSaveErrorMessage(
  error: unknown,
  marketKind?: string,
): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Faza ligowa już się rozpoczęła. Typu nie można zmienić.";
    }
    if (error.status === 404) {
      return "Ten rynek długoterminowy nie istnieje.";
    }
    if (error.status === 422) {
      return longTermSaveUnprocessableMessage(marketKind);
    }
    if (error.status === 401) {
      return "Sesja wygasła. Zaloguj się ponownie.";
    }
  }
  return "Nie udało się zapisać typu. Spróbuj ponownie.";
}

export function longTermSettleErrorMessage(
  error: unknown,
  marketKind?: string,
): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Faza ligowa nie jest jeszcze kompletna. Rozliczenie jest zablokowane.";
    }
    if (error.status === 404) {
      return "Ten rynek długoterminowy nie istnieje.";
    }
    if (error.status === 422) {
      return longTermSettleUnprocessableMessage(marketKind);
    }
    if (error.status === 403) {
      return "Brak uprawnień administratora.";
    }
  }
  return "Nie udało się zatwierdzić wyniku. Spróbuj ponownie.";
}

function longTermSettleUnprocessableMessage(marketKind?: string): string {
  if (marketKind === MARKET_KIND_FREE_TEXT) {
    return "Podaj co najmniej jedno unikalne imię i nazwisko (najwyżej 160 znaków).";
  }
  if (marketKind === MARKET_KIND_YES_NO) {
    return "Wybierz TAK albo NIE.";
  }
  if (marketKind === MARKET_KIND_SINGLE_TEAM) {
    return "Wybierz co najmniej jedną drużynę z fazy ligowej.";
  }
  return "Wskaż dokładnie tyle drużyn, ile wymaga rynek.";
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
  return "Nie udało się wczytać propozycji tabeli.";
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
  const action = longTermChangeActionLabel(change);
  return `${when}: ${who}, ${market}, ${action} (${formatAdminChangePayload(change)})`;
}

function isLongTermPickDebut(change: LongTermPickChange): boolean {
  // previous_team_ids zostaje null przy edycji tekstu i TAK/NIE
  return (
    change.previous_team_ids === null &&
    change.previous_subject_text === null &&
    change.previous_is_text_correct === null
  );
}

function longTermAuditPayloadKind(
  change: LongTermPickChange,
): "text" | "yes_no" | "teams" {
  if (change.previous_subject_text != null || change.new_subject_text != null) {
    return "text";
  }
  if (
    change.previous_is_text_correct != null ||
    change.new_is_text_correct != null
  ) {
    return "yes_no";
  }
  return "teams";
}

function longTermChangeActionLabel(change: LongTermPickChange): string {
  if (isLongTermPickDebut(change)) {
    return "pierwszy zapis";
  }
  const kind = longTermAuditPayloadKind(change);
  if (kind === "text") {
    return "zmiana wpisu";
  }
  if (kind === "yes_no") {
    return "zmiana TAK/NIE";
  }
  return "zmiana zestawu";
}

function formatYesNoAuditValue(value: boolean | null): string {
  if (value == null) {
    return "";
  }
  return value ? "TAK" : "NIE";
}

function formatAdminChangePayload(change: LongTermPickChange): string {
  const kind = longTermAuditPayloadKind(change);
  if (kind === "text") {
    const next = change.new_subject_text ?? "";
    if (isLongTermPickDebut(change) || change.previous_subject_text === null) {
      return next;
    }
    return `${change.previous_subject_text} -> ${next}`;
  }
  if (kind === "yes_no") {
    const next = formatYesNoAuditValue(change.new_is_text_correct);
    if (
      isLongTermPickDebut(change) ||
      change.previous_is_text_correct === null
    ) {
      return next;
    }
    return `${formatYesNoAuditValue(change.previous_is_text_correct)} -> ${next}`;
  }
  const nextSet = change.new_team_ids.join(",");
  if (isLongTermPickDebut(change) || change.previous_team_ids === null) {
    return nextSet;
  }
  return `${change.previous_team_ids.join(",")} -> ${nextSet}`;
}

function longTermSaveUnprocessableMessage(marketKind?: string): string {
  if (marketKind === MARKET_KIND_FREE_TEXT) {
    return "Wpisz niepuste imię i nazwisko (najwyżej 160 znaków).";
  }
  if (marketKind === MARKET_KIND_YES_NO) {
    return "Wybierz TAK albo NIE.";
  }
  if (marketKind === MARKET_KIND_SINGLE_TEAM) {
    return "Wybierz dokładnie jedną drużynę z fazy ligowej.";
  }
  return "Wybierz dokładnie wymaganą liczbę różnych drużyn z fazy ligowej.";
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
    picked_subject_text: saved.subject_texts[0] ?? null,
    picked_is_text_correct: saved.is_text_correct,
    changes: changes ?? market.changes,
  };
}

export function applySettledLongTermResult(
  market: LongTermMarketCard,
  settled: SettleLongTermResponse,
): LongTermMarketCard {
  return {
    ...market,
    result_team_ids: settled.result_team_ids,
    result_subject_texts: settled.subject_texts,
    result_is_text_correct: settled.is_text_correct,
    settled_at: settled.settled_at,
    points: scoreAfterSettlement(market, settled),
  };
}

function scoreAfterSettlement(
  market: LongTermMarketCard,
  settled: SettleLongTermResponse,
): number {
  if (market.scoring_kind === SCORING_KIND_ZONE_AND_POSITION) {
    if (market.picked_team_ids.length === 0) {
      return 0;
    }
    return scoreZoneAndPosition(
      market.picked_team_ids,
      settled.result_team_ids,
      market.points_per_correct,
      market.points_per_exact_position,
      market.top_zone_size,
      market.bot_zone_size,
    );
  }
  if (market.scoring_kind !== SCORING_KIND_EXACT_SUBJECT) {
    return 0;
  }
  return scoreExactAfterSettlement(market, settled);
}

function scoreExactAfterSettlement(
  market: LongTermMarketCard,
  settled: SettleLongTermResponse,
): number {
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    const pick = market.picked_subject_text;
    const picks = pick == null ? [] : [normalizeSubjectText(pick)];
    return scoreExactSubject(
      picks,
      settled.subject_texts.map(normalizeSubjectText),
      market.points_per_correct,
    );
  }
  if (market.market_kind === MARKET_KIND_SINGLE_TEAM) {
    return scoreExactSubject(
      market.picked_team_ids,
      settled.result_team_ids,
      market.points_per_correct,
    );
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    const picks =
      market.picked_is_text_correct == null
        ? []
        : [market.picked_is_text_correct];
    const results =
      settled.is_text_correct == null ? [] : [settled.is_text_correct];
    return scoreExactSubject(picks, results, market.points_per_correct);
  }
  return 0;
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
      `${result.settled_match_count} meczów). Tabela to propozycja — ` +
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

export function formatLongTermStandingStats(team: LongTermStandingTeam): string {
  const signedDifference =
    team.goal_difference > 0
      ? `+${team.goal_difference}`
      : String(team.goal_difference);
  return `${team.points} pkt · ${signedDifference} · ${team.goals_for} bramek`;
}

export function formatLongTermStandingLine(
  team: LongTermStandingTeam,
  teamNameDisplay: TeamNameDisplayPreference,
): string {
  const name = formatLongTermTeamName(team, teamNameDisplay);
  return `${name} · ${formatLongTermStandingStats(team)}`;
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
