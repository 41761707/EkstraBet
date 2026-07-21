"use client";

import type { PredictionPreviewResponse } from "@/types/api";

interface PredictionSimulationResultProps {
  result: PredictionPreviewResponse;
}

function formatProbability(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function PredictionSimulationResult({
  result,
}: PredictionSimulationResultProps) {
  const sortedBuckets = Object.entries(result.goals.total_buckets).sort(
    ([left], [right]) => left.localeCompare(right, "pl", { numeric: true }),
  );

  return (
    <section className="space-y-4" aria-live="polite">
      <h2 className="text-2xl font-semibold text-white">Wynik symulacji</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <ResultCard
          title="Rezultat 1X2"
          values={[
            ["Gospodarz", result.result.p_home],
            ["Remis", result.result.p_draw],
            ["Gość", result.result.p_away],
          ]}
        />
        <ResultCard
          title="Obie strzelą"
          values={[
            ["Tak", result.btts.p_yes],
            ["Nie", result.btts.p_no],
          ]}
        />
        <ResultCard
          title="Suma 2,5 gola"
          values={[
            ["Powyżej", result.goals.over_25],
            ["Poniżej", result.goals.under_25],
          ]}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ResultCard
          title="Liczba goli"
          values={sortedBuckets.map(([bucket, probability]) => [
            bucket,
            probability,
          ])}
        />
        <ResultCard
          title="Najbardziej prawdopodobne wyniki"
          values={result.goals.top_exact_scores.map((score) => [
            score.score,
            score.probability,
          ])}
        />
      </div>
      <p className="text-sm text-slate-400">
        Oczekiwane gole: gospodarze {result.goals.lambda_home.toFixed(2)}, goście{" "}
        {result.goals.lambda_away.toFixed(2)}.
      </p>
    </section>
  );
}

interface ResultCardProps {
  title: string;
  values: (string | number)[][];
}

function ResultCard({ title, values }: ResultCardProps) {
  return (
    <article className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
      <h3 className="mb-3 font-semibold text-sky-300">{title}</h3>
      <dl className="space-y-2">
        {values.map(([label, value]) => (
          <div key={String(label)} className="flex justify-between gap-4">
            <dt className="text-slate-300">{label}</dt>
            <dd className="font-medium text-white">
              {formatProbability(Number(value))}
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
