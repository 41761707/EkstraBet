import type { SeasonProjectionStandingRow } from "@/types/api";

/** Whether the section should start a network fetch for the projection. */
export function shouldFetchSeasonProjection(
  isOpen: boolean,
  hasData: boolean,
): boolean {
  return isOpen && !hasData;
}

/** Stable sort by expected position, then team_id as tie-break. */
export function sortStandingsByExpectedPosition(
  standings: SeasonProjectionStandingRow[],
): SeasonProjectionStandingRow[] {
  return [...standings].sort((left, right) => {
    if (left.expected_position !== right.expected_position) {
      return left.expected_position - right.expected_position;
    }
    return left.team_id - right.team_id;
  });
}

export function formatProjectionPoints(value: number): string {
  return value.toFixed(1);
}
