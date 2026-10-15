import type {
  HockeyGoalsDistribution,
  SportLeagueStatRow,
} from "@/types/api";

export interface StatHighlight {
  label: string;
  value: string;
  detail: string | null;
}

export interface GoalBucketView {
  id: string;
  label: string;
  count: number;
  piePercent: number;
}

export interface TeamBarPoint {
  label: string;
  value: number;
  title: string;
}

type NumericStatKey = "avg_for" | "avg_against" | "over_5_5_pct";

const GOAL_BUCKET_DEFS: {
  id: string;
  label: string;
  field: keyof HockeyGoalsDistribution;
}[] = [
  { id: "under_5", label: "Mniej niż 5", field: "under_5" },
  { id: "exactly_5", label: "Dokładnie 5", field: "exactly_5" },
  { id: "exactly_6", label: "Dokładnie 6", field: "exactly_6" },
  { id: "exactly_7", label: "Dokładnie 7", field: "exactly_7" },
  { id: "over_7", label: "8+", field: "over_7" },
];

export function mean(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  const total = values.reduce((sum, value) => sum + value, 0);
  return total / values.length;
}

/** Integer percents that sum to 100, using the largest remainder. */
export function integerShares(counts: number[]): number[] {
  const total = counts.reduce((sum, count) => sum + count, 0);
  if (total <= 0) {
    return counts.map(() => 0);
  }
  const exact = counts.map((count) => (count * 100) / total);
  const floors = exact.map((value) => Math.floor(value));
  let leftover = 100 - floors.reduce((sum, value) => sum + value, 0);
  const order = exact
    .map((value, index) => ({
      index,
      fraction: value - Math.floor(value),
    }))
    .sort(
      (left, right) =>
        right.fraction - left.fraction || left.index - right.index,
    );
  const shares = [...floors];
  for (const entry of order) {
    if (leftover <= 0) {
      break;
    }
    shares[entry.index] += 1;
    leftover -= 1;
  }
  return shares;
}

export function over55Count(distribution: HockeyGoalsDistribution): number {
  return (
    distribution.exactly_6 + distribution.exactly_7 + distribution.over_7
  );
}

export function over65Count(distribution: HockeyGoalsDistribution): number {
  return distribution.exactly_7 + distribution.over_7;
}

export function goalBucketViews(
  distribution: HockeyGoalsDistribution,
): GoalBucketView[] {
  const counts = GOAL_BUCKET_DEFS.map((bucket) => distribution[bucket.field]);
  const shares = integerShares(counts);
  return GOAL_BUCKET_DEFS.map((bucket, index) => ({
    id: bucket.id,
    label: bucket.label,
    count: counts[index],
    piePercent: shares[index],
  }));
}

export function sortBestFirst<T extends { value: number }>(
  points: T[],
  higherIsBetter: boolean,
): T[] {
  return [...points].sort((left, right) =>
    higherIsBetter ? right.value - left.value : left.value - right.value,
  );
}

function numericValue(
  row: SportLeagueStatRow,
  key: NumericStatKey,
): number | null {
  const value = row[key];
  if (value === null || value === undefined || Number.isNaN(value)) {
    return null;
  }
  return value;
}

function extremeRow(
  rows: SportLeagueStatRow[],
  key: NumericStatKey,
  pick: "max" | "min",
): { row: SportLeagueStatRow; value: number } | null {
  let best: { row: SportLeagueStatRow; value: number } | null = null;
  for (const row of rows) {
    const value = numericValue(row, key);
    if (value === null) {
      continue;
    }
    const isBetter =
      best === null ||
      (pick === "max" ? value > best.value : value < best.value);
    if (isBetter) {
      best = { row, value };
    }
  }
  return best;
}

function formatAverage(value: number): string {
  return value.toFixed(2);
}

function formatRate(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function averageHighlights(
  rows: SportLeagueStatRow[],
  kind: "shots" | "goals",
): StatHighlight[] {
  const forValues = rows
    .map((row) => numericValue(row, "avg_for"))
    .filter((value): value is number => value !== null);
  const leagueAverage = mean(forValues);
  const bestFor = extremeRow(rows, "avg_for", "max");
  const bestAgainst = extremeRow(rows, "avg_against", "min");
  const forLabel =
    kind === "shots"
      ? "Najwyższa średnia strzałów celnych drużyny"
      : "Najwyższa średnia bramek zdobytych";
  const againstLabel =
    kind === "shots"
      ? "Najniższa średnia strzałów celnych przeciw"
      : "Najniższa średnia bramek straconych";
  const leagueLabel =
    kind === "shots"
      ? "Średnia ligowa strzałów na mecz"
      : "Średnia ligowa bramek na mecz";
  const items: StatHighlight[] = [];
  if (bestFor) {
    items.push({
      label: forLabel,
      value: formatAverage(bestFor.value),
      detail: bestFor.row.team_name,
    });
  }
  if (bestAgainst) {
    items.push({
      label: againstLabel,
      value: formatAverage(bestAgainst.value),
      detail: bestAgainst.row.team_name,
    });
  }
  if (leagueAverage !== null) {
    items.push({
      label: leagueLabel,
      value: formatAverage(leagueAverage),
      detail: null,
    });
  }
  return items;
}

export function teamBarPoints(
  rows: SportLeagueStatRow[],
  key: NumericStatKey,
): TeamBarPoint[] {
  const points: TeamBarPoint[] = [];
  for (const row of rows) {
    const value = numericValue(row, key);
    if (value === null) {
      continue;
    }
    const shortcut = row.team_shortcut.trim();
    points.push({
      label: shortcut || row.team_name,
      value,
      title: row.team_name,
    });
  }
  return points;
}

export function leagueAverage(
  rows: SportLeagueStatRow[],
  key: NumericStatKey,
): number | null {
  const values = rows
    .map((row) => numericValue(row, key))
    .filter((value): value is number => value !== null);
  return mean(values);
}

function shareLabel(count: number, total: number): string {
  if (total <= 0) {
    return "0 (0%)";
  }
  const percent = (count / total) * 100;
  return `${count} (${percent.toFixed(1)}%)`;
}

export function overUnderHighlights(
  rows: SportLeagueStatRow[],
  distribution: HockeyGoalsDistribution | null | undefined,
): StatHighlight[] {
  const items: StatHighlight[] = [];
  const total = distribution?.total_matches ?? 0;
  if (distribution && total > 0) {
    items.push({
      label: "Over 5.5 w meczach ligi",
      value: shareLabel(over55Count(distribution), total),
      detail: "Co najmniej 6 bramek",
    });
    items.push({
      label: "Over 6.5 w meczach ligi",
      value: shareLabel(over65Count(distribution), total),
      detail: "Co najmniej 7 bramek",
    });
  }
  const best = extremeRow(rows, "over_5_5_pct", "max");
  const worst = extremeRow(rows, "over_5_5_pct", "min");
  const average = leagueAverage(rows, "over_5_5_pct");
  if (best) {
    items.push({
      label: "Najwyższy % Over 5.5",
      value: formatRate(best.value),
      detail: best.row.team_name,
    });
  }
  if (worst) {
    items.push({
      label: "Najniższy % Over 5.5",
      value: formatRate(worst.value),
      detail: worst.row.team_name,
    });
  }
  if (average !== null) {
    items.push({
      label: "Średni % Over 5.5 w lidze",
      value: formatRate(average),
      detail: null,
    });
  }
  return items;
}
