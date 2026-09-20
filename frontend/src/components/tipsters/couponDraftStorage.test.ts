import { describe, expect, it } from "vitest";

import {
  clearCouponDraft,
  couponDraftStorageKey,
  matchesForDraftLegs,
  readCouponDraft,
  writeCouponDraft,
} from "@/components/tipsters/couponDraftStorage";
import type { CatalogMatch } from "@/types/api";

const MATCH: CatalogMatch = {
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
};

function memoryStorage(initial: Record<string, string> = {}) {
  const data = { ...initial };
  return {
    getItem(key: string) {
      return data[key] ?? null;
    },
    setItem(key: string, value: string) {
      data[key] = value;
    },
    removeItem(key: string) {
      delete data[key];
    },
    data,
  };
}

describe("couponDraftStorage", () => {
  it("round-trips a slip snapshot and keeps matches for draft legs", () => {
    const key = couponDraftStorageKey("/profile/alice");
    const storage = memoryStorage();
    const draft = {
      legs: [{ matchId: 10, eventIds: [6, 12], odds: "1.55" }],
      mode: "units" as const,
      stakeRaw: "2",
      matches: [MATCH],
    };

    writeCouponDraft(key, draft, storage);
    expect(readCouponDraft(key, storage)).toEqual(draft);
    expect(matchesForDraftLegs([MATCH], draft.legs)).toEqual([MATCH]);
    clearCouponDraft(key, storage);
    expect(readCouponDraft(key, storage)).toBeNull();
  });

  it("ignores malformed snapshots", () => {
    const key = couponDraftStorageKey("/profile/alice");
    const storage = memoryStorage({ [key]: "{not-json" });
    expect(readCouponDraft(key, storage)).toBeNull();
  });
});
