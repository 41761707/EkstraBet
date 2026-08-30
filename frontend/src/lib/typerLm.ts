/** Presentation helpers for the Champions League Typer participant UI. */

import { ApiError } from "@/lib/apiShared";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import type {
  SaveTyperPredictionResponse,
  TyperDashboardResponse,
  TyperMatch,
  TyperOutcome,
  TyperPredictionChange,
  TyperRound,
} from "@/types/api";

export const TYPER_LM_ODDS_PLACEHOLDER = "Kurs pojawi się w dniu meczu";
export const TYPER_DRAW_OUTCOME_LABEL = "Remis";
export const TYPER_OUTCOMES: readonly TyperOutcome[] = ["1", "X", "2"];
export const GROUP_STAGE_MAX_ROUND = 8;
export const SHORT_HISTORY_LIMIT = 3;
export const TYPER_LOCK_TICK_MS = 1000;

export type TyperPointsStatus = "hit" | "miss" | "unsettled" | "none";

export function formatTyperOutcomeButtonLabel(
  match: Pick<TyperMatch, "home_team" | "away_team">,
  outcome: TyperOutcome,
  teamNameDisplay: TeamNameDisplayPreference,
): string {
  if (outcome === "1") {
    return formatTeamName(
      match.home_team.name,
      match.home_team.shortcut,
      teamNameDisplay,
    );
  }
  if (outcome === "2") {
    return formatTeamName(
      match.away_team.name,
      match.away_team.shortcut,
      teamNameDisplay,
    );
  }
  return TYPER_DRAW_OUTCOME_LABEL;
}

export function formatTyperRoundLabel(
  roundNumber: number,
  roundLabel?: string | null,
): string {
  if (roundNumber >= 1 && roundNumber <= GROUP_STAGE_MAX_ROUND) {
    return `Kolejka ${roundNumber}`;
  }
  const trimmed = roundLabel?.trim() ?? "";
  if (trimmed !== "" && trimmed !== String(roundNumber)) {
    return trimmed;
  }
  return `Runda ${roundNumber}`;
}

export function isTyperDeadlinePassed(
  gameDate: string,
  nowMs: number,
): boolean {
  const kickoffMs = Date.parse(gameDate);
  if (Number.isNaN(kickoffMs)) {
    return false;
  }
  return nowMs >= kickoffMs;
}

export function isTyperMatchLockedForUi(
  match: Pick<TyperMatch, "is_locked" | "game_date">,
  nowMs?: number | null,
): boolean {
  if (match.is_locked) {
    return true;
  }
  if (nowMs == null) {
    return false;
  }
  return isTyperDeadlinePassed(match.game_date, nowMs);
}

export function formatTyperResultLabel(
  match: TyperMatch,
  nowMs?: number | null,
): string | null {
  if (!isTyperMatchLockedForUi(match, nowMs)) {
    return null;
  }
  const result = match.result?.trim() ?? "";
  if (result === "1" || result === "X" || result === "2") {
    return `Wynik: ${result}`;
  }
  return "Oczekiwanie na wynik";
}

export function addPendingMatchId(
  current: ReadonlySet<number>,
  matchId: number,
): Set<number> {
  const next = new Set(current);
  next.add(matchId);
  return next;
}

export function removePendingMatchId(
  current: ReadonlySet<number>,
  matchId: number,
): Set<number> {
  const next = new Set(current);
  next.delete(matchId);
  return next;
}

export function selectInitialRoundNumber(
  rounds: readonly TyperRound[],
): number | null {
  if (rounds.length === 0) {
    return null;
  }
  const openRound = rounds.find((round) =>
    round.matches.some((match) => !match.is_locked),
  );
  if (openRound) {
    return openRound.round_number;
  }
  return rounds[rounds.length - 1]?.round_number ?? null;
}

export function isTyperOddsPlaceholderVisible(match: TyperMatch): boolean {
  return (
    match.odds_home === null &&
    match.odds_draw === null &&
    match.odds_away === null
  );
}

export function formatTyperOddsValue(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return formatOdds(value);
}

export function getTyperPointsStatus(match: TyperMatch): TyperPointsStatus {
  if (match.outcome === null) {
    return "none";
  }
  if (match.points === null) {
    return "unsettled";
  }
  if (match.points > 0) {
    return "hit";
  }
  return "miss";
}

export function formatTyperPointsLabel(match: TyperMatch): string {
  const status = getTyperPointsStatus(match);
  if (status === "none") {
    return "—";
  }
  if (status === "unsettled") {
    return "Nierozstrzygnięte";
  }
  if (status === "miss") {
    return "0 pkt";
  }
  return `${formatOdds(match.points ?? 0)} pkt`;
}

export function formatOutcomeTransition(
  previous: TyperOutcome | null,
  next: TyperOutcome,
): string {
  const from = previous ?? "—";
  return `${from} na ${next}`;
}

export function formatPredictionChangeLine(
  change: TyperPredictionChange,
): string {
  const when = formatMatchDateTime(change.changed_at);
  const transition = formatOutcomeTransition(
    change.previous_outcome,
    change.new_outcome,
  );
  return `${when}: ${transition}`;
}

export function takeRecentPredictionChanges(
  changes: readonly TyperPredictionChange[],
  limit: number = SHORT_HISTORY_LIMIT,
): TyperPredictionChange[] {
  if (changes.length <= limit) {
    return [...changes];
  }
  return changes.slice(-limit);
}

export function typerSaveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Mecz już się rozpoczął. Typu nie można zmienić.";
    }
    if (error.status === 404) {
      return "Ten mecz nie jest opublikowany w Typerze.";
    }
    if (error.status === 422) {
      return "Wybierz 1, X albo 2.";
    }
    if (error.status === 401) {
      return "Sesja wygasła. Zaloguj się ponownie.";
    }
  }
  return "Nie udało się zapisać typu. Spróbuj ponownie.";
}

export function lockTyperMatch(match: TyperMatch): TyperMatch {
  return { ...match, is_locked: true };
}

export function applySavedPrediction(
  match: TyperMatch,
  saved: SaveTyperPredictionResponse,
  actor: { uuid: string; displayName: string },
): TyperMatch {
  if (!saved.audit_written) {
    return { ...match, outcome: saved.outcome };
  }
  const change: TyperPredictionChange = {
    match_id: saved.match_id,
    user_uuid: actor.uuid,
    display_name: actor.displayName,
    previous_outcome: saved.previous_outcome,
    new_outcome: saved.outcome,
    changed_at: saved.updated_at,
  };
  return {
    ...match,
    outcome: saved.outcome,
    changes: [...match.changes, change],
  };
}

export function updateDashboardMatch(
  dashboard: TyperDashboardResponse,
  matchId: number,
  updater: (match: TyperMatch) => TyperMatch,
): TyperDashboardResponse {
  return {
    ...dashboard,
    rounds: dashboard.rounds.map((round) => ({
      ...round,
      matches: round.matches.map((match) =>
        match.match_id === matchId ? updater(match) : match,
      ),
    })),
  };
}

export function canSaveTyperOutcome(
  match: TyperMatch,
  outcome: TyperOutcome,
  isPending: boolean,
  nowMs?: number | null,
): boolean {
  if (isTyperMatchLockedForUi(match, nowMs) || isPending) {
    return false;
  }
  return match.outcome !== outcome;
}
