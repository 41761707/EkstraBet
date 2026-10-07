import {
  HOCKEY_FAMILY_ORDER,
  hockeyFamilyLabel,
} from "@/lib/hockeyMarketLabels";

export interface EventFilterOption {
  id: number;
  label: string;
  familyName: string;
}

export interface GroupedBetEventOptions {
  popular: EventFilterOption[];
  niche: EventFilterOption[];
}

export interface BetEventFilterSection {
  title: string;
  options: EventFilterOption[];
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

function isHockeyFamily(familyName: string): boolean {
  return familyName.startsWith("HOCKEY_");
}

/** Popular/niche football markets, then each hockey family under its label. */
export function betEventFilterSections(
  events: EventFilterOption[],
): BetEventFilterSection[] {
  const hockey = events.filter((event) => isHockeyFamily(event.familyName));
  const football = events.filter((event) => !isHockeyFamily(event.familyName));
  const grouped = groupBetEventOptions(football);
  const sections: BetEventFilterSection[] = [];
  if (grouped.popular.length > 0) {
    sections.push({ title: "Najpopularniejsze", options: grouped.popular });
  }
  if (grouped.niche.length > 0) {
    sections.push({ title: "Pozostałe", options: grouped.niche });
  }
  for (const familyName of HOCKEY_FAMILY_ORDER) {
    const options = hockey
      .filter((event) => event.familyName === familyName)
      .sort((left, right) => left.label.localeCompare(right.label, "pl"));
    if (options.length > 0) {
      sections.push({ title: hockeyFamilyLabel(familyName), options });
    }
  }
  const known = new Set(HOCKEY_FAMILY_ORDER);
  const otherHockey = hockey.filter((event) => !known.has(event.familyName));
  if (otherHockey.length > 0) {
    sections.push({
      title: "Pozostałe hokej",
      options: [...otherHockey].sort((left, right) =>
        left.label.localeCompare(right.label, "pl"),
      ),
    });
  }
  return sections;
}
