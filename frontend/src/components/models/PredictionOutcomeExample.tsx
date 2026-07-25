"use client";

import { useId, useState } from "react";

import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import { formatProbability } from "@/lib/format";
import {
  calculateAccuracy,
  DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
  MAX_EXAMPLE_GOALS,
  MIN_EXAMPLE_GOALS,
  settleExamplePredictions,
  validateExampleGoals,
  type AccuracyChange,
  type PredictionExampleFixture,
  type PredictionSettlement,
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

function formatAccuracy(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return formatProbability(value);
}

function GoalsInputs({
  homeGoals,
  awayGoals,
  homeLabel,
  awayLabel,
  onHomeChange,
  onAwayChange,
  errorMessage,
}: {
  homeGoals: number;
  awayGoals: number;
  homeLabel: string;
  awayLabel: string;
  onHomeChange: (value: number) => void;
  onAwayChange: (value: number) => void;
  errorMessage: string | null;
}) {
  const homeId = useId();
  const awayId = useId();
  const errorId = useId();

  return (
    <fieldset className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/50 p-4">
      <legend className="px-1 text-sm font-semibold text-sky-300">
        Wynik meczu (symulacja rozliczenia)
      </legend>
      <p className="text-sm text-slate-400">
        Zmiana wyniku aktualizuje wyłącznie Hit/Miss i przykładowe accuracy.
        Prawdopodobieństwa modelu pozostają bez zmian.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-2 text-sm text-slate-300" htmlFor={homeId}>
          <span className="block font-medium">Gole — {homeLabel}</span>
          <input
            id={homeId}
            type="number"
            inputMode="numeric"
            min={MIN_EXAMPLE_GOALS}
            max={MAX_EXAMPLE_GOALS}
            step={1}
            value={homeGoals}
            aria-invalid={errorMessage ? true : undefined}
            aria-describedby={errorMessage ? errorId : undefined}
            onChange={(event) => onHomeChange(Number(event.target.value))}
            className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
          />
        </label>
        <label className="space-y-2 text-sm text-slate-300" htmlFor={awayId}>
          <span className="block font-medium">Gole — {awayLabel}</span>
          <input
            id={awayId}
            type="number"
            inputMode="numeric"
            min={MIN_EXAMPLE_GOALS}
            max={MAX_EXAMPLE_GOALS}
            step={1}
            value={awayGoals}
            aria-invalid={errorMessage ? true : undefined}
            aria-describedby={errorMessage ? errorId : undefined}
            onChange={(event) => onAwayChange(Number(event.target.value))}
            className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
          />
        </label>
      </div>
      {errorMessage ? (
        <p id={errorId} className="text-sm text-red-300" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </fieldset>
  );
}

function SettlementTable({
  settlements,
}: {
  settlements: PredictionSettlement[];
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-left text-sm text-slate-300">
        <caption className="sr-only">
          Rozliczenie przykładowych predykcji Hit lub Miss
        </caption>
        <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-3 font-medium">
              Rynek
            </th>
            <th scope="col" className="px-3 py-3 font-medium">
              Predykcja
            </th>
            <th scope="col" className="px-3 py-3 font-medium">
              Fakt
            </th>
            <th scope="col" className="px-3 py-3 font-medium">
              Wynik
            </th>
          </tr>
        </thead>
        <tbody>
          {settlements.map((settlement) => {
            const isHit = settlement.outcome === "hit";
            return (
              <tr
                key={settlement.marketId}
                className="border-t border-slate-700/70"
              >
                <th
                  scope="row"
                  className="px-3 py-3 font-medium text-slate-100"
                >
                  {settlement.marketLabel}
                </th>
                <td className="px-3 py-3">
                  {settlement.predictedLabel}
                  <span className="ml-2 font-mono text-xs text-slate-500">
                    {formatProbability(settlement.probability)}
                  </span>
                </td>
                <td className="px-3 py-3">{settlement.actualLabel}</td>
                <td className="px-3 py-3">
                  <span
                    className={
                      isHit
                        ? "rounded-full border border-emerald-500/40 bg-emerald-950/40 px-2 py-0.5 text-xs font-semibold text-emerald-200"
                        : "rounded-full border border-rose-500/40 bg-rose-950/30 px-2 py-0.5 text-xs font-semibold text-rose-200"
                    }
                  >
                    {isHit ? "Hit" : "Miss"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AccuracyPanel({ change }: { change: AccuracyChange }) {
  return (
    <div
      className="grid gap-3 rounded-xl border border-slate-700/80 bg-slate-900/50 p-4 sm:grid-cols-2"
      aria-live="polite"
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Accuracy przed
        </p>
        <p className="mt-1 text-lg font-semibold text-white">
          {formatAccuracy(change.accuracyBefore)}
        </p>
        <p className="text-xs text-slate-400">
          {change.correctBefore}/{change.totalBefore} trafień
        </p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Accuracy po rozliczeniu
        </p>
        <p className="mt-1 text-lg font-semibold text-sky-200">
          {formatAccuracy(change.accuracyAfter)}
        </p>
        <p className="text-xs text-slate-400">
          {change.correctAfter}/{change.totalAfter} (+{change.hitsAdded} Hit, +
          {change.missesAdded} Miss)
        </p>
      </div>
    </div>
  );
}

function PlayedBetterWalkthrough() {
  return (
    <section
      className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4"
      aria-labelledby="played-better-walkthrough-heading"
    >
      <h3
        id="played-better-walkthrough-heading"
        className="text-base font-semibold text-white"
      >
        Osobno: ocena jakości gry po meczu
      </h3>
      <p className="text-sm leading-relaxed text-slate-300">
        Modele PLAYED_BETTER nie rozliczają się z samego wyniku bramkowego.
        Wejściem są statystyki pomeczowe (strzały, posiadanie, rożne, kartki…),
        a wyjściem trzy prawdopodobieństwa: kto zagrał lepiej lub remis jakości.
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
        <li>
          <span className="font-medium text-slate-100">V1 (z xG)</span> —
          wymaga dodatniego xG obu drużyn; bez xG mecz jest pomijany.
        </li>
        <li>
          <span className="font-medium text-slate-100">NOXG</span> — celowo bez
          xG; działa, gdy expected goals są niedostępne.
        </li>
      </ul>
      <p className="text-sm text-slate-400">
        Zmiana wyniku powyżej nie uruchamia ponownie PLAYED_BETTER — to ocenia
        jakość gry, nie koryguje historycznych predykcji przedmeczowych.
      </p>
    </section>
  );
}

export function PredictionOutcomeExample({
  fixture = DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
}: PredictionOutcomeExampleProps) {
  const [homeGoals, setHomeGoals] = useState(1);
  const [awayGoals, setAwayGoals] = useState(1);
  const preview = fixtureToPreview(fixture);
  const validation = validateExampleGoals(homeGoals, awayGoals);

  let settlements: PredictionSettlement[] = [];
  let accuracy: AccuracyChange | null = null;
  if (validation.valid) {
    settlements = settleExamplePredictions(homeGoals, awayGoals, fixture);
    accuracy = calculateAccuracy(
      fixture.baselineCorrect,
      fixture.baselineTotal,
      settlements,
    );
  }

  return (
    <section className="space-y-6" aria-labelledby="outcome-example-heading">
      <div className="space-y-2">
        <h2
          id="outcome-example-heading"
          className="text-xl font-semibold text-white sm:text-2xl"
        >
          Jak wynik rozlicza predykcję?
        </h2>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-400">
          Poniższy przykład pokazuje, że historyczna predykcja (wykresy) jest
          niezmienna. Po meczu aktualizujemy tylko wskaźniki Hit/Miss oraz
          przykładowe accuracy — bez ponownego liczenia modelu.
        </p>
      </div>

      <PredictionSimulationResult
        result={preview}
        homeTeamLabel={fixture.homeTeamLabel}
        awayTeamLabel={fixture.awayTeamLabel}
        title="Niezmienne prawdopodobieństwa (przykład edukacyjny)"
      />

      <GoalsInputs
        homeGoals={homeGoals}
        awayGoals={awayGoals}
        homeLabel={fixture.homeTeamLabel}
        awayLabel={fixture.awayTeamLabel}
        onHomeChange={setHomeGoals}
        onAwayChange={setAwayGoals}
        errorMessage={validation.valid ? null : validation.message}
      />

      {validation.valid && accuracy ? (
        <>
          <SettlementTable settlements={settlements} />
          <AccuracyPanel change={accuracy} />
        </>
      ) : null}

      <PlayedBetterWalkthrough />
    </section>
  );
}
