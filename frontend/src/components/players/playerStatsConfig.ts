import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/lib/playerFilterParams";
import type { PlayerStatKey } from "@/types/api";

export interface PlayerStatDefinition {
  key: PlayerStatKey;
  label: string;
  chartTitle: string;
  defaultLine: number;
  minLine: number;
  maxLine: number;
  step: number;
  hasLineSlider: boolean;
}

export const FOOTBALL_PLAYER_STATS: PlayerStatDefinition[] = [
  {
    key: "goals",
    label: "Bramki",
    chartTitle: "Liczba bramek",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 4,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "assists",
    label: "Asysty",
    chartTitle: "Liczba asyst",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 4,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "shots",
    label: "Strzały",
    chartTitle: "Liczba strzałów",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 10,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "shots_on_target",
    label: "Strzały celne",
    chartTitle: "Liczba strzałów celnych",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 6,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "fouls_conceded",
    label: "Faule",
    chartTitle: "Liczba fauli popełnionych",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 6,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "yellow_cards",
    label: "Żółte kartki",
    chartTitle: "Liczba żółtych kartek",
    defaultLine: 0.5,
    minLine: 0.5,
    maxLine: 0.5,
    step: 0.5,
    hasLineSlider: false,
  },
];

export const HOCKEY_SKATER_PLAYER_STATS: PlayerStatDefinition[] = [
  {
    key: "points",
    label: "Punkty",
    chartTitle: "Liczba punktów",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 4,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "goals",
    label: "Bramki",
    chartTitle: "Liczba bramek",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 4,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "assists",
    label: "Asysty",
    chartTitle: "Liczba asyst",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 4,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "sog",
    label: "Strzały na bramkę",
    chartTitle: "Liczba strzałów na bramkę",
    defaultLine: 1.5,
    minLine: 0,
    maxLine: 6,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "plus_minus",
    label: "Plus/Minus",
    chartTitle: "Plus/Minus",
    defaultLine: 0.5,
    minLine: -3,
    maxLine: 3,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "penalty_minutes",
    label: "Minuty kar",
    chartTitle: "Minuty kar",
    defaultLine: 0.5,
    minLine: 0,
    maxLine: 10,
    step: 0.5,
    hasLineSlider: true,
  },
  {
    key: "toi_minutes",
    label: "Czas na lodzie",
    chartTitle: "Czas na lodzie (minuty)",
    defaultLine: 15,
    minLine: 5,
    maxLine: 25,
    step: 0.5,
    hasLineSlider: true,
  },
];

export const HOCKEY_GOALIE_PLAYER_STATS: PlayerStatDefinition[] = [
  {
    key: "shots_against",
    label: "Strzały na bramkę",
    chartTitle: "Strzały na bramkę bramkarza",
    defaultLine: 28,
    minLine: 0,
    maxLine: 60,
    step: 1,
    hasLineSlider: false,
  },
  {
    key: "shots_saved",
    label: "Obrony",
    chartTitle: "Liczba obron",
    defaultLine: 28,
    minLine: 0,
    maxLine: 60,
    step: 1,
    hasLineSlider: false,
  },
  {
    key: "saves_acc",
    label: "Skuteczność obron (%)",
    chartTitle: "Skuteczność obron (%)",
    defaultLine: 90,
    minLine: 70,
    maxLine: 100,
    step: 0.5,
    hasLineSlider: false,
  },
  {
    key: "toi_minutes",
    label: "Czas na lodzie",
    chartTitle: "Czas na lodzie (minuty)",
    defaultLine: 15,
    minLine: 5,
    maxLine: 65,
    step: 0.5,
    hasLineSlider: false,
  },
];

export const MATCH_LIMIT_OPTIONS = [
  { label: "Cały sezon", value: 50 },
  { label: "Ostatnie 5 meczów", value: 5 },
  { label: "Ostatnie 10 meczów", value: 10 },
  { label: "Ostatnie 15 meczów", value: 15 },
] as const;

export const HOCKEY_MATCH_LIMIT_OPTIONS = [
  { label: "Ostatnie 10 meczów", value: 10 },
  { label: "Ostatnie 5 meczów", value: 5 },
  { label: "Ostatnie 15 meczów", value: 15 },
  { label: "Ostatnie 20 meczów", value: 20 },
  { label: "Cały sezon", value: 200 },
] as const;

export function getMatchLimitOptions(sportId: number) {
  return sportId === HOCKEY_SPORT_ID
    ? HOCKEY_MATCH_LIMIT_OPTIONS
    : MATCH_LIMIT_OPTIONS;
}

export function getConfigurablePlayerStats(sportId: number) {
  return sportId === HOCKEY_SPORT_ID
    ? HOCKEY_SKATER_PLAYER_STATS
    : FOOTBALL_PLAYER_STATS;
}

export function getStatDefinition(
  key: PlayerStatKey,
  sportId: number = FOOTBALL_SPORT_ID,
  playerRole?: "skater" | "goalie",
): PlayerStatDefinition {
  const source =
    sportId === HOCKEY_SPORT_ID && playerRole === "goalie"
      ? HOCKEY_GOALIE_PLAYER_STATS
      : getConfigurablePlayerStats(sportId);
  const definition = source.find((item) => item.key === key);
  if (!definition) {
    throw new Error(`Unknown player stat key: ${key}`);
  }
  return definition;
}
