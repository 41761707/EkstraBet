"use client";

import { useEffect, useState } from "react";
import { ExpandableSection } from "@/components/ExpandableSection";
import { TeamLeagueComparisonChart } from "@/components/charts/TeamLeagueComparisonChart";
import { SignedLeagueProfitChart } from "@/components/stats/SignedLeagueProfitChart";
import type {
  ModelBetProfitLeagueComparison,
  ModelLeagueComparisons,
  ModelPredictionLeagueComparison,
} from "@/types/api";

const STAT_FAMILIES = ["ou", "btts", "result"] as const;
type StatFamily = (typeof STAT_FAMILIES)[number];

const FAMILY_TITLES: Record<StatFamily, string> = {
  ou: "Over/Under",
  btts: "BTTS",
  result: "1X2",
};

const PILL_BUTTON_ACTIVE =
  "rounded-full bg-sky-600 px-3 py-1.5 text-sm text-white transition hover:bg-sky-500";
const PILL_BUTTON_IDLE =
  "rounded-full bg-slate-800 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-700";

interface ModelLeagueComparisonsPanelProps {
  comparisons: ModelLeagueComparisons;
}

interface ModelFamilyPillsProps {
  models: { model_id: number; model_name: string }[];
  selectedModelId: number | null;
  onSelect: (modelId: number) => void;
}

function familiesWithModels<T>(
  families: Record<StatFamily, T[]>,
): StatFamily[] {
  return STAT_FAMILIES.filter((family) => families[family].length > 0);
}

export function ModelFamilyPills({
  models,
  selectedModelId,
  onSelect,
}: ModelFamilyPillsProps) {
  if (models.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {models.map((model) => (
        <button
          key={model.model_id}
          type="button"
          onClick={() => onSelect(model.model_id)}
          className={
            selectedModelId === model.model_id
              ? PILL_BUTTON_ACTIVE
              : PILL_BUTTON_IDLE
          }
          aria-pressed={selectedModelId === model.model_id}
        >
          {model.model_name}
        </button>
      ))}
    </div>
  );
}

function useSelectedModelId(
  modelIds: number[],
): [number | null, (modelId: number) => void] {
  const firstId = modelIds[0] ?? null;
  const idsKey = modelIds.join(",");
  const [selectedId, setSelectedId] = useState<number | null>(firstId);

  useEffect(() => {
    // nowa odpowiedź filtrów wraca do pierwszego modelu rodziny
    setSelectedId(firstId);
  }, [firstId, idsKey]);

  const isSelectedAvailable =
    selectedId !== null && modelIds.includes(selectedId);
  return [isSelectedAvailable ? selectedId : firstId, setSelectedId];
}

function PredictionFamilyBlock({
  family,
  models,
}: {
  family: StatFamily;
  models: ModelPredictionLeagueComparison[];
}) {
  const [selectedId, setSelectedId] = useSelectedModelId(
    models.map((model) => model.model_id),
  );
  const selected =
    models.find((model) => model.model_id === selectedId) ?? models[0];
  if (!selected) {
    return null;
  }

  return (
    <ExpandableSection title={FAMILY_TITLES[family]}>
      <div className="space-y-3">
        <ModelFamilyPills
          models={models}
          selectedModelId={selected.model_id}
          onSelect={setSelectedId}
        />
        <TeamLeagueComparisonChart
          title="Skuteczność (%)"
          leagueAverage={selected.average_accuracy_pct}
          averageLabel="Średnia modelu"
          labelWidthClassName="10rem"
          teams={selected.leagues.map((league) => ({
            teamName: league.league_name,
            value: league.accuracy_pct,
          }))}
        />
      </div>
    </ExpandableSection>
  );
}

function ProfitFamilyBlock({
  family,
  models,
}: {
  family: StatFamily;
  models: ModelBetProfitLeagueComparison[];
}) {
  const [selectedId, setSelectedId] = useSelectedModelId(
    models.map((model) => model.model_id),
  );
  const selected =
    models.find((model) => model.model_id === selectedId) ?? models[0];
  if (!selected) {
    return null;
  }

  return (
    <ExpandableSection title={FAMILY_TITLES[family]}>
      <div className="space-y-3">
        <ModelFamilyPills
          models={models}
          selectedModelId={selected.model_id}
          onSelect={setSelectedId}
        />
        <SignedLeagueProfitChart
          title="Profit (unit)"
          totalProfit={selected.total_profit}
          points={selected.leagues.map((league) => ({
            leagueName: league.league_name,
            profit: league.profit,
            totalBets: league.total_bets,
          }))}
        />
      </div>
    </ExpandableSection>
  );
}

export function ModelLeagueComparisonsPanel({
  comparisons,
}: ModelLeagueComparisonsPanelProps) {
  const predictionFamilies = familiesWithModels(comparisons.predictions);
  const profitFamilies = familiesWithModels(comparisons.bet_profits);
  if (predictionFamilies.length === 0 && profitFamilies.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {predictionFamilies.length > 0 ? (
        <ExpandableSection
          title="Skuteczność predykcji per liga"
          defaultOpen
        >
          <div className="space-y-3">
            <p className="text-sm text-slate-400">
              Wykresy pokazują skuteczność aktywnego modelu w ligach na tle
              średniej ważonej liczbą predykcji. Przełącz model przyciskiem.
            </p>
            {predictionFamilies.map((family) => (
              <PredictionFamilyBlock
                key={`pred-${family}`}
                family={family}
                models={comparisons.predictions[family]}
              />
            ))}
          </div>
        </ExpandableSection>
      ) : null}

      {profitFamilies.length > 0 ? (
        <ExpandableSection
          title="Profit zakładów per liga"
          defaultOpen
        >
          <div className="space-y-3">
            <p className="text-sm text-slate-400">
              Profit to suma unitów (stawka 1) po filtrach EV i podatku. Oś
              zero oddziela zysk od straty.
            </p>
            {profitFamilies.map((family) => (
              <ProfitFamilyBlock
                key={`profit-${family}`}
                family={family}
                models={comparisons.bet_profits[family]}
              />
            ))}
          </div>
        </ExpandableSection>
      ) : null}
    </div>
  );
}
