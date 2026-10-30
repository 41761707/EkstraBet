import { describe, expect, it } from "vitest";

import {
  AKO_STAKE_ASSUMPTION,
  COMBINED_LEG_ASSUMPTION,
  STAKE_ADVICE_DEBOUNCE_MS,
  buildAdviseStakeRequest,
  buildCouponCreateRequest,
  formatAppliedAdviceStake,
  formatStakeAdviceProbability,
  formatStakeAdviceUnits,
  STAKE_ADVICE_NETWORK_ERROR,
  stakeAdviceAgentLines,
  stakeAdviceAssumptions,
  stakeAdviceErrorMessage,
  stakeAdviceReasonLabel,
  stakeAdviceRequestOrNull,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import type { CatalogEvent, CatalogMatch, LegAdvice } from "@/types/api";

const LEGS: DraftCouponLeg[] = [
  { matchId: 10, eventIds: [6, 12], odds: "1.85" },
  { matchId: 11, eventIds: [1], odds: "2.00" },
];

const MATCHES: CatalogMatch[] = [
  {
    id: 10,
    league_id: 1,
    league_name: "Ekstraklasa",
    league_tier: 1,
    game_date: "2026-09-21T18:00:00Z",
    result: null,
    home_id: 1,
    home_name: "Legia",
    home_shortcut: "LEG",
    away_id: 2,
    away_name: "Lech",
    away_shortcut: "LPO",
  },
];

const EVENTS: CatalogEvent[] = [
  { id: 1, name: "Gospodarz wygrywa" },
  { id: 6, name: "BTTS tak" },
];

describe("stake advice reason labels", () => {
  it("maps every reason to Polish, including model_not_ready as information", () => {
    expect(stakeAdviceReasonLabel("no_bet_low_edge")).toBe(
      "Werdykt modeli nie wskazuje na przewagę nad kursem " +
        "(wyższy kurs od przewidywanego prawdopodobieństwa). " +
        "Sugerowana stawka to 0.",
    );
    expect(stakeAdviceReasonLabel("no_prediction")).toBe(
      "Żadne zdarzenie nie ma opublikowanego modelu. " +
        "Sugestia opiera się tylko i wyłącznie na wprowadzonej pewności i kursie.",
    );
    expect(stakeAdviceReasonLabel("model_not_ready")).toBe(
      "UWAGA: Model jest w fazie testów i nie spełnia wszystkich " +
        "kryteriów. Sugestia bazuje na zwykłej predykcji.",
    );
    expect(stakeAdviceReasonLabel("ok")).toBe("Jest dodatnia rada stawki.");
    expect(stakeAdviceReasonLabel("other")).toBe("Nieznana odpowiedź systemu.");
  });

  it("uses an advice message when the request never reaches the API", () => {
    expect(stakeAdviceErrorMessage(new Error("network down"))).toBe(
      STAKE_ADVICE_NETWORK_ERROR,
    );
  });
});

describe("buildAdviseStakeRequest", () => {
  it("serializes the same legs as coupon create and keeps confidence", () => {
    const advice = buildAdviseStakeRequest(LEGS, 70);
    const coupon = buildCouponCreateRequest(LEGS, "money", "10");
    expect("legs" in advice).toBe(true);
    expect("legs" in coupon).toBe(true);
    if (!("legs" in advice) || !("legs" in coupon)) {
      return;
    }
    expect(advice.confidence).toBe(70);
    expect(advice.legs).toEqual(coupon.legs);
    expect(advice).not.toHaveProperty("stake_amount");
    expect(advice).not.toHaveProperty("stake_units");
  });

  it("rejects confidence outside 0-100 and incomplete legs", () => {
    expect(buildAdviseStakeRequest(LEGS, 101)).toEqual({
      error: "Pewność musi być liczbą całkowitą od 0 do 100.",
    });
    expect(buildAdviseStakeRequest(LEGS, -1)).toEqual({
      error: "Pewność musi być liczbą całkowitą od 0 do 100.",
    });
    expect(buildAdviseStakeRequest(LEGS, 70.5)).toEqual({
      error: "Pewność musi być liczbą całkowitą od 0 do 100.",
    });
    expect(buildAdviseStakeRequest([], 50)).toEqual({
      error: "Kupon musi mieć od 1 do 8 zdarzeń.",
    });
    expect(
      buildAdviseStakeRequest(
        [{ matchId: 10, eventIds: [1], odds: "1.00" }],
        50,
      ),
    ).toEqual({
      error: "Każde zdarzenie musi mieć kurs co najmniej 1.01.",
    });
  });

  it("accepts the slider endpoints", () => {
    expect("confidence" in buildAdviseStakeRequest([LEGS[1]], 0)).toBe(true);
    expect("confidence" in buildAdviseStakeRequest([LEGS[1]], 100)).toBe(true);
  });
});

describe("stakeAdviceRequestOrNull", () => {
  it("returns null while the checkbox is off", () => {
    expect(stakeAdviceRequestOrNull(false, LEGS, 70)).toBeNull();
  });

  it("returns null until the legs can be posted", () => {
    expect(
      stakeAdviceRequestOrNull(
        true,
        [{ matchId: 10, eventIds: [1], odds: "" }],
        70,
      ),
    ).toBeNull();
  });

  it("returns the advise body only when the checkbox is on", () => {
    const request = stakeAdviceRequestOrNull(true, LEGS, 70);
    expect(request).toEqual(buildAdviseStakeRequest(LEGS, 70));
  });
});

describe("stake advice presentation", () => {
  it("warns on a combined leg and on an AKO coupon", () => {
    expect(stakeAdviceAssumptions([LEGS[1]])).toEqual([]);
    expect(stakeAdviceAssumptions([LEGS[0]])).toEqual([
      COMBINED_LEG_ASSUMPTION,
    ]);
    expect(stakeAdviceAssumptions(LEGS)).toEqual([
      COMBINED_LEG_ASSUMPTION,
      AKO_STAKE_ASSUMPTION,
    ]);
  });

  it("formats probability, units and the stake written into the money field", () => {
    expect(formatStakeAdviceProbability(0.625)).toBe("62.5%");
    expect(formatStakeAdviceUnits(1.2)).toBe("1.20");
    expect(formatAppliedAdviceStake(10.5)).toBe("10.50");
    expect(STAKE_ADVICE_DEBOUNCE_MS).toBe(400);
  });

  it("lists only legs the system agent played", () => {
    const legs: LegAdvice[] = [
      {
        match_id: 10,
        event_ids: [1, 6],
        model_probability: 0.4,
        implied_probability: 0.5,
        agent_liked: true,
        p_used: 0.45,
      },
      {
        match_id: 11,
        event_ids: [1],
        model_probability: null,
        implied_probability: 0.5,
        agent_liked: false,
        p_used: 0.4,
      },
    ];
    expect(stakeAdviceAgentLines(legs, MATCHES, EVENTS)).toEqual([
      {
        key: "10:1,6",
        label: "Legia – Lech: Gospodarz wygrywa, BTTS tak",
      },
    ]);
  });
});
