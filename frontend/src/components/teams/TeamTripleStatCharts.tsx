import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import type {
  TeamMatchStatChartDefinition,
  TeamMatchStatThresholds,
} from "@/components/teams/teamMatchStatsConfig";
import type { TeamSeasonMatchPoint } from "@/types/api";

interface TeamTripleStatChartsProps {
  teamName: string;
  chartMatches: TeamSeasonMatchPoint[];
  buildLabel: (match: TeamSeasonMatchPoint) => string;
  definition: TeamMatchStatChartDefinition;
  thresholdLines: TeamMatchStatThresholds;
}

export function TeamTripleStatCharts({
  teamName,
  chartMatches,
  buildLabel,
  definition,
  thresholdLines,
}: TeamTripleStatChartsProps) {
  const labels = chartMatches.map((match) => buildLabel(match));

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <VerticalStatChart
        title={definition.teamChartTitle}
        playerName={teamName}
        thresholdLine={thresholdLines.team}
        points={chartMatches.map((match, index) => ({
          label: labels[index],
          value: definition.teamValue(match),
        }))}
      />
      <VerticalStatChart
        title={definition.opponentChartTitle}
        playerName={teamName}
        thresholdLine={thresholdLines.opponent}
        points={chartMatches.map((match, index) => ({
          label: labels[index],
          value: definition.opponentValue(match),
        }))}
      />
      <VerticalStatChart
        title={definition.totalChartTitle}
        playerName="Razem"
        thresholdLine={thresholdLines.total}
        points={chartMatches.map((match, index) => ({
          label: labels[index],
          value: definition.totalValue(match),
        }))}
      />
    </div>
  );
}
