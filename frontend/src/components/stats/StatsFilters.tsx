"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DateInput } from "@/components/filters/DateInput";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  resetModelStatsFilters,
  statsFilterPath,
  type StatsFilterValues,
} from "@/lib/statsFilterParams";
import type {
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
  FilterOption,
} from "@/types/api";

export type { StatsFilterValues };

interface StatsFiltersProps {
  leagues: FilterOption[];
  seasons: FilterOption[];
  resultModels: FilterOption[];
  ouModels: FilterOption[];
  bttsModels: FilterOption[];
  values: StatsFilterValues;
}

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;

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
    const availableLeagueIds = leagues.map((league) => league.id);
    navigateSearch(
      statsFilterPath(
        {
          ...nextState,
          compareLeagueIds: values.compareLeagueIds,
          compareSeasonId: values.compareSeasonId,
        },
        availableLeagueIds,
      ),
      router,
    );
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(state);
  }

  function handleReset() {
    const resetState = resetModelStatsFilters({
      ...state,
      compareLeagueIds: values.compareLeagueIds,
      compareSeasonId: values.compareSeasonId,
    });
    setState(resetState);
    applyFilters(resetState);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="stats-leagues"
          options={leagues}
          selectedIds={state.leagueIds}
          showClearAll
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
          <span className="font-medium text-text">Sezon</span>
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
            className={FILTER_INPUT_CLASS_NAME}
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
          <span className="font-medium text-text">Typ statystyki</span>
          <select
            value={state.statType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                statType: event.target.value as AnalyticsStatType,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
          >
            <option value="all">Wszystkie</option>
            <option value="ou">Over/Under</option>
            <option value="btts">BTTS</option>
            <option value="result">1X2</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Grupuj według</span>
          <select
            value={state.groupBy}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                groupBy: event.target.value as AnalyticsGroupBy,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
          >
            <option value="none">Brak</option>
            <option value="league">Liga</option>
            <option value="team">Drużyna (jedna liga)</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Sposoby agregacji</span>
          <select
            value={state.aggregationMetric}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                aggregationMetric:
                  event.target.value as AnalyticsAggregationMetric,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
          >
            <option value="accuracy">Skuteczność</option>
            <option value="profit">Zysk</option>
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-2 text-sm">
          <span className="font-medium text-text">Data od</span>
          <DateInput
            value={state.dateFrom}
            onChange={(dateFrom) =>
              setState((current) => ({ ...current, dateFrom }))
            }
            ariaLabel="Data od"
          />
        </div>
        <div className="space-y-2 text-sm">
          <span className="font-medium text-text">Data do</span>
          <DateInput
            value={state.dateTo}
            onChange={(dateTo) =>
              setState((current) => ({ ...current, dateTo }))
            }
            ariaLabel="Data do"
          />
        </div>
        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Kolejka od</span>
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
            className={FILTER_INPUT_CLASS_NAME}
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Kolejka do</span>
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
            className={FILTER_INPUT_CLASS_NAME}
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-4 text-sm text-text">
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
            className="rounded border-border bg-surface-muted text-accent-text"
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
            className="rounded border-border bg-surface-muted text-accent-text"
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
            className="rounded border-border bg-surface-muted text-accent-text"
          />
          Uwzględnij podatek 12%
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-hover"
        >
          Zastosuj filtry
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-lg border border-border px-4 py-2 text-sm text-text transition hover:bg-surface-muted"
        >
          Resetuj
        </button>
      </div>
    </form>
  );
}
