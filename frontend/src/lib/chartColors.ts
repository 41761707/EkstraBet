/** Semantyczne kolory: nie/poniżej/gość = czerwony, tak/powyżej/gospodarz = zielony, remis = żółty. */

export const CHART_COLOR_NEGATIVE = "#d95757";
export const CHART_COLOR_POSITIVE = "#52b788";
export const CHART_COLOR_DRAW = "#d9b44a";
export const CHART_COLOR_NEUTRAL = "#64748b";

function normalizeLabel(label: string): string {
  return label
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

function isDrawLabel(normalized: string): boolean {
  return (
    normalized.includes("remis") ||
    normalized === "draw" ||
    normalized === "x" ||
    normalized === "remisy"
  );
}

function isAwayWinLabel(normalized: string): boolean {
  return (
    normalized === "away" ||
    normalized === "gosc" ||
    normalized.includes("gosc") ||
    normalized.includes("wygrana goscia") ||
    normalized.includes("away win")
  );
}

function isHomeWinLabel(normalized: string): boolean {
  return (
    normalized === "home" ||
    normalized.includes("gospodarz") ||
    normalized.includes("wygrana gospodarza") ||
    normalized.includes("home win")
  );
}

function isNegativeLabel(normalized: string): boolean {
  return (
    normalized.includes("under") ||
    normalized.includes("ponizej") ||
    normalized.endsWith(" nie") ||
    normalized.startsWith("nie ") ||
    normalized === "nie" ||
    normalized === "no" ||
    normalized.includes("no btts") ||
    normalized === "btts nie" ||
    normalized.includes("incorrect") ||
    normalized.includes("err") ||
    normalized.includes("niepopraw")
  );
}

function isPositiveLabel(normalized: string): boolean {
  return (
    normalized.includes("over") ||
    normalized.includes("powyzej") ||
    normalized.includes("tak") ||
    normalized === "yes" ||
    normalized === "btts" ||
    normalized === "btts tak" ||
    normalized.includes("correct") ||
    normalized.includes("popraw")
  );
}

export function getSemanticBarColor(label: string): string {
  const normalized = normalizeLabel(label);

  if (isDrawLabel(normalized)) {
    return CHART_COLOR_DRAW;
  }
  if (isAwayWinLabel(normalized)) {
    return CHART_COLOR_NEGATIVE;
  }
  if (isHomeWinLabel(normalized)) {
    return CHART_COLOR_POSITIVE;
  }
  if (isNegativeLabel(normalized)) {
    return CHART_COLOR_NEGATIVE;
  }
  if (isPositiveLabel(normalized)) {
    return CHART_COLOR_POSITIVE;
  }

  return CHART_COLOR_NEUTRAL;
}

export function getTeamComparisonBarColor(
  value: number,
  average: number,
): string {
  const delta = value - average;
  if (Math.abs(delta) < 0.05) {
    return CHART_COLOR_DRAW;
  }
  return delta > 0 ? CHART_COLOR_POSITIVE : CHART_COLOR_NEGATIVE;
}
