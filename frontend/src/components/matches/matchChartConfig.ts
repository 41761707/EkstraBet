export const MATCH_H2H_DEFAULT = 5;
export const MATCH_H2H_MIN = 0;
export const MATCH_H2H_MAX = 10;

export const MATCH_LOOKBACK_DEFAULT = 10;
export const MATCH_LOOKBACK_MIN = 5;
export const MATCH_LOOKBACK_MAX = 15;

export const MATCH_OU_LINE_MIN = 0.5;
export const MATCH_OU_LINE_MAX = 4.5;
export const MATCH_OU_LINE_STEP = 0.5;
export const MATCH_OU_LINE_DEFAULT = 2.5;

export function resolveMatchLookbackBounds(matchCount: number): {
  min: number;
  max: number;
  defaultValue: number;
} {
  if (matchCount <= 0) {
    return { min: 0, max: 0, defaultValue: 0 };
  }

  const max = Math.min(matchCount, MATCH_LOOKBACK_MAX);
  const min = Math.min(MATCH_LOOKBACK_MIN, max);
  const defaultValue = Math.min(MATCH_LOOKBACK_DEFAULT, max);

  return { min, max, defaultValue };
}
