"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DateInput } from "@/components/filters/DateInput";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
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

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;

export function BetsFilters({
  leagues,
  events,
  models,
  values,
}: BetsFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: BetsFilterValues) {
    navigateSearch(betsFilterPath(nextState), router);
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
    navigateSearch("/bets", router);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="leagues"
          options={leagues}
          selectedIds={state.leagueIds}
          showClearAll
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
        <div className="space-y-2 text-sm">
          <span className="font-medium text-text">Data meczu</span>
          <DateInput
            value={state.matchDate}
            onChange={(matchDate) =>
              setState((current) => ({ ...current, matchDate }))
            }
            ariaLabel="Data meczu"
          />
        </div>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Min. kurs</span>
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
            className={FILTER_INPUT_CLASS_NAME}
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Sortuj według</span>
          <select
            value={state.sortBy}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                sortBy: event.target.value as BetSortBy,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
          >
            <option value="ev">EV</option>
            <option value="probability">Prawdopodobieństwo</option>
            <option value="game_date">Data meczu</option>
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-text">Kolejność</span>
          <select
            value={state.sortOrder}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                sortOrder: event.target.value as BetSortOrder,
              }))
            }
            className={FILTER_INPUT_CLASS_NAME}
          >
            <option value="desc">Malejąco</option>
            <option value="asc">Rosnąco</option>
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-4 text-sm text-text">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.fromNow}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                fromNow: event.target.checked,
              }))
            }
            className="rounded border-border bg-surface-raised accent-accent"
          />
          Tylko od teraz
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
            className="rounded border-border bg-surface-raised accent-accent"
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
            className="rounded border-border bg-surface-raised accent-accent"
          />
          Uwzględnij podatek 12%
        </label>
      </div>

      <label className="block max-w-xs space-y-2 text-sm">
        <span className="font-medium text-text">Status rozliczenia</span>
        <select
          value={state.settlementStatus}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              settlementStatus: event.target.value as SettlementStatus | "",
            }))
          }
          className={FILTER_INPUT_CLASS_NAME}
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
