"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import type {
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
  FilterOption,
} from "@/types/api";

export interface StatsFilterValues {
  leagueIds: number[];
  seasonId: number | null;
  modelResultIds: number[];
  modelOuIds: number[];
  modelBttsIds: number[];
  dateFrom: string;
  dateTo: string;
  roundFrom: string;
  roundTo: string;
  statType: AnalyticsStatType;
  settledOnly: boolean;
  positiveEvOnly: boolean;
  applyTax: boolean;
  groupBy: AnalyticsGroupBy;
  aggregationMetric: AnalyticsAggregationMetric;
  includeLeagueCharacteristics: boolean;
}

interface StatsFiltersProps {
  leagues: FilterOption[];
  seasons: FilterOption[];
  resultModels: FilterOption[];
  ouModels: FilterOption[];
  bttsModels: FilterOption[];
  values: StatsFilterValues;
}

const inputClassName =
  "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100";

export function StatsFilters({
  leagues,
  seasons,
  resultModels,
  ouModels,
  bttsModels,
  values,
}: StatsFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: StatsFilterValues) {
    const params = new URLSearchParams();
    if (nextState.leagueIds.length > 0) {
      params.set("league_ids", nextState.leagueIds.join(","));
    }
    if (nextState.seasonId) {
      params.set("season_id", String(nextState.seasonId));
    }
    if (nextState.modelResultIds.length > 0) {
      params.set("model_result_ids", nextState.modelResultIds.join(","));
    }
    if (nextState.modelOuIds.length > 0) {
      params.set("model_ou_ids", nextState.modelOuIds.join(","));
    }
    if (nextState.modelBttsIds.length > 0) {
      params.set("model_btts_ids", nextState.modelBttsIds.join(","));
    }
    if (nextState.dateFrom) {
      params.set("date_from", nextState.dateFrom);
    }
    if (nextState.dateTo) {
      params.set("date_to", nextState.dateTo);
    }
    if (nextState.roundFrom) {
      params.set("round_from", nextState.roundFrom);
    }
    if (nextState.roundTo) {
      params.set("round_to", nextState.roundTo);
    }
    if (nextState.statType !== "all") {
      params.set("stat_type", nextState.statType);
    }
    if (!nextState.settledOnly) {
      params.set("settled_only", "false");
    }
    if (nextState.positiveEvOnly) {
      params.set("positive_ev_only", "true");
    }
    if (nextState.applyTax) {
      params.set("apply_tax", "true");
    }
    if (nextState.groupBy !== "none") {
      params.set("group_by", nextState.groupBy);
    }
    if (nextState.aggregationMetric !== "accuracy") {
      params.set("aggregation_metric", nextState.aggregationMetric);
    }
    if (nextState.includeLeagueCharacteristics) {
      params.set("include_league_characteristics", "true");
    }

    const query = params.toString();
    router.push(query ? `/stats?${query}` : "/stats");
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(state);
  }

  function handleReset() {
    router.push("/stats");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="stats-leagues"
          options={leagues}
          selectedIds={state.leagueIds}
          onChange={(leagueIds) =>
            setState((current) => ({ ...current, leagueIds }))
          }
        />
        <MultiSelectCheckboxGroup
          label="Modele rezultatu"
          name="stats-result-models"
          options={resultModels}
          selectedIds={state.modelResultIds}
          onChange={(modelResultIds) =>
            setState((current) => ({ ...current, modelResultIds }))
          }
        />
        <MultiSelectCheckboxGroup
          label="Modele OU"
          name="stats-ou-models"
          options={ouModels}
          selectedIds={state.modelOuIds}
          onChange={(modelOuIds) =>
            setState((current) => ({ ...current, modelOuIds }))
          }
        />
        <MultiSelectCheckboxGroup
          label="Modele BTTS"
          name="stats-btts-models"
          options={bttsModels}
          selectedIds={state.modelBttsIds}
          onChange={(modelBttsIds) =>
            setState((current) => ({ ...current, modelBttsIds }))
          }
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Sezon</span>
          <select
            value={state.seasonId ?? ""}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                seasonId: event.target.value
                  ? Number(event.target.value)
                  : null,
              }))
            }
            className={inputClassName}
          >
            <option value="">Wszystkie sezony</option>
            {seasons.map((season) => (
              <option key={season.id} value={season.id}>
                {season.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Typ statystyki</span>
          <select
            value={state.statType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                statType: event.target.value as AnalyticsStatType,
              }))
            }
            className={inputClassName}
          >
            <option value="all">Wszystkie</option>
            <option value="ou">Over/Under</option>
            <option value="btts">BTTS</option>
            <option value="result">1X2</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Grupuj według</span>
          <select
            value={state.groupBy}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                groupBy: event.target.value as AnalyticsGroupBy,
              }))
            }
            className={inputClassName}
          >
            <option value="none">Brak</option>
            <option value="league">Liga</option>
            <option value="team">Drużyna (jedna liga)</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Metryka agregacji</span>
          <select
            value={state.aggregationMetric}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                aggregationMetric:
                  event.target.value as AnalyticsAggregationMetric,
              }))
            }
            className={inputClassName}
          >
            <option value="accuracy">Trafność</option>
            <option value="profit">Zysk</option>
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Data od</span>
          <input
            type="date"
            value={state.dateFrom}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                dateFrom: event.target.value,
              }))
            }
            className={inputClassName}
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Data do</span>
          <input
            type="date"
            value={state.dateTo}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                dateTo: event.target.value,
              }))
            }
            className={inputClassName}
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Kolejka od</span>
          <input
            type="number"
            min={1}
            value={state.roundFrom}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                roundFrom: event.target.value,
              }))
            }
            className={inputClassName}
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Kolejka do</span>
          <input
            type="number"
            min={1}
            value={state.roundTo}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                roundTo: event.target.value,
              }))
            }
            className={inputClassName}
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-4 text-sm text-slate-200">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.settledOnly}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                settledOnly: event.target.checked,
              }))
            }
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Tylko rozliczone mecze
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.positiveEvOnly}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                positiveEvOnly: event.target.checked,
              }))
            }
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Tylko dodatnie EV
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.applyTax}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                applyTax: event.target.checked,
              }))
            }
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Uwzględnij podatek 12%
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.includeLeagueCharacteristics}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                includeLeagueCharacteristics: event.target.checked,
              }))
            }
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Charakterystyka ligi
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
        >
          Zastosuj filtry
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
        >
          Resetuj
        </button>
      </div>
    </form>
  );
}
