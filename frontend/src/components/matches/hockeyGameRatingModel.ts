import type {
  HockeyRatedPlayer,
  HockeyRatingParts,
} from "@/types/api";

export type HockeyRatingMetric = "total" | "offense" | "defense";

export interface GroupedRatingRows {
  forward: HockeyRatedPlayer[];
  defense: HockeyRatedPlayer[];
  goalie: HockeyRatedPlayer[];
}

const CHART_GROUP_ORDER: readonly HockeyRatedPlayer["group"][] = [
  "forward",
  "defense",
  "goalie",
];

const RATING_SCALE_FLOOR = 1;

// minus z protokołu (U+2212), nie dywiz z klawiatury
const RATING_MINUS = "\u2212";

const RATING_PART_LABELS: readonly {
  key: keyof HockeyRatingParts;
  label: string;
}[] = [
  { key: "production", label: "produkcja" },
  { key: "empty_net", label: "pusta bramka" },
  { key: "shots", label: "strzały" },
  { key: "teammate_goals", label: "gole kolegów" },
  { key: "faceoffs", label: "wznowienia" },
  { key: "goals_against", label: "bramki stracone" },
  { key: "penalties", label: "kary" },
  { key: "blocks", label: "bloki" },
  { key: "goaltending", label: "bramkarz" },
];

/** Forward, defense and goalie lists, each sorted for one chart. */
export function groupRatingRows(
  players: readonly HockeyRatedPlayer[],
  metric: HockeyRatingMetric,
): GroupedRatingRows {
  const grouped: GroupedRatingRows = {
    forward: [],
    defense: [],
    goalie: [],
  };
  for (const player of players) {
    grouped[player.group].push(player);
  }
  for (const group of CHART_GROUP_ORDER) {
    grouped[group].sort((left, right) =>
      compareByMetric(left, right, metric),
    );
  }
  return grouped;
}

/** Shared bar scale for one team. Never below 1. */
export function ratingScale(players: readonly HockeyRatedPlayer[]): number {
  let scale = RATING_SCALE_FLOOR;
  for (const player of players) {
    scale = Math.max(
      scale,
      Math.abs(player.total),
      Math.abs(player.offense),
      Math.abs(player.defense),
    );
  }
  return scale;
}

/** One decimal: `+3.2`, `−1.4`, or unsigned `0.0`. */
export function formatRating(value: number): string {
  const text = value.toFixed(1);
  if (text === "0.0" || text === "-0.0") {
    return "0.0";
  }
  if (text.startsWith("-")) {
    return `${RATING_MINUS}${text.slice(1)}`;
  }
  return `+${text}`;
}

/** Polish title of the non-zero leaves, in protocol order. */
export function ratingTooltip(parts: HockeyRatingParts): string {
  const chunks: string[] = [];
  for (const item of RATING_PART_LABELS) {
    if (parts[item.key] === 0) {
      continue;
    }
    chunks.push(`${item.label} ${formatRating(parts[item.key])}`);
  }
  if (chunks.length === 0) {
    return "";
  }
  const [first, ...rest] = chunks;
  return [capitalizeLabel(first), ...rest].join(", ");
}

function compareByMetric(
  left: HockeyRatedPlayer,
  right: HockeyRatedPlayer,
  metric: HockeyRatingMetric,
): number {
  if (left[metric] !== right[metric]) {
    return right[metric] - left[metric];
  }
  // zwykłe porównanie kodów, bez locale
  if (left.player_name < right.player_name) {
    return -1;
  }
  if (left.player_name > right.player_name) {
    return 1;
  }
  return 0;
}

function capitalizeLabel(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1);
}
