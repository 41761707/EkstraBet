import { HOCKEY_SPORT_ID } from "@/types/api";

export const HOCKEY_STAT_OPTIONS = [
  "Bramki",
  "Bramki w pierwszej tercji",
  "Bramki drużyny/przeciwników",
  "Strzały celne",
  "Rezultaty",
] as const;

export const BASKETBALL_STAT_OPTIONS = [
  "Punkty",
  "Punkty drużyny/przeciwników",
  "Rezultaty",
] as const;

export const HOCKEY_DEFAULT_STATS = [...HOCKEY_STAT_OPTIONS];
export const BASKETBALL_DEFAULT_STATS = [
  "Punkty",
  "Punkty drużyny/przeciwników",
  "Rezultaty",
];

export function defaultOuLine(sportId: number): number {
  return sportId === HOCKEY_SPORT_ID ? 5.5 : 220.5;
}

export function ouLineBounds(sportId: number): {
  min: number;
  max: number;
  step: number;
} {
  if (sportId === HOCKEY_SPORT_ID) {
    return { min: 4, max: 8, step: 0.5 };
  }
  return { min: 180, max: 260, step: 0.5 };
}

export const SPORT_LOOKBACK_MIN = 5;
export const SPORT_LOOKBACK_MAX = 15;
export const SPORT_LOOKBACK_DEFAULT = 10;
