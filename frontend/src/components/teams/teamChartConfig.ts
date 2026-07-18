export const TEAM_OU_LINE_MIN = 0.5;
export const TEAM_OU_LINE_MAX = 4.5;
export const TEAM_OU_LINE_STEP = 0.5;
export const TEAM_OU_LINE_DEFAULT = 2.5;

export const TEAM_LOOKBACK_MIN = 5;

export function resolveLookbackBounds(matchCount: number): {
  min: number;
  max: number;
  defaultValue: number;
} {
  if (matchCount <= 0) {
    return { min: 0, max: 0, defaultValue: 0 };
  }

  const max = matchCount;
  const min = Math.min(TEAM_LOOKBACK_MIN, max);
  return {
    min,
    max,
    defaultValue: max,
  };
}
