import {
  matchCardHasProbabilities,
  type FootballMatchCard,
} from "@/components/matches/matchCardModel";

/**
 * Płótno 1080 px oglądane na szerokości telefonu (~390 px) skaluje się ~0,36 raza.
 * Dlatego bloki i wiersze są wysokie: po otwarciu PNG napis zostaje przy ~13 px.
 */
export const MATCH_CARD_METRICS = {
  width: 1080,
  margin: 48,
  gap: 24,
  pad: 32,
  header: 380,
  footer: 80,
  probTitle: 56,
  probBlock: 140,
  scoreBlock: 168,
  probPad: 28,
  probEmpty: 148,
  h2hHead: 148,
  row: 76,
  sectionTail: 32,
  h2hStats: 268,
  h2hEmpty: 160,
  formHead: 152,
  formEmpty: 168,
} as const;

export const MATCH_CARD_INNER_LEFT = MATCH_CARD_METRICS.margin + MATCH_CARD_METRICS.pad;
export const MATCH_CARD_INNER_WIDTH =
  MATCH_CARD_METRICS.width - MATCH_CARD_INNER_LEFT * 2;

export interface MatchCardFrame {
  width: number;
  height: number;
  probabilitiesY: number;
  probabilitiesHeight: number;
  headToHeadY: number;
  headToHeadHeight: number;
  homeFormY: number;
  homeFormHeight: number;
  awayFormY: number;
  awayFormHeight: number;
}

export function layoutMatchCard(card: FootballMatchCard): MatchCardFrame {
  const probabilitiesHeight = probabilitySectionHeight(card);
  const headToHeadHeight = headToHeadSectionHeight(card.headToHead.rows.length);
  const homeFormHeight = stackedHeight(
    card.homeForm.rows.length,
    MATCH_CARD_METRICS.formHead,
    MATCH_CARD_METRICS.formEmpty,
  );
  const awayFormHeight = stackedHeight(
    card.awayForm.rows.length,
    MATCH_CARD_METRICS.formHead,
    MATCH_CARD_METRICS.formEmpty,
  );
  const probabilitiesY = MATCH_CARD_METRICS.header + MATCH_CARD_METRICS.gap;
  const headToHeadY = probabilitiesY + probabilitiesHeight + MATCH_CARD_METRICS.gap;
  const homeFormY = headToHeadY + headToHeadHeight + MATCH_CARD_METRICS.gap;
  const awayFormY = homeFormY + homeFormHeight + MATCH_CARD_METRICS.gap;
  const height = awayFormY + awayFormHeight + MATCH_CARD_METRICS.footer;
  return {
    width: MATCH_CARD_METRICS.width,
    height,
    probabilitiesY,
    probabilitiesHeight,
    headToHeadY,
    headToHeadHeight,
    homeFormY,
    homeFormHeight,
    awayFormY,
    awayFormHeight,
  };
}

export function matchCardNameFontSize(name: string): number {
  if (name.length <= 14) {
    return 64;
  }
  if (name.length <= 22) {
    return 52;
  }
  if (name.length <= 28) {
    return 44;
  }
  return 36;
}

function probabilitySectionHeight(card: FootballMatchCard): number {
  if (!matchCardHasProbabilities(card)) {
    return MATCH_CARD_METRICS.probEmpty;
  }
  const blocks = [card.result, card.btts, card.overUnder].filter(
    (block) => block !== null,
  ).length;
  const scores = card.topScores.length > 0 ? MATCH_CARD_METRICS.scoreBlock : 0;
  return (
    MATCH_CARD_METRICS.probPad
    + MATCH_CARD_METRICS.probTitle
    + blocks * MATCH_CARD_METRICS.probBlock
    + scores
    + MATCH_CARD_METRICS.probPad
  );
}

function headToHeadSectionHeight(rowCount: number): number {
  if (rowCount <= 0) {
    return MATCH_CARD_METRICS.h2hEmpty;
  }
  return (
    MATCH_CARD_METRICS.h2hHead
    + rowCount * MATCH_CARD_METRICS.row
    + MATCH_CARD_METRICS.h2hStats
  );
}

function stackedHeight(rowCount: number, head: number, empty: number): number {
  if (rowCount <= 0) {
    return empty;
  }
  return head + rowCount * MATCH_CARD_METRICS.row + MATCH_CARD_METRICS.sectionTail;
}
