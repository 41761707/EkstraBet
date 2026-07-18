import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/lib/playerFilterParams";
import type { ReactNode } from "react";
import type {
  FootballPlayerStatsSummary,
  HockeyPlayerStatsSummary,
} from "@/types/api";

interface PlayerSummaryTilesProps {
  sportId: number;
  playerRole?: "skater" | "goalie";
  summary: FootballPlayerStatsSummary | HockeyPlayerStatsSummary;
}

const tiles = [
  { emoji: "🎯", key: "goals", label: "Bramki" },
  { emoji: "🍎", key: "assists", label: "Asysty" },
  { emoji: "🏹", key: "shots", label: "Strzały" },
  { emoji: "🎯", key: "shots_on_target", label: "Strzały celne" },
] as const;

const hockeySkaterTiles = [
  { emoji: "📄", key: "points", label: "Punkty" },
  { emoji: "🎯", key: "goals", label: "Bramki" },
  { emoji: "🍎", key: "assists", label: "Asysty" },
  { emoji: "➕➖", key: "plus_minus", label: "Plus minus" },
  { emoji: "⏱️", key: "penalty_minutes", label: "Minuty kar" },
  { emoji: "🕓", key: "average_toi", label: "Średni czas na lodzie" },
  { emoji: "🏒", key: "average_sog", label: "Strzały celne na mecz" },
] as const;

const hockeyGoalieTiles = [
  { emoji: "🎯", key: "shots_against", label: "Średnia liczba strzałów" },
  { emoji: "🛡️", key: "shots_saved", label: "Średnia liczba obron" },
  { emoji: "📊", key: "saves_acc", label: "Średnia skuteczność obron" },
  { emoji: "🕓", key: "average_toi", label: "Średni czas na lodzie" },
] as const;

export function PlayerSummaryTiles({
  sportId,
  playerRole,
  summary,
}: PlayerSummaryTilesProps) {
  if (sportId === HOCKEY_SPORT_ID) {
    const hockeySummary = summary as HockeyPlayerStatsSummary;
    const hockeyTiles =
      playerRole === "goalie" ? hockeyGoalieTiles : hockeySkaterTiles;
    return (
      <SummaryGrid columns={playerRole === "goalie" ? "four" : "seven"}>
        {hockeyTiles.map((tile) => (
          <SummaryTile
            key={tile.key}
            emoji={tile.emoji}
            label={tile.label}
            value={formatSummaryValue(
              hockeySummary[tile.key],
              tile.key === "saves_acc",
            )}
          />
        ))}
      </SummaryGrid>
    );
  }

  if (sportId !== FOOTBALL_SPORT_ID) {
    return null;
  }

  const footballSummary = summary as FootballPlayerStatsSummary;
  return (
    <SummaryGrid columns="four">
      {tiles.map((tile) => (
        <SummaryTile
          key={tile.key}
          emoji={tile.emoji}
          label={tile.label}
          value={footballSummary[tile.key]}
        />
      ))}
    </SummaryGrid>
  );
}

function SummaryGrid({
  columns,
  children,
}: {
  columns: "four" | "seven";
  children: ReactNode;
}) {
  const className =
    columns === "seven"
      ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7"
      : "grid gap-3 sm:grid-cols-2 xl:grid-cols-4";
  return <div className={className}>{children}</div>;
}

function SummaryTile({
  emoji,
  label,
  value,
}: {
  emoji: string;
  label: string;
  value: string | number | null;
}) {
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-900/50 p-4 text-center">
      <div className="text-3xl">{emoji}</div>
      <div className="mt-2 text-3xl font-semibold text-white">
        {value ?? "-"}
      </div>
      <div className="mt-1 text-sm text-slate-400">{label}</div>
    </div>
  );
}

function formatSummaryValue(
  value: string | number | null,
  isPercentage: boolean,
): string | number | null {
  if (value === null) {
    return null;
  }
  return isPercentage ? `${value}%` : value;
}
