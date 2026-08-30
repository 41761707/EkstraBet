/** Pure helpers for the Champions League Typer admin publication panel. */

import { ApiError } from "@/lib/apiShared";
import { formatMatchDateTime } from "@/lib/format";
import { GROUP_STAGE_MAX_ROUND } from "@/lib/typerLm";
import type {
  LeagueRound,
  TyperAdminCandidate,
  TyperPredictionChange,
} from "@/types/api";

export const GROUP_STAGE_MATCH_COUNT = 9;
export const KNOCKOUT_MIN_ROUND = 900;
export const CHAMPIONS_LEAGUE_LEAGUE_ID = 42;
export const GROUP_STAGE_ROUNDS: readonly number[] = [1, 2, 3, 4, 5, 6, 7, 8];

export function isGroupStageRound(roundNumber: number): boolean {
  return roundNumber >= 1 && roundNumber <= GROUP_STAGE_MAX_ROUND;
}

export function unpublishedMatchIds(
  candidates: readonly TyperAdminCandidate[],
): number[] {
  return candidates
    .filter((candidate) => !candidate.is_published)
    .map((candidate) => candidate.match_id);
}

export function publishedMatchCount(
  candidates: readonly TyperAdminCandidate[],
): number {
  return candidates.filter((candidate) => candidate.is_published).length;
}

export function defaultSelectedMatchIds(
  candidates: readonly TyperAdminCandidate[],
  roundNumber: number,
): number[] {
  if (isGroupStageRound(roundNumber)) {
    return [];
  }
  return unpublishedMatchIds(candidates);
}

export function toggleSelectedMatchId(
  selectedIds: readonly number[],
  matchId: number,
): number[] {
  if (selectedIds.includes(matchId)) {
    return selectedIds.filter((id) => id !== matchId);
  }
  return [...selectedIds, matchId];
}

export function resolveGroupMatchCount(count?: number | null): number {
  if (count == null || count < 1) {
    return GROUP_STAGE_MATCH_COUNT;
  }
  return count;
}

export function canPublishSelection(
  candidates: readonly TyperAdminCandidate[],
  selectedIds: readonly number[],
  roundNumber: number,
  groupMatchCount: number = GROUP_STAGE_MATCH_COUNT,
): boolean {
  const unpublished = new Set(unpublishedMatchIds(candidates));
  if (selectedIds.length === 0) {
    return false;
  }
  const unique = new Set(selectedIds);
  if (unique.size !== selectedIds.length) {
    return false;
  }
  for (const matchId of unique) {
    if (!unpublished.has(matchId)) {
      return false;
    }
  }
  if (isGroupStageRound(roundNumber)) {
    return publishedMatchCount(candidates) + unique.size === groupMatchCount;
  }
  return unique.size === unpublished.size;
}

export function publicationCounterLabel(
  candidates: readonly TyperAdminCandidate[],
  selectedIds: readonly number[],
  roundNumber: number,
  groupMatchCount: number = GROUP_STAGE_MATCH_COUNT,
): string {
  if (isGroupStageRound(roundNumber)) {
    const complete = publishedMatchCount(candidates) + selectedIds.length;
    return `${complete}/${groupMatchCount}`;
  }
  return `${selectedIds.length}/${unpublishedMatchIds(candidates).length}`;
}

export function selectKnockoutRounds(
  rounds: readonly LeagueRound[],
): LeagueRound[] {
  return rounds.filter((round) => round.round_number >= KNOCKOUT_MIN_ROUND);
}

export function shouldApplyAdminLoad(
  requestId: number,
  latestRequestId: number,
): boolean {
  return requestId === latestRequestId;
}

export function candidateOddsLabel(candidate: TyperAdminCandidate): string {
  if (candidate.has_complete_superbet_odds) {
    return "Kursy Superbet kompletne";
  }
  return "Brak kompletnych kursów Superbet — nie blokuje publikacji";
}

export function parseOptionalPositiveInt(
  rawValue: string,
): number | undefined {
  const trimmed = rawValue.trim();
  if (trimmed === "") {
    return undefined;
  }
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return undefined;
  }
  return parsed;
}

export function parseKnockoutRoundNumber(
  rawValue: string,
): number | undefined {
  const parsed = parseOptionalPositiveInt(rawValue);
  if (parsed === undefined || parsed < KNOCKOUT_MIN_ROUND) {
    return undefined;
  }
  return parsed;
}

export function formatAdminPredictionChangeLine(
  change: TyperPredictionChange,
): string {
  const when = formatMatchDateTime(change.changed_at);
  const from = change.previous_outcome ?? "—";
  return (
    `${when}: ${change.display_name} (${change.user_uuid}), ` +
    `mecz ${change.match_id}, ${from} na ${change.new_outcome}`
  );
}

export function tryBeginAdminMutation(
  inFlightRef: { current: boolean },
): boolean {
  if (inFlightRef.current) {
    return false;
  }
  inFlightRef.current = true;
  return true;
}

function sharedAdminAuthErrorMessage(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  if (error.status === 403) {
    return "Brak uprawnień administratora.";
  }
  if (error.status === 401) {
    return "Sesja wygasła. Zaloguj się ponownie.";
  }
  return null;
}

export function typerAdminPublicationErrorMessage(
  error: unknown,
  groupMatchCount: number = GROUP_STAGE_MATCH_COUNT,
): string {
  const authMessage = sharedAdminAuthErrorMessage(error);
  if (authMessage !== null) {
    return authMessage;
  }
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return (
        "Operacja odrzucona: mecz jest już opublikowany, ma typy " +
        "albo już się rozpoczął."
      );
    }
    if (error.status === 422) {
      return (
        "Zestaw nie spełnia reguł publikacji (dokładnie " +
        `${groupMatchCount} meczów w fazie ligowej albo komplet ` +
        "rundy pucharowej)."
      );
    }
    if (error.status === 404) {
      return "Brak meczów Ligi Mistrzów dla wybranej rundy.";
    }
  }
  return "Nie udało się wykonać operacji. Spróbuj ponownie.";
}

export function adminCandidateLoadErrorMessage(
  error: unknown,
): string | null {
  if (error instanceof ApiError && error.status === 404) {
    return null;
  }
  return typerAdminPublicationErrorMessage(error);
}

export function typerAdminAuditErrorMessage(error: unknown): string {
  const authMessage = sharedAdminAuthErrorMessage(error);
  if (authMessage !== null) {
    return authMessage;
  }
  if (error instanceof ApiError && error.status === 404) {
    return auditNotFoundMessage(error.message);
  }
  return "Nie udało się wczytać audytu. Spróbuj ponownie.";
}

function auditNotFoundMessage(detail: string): string {
  const normalized = detail.toLowerCase();
  if (normalized.includes("user not found")) {
    return "Nie znaleziono użytkownika o podanym UUID.";
  }
  if (normalized.includes("season not found")) {
    return "Nie znaleziono sezonu.";
  }
  if (normalized.includes("published match not found")) {
    return "Nie znaleziono opublikowanego meczu.";
  }
  return "Nie znaleziono użytkownika, meczu albo sezonu.";
}
