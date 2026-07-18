import { ExpandableSection } from "@/components/ExpandableSection";
import { bucketsToDistribution } from "@/components/leagues/leagueStatsUtils";
import { DistributionChart } from "@/components/stats/AnalyticsCharts";
import { formatPercent } from "@/lib/format";
import type { ChartDistribution, LeagueCharacteristics } from "@/types/api";

interface LeagueCharacteristicsSectionProps {
  characteristics: LeagueCharacteristics;
  leagueName: string;
}

function BucketTable({
  rows,
}: {
  rows: { label: string; count: number; percentage: number }[];
}) {
  return (
    <ul className="space-y-2 text-sm text-slate-300">
      {rows.map((row) => (
        <li key={row.label} className="flex items-center justify-between">
          <span>{row.label}</span>
          <span>
            {row.count} ({formatPercent(row.percentage)})
          </span>
        </li>
      ))}
    </ul>
  );
}

function DistributionPanel({
  title,
  chartTitle,
  distribution,
  tableRows,
}: {
  title: string;
  chartTitle: string;
  distribution: ChartDistribution;
  tableRows: { label: string; count: number; percentage: number }[];
}) {
  return (
    <ExpandableSection title={title}>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
          <h4 className="mb-3 text-sm font-semibold text-white">Tabela</h4>
          <BucketTable rows={tableRows} />
        </div>
        <DistributionChart data={distribution} title={chartTitle} />
      </div>
    </ExpandableSection>
  );
}

export function LeagueCharacteristicsSection({
  characteristics,
  leagueName,
}: LeagueCharacteristicsSectionProps) {
  const ouDistribution = bucketsToDistribution(
    characteristics.ou,
    ["under_2_5", "over_2_5"],
    (key) => (key === "under_2_5" ? "Poniżej 2.5" : "Powyżej 2.5"),
  );

  const bttsDistribution = bucketsToDistribution(
    characteristics.btts,
    ["no", "yes"],
    (key) => (key === "no" ? "BTTS nie" : "BTTS tak"),
  );

  const resultDistribution = bucketsToDistribution(
    characteristics.result,
    ["away", "draw", "home"],
    (key) => {
      if (key === "home") return "Gospodarz";
      if (key === "draw") return "Remis";
      return "Gość";
    },
  );

  return (
    <ExpandableSection title={`Charakterystyki ligi: ${leagueName}`}>
      <div className="space-y-4">
        <p className="text-sm text-slate-400">
          Do tej pory rozegrano {characteristics.played_matches} meczów.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Rozegrane mecze
            </p>
            <p className="mt-1 text-2xl font-semibold text-white">
              {characteristics.played_matches}
            </p>
          </div>
          <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Średnia bramek / mecz
            </p>
            <p className="mt-1 text-2xl font-semibold text-white">
              {characteristics.avg_goals_per_match.toFixed(2)}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <DistributionPanel
            title="Over/Under 2.5"
            chartTitle="Procentowy rozkład OU w lidze"
            distribution={ouDistribution}
            tableRows={ouDistribution.labels.map((label, index) => ({
              label,
              count: ouDistribution.values[index],
              percentage: ouDistribution.percentages[index],
            }))}
          />

          <DistributionPanel
            title="BTTS"
            chartTitle="Procentowy rozkład BTTS w lidze"
            distribution={bttsDistribution}
            tableRows={bttsDistribution.labels.map((label, index) => ({
              label,
              count: bttsDistribution.values[index],
              percentage: bttsDistribution.percentages[index],
            }))}
          />

          <DistributionPanel
            title="Rezultat 1X2"
            chartTitle="Procentowy rozkład zwycięstw w lidze"
            distribution={resultDistribution}
            tableRows={resultDistribution.labels.map((label, index) => ({
              label,
              count: resultDistribution.values[index],
              percentage: resultDistribution.percentages[index],
            }))}
          />
        </div>
      </div>
    </ExpandableSection>
  );
}
