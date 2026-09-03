export interface EventFilterOption {
  id: number;
  label: string;
  familyName: string;
}

export interface GroupedBetEventOptions {
  popular: EventFilterOption[];
  niche: EventFilterOption[];
}

const POPULAR_FAMILIES = ["OU", "BTTS", "REZULTAT"] as const;
const NICHE_FAMILIES = ["EXACT", "GOALS", "GOALS-6-CLASSES"] as const;

export function isPopularEventFamily(familyName: string): boolean {
  return (POPULAR_FAMILIES as readonly string[]).includes(familyName);
}

export function familyDisplayRank(familyName: string): number {
  const popularIndex = (POPULAR_FAMILIES as readonly string[]).indexOf(
    familyName,
  );
  if (popularIndex >= 0) {
    return popularIndex;
  }
  const nicheIndex = (NICHE_FAMILIES as readonly string[]).indexOf(familyName);
  if (nicheIndex >= 0) {
    return POPULAR_FAMILIES.length + nicheIndex;
  }
  return POPULAR_FAMILIES.length + NICHE_FAMILIES.length;
}

export function compareBetEventOptions(
  left: EventFilterOption,
  right: EventFilterOption,
): number {
  const rankDiff =
    familyDisplayRank(left.familyName) - familyDisplayRank(right.familyName);
  if (rankDiff !== 0) {
    return rankDiff;
  }
  return left.label.localeCompare(right.label, "pl");
}

export function mergeEventFilterOption(
  current: EventFilterOption | undefined,
  next: EventFilterOption,
): EventFilterOption {
  if (!current) {
    return next;
  }
  if (familyDisplayRank(next.familyName) < familyDisplayRank(current.familyName)) {
    return { ...current, familyName: next.familyName };
  }
  return current;
}

export function groupBetEventOptions(
  events: EventFilterOption[],
): GroupedBetEventOptions {
  const sorted = [...events].sort(compareBetEventOptions);
  return {
    popular: sorted.filter((event) => isPopularEventFamily(event.familyName)),
    niche: sorted.filter((event) => !isPopularEventFamily(event.familyName)),
  };
}
