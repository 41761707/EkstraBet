import { ProbabilityDonutChart } from "@/components/charts/ProbabilityDonutChart";
import {
  buildHockeyPredictionCharts,
  type HockeyModelDonuts,
} from "@/components/matches/hockeyPredictionChartModel";
import {
  formatSegmentProbability,
  type ProbabilitySegmentView,
} from "@/components/predictions/predictionChartModel";
import type { MatchPredictionItem } from "@/types/api";

interface HockeyPredictionChartsProps {
  predictions: MatchPredictionItem[];
  homeTeamLabel: string;
  awayTeamLabel: string;
}

export function HockeyPredictionCharts({
  predictions,
  homeTeamLabel,
  awayTeamLabel,
}: HockeyPredictionChartsProps) {
  const charts = buildHockeyPredictionCharts(
    predictions,
    homeTeamLabel,
    awayTeamLabel,
  );
  if (charts.length === 0) {
    return null;
  }

  return (
    <section className="space-y-6" aria-label="Analiza predykcji">
      <h2 className="text-2xl font-semibold text-text">Analiza predykcji</h2>
      {charts.map((chart) => (
        <ModelDonuts key={chart.modelId} chart={chart} />
      ))}
    </section>
  );
}

function ModelDonuts({ chart }: { chart: HockeyModelDonuts }) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-text">{chart.modelName}</h3>
      <div className="grid gap-4 md:grid-cols-3">
        {chart.winner.length > 0 ? (
          <ProbabilityDonutChart
            title="Zwycięzca (OT/SO)"
            segments={chart.winner}
            ariaLabel={segmentsAria("Zwycięzca", chart.winner)}
          />
        ) : null}
        {chart.total55.length > 0 ? (
          <ProbabilityDonutChart
            title="Suma 5,5 gola"
            segments={chart.total55}
            ariaLabel={segmentsAria("Suma 5,5", chart.total55)}
          />
        ) : null}
        {chart.total65.length > 0 ? (
          <ProbabilityDonutChart
            title="Suma 6,5 gola"
            segments={chart.total65}
            ariaLabel={segmentsAria("Suma 6,5", chart.total65)}
          />
        ) : null}
      </div>
    </div>
  );
}

function segmentsAria(
  prefix: string,
  segments: ProbabilitySegmentView[],
): string {
  const parts = segments.map(
    (segment) =>
      `${segment.label} ${formatSegmentProbability(segment.probability)}`,
  );
  return `${prefix}: ${parts.join(", ")}`;
}
