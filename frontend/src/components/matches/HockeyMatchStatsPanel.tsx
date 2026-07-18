"use client";

import type { HockeyMatchStats } from "@/types/api";

interface HockeyMatchStatsPanelProps {
  stats: HockeyMatchStats;
  homeTeamName: string;
  awayTeamName: string;
}

interface StatDefinition {
  label: string;
  homeKey: keyof HockeyMatchStats;
  awayKey: keyof HockeyMatchStats;
  suffix?: string;
  decimals?: number;
  lowerIsBetter?: boolean;
}

const statDefinitions: StatDefinition[] = [
  { label: "Bramki", homeKey: "home_goals", awayKey: "away_goals" },
  {
    label: "Strzały na bramkę",
    homeKey: "home_shots_on_goal",
    awayKey: "away_shots_on_goal",
  },
  {
    label: "Minuty kar",
    homeKey: "home_penalty_minutes",
    awayKey: "away_penalty_minutes",
    lowerIsBetter: true,
  },
  {
    label: "Liczba kar",
    homeKey: "home_penalties",
    awayKey: "away_penalties",
    lowerIsBetter: true,
  },
  {
    label: "Bramki w przewadze (PP)",
    homeKey: "home_pp_goals",
    awayKey: "away_pp_goals",
  },
  {
    label: "Bramki w osłabieniu (SH)",
    homeKey: "home_sh_goals",
    awayKey: "away_sh_goals",
  },
  {
    label: "Skuteczność strzałów (%)",
    homeKey: "home_shots_accuracy",
    awayKey: "away_shots_accuracy",
    suffix: "%",
    decimals: 1,
  },
  {
    label: "Liczba obron",
    homeKey: "home_saves",
    awayKey: "away_saves",
  },
  {
    label: "Skuteczność obron (%)",
    homeKey: "home_saves_accuracy",
    awayKey: "away_saves_accuracy",
    suffix: "%",
    decimals: 1,
  },
  {
    label: "Skuteczność w przewadze (%)",
    homeKey: "home_pp_accuracy",
    awayKey: "away_pp_accuracy",
    suffix: "%",
    decimals: 1,
  },
  {
    label: "Skuteczność w osłabieniu (%)",
    homeKey: "home_pk_accuracy",
    awayKey: "away_pk_accuracy",
    suffix: "%",
    decimals: 1,
  },
  {
    label: "Wygrane wznowienia",
    homeKey: "home_faceoffs_won",
    awayKey: "away_faceoffs_won",
  },
  {
    label: "Skuteczność wznowień (%)",
    homeKey: "home_faceoffs_accuracy",
    awayKey: "away_faceoffs_accuracy",
    suffix: "%",
    decimals: 1,
  },
  {
    label: "Liczba uderzeń",
    homeKey: "home_hits",
    awayKey: "away_hits",
  },
  {
    label: "Liczba strat",
    homeKey: "home_turnovers",
    awayKey: "away_turnovers",
    lowerIsBetter: true,
  },
  {
    label: "Bramki na pustą bramkę",
    homeKey: "home_empty_net_goals",
    awayKey: "away_empty_net_goals",
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
        : value.toFixed(1);
  return suffix ? `${formatted}${suffix}` : formatted;
}

function compareValues(
  homeValue: number | null | undefined,
  awayValue: number | null | undefined,
  lowerIsBetter = false,
): "home" | "away" | "equal" | "unknown" {
  if (
    homeValue === null ||
    homeValue === undefined ||
    awayValue === null ||
    awayValue === undefined
  ) {
    return "unknown";
  }
  if (homeValue === awayValue) {
    return "equal";
  }
  if (lowerIsBetter) {
    return homeValue < awayValue ? "home" : "away";
  }
  return homeValue > awayValue ? "home" : "away";
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

export function HockeyMatchStatsPanel({
  stats,
  homeTeamName,
  awayTeamName,
}: HockeyMatchStatsPanelProps) {
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
            definition.lowerIsBetter,
          );

          return (
            <div key={definition.label} className="grid grid-cols-2 gap-4">
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
