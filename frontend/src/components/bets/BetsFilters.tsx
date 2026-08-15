"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import {
  betsFilterPath,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";
import { navigateSearch } from "@/lib/clientNavigation";
import type {
  BetSortBy,
  BetSortOrder,
  FilterOption,
  SettlementStatus,
} from "@/types/api";

export type { BetsFilterValues };

interface BetsFiltersProps {
  leagues: FilterOption[];
  events: FilterOption[];
  models: FilterOption[];
  values: BetsFilterValues;
}

const inputClassName =
  "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100";

export function BetsFilters({
  leagues,
  events,
  models,
  values,
}: BetsFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: BetsFilterValues) {
    navigateSearch(betsFilterPath(nextState), () => router.refresh());
  }

  function update(partial: Partial<BetsFilterValues>) {
    const nextState = { ...state, ...partial, page: 1 };
    setState(nextState);
    applyFilters(nextState);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters({ ...state, page: 1 });
  }

  function handleReset() {
    const resetState: BetsFilterValues = {
      leagueIds: [],
      eventIds: [],
      modelIds: [],
      matchDate: new Date().toISOString().slice(0, 10),
      fromNow: false,
      minOdds: 1.5,
      positiveEvOnly: false,
      applyTax: false,
      settlementStatus: "",
      sortBy: "ev",
      sortOrder: "desc",
      page: 1,
    };
    setState(resetState);
    navigateSearch("/bets", () => router.refresh());
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="leagues"
          options={leagues}
          selectedIds={state.leagueIds}
          onChange={(leagueIds) =>
            setState((current) => ({ ...current, leagueIds }))
          }
        />
        <MultiSelectCheckboxGroup
          label="Wydarzenia"
          name="events"
          options={events}
          selectedIds={state.eventIds}
          onChange={(eventIds) =>
            setState((current) => ({ ...current, eventIds }))
          }
        />
        <MultiSelectCheckboxGroup
          label="Modele"
          name="models"
          options={models}
          selectedIds={state.modelIds}
          onChange={(modelIds) =>
            setState((current) => ({ ...current, modelIds }))
          }
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Data meczu</span>
          <input
            type="date"
            value={state.matchDate}
            onChange={(event) => update({ matchDate: event.target.value })}
            className={inputClassName}
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Min. kurs</span>
          <input
            type="number"
            min={1}
            max={20}
            step={0.1}
            value={state.minOdds}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                minOdds: Number(event.target.value) || 1,
              }))
            }
            onBlur={(event) => {
              const minOdds = Number(event.target.value) || 1;
              const nextState = { ...state, minOdds, page: 1 };
              setState(nextState);
              applyFilters(nextState);
            }}
            className={inputClassName}
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Sortuj według</span>
          <select
            value={state.sortBy}
            onChange={(event) =>
              update({ sortBy: event.target.value as BetSortBy })
            }
            className={inputClassName}
          >
            <option value="ev">EV</option>
            <option value="probability">Prawdopodobieństwo</option>
            <option value="game_date">Data meczu</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-200">Kolejność</span>
          <select
            value={state.sortOrder}
            onChange={(event) =>
              update({ sortOrder: event.target.value as BetSortOrder })
            }
            className={inputClassName}
          >
            <option value="desc">Malejąco</option>
            <option value="asc">Rosnąco</option>
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-4 text-sm text-slate-200">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.fromNow}
            onChange={(event) => update({ fromNow: event.target.checked })}
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Tylko od teraz
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.positiveEvOnly}
            onChange={(event) =>
              update({ positiveEvOnly: event.target.checked })
            }
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Tylko dodatnie EV
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.applyTax}
            onChange={(event) => update({ applyTax: event.target.checked })}
            className="rounded border-slate-600 bg-slate-800 text-sky-500"
          />
          Uwzględnij podatek 12%
        </label>
      </div>

      <label className="block max-w-xs space-y-2 text-sm">
        <span className="font-medium text-slate-200">Status rozliczenia</span>
        <select
          value={state.settlementStatus}
          onChange={(event) =>
            update({
              settlementStatus: event.target.value as SettlementStatus | "",
            })
          }
          className={inputClassName}
        >
          <option value="">Wszystkie</option>
          <option value="pending">Oczekujący</option>
          <option value="won">Wygrany</option>
          <option value="lost">Przegrany</option>
        </select>
      </label>

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
