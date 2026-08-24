import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import {
  DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
  type PredictionExampleFixture,
} from "@/lib/modelOutcomeExample";
import type { PredictionPreviewResponse } from "@/types/api";

interface PredictionOutcomeExampleProps {
  fixture?: PredictionExampleFixture;
}

function fixtureToPreview(
  fixture: PredictionExampleFixture,
): PredictionPreviewResponse {
  return {
    result: fixture.result,
    btts: fixture.btts,
    goals: {
      lambda_home: fixture.goals.lambda_home,
      lambda_away: fixture.goals.lambda_away,
      total_buckets: fixture.goals.total_buckets,
      over_25: fixture.goals.over_25,
      under_25: fixture.goals.under_25,
      top_exact_scores: fixture.goals.top_exact_scores,
    },
  };
}

function PlayedBetterWalkthrough() {
  return (
    <section
      className="space-y-3 rounded-xl border border-border bg-surface p-4"
      aria-labelledby="played-better-walkthrough-heading"
    >
      <h3
        id="played-better-walkthrough-heading"
        className="text-base font-semibold text-text"
      >
        Osobno: ocena jakości gry po meczu
      </h3>
      <p className="text-sm leading-relaxed text-muted">
        Modele PLAYED_BETTER nie wynikają z samego rezultatu bramkowego.
        Wejściem są statystyki pomeczowe (strzały, posiadanie, rożne, kartki…),
        a wyjściem trzy prawdopodobieństwa: kto zagrał lepiej lub remis jakości.
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
        <li>
          <span className="font-medium text-text">V1 (z xG)</span> —
          wymaga dodatniego xG obu drużyn; bez xG mecz jest pomijany.
        </li>
        <li>
          <span className="font-medium text-text">NOXG</span> — celowo bez
          xG; działa, gdy expected goals są niedostępne.
        </li>
      </ul>
    </section>
  );
}

/** Static educational charts for a fixed pre-match prediction example. */
export function PredictionOutcomeExample({
  fixture = DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
}: PredictionOutcomeExampleProps) {
  const preview = fixtureToPreview(fixture);

  return (
    <section className="space-y-6" aria-labelledby="outcome-example-heading">
      <div className="space-y-2">
        <h2
          id="outcome-example-heading"
          className="text-xl font-semibold text-text sm:text-2xl"
        >
          Przykładowa predykcja przedmeczowa
        </h2>
        <p className="max-w-3xl text-sm leading-relaxed text-muted">
          Ilustracja kształtu predykcji: jak wyglądają wyjścia modeli 1X2, BTTS
          i goli (Poisson) dla jednego meczu.
        </p>
      </div>

      <PredictionSimulationResult
        result={preview}
        homeTeamLabel={fixture.homeTeamLabel}
        awayTeamLabel={fixture.awayTeamLabel}
        title="Prawdopodobieństwa modeli (przykład edukacyjny)"
      />

      <PlayedBetterWalkthrough />
    </section>
  );
}
