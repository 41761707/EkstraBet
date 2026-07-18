import type { ChartDistribution } from "@/types/api";

export function bucketsToDistribution(
  buckets: Record<string, { count: number; percentage: number }>,
  keys: string[],
  labelForKey: (key: string) => string,
): ChartDistribution {
  return {
    labels: keys.map(labelForKey),
    values: keys.map((key) => buckets[key]?.count ?? 0),
    percentages: keys.map((key) => buckets[key]?.percentage ?? 0),
  };
}

export function winRatePercentage(wins: number, played: number): number {
  if (played <= 0) {
    return 0;
  }
  return Math.round((wins * 10000) / played) / 100;
}
