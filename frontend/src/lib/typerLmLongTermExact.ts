/** Exact-subject helpers for Typer LM long-term markets. */

import {
  areTeamIdSequencesEqual,
  isLongTermMarketLockedForUi,
  MARKET_KIND_FREE_TEXT,
  MARKET_KIND_SINGLE_TEAM,
  MARKET_KIND_YES_NO,
} from "@/lib/typerLmLongTermRanking";
import type { LongTermMarketCard } from "@/types/api";

export const SUBJECT_TEXT_MAX_LENGTH = 160;

export type ExactSubjectPickStatus = "pending" | "hit" | "miss";

export interface LongTermExactPicksDraft {
  subjectText?: string;
  isTextCorrect?: boolean | null;
  teamIds?: readonly number[];
}

/**
 * Trim, collapse whitespace, and lower-case a typed name.
 * JS toLowerCase is a deliberate surrogate for Python casefold — not a full
 * Unicode casefold (ß stays ß here, backend maps it to ss).
 */
export function normalizeSubjectText(raw: string): string {
  return raw.trim().split(/\s+/).join(" ").toLowerCase();
}

/** Return |set(picks) ∩ set(results)| * pointsPerCorrect. */
export function scoreExactSubject<T>(
  pickValues: readonly T[],
  resultValues: readonly T[],
  pointsPerCorrect: number,
): number {
  const resultSet = new Set(resultValues);
  const uniquePicks = new Set(pickValues);
  let hits = 0;
  uniquePicks.forEach((value) => {
    if (resultSet.has(value)) {
      hits += 1;
    }
  });
  return hits * pointsPerCorrect;
}

/**
 * Classify one pick against a result set.
 * For free-text strings both sides must already be normalizeSubjectText
 * output; use classifyFreeTextPick for raw names.
 */
export function classifyExactSubjectPick<T>(
  pick: T,
  results: readonly T[],
): ExactSubjectPickStatus {
  if (results.length === 0) {
    return "pending";
  }
  return results.includes(pick) ? "hit" : "miss";
}

/**
 * Classify a typed name against admin-typed result names.
 * Normalizes both sides the same way as settlement scoring.
 */
export function classifyFreeTextPick(
  pick: string,
  results: readonly string[],
): ExactSubjectPickStatus {
  return classifyExactSubjectPick(
    normalizeSubjectText(pick),
    results.map(normalizeSubjectText),
  );
}

export function canSaveLongTermExactPicks(
  market: LongTermMarketCard,
  draft: LongTermExactPicksDraft,
  isPending: boolean,
  nowMs?: number | null,
): boolean {
  if (isPending || isLongTermMarketLockedForUi(market, nowMs)) {
    return false;
  }
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    return canSaveFreeTextPick(market, draft.subjectText ?? "");
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    return canSaveYesNoPick(market, draft.isTextCorrect);
  }
  if (market.market_kind === MARKET_KIND_SINGLE_TEAM) {
    return canSaveSingleTeamPick(market, draft.teamIds ?? []);
  }
  return false;
}

function canSaveFreeTextPick(
  market: LongTermMarketCard,
  raw: string,
): boolean {
  const stripped = raw.trim();
  const normalized = normalizeSubjectText(raw);
  if (normalized === "") {
    return false;
  }
  if (
    stripped.length > SUBJECT_TEXT_MAX_LENGTH ||
    normalized.length > SUBJECT_TEXT_MAX_LENGTH
  ) {
    return false;
  }
  const saved = normalizeSubjectText(market.picked_subject_text ?? "");
  return normalized !== saved;
}

function canSaveYesNoPick(
  market: LongTermMarketCard,
  value: boolean | null | undefined,
): boolean {
  if (value !== true && value !== false) {
    return false;
  }
  return value !== market.picked_is_text_correct;
}

function canSaveSingleTeamPick(
  market: LongTermMarketCard,
  teamIds: readonly number[],
): boolean {
  if (teamIds.length !== 1) {
    return false;
  }
  return !areTeamIdSequencesEqual(teamIds, market.picked_team_ids);
}
