import { describe, expect, it } from "vitest";

import {
  EVENT_ADVISOR_NETWORK_ERROR,
  EVENT_ADVISOR_REASON_LABELS,
  EVENT_SUGGESTION_TIERS,
  buildSuggestEventsRequest,
  eventAdvisorErrorMessage,
  suggestionTierGroups,
  suggestionTierLabel,
  suggestionsAreEmpty,
  visibleReasonLabels,
  withoutMatchSuggestions,
} from "@/components/tipsters/eventAdvisorModel";
import { ApiError } from "@/lib/apiShared";
import type { EventSuggestion, EventSuggestionTiers } from "@/types/api";

const REASON_CODES = [
  "computer_bet",
  "league_on_slip",
  "league_history",
  "event_history",
  "odds_in_band",
  "computer_lean",
];

function suggestion(
  tier: EventSuggestion["tier"],
  matchId: number,
  eventId: number,
): EventSuggestion {
  return {
    tier,
    match_id: matchId,
    event_id: eventId,
    event_name: "Gospodarz wygrywa",
    league_id: 1,
    league_name: "K League",
    home_name: "Seoul",
    away_name: "Busan",
    game_date: "2026-10-31T18:00:00",
    odds: 1.8,
    bookmaker_id: 3,
    score: 0.9,
    reasons: ["computer_bet", "unknown_code"],
  };
}

describe("event advisor reason labels", () => {
  it("covers the six codes and drops an unknown code", () => {
    expect(Object.keys(EVENT_ADVISOR_REASON_LABELS)).toEqual(REASON_CODES);
    expect(visibleReasonLabels([
      "computer_bet",
      "not_a_reason",
      "odds_in_band",
    ])).toEqual([
      "Werdykt komputera: graj",
      "Kurs w Twoim zakresie",
    ]);
    expect(EVENT_ADVISOR_REASON_LABELS.league_on_slip).toBe(
      "Liga jest już na tym kuponie",
    );
    expect(EVENT_ADVISOR_REASON_LABELS.league_history).toBe(
      "Tę ligę grasz często",
    );
    expect(EVENT_ADVISOR_REASON_LABELS.event_history).toBe(
      "Ten typ zdarzenia grasz często",
    );
    expect(EVENT_ADVISOR_REASON_LABELS.computer_lean).toBe(
      "Model widzi sensowny typ",
    );
  });
});

describe("suggestion tiers", () => {
  it("keeps only S, A and B in that order", () => {
    const tiers: EventSuggestionTiers = {
      S: [suggestion("S", 1, 7)],
      A: [suggestion("A", 2, 8)],
      B: [],
    };
    // Nadmiarowy klucz nie może utworzyć czwartego piętra.
    const withExtra = {
      ...tiers,
      C: [suggestion("B", 9, 1)],
    } as EventSuggestionTiers;

    const groups = suggestionTierGroups(withExtra);

    expect(groups.map((group) => group.tier)).toEqual(["S", "A", "B"]);
    expect(EVENT_SUGGESTION_TIERS).toEqual(["S", "A", "B"]);
    expect(groups[0]?.label).toBe(suggestionTierLabel("S"));
    expect(suggestionTierLabel("A")).toBe("A — Warto rozważyć");
    expect(suggestionTierLabel("B")).toBe("B — Luźniej pasuje");
    expect(groups[0]?.items).toEqual([suggestion("S", 1, 7)]);
    expect(suggestionsAreEmpty(tiers)).toBe(false);
    expect(suggestionsAreEmpty({ S: [], A: [], B: [] })).toBe(true);
  });

  it("drops every row of a match added to the draft", () => {
    const tiers: EventSuggestionTiers = {
      S: [suggestion("S", 10, 7)],
      A: [suggestion("A", 10, 8), suggestion("A", 11, 7)],
      B: [],
    };
    const visible = withoutMatchSuggestions(tiers, new Set([10]));
    expect(visible).toEqual({
      S: [],
      A: [suggestion("A", 11, 7)],
      B: [],
    });
    // Sam serwer nie był pusty. Pusty widok powstaje dopiero po odjęciu szkicu.
    expect(suggestionsAreEmpty(tiers)).toBe(false);
    expect(suggestionsAreEmpty(
      withoutMatchSuggestions(tiers, new Set([10, 11])),
    )).toBe(true);
  });
});

describe("buildSuggestEventsRequest", () => {
  it("sends match and event ids without odds or a stake", () => {
    expect(buildSuggestEventsRequest([
      { matchId: 10, eventIds: [7, 8] },
    ])).toEqual({
      legs: [{ match_id: 10, event_ids: [7, 8] }],
    });
    expect(buildSuggestEventsRequest([])).toEqual({ legs: [] });
  });
});

describe("eventAdvisorErrorMessage", () => {
  it("keeps an API message and replaces a network failure", () => {
    expect(eventAdvisorErrorMessage(new ApiError(422, "bad draft"))).toBe(
      "bad draft",
    );
    expect(eventAdvisorErrorMessage(new Error("offline"))).toBe(
      EVENT_ADVISOR_NETWORK_ERROR,
    );
  });
});
