import { HorizontalProbabilityBars } from "@/components/charts/HorizontalProbabilityBars";
import { ProbabilityDonutChart } from "@/components/charts/ProbabilityDonutChart";
import { VerticalProbabilityBars } from "@/components/charts/VerticalProbabilityBars";
import {
  buildHockeyPredictionCharts,
  buildHockeyScoreBars,
  type HockeyModelDonuts,
  type HockeyScoreBars,
} from "@/components/matches/hockeyPredictionChartModel";
import {
  formatSegmentProbability,
  type ProbabilitySegmentView,
} from "@/components/predictions/predictionChartModel";
import type { HockeyScoreChart, MatchPredictionItem } from "@/types/api";

const EMPTY_GOAL_DISTRIBUTION = "Brak rozkładu liczby goli.";
const EMPTY_EXACT_SCORES = "Brak najbardziej prawdopodobnych wyników.";

interface HockeyPredictionChartsProps {
  predictions: MatchPredictionItem[];
  homeTeamLabel: string;
  awayTeamLabel: string;
  scoreCharts: HockeyScoreChart[];
}

export function HockeyPredictionCharts({
  predictions,
  homeTeamLabel,
  awayTeamLabel,
  scoreCharts,
}: HockeyPredictionChartsProps) {
  const charts = buildHockeyPredictionCharts(
    predictions,
    homeTeamLabel,
    awayTeamLabel,
  );
  if (charts.length === 0) {
    return null;
  }
  const barsByModel = new Map(
    scoreCharts.map((chart) => [chart.model_id, buildHockeyScoreBars(chart)]),
  );

  return (
    <section className="space-y-6" aria-label="Analiza predykcji">
      <h2 className="text-2xl font-semibold text-text">Analiza predykcji</h2>
      {charts.map((chart) => (
        <ModelDonuts
          key={chart.modelId}
          chart={chart}
          bars={barsByModel.get(chart.modelId) ?? null}
          homeTeamLabel={homeTeamLabel}
          awayTeamLabel={awayTeamLabel}
        />
      ))}
    </section>
  );
}

function ModelDonuts({
  chart,
  bars,
  homeTeamLabel,
  awayTeamLabel,
}: {
  chart: HockeyModelDonuts;
  bars: HockeyScoreBars | null;
  homeTeamLabel: string;
  awayTeamLabel: string;
}) {
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
      {bars ? (
        <ScoreDistribution
          bars={bars}
          homeTeamLabel={homeTeamLabel}
          awayTeamLabel={awayTeamLabel}
        />
      ) : null}
    </div>
  );
}

function ScoreDistribution({
  bars,
  homeTeamLabel,
  awayTeamLabel,
}: {
  bars: HockeyScoreBars;
  homeTeamLabel: string;
  awayTeamLabel: string;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <VerticalProbabilityBars
          title={homeTeamLabel}
          points={bars.home}
          emptyMessage={EMPTY_GOAL_DISTRIBUTION}
        />
        <VerticalProbabilityBars
          title="Liczba goli"
          points={bars.total}
          emptyMessage={EMPTY_GOAL_DISTRIBUTION}
        />
        <VerticalProbabilityBars
          title={awayTeamLabel}
          points={bars.away}
          emptyMessage={EMPTY_GOAL_DISTRIBUTION}
        />
      </div>
      <HorizontalProbabilityBars
        title="Najbardziej prawdopodobne wyniki"
        points={bars.exactScores}
        emptyMessage={EMPTY_EXACT_SCORES}
      />
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
