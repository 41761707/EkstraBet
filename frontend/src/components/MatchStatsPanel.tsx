"use client";

import type { MatchBasicStats } from "@/types/api";

interface MatchStatsPanelProps {
  stats: MatchBasicStats;
  homeTeamName: string;
  awayTeamName: string;
}

interface StatDefinition {
  label: string;
  homeKey: keyof MatchBasicStats;
  awayKey: keyof MatchBasicStats;
  suffix?: string;
  decimals?: number;
}

const statDefinitions: StatDefinition[] = [
  { label: "Bramki", homeKey: "home_goals", awayKey: "away_goals" },
  {
    label: "Expected Goals (xG)",
    homeKey: "home_xg",
    awayKey: "away_xg",
    decimals: 2,
  },
  {
    label: "Posiadanie piłki (%)",
    homeKey: "home_possession",
    awayKey: "away_possession",
    suffix: "%",
  },
  {
    label: "Strzały (wszystkie)",
    homeKey: "home_shots",
    awayKey: "away_shots",
  },
  {
    label: "Strzały na bramkę",
    homeKey: "home_shots_on_goal",
    awayKey: "away_shots_on_goal",
  },
  {
    label: "Rzuty wolne",
    homeKey: "home_free_kicks",
    awayKey: "away_free_kicks",
  },
  {
    label: "Rzuty rożne",
    homeKey: "home_corners",
    awayKey: "away_corners",
  },
  { label: "Spalone", homeKey: "home_offsides", awayKey: "away_offsides" },
  { label: "Faule", homeKey: "home_fouls", awayKey: "away_fouls" },
  {
    label: "Żółte kartki",
    homeKey: "home_yellow_cards",
    awayKey: "away_yellow_cards",
  },
  {
    label: "Czerwone kartki",
    homeKey: "home_red_cards",
    awayKey: "away_red_cards",
  },
];

function formatStatValue(
  value: number | null | undefined,
  suffix?: string,
  decimals?: number,
): string {
  if (value === null || value === undefined) {
    return "Brak danych";
  }
  const formatted =
    decimals !== undefined
      ? value.toFixed(decimals)
      : Number.isInteger(value)
        ? String(value)
        : value.toFixed(2);
  return suffix ? `${formatted}${suffix}` : formatted;
}

function compareValues(
  homeValue: number | null | undefined,
  awayValue: number | null | undefined,
): "home" | "away" | "equal" | "unknown" {
  if (
    homeValue === null ||
    homeValue === undefined ||
    awayValue === null ||
    awayValue === undefined
  ) {
    return "unknown";
  }
  if (homeValue > awayValue) {
    return "home";
  }
  if (awayValue > homeValue) {
    return "away";
  }
  return "equal";
}

function cardClassName(side: "home" | "away", winner: ReturnType<typeof compareValues>) {
  if (winner === "unknown" || winner === "equal") {
    return "border-slate-600/80 bg-slate-800/60 text-white";
  }
  if (winner === side) {
    return "border-emerald-500/40 bg-emerald-950/50 text-emerald-50";
  }
  return "border-rose-500/40 bg-rose-950/40 text-rose-50";
}

function StatCard({
  value,
  label,
  tone,
}: {
  value: string;
  label: string;
  tone: string;
}) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-center shadow-sm ${tone}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="mt-1 text-sm text-slate-300">{label}</div>
    </div>
  );
}

export function MatchStatsPanel({
  stats,
  homeTeamName,
  awayTeamName,
}: MatchStatsPanelProps) {
  const visibleStats = statDefinitions.filter(
    (definition) =>
      stats[definition.homeKey] !== null || stats[definition.awayKey] !== null,
  );

  if (visibleStats.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 items-start gap-4">
        <h3 className="text-right text-lg font-semibold text-white">
          {homeTeamName}
        </h3>
        <h3 className="text-lg font-semibold text-white">{awayTeamName}</h3>
      </div>

      <div className="space-y-3">
        {visibleStats.map((definition) => {
          const homeValue = stats[definition.homeKey];
          const awayValue = stats[definition.awayKey];
          const winner = compareValues(
            typeof homeValue === "number" ? homeValue : null,
            typeof awayValue === "number" ? awayValue : null,
          );

          return (
            <div
              key={definition.label}
              className="grid grid-cols-2 gap-4"
            >
              <StatCard
                value={formatStatValue(
                  typeof homeValue === "number" ? homeValue : null,
                  definition.suffix,
                  definition.decimals,
                )}
                label={definition.label}
                tone={cardClassName("home", winner)}
              />
              <StatCard
                value={formatStatValue(
                  typeof awayValue === "number" ? awayValue : null,
                  definition.suffix,
                  definition.decimals,
                )}
                label={definition.label}
                tone={cardClassName("away", winner)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
