import type { ReactNode } from "react";

import { formatDisplayedRating } from "@/components/matches/hockeyGameRatingModel";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type FootballPlayerStatsSummary,
  type HockeyPlayerStatsSummary,
} from "@/types/api";

interface PlayerSummaryTilesProps {
  sportId: number;
  playerRole?: "skater" | "goalie";
  summary: FootballPlayerStatsSummary | HockeyPlayerStatsSummary;
  averageRating?: number | null;
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
  averageRating,
}: PlayerSummaryTilesProps) {
  if (sportId === HOCKEY_SPORT_ID) {
    const hockeySummary = summary as HockeyPlayerStatsSummary;
    const hockeyTiles =
      playerRole === "goalie" ? hockeyGoalieTiles : hockeySkaterTiles;
    return (
      <SummaryGrid columns={playerRole === "goalie" ? "five" : "eight"}>
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
        {averageRating !== undefined ? (
          <SummaryTile
            emoji="⭐"
            label="Średnia ocena"
            value={
              averageRating === null ? "—" : formatDisplayedRating(averageRating)
            }
          />
        ) : null}
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
  columns: "four" | "five" | "eight";
  children: ReactNode;
}) {
  const className =
    columns === "eight"
      ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8"
      : columns === "five"
        ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
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
    <div className="rounded-xl border border-border bg-surface p-4 text-center">
      <div className="text-3xl">{emoji}</div>
      <div className="mt-2 text-3xl font-semibold text-text">
        {value ?? "-"}
      </div>
      <div className="mt-1 text-sm text-muted">{label}</div>
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
