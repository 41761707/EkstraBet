import type {
  SeasonProjectionMode,
  SeasonProjectionModeFlags,
  SeasonProjectionStandingRow,
} from "@/types/api";

export const SEASON_PROJECTION_MODE_LABELS: Record<
  SeasonProjectionMode,
  string
> = {
  from_now: "Od ostatniej kolejki",
  from_season_start: "Od początku sezonu",
};

export const PROJECTION_COLUMN_LEGEND: ReadonlyArray<{
  symbol: string;
  meaning: string;
}> = [
  {
    symbol: "#",
    meaning: "Pozycja w naszej projekcji końca sezonu",
  },
  {
    symbol: "Pkt",
    meaning:
      "Aktualne punkty — po ostatniej kolejce albo 0 przy starcie sezonu",
  },
  {
    symbol: "xPts",
    meaning: "Oczekiwane punkty na koniec sezonu (średnia z symulacji)",
  },
  {
    symbol: "SD",
    meaning: "Odchylenie standardowe punktów — miara niepewności",
  },
  {
    symbol: "P05–P95",
    meaning: "Zakres punktów w 90% symulacji",
  },
  {
    symbol: "Min–Max",
    meaning: "Najniższy i najwyższy wynik spośród wszystkich symulacji",
  },
];

/** Whether the section should load available projection mode flags. */
export function shouldFetchProjectionModes(
  isOpen: boolean,
  hasFlags: boolean,
): boolean {
  return isOpen && !hasFlags;
}

/** Whether the section should fetch a projection for the selected mode. */
export function shouldFetchSeasonProjection(
  isOpen: boolean,
  selectedMode: SeasonProjectionMode | null,
  hasDataForMode: boolean,
): boolean {
  return isOpen && selectedMode !== null && !hasDataForMode;
}

export function hasAnyProjectionMode(
  flags: Pick<SeasonProjectionModeFlags, "from_now" | "from_season_start">,
): boolean {
  return flags.from_now || flags.from_season_start;
}

export function defaultSeasonProjectionMode(
  flags: Pick<SeasonProjectionModeFlags, "from_now" | "from_season_start">,
): SeasonProjectionMode | null {
  if (flags.from_now) {
    return "from_now";
  }
  if (flags.from_season_start) {
    return "from_season_start";
  }
  return null;
}

export function availableSeasonProjectionModes(
  flags: Pick<SeasonProjectionModeFlags, "from_now" | "from_season_start">,
): SeasonProjectionMode[] {
  const modes: SeasonProjectionMode[] = [];
  if (flags.from_now) {
    modes.push("from_now");
  }
  if (flags.from_season_start) {
    modes.push("from_season_start");
  }
  return modes;
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

export function probabilityForTablePosition(
  probabilities: number[],
  tablePosition: number,
): number | null {
  const index = tablePosition - 1;
  if (index < 0 || index >= probabilities.length) {
    return null;
  }
  return probabilities[index];
}
