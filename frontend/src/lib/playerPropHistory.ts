const EMPTY_HISTORY_COUNT = "—";

/** Compact hit counter next to the recent-match strip. */
export function formatPropHistoryCount(hits: number, played: number): string {
  if (played === 0) {
    return EMPTY_HISTORY_COUNT;
  }
  return `${hits} na ${played}`;
}
