"use client";

import { HorizontalProbabilityBars } from "@/components/charts/HorizontalProbabilityBars";
import { ProbabilityDonutChart } from "@/components/charts/ProbabilityDonutChart";
import { VerticalProbabilityBars } from "@/components/charts/VerticalProbabilityBars";
import {
  buildPredictionChartModel,
  formatSegmentProbability,
} from "@/components/predictions/predictionChartModel";
import type { PredictionPreviewResponse } from "@/types/api";

interface PredictionSimulationResultProps {
  result: PredictionPreviewResponse;
  homeTeamLabel: string;
  awayTeamLabel: string;
  title?: string;
}

export function PredictionSimulationResult({
  result,
  homeTeamLabel,
  awayTeamLabel,
  title = "Wynik symulacji",
}: PredictionSimulationResultProps) {
  const chart = buildPredictionChartModel(result, homeTeamLabel, awayTeamLabel);
  const hasExpectedGoals =
    chart.lambdaHome > 0 || chart.lambdaAway > 0;

  return (
    <section className="space-y-4" aria-live="polite">
      <h2 className="text-2xl font-semibold text-white">{title}</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <ProbabilityDonutChart
          title="Rezultat 1X2"
          segments={chart.result1x2}
          ariaLabel={`1X2: ${homeTeamLabel} ${formatSegmentProbability(result.result.p_home)}, remis ${formatSegmentProbability(result.result.p_draw)}, ${awayTeamLabel} ${formatSegmentProbability(result.result.p_away)}`}
        />
        <ProbabilityDonutChart
          title="Obie strzelą"
          segments={chart.btts}
          ariaLabel={`BTTS: tak ${formatSegmentProbability(result.btts.p_yes)}, nie ${formatSegmentProbability(result.btts.p_no)}`}
        />
        <ProbabilityDonutChart
          title="Suma 2,5 gola"
          segments={chart.overUnder}
          ariaLabel={`Over/Under 2.5: powyżej ${formatSegmentProbability(result.goals.over_25)}, poniżej ${formatSegmentProbability(result.goals.under_25)}`}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <VerticalProbabilityBars
          title="Liczba goli"
          points={chart.goalBuckets}
          emptyMessage="Brak rozkładu liczby goli."
        />
        <HorizontalProbabilityBars
          title="Najbardziej prawdopodobne wyniki"
          points={chart.exactScores}
          emptyMessage="Brak najbardziej prawdopodobnych wyników."
        />
      </div>
      {hasExpectedGoals ? (
        <p className="text-sm text-slate-400">
          Oczekiwane gole: gospodarze {chart.lambdaHome.toFixed(2)}, goście{" "}
          {chart.lambdaAway.toFixed(2)}.
        </p>
      ) : null}
    </section>
  );
}
