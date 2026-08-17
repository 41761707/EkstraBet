"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  resetLeagueComparisonFilters,
  statsFilterPath,
  type StatsFilterValues,
} from "@/lib/statsFilterParams";
import type { FilterOption } from "@/types/api";

interface LeagueComparisonFiltersProps {
  leagues: FilterOption[];
  seasons: FilterOption[];
  values: StatsFilterValues;
}

const inputClassName =
  "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100";

export function LeagueComparisonFilters({
  leagues,
  seasons,
  values,
}: LeagueComparisonFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: StatsFilterValues) {
    const availableLeagueIds = leagues.map((league) => league.id);
    navigateSearch(
      statsFilterPath(
        {
          ...values,
          compareLeagueIds: nextState.compareLeagueIds,
          compareSeasonId: nextState.compareSeasonId,
        },
        availableLeagueIds,
      ),
      router,
    );
  }

  function update(partial: Partial<StatsFilterValues>) {
    const nextState = { ...state, ...partial };
    setState(nextState);
    applyFilters(nextState);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(state);
  }

  function handleReset() {
    applyFilters(resetLeagueComparisonFilters(state));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="compare-leagues"
          options={leagues}
          selectedIds={state.compareLeagueIds}
          showClearAll
          onChange={(compareLeagueIds) =>
            setState((current) => ({ ...current, compareLeagueIds }))
          }
        />
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Sezon</span>
          <select
            value={state.compareSeasonId ?? ""}
            onChange={(event) =>
              update({
                compareSeasonId: event.target.value
                  ? Number(event.target.value)
                  : null,
              })
            }
            className={inputClassName}
          >
            <option value="">Najnowszy sezon każdej ligi</option>
            {seasons.map((season) => (
              <option key={season.id} value={season.id}>
                {season.label}
              </option>
            ))}
          </select>
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
