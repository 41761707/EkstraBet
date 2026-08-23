"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
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

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;

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

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(state);
  }

  function handleReset() {
    const resetState = resetLeagueComparisonFilters(state);
    setState(resetState);
    applyFilters(resetState);
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
          <span className="font-medium text-text">Sezon</span>
          <select
            value={state.compareSeasonId ?? ""}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                compareSeasonId: event.target.value
                  ? Number(event.target.value)
                  : null,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
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
