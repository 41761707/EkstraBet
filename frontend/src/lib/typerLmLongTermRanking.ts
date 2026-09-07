/** Ranked-table helpers for Typer LM long-term markets. */

import { hasWarsawNaiveDateTimePassed } from "@/lib/date";

export const MARKET_KIND_RANKED_TEAM_TABLE = "ranked_team_table";
export const MARKET_KIND_SINGLE_TEAM = "single_team";
export const MARKET_KIND_FREE_TEXT = "free_text";
export const MARKET_KIND_YES_NO = "yes_no";
export const SCORING_KIND_ZONE_AND_POSITION = "zone_and_position";
export const SCORING_KIND_EXACT_SUBJECT = "exact_subject";

export type RankedTableZone = "top" | "middle" | "bot";
export type RankedPickClassification = "pending" | "miss" | "zone" | "exact";

/** Return the scoring zone for a 1-based table slot. */
export function zoneForPosition(
  position: number,
  selectionSize: number,
  topZoneSize: number,
  botZoneSize: number,
): RankedTableZone {
  // -1 i 0 oznaczają brak strefy (kolumny rynku nieużywane)
  if (topZoneSize > 0 && position <= topZoneSize) {
    return "top";
  }
  if (botZoneSize > 0 && position > selectionSize - botZoneSize) {
    return "bot";
  }
  return "middle";
}

/** Move one team to another slot; remaining tiles keep relative order. */
export function moveTeamInRanking(
  teamIds: readonly number[],
  fromIndex: number,
  toIndex: number,
): number[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= teamIds.length ||
    toIndex >= teamIds.length
  ) {
    return [...teamIds];
  }
  const next = [...teamIds];
  const [moved] = next.splice(fromIndex, 1);
  if (moved === undefined) {
    return [...teamIds];
  }
  next.splice(toIndex, 0, moved);
  return next;
}

/** Compare two table sequences; order is part of the pick. */
export function areTeamIdSequencesEqual(
  left: readonly number[],
  right: readonly number[],
): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((id, index) => id === right[index]);
}

/**
 * Score a ranked table. Middle slots never score.
 * Same zone -> pointsPerZone; same position -> plus exact bonus.
 */
export function scoreZoneAndPosition(
  pickTeamIds: readonly number[],
  resultTeamIds: readonly number[],
  pointsPerZone: number,
  pointsPerExactPosition: number,
  topZoneSize: number,
  botZoneSize: number,
): number {
  const selectionSize = pickTeamIds.length;
  const resultPositions = new Map<number, number>();
  resultTeamIds.forEach((teamId, index) => {
    resultPositions.set(teamId, index + 1);
  });
  let total = 0;
  pickTeamIds.forEach((teamId, index) => {
    const pickPosition = index + 1;
    const pickZone = zoneForPosition(
      pickPosition,
      selectionSize,
      topZoneSize,
      botZoneSize,
    );
    if (pickZone === "middle") {
      return;
    }
    // join po team_id: ta sama drużyna może stać na innym miejscu
    const resultPosition = resultPositions.get(teamId);
    if (resultPosition === undefined) {
      return;
    }
    const resultZone = zoneForPosition(
      resultPosition,
      selectionSize,
      topZoneSize,
      botZoneSize,
    );
    if (resultZone !== pickZone) {
      return;
    }
    total += pointsPerZone;
    if (resultPosition === pickPosition) {
      total += pointsPerExactPosition;
    }
  });
  return total;
}

/** Classify one ranked-table tile after settlement. */
export function classifyRankedPick(
  teamId: number,
  pickPosition: number,
  resultTeamIds: readonly number[],
  selectionSize: number,
  topZoneSize: number,
  botZoneSize: number,
): RankedPickClassification {
  if (resultTeamIds.length === 0) {
    return "pending";
  }
  const pickZone = zoneForPosition(
    pickPosition,
    selectionSize,
    topZoneSize,
    botZoneSize,
  );
  if (pickZone === "middle") {
    return "miss";
  }
  const resultPosition = resultTeamIds.indexOf(teamId) + 1;
  if (resultPosition === 0) {
    return "miss";
  }
  const resultZone = zoneForPosition(
    resultPosition,
    selectionSize,
    topZoneSize,
    botZoneSize,
  );
  if (resultZone !== pickZone) {
    return "miss";
  }
  if (resultPosition === pickPosition) {
    return "exact";
  }
  return "zone";
}

/** True when the server flag or the local Warsaw deadline has locked typing. */
export function isLongTermMarketLockedForUi(
  market: { is_locked: boolean; deadline_at: string | null },
  nowMs?: number | null,
): boolean {
  if (market.is_locked) {
    return true;
  }
  if (nowMs == null || market.deadline_at == null) {
    return false;
  }
  return hasWarsawNaiveDateTimePassed(market.deadline_at, new Date(nowMs));
}
