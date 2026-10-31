/** Labels and draft mapping for the event suggestion panel. */

import { ApiError } from "@/lib/apiShared";
import type {
  EventSuggestion,
  EventSuggestionTier,
  EventSuggestionTiers,
  SuggestEventsRequest,
} from "@/types/api";

export const EVENT_SUGGESTION_TIERS: readonly EventSuggestionTier[] = [
  "S",
  "A",
  "B",
];

const TIER_PHRASES: Record<EventSuggestionTier, string> = {
  S: "Najlepsze dopasowania do Twoich preferencji",
  A: "Bliskie Twoim preferencjom",
  B: "Mogą Ci się spodobać",
};

/** Closed set. An unknown code is not a chip. */
export const EVENT_ADVISOR_REASON_LABELS: Record<string, string> = {
  computer_bet: "Werdykt komputera: graj",
  league_on_slip: "Liga jest już na tym kuponie",
  league_history: "Tę ligę grasz często",
  event_history: "Ten typ zdarzenia grasz często",
  odds_in_band: "Kurs w Twoim zakresie",
  computer_lean: "Model lubi ten typ",
};

export const EVENT_ADVISOR_NETWORK_ERROR =
  "Nie udało się pobrać sugestii. Spróbuj ponownie.";

export interface SuggestionTierGroup {
  tier: EventSuggestionTier;
  label: string;
  items: EventSuggestion[];
}

export interface SuggestableDraftLeg {
  matchId: number;
  eventIds: number[];
}

/** Full group title, for example "S — Najmocniej pasuje". */
export function suggestionTierLabel(tier: EventSuggestionTier): string {
  return `${tier} -  ${TIER_PHRASES[tier]}`;
}

/** Phrase next to the S/A/B badge. */
export function suggestionTierPhrase(tier: EventSuggestionTier): string {
  return TIER_PHRASES[tier];
}

/**
 * Always S, then A, then B. Extra keys on the payload are ignored.
 */
export function suggestionTierGroups(
  tiers: EventSuggestionTiers,
): SuggestionTierGroup[] {
  return EVENT_SUGGESTION_TIERS.map((tier) => ({
    tier,
    label: suggestionTierLabel(tier),
    items: tiers[tier],
  }));
}

export function suggestionsAreEmpty(tiers: EventSuggestionTiers): boolean {
  return suggestionTierGroups(tiers).every((group) => group.items.length === 0);
}

/** Polish chip text. Unknown codes disappear. */
export function visibleReasonLabels(codes: readonly string[]): string[] {
  const labels: string[] = [];
  for (const code of codes) {
    const label = EVENT_ADVISOR_REASON_LABELS[code];
    if (label !== undefined) {
      labels.push(label);
    }
  }
  return labels;
}

/** Match ids already on the slip. A later catalog add is included. */
export function draftMatchIds(
  legs: readonly SuggestableDraftLeg[],
): Set<number> {
  const matchIds = new Set<number>();
  for (const leg of legs) {
    matchIds.add(leg.matchId);
  }
  return matchIds;
}

/** Drop every row of a match already added to the draft. */
export function withoutMatchSuggestions(
  tiers: EventSuggestionTiers,
  matchIds: ReadonlySet<number>,
): EventSuggestionTiers {
  if (matchIds.size === 0) {
    return tiers;
  }
  return {
    S: tiers.S.filter((item) => !matchIds.has(item.match_id)),
    A: tiers.A.filter((item) => !matchIds.has(item.match_id)),
    B: tiers.B.filter((item) => !matchIds.has(item.match_id)),
  };
}

/** Draft legs for POST /tipsters/me/suggest-events. No odds and no stake. */
export function buildSuggestEventsRequest(
  legs: readonly SuggestableDraftLeg[],
): SuggestEventsRequest {
  return {
    legs: legs.map((leg) => ({
      match_id: leg.matchId,
      event_ids: [...leg.eventIds],
    })),
  };
}

/** Suggestion failures stay distinct from a failed coupon save. */
export function eventAdvisorErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return EVENT_ADVISOR_NETWORK_ERROR;
}
