"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  sportLeaguePath,
  type SportLeagueFilters,
} from "@/lib/sportLeagueParams";

interface SportLeagueDateFilterProps {
  leagueSlug: string;
  filters: SportLeagueFilters;
}

const inputClassName =
  "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100";

export function SportLeagueDateFilter({
  leagueSlug,
  filters,
}: SportLeagueDateFilterProps) {
  const router = useRouter();
  const [state, setState] = useState(filters);

  function apply(nextState: SportLeagueFilters) {
    router.push(sportLeaguePath(leagueSlug, nextState));
  }

  function update(partial: Partial<SportLeagueFilters>) {
    const nextState = { ...state, ...partial };
    setState(nextState);
    apply(nextState);
  }

  return (
    <section className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={state.dateFilter}
          onChange={(event) =>
            update({ dateFilter: event.target.checked })
          }
          className="rounded border-slate-600 bg-slate-900"
        />
        Filtruj po dacie
      </label>

      {state.dateFilter ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Od</span>
            <input
              type="date"
              className={inputClassName}
              value={state.dateFrom}
              onChange={(event) =>
                update({ dateFrom: event.target.value })
              }
            />
          </label>
          <label className="space-y-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Do</span>
            <input
              type="date"
              className={inputClassName}
              value={state.dateTo}
              onChange={(event) =>
                update({ dateTo: event.target.value })
              }
            />
          </label>
        </div>
      ) : null}
    </section>
  );
}
