"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DateInput } from "@/components/filters/DateInput";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  defaultSportDateRange,
  sportLeaguePath,
  type SportLeagueFilters,
} from "@/lib/sportLeagueParams";

interface SportLeagueDateFilterProps {
  leagueSlug: string;
  filters: SportLeagueFilters;
}

export function SportLeagueDateFilter({
  leagueSlug,
  filters,
}: SportLeagueDateFilterProps) {
  const router = useRouter();
  const [state, setState] = useState(filters);

  function apply(nextState: SportLeagueFilters) {
    navigateSearch(sportLeaguePath(leagueSlug, nextState), router);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    apply(state);
  }

  function handleReset() {
    const { from, to } = defaultSportDateRange();
    const resetState: SportLeagueFilters = {
      ...state,
      dateFilter: true,
      dateFrom: from,
      dateTo: to,
    };
    setState(resetState);
    apply(resetState);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4"
    >
      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={state.dateFilter}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              dateFilter: event.target.checked,
            }))
          }
          className="rounded border-slate-600 bg-slate-900"
        />
        Filtruj po dacie
      </label>

      {state.dateFilter ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Od</span>
            <DateInput
              value={state.dateFrom}
              onChange={(dateFrom) =>
                setState((current) => ({ ...current, dateFrom }))
              }
              ariaLabel="Data od"
            />
          </div>
          <div className="space-y-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Do</span>
            <DateInput
              value={state.dateTo}
              onChange={(dateTo) =>
                setState((current) => ({ ...current, dateTo }))
              }
              ariaLabel="Data do"
            />
          </div>
        </div>
      ) : null}

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
