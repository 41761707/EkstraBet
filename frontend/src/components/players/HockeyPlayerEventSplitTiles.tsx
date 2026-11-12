import type { HockeyPlayerEventSplit } from "@/types/api";

interface EventTile {
  key: keyof HockeyPlayerEventSplit;
  emoji: string;
  label: string;
}

const EVENT_TILES: EventTile[] = [
  { key: "goals", emoji: "🎯", label: "Gole w zdarzeniach" },
  { key: "power_play_goals", emoji: "⚡", label: "W przewadze" },
  { key: "empty_net_goals", emoji: "🥅", label: "Do pustej bramki" },
  { key: "goals_period_1", emoji: "1️⃣", label: "1. tercja" },
  { key: "goals_period_2", emoji: "2️⃣", label: "2. tercja" },
  { key: "goals_period_3", emoji: "3️⃣", label: "3. tercja" },
  { key: "goals_overtime", emoji: "⏱️", label: "Dogrywka" },
  { key: "shootout_goals", emoji: "🏒", label: "Karne" },
  { key: "minor_penalties", emoji: "🟨", label: "Kary mniejsze" },
  { key: "major_penalties", emoji: "🟥", label: "Kary większe" },
  { key: "misconduct_penalties", emoji: "⛔", label: "Kary meczu" },
  {
    key: "unsportsmanlike_penalties",
    emoji: "🚫",
    label: "Kary za niesportowe zachowanie",
  },
  { key: "disallowed_goals", emoji: "❌", label: "Bramki anulowane" },
];

interface HockeyPlayerEventSplitTilesProps {
  split: HockeyPlayerEventSplit;
}

export function HockeyPlayerEventSplitTiles({
  split,
}: HockeyPlayerEventSplitTilesProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {EVENT_TILES.map((tile) => (
        <div
          key={tile.key}
          className="rounded-xl border border-border bg-surface p-4 text-center"
        >
          <div className="text-3xl">{tile.emoji}</div>
          <div className="mt-2 text-3xl font-semibold text-text">
            {split[tile.key]}
          </div>
          <div className="mt-1 text-sm text-muted">{tile.label}</div>
        </div>
      ))}
    </div>
  );
}
