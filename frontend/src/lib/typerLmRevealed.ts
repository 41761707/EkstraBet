/** Pure presentation helpers for the revealed Typer LM picks matrix. */

import { ApiError } from "@/lib/apiShared";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTyperOutcomeButtonLabel } from "@/lib/typerLm";
import type {
  TyperOutcome,
  TyperRevealedMatch,
} from "@/types/api";

export function revealedPredictionsLoadErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "Sesja wygasła. Zaloguj się ponownie.";
  }
  if (error instanceof ApiError && error.status === 422) {
    return "Wybrana runda nie jest obsługiwana.";
  }
  return "Nie udało się wczytać typów uczestników. Spróbuj ponownie.";
}

/**
 * Format a revealed 1X2 cell using the existing team-name preference,
 * then append the explicit outcome marker.
 */
export function formatRevealedPickLabel(
  match: TyperRevealedMatch,
  outcome: TyperOutcome,
  preference: TeamNameDisplayPreference,
): string {
  const choiceLabel = formatTyperOutcomeButtonLabel(
    match,
    outcome,
    preference,
  );
  return `${choiceLabel} (${outcome})`;
}

/**
 * Index revealed picks by match, then by user, so table cells do not
 * scan the payload on every render.
 */
export function buildRevealedPickLookup(
  matches: TyperRevealedMatch[],
): Map<number, Map<string, TyperOutcome>> {
  const lookup = new Map<number, Map<string, TyperOutcome>>();
  for (const match of matches) {
    const picksByUser = new Map<string, TyperOutcome>();
    for (const pick of match.picks) {
      picksByUser.set(pick.user_uuid, pick.outcome);
    }
    lookup.set(match.match_id, picksByUser);
  }
  return lookup;
}
