/** sessionStorage snapshot of an unsaved coupon slip. */

import type { DraftCouponLeg } from "@/components/tipsters/tipsterModel";
import type { CatalogMatch, StakeInputMode } from "@/types/api";

export const COUPON_DRAFT_STORAGE_PREFIX = "ekstrabet.tipster.coupon-draft:";

export interface PersistedCouponDraft {
  legs: DraftCouponLeg[];
  mode: StakeInputMode;
  stakeRaw: string;
  matches: CatalogMatch[];
}

const STAKE_MODES: readonly StakeInputMode[] = ["money", "units"];

export function couponDraftStorageKey(profilePath: string): string {
  return `${COUPON_DRAFT_STORAGE_PREFIX}${profilePath}`;
}

export function readCouponDraft(
  key: string,
  storage: Pick<Storage, "getItem"> | null = browserSessionStorage(),
): PersistedCouponDraft | null {
  if (!storage) {
    return null;
  }
  try {
    const raw = storage.getItem(key);
    if (!raw) {
      return null;
    }
    return parseCouponDraft(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function writeCouponDraft(
  key: string,
  draft: PersistedCouponDraft,
  storage: Pick<Storage, "setItem"> | null = browserSessionStorage(),
): void {
  if (!storage) {
    return;
  }
  try {
    storage.setItem(key, JSON.stringify(draft));
  } catch {
    // quota / private mode — szkic zostaje tylko w pamięci komponentu
  }
}

export function clearCouponDraft(
  key: string,
  storage: Pick<Storage, "removeItem"> | null = browserSessionStorage(),
): void {
  if (!storage) {
    return;
  }
  try {
    storage.removeItem(key);
  } catch {
    // ignore
  }
}

export function matchesForDraftLegs(
  matches: CatalogMatch[],
  legs: DraftCouponLeg[],
): CatalogMatch[] {
  const needed = new Set(legs.map((leg) => leg.matchId));
  return matches.filter((match) => needed.has(match.id));
}

function parseCouponDraft(value: unknown): PersistedCouponDraft | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const raw = value as Partial<PersistedCouponDraft>;
  if (!Array.isArray(raw.legs) || !raw.legs.every(isDraftLeg)) {
    return null;
  }
  if (raw.mode !== undefined && !isStakeMode(raw.mode)) {
    return null;
  }
  if (raw.stakeRaw !== undefined && typeof raw.stakeRaw !== "string") {
    return null;
  }
  const matches = Array.isArray(raw.matches)
    ? raw.matches.filter(isCatalogMatch)
    : [];
  return {
    legs: raw.legs,
    mode: raw.mode ?? "money",
    stakeRaw: raw.stakeRaw ?? "",
    matches,
  };
}

function isDraftLeg(value: unknown): value is DraftCouponLeg {
  if (!value || typeof value !== "object") {
    return false;
  }
  const leg = value as DraftCouponLeg;
  return (
    typeof leg.matchId === "number" &&
    Array.isArray(leg.eventIds) &&
    leg.eventIds.every((id) => typeof id === "number") &&
    typeof leg.odds === "string"
  );
}

function isStakeMode(value: unknown): value is StakeInputMode {
  return STAKE_MODES.some((mode) => mode === value);
}

function isCatalogMatch(value: unknown): value is CatalogMatch {
  if (!value || typeof value !== "object") {
    return false;
  }
  const match = value as CatalogMatch;
  return typeof match.id === "number" && typeof match.home_name === "string";
}

function browserSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}
