"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DateInput } from "@/components/filters/DateInput";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import {
  betEventFilterSections,
  type EventFilterOption,
} from "@/lib/betEventOptions";
import {
  betsFilterPath,
  createDefaultBetsFilterValues,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type BetSortBy,
  type BetSortOrder,
  type FilterOption,
  type SettlementStatus,
} from "@/types/api";

export type { BetsFilterValues };

interface BetsFiltersProps {
  leagues: FilterOption[];
  events: EventFilterOption[];
  models: FilterOption[];
  values: BetsFilterValues;
}

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;
const BETS_CHECKBOX_LIST_HEIGHT_CLASS_NAME = "h-45";
const SPORT_OPTIONS = [
  { id: FOOTBALL_SPORT_ID, label: "Piłka nożna" },
  { id: HOCKEY_SPORT_ID, label: "Hokej" },
] as const;

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

  function handleSportChange(nextSportId: number) {
    if (nextSportId === state.sportId) {
      return;
    }
    const reset = createDefaultBetsFilterValues({ sportId: nextSportId });
    setState(reset);
    navigateSearch(betsFilterPath(reset), router);
  }

  function handleReset() {
    const resetState = createDefaultBetsFilterValues({
      sportId: state.sportId,
    });
    setState(resetState);
    navigateSearch(betsFilterPath(resetState), router);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <label className="block max-w-xs space-y-2 text-sm">
        <span className="font-medium text-text">Sport</span>
        <select
          value={state.sportId}
          onChange={(event) => handleSportChange(Number(event.target.value))}
          className={FILTER_INPUT_CLASS_NAME}
        >
          {SPORT_OPTIONS.map((sport) => (
            <option key={sport.id} value={sport.id}>
              {sport.label}
            </option>
          ))}
        </select>
      </label>
      <BetsCheckboxFilters
        leagues={leagues}
        events={events}
        models={models}
        state={state}
        onChange={setState}
      />
      <BetsDateSortFields state={state} onChange={setState} />
      <BetsToggleFilters state={state} onChange={setState} />
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

interface BetsFilterFieldsProps {
  state: BetsFilterValues;
  onChange: (updater: (current: BetsFilterValues) => BetsFilterValues) => void;
}

function BetsCheckboxFilters({
  leagues,
  events,
  models,
  state,
  onChange,
}: BetsFilterFieldsProps & {
  leagues: FilterOption[];
  events: EventFilterOption[];
  models: FilterOption[];
}) {
  const eventSections = betEventFilterSections(events);
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <MultiSelectCheckboxGroup
        label="Ligi"
        name="leagues"
        options={leagues}
        selectedIds={state.leagueIds}
        showClearAll
        maxHeightClassName={BETS_CHECKBOX_LIST_HEIGHT_CLASS_NAME}
        onChange={(leagueIds) => onChange((current) => ({ ...current, leagueIds }))}
      />
      <MultiSelectCheckboxGroup
        label="Wydarzenia"
        name="events"
        sections={eventSections}
        selectedIds={state.eventIds}
        maxHeightClassName={BETS_CHECKBOX_LIST_HEIGHT_CLASS_NAME}
        onChange={(eventIds) => onChange((current) => ({ ...current, eventIds }))}
      />
      <MultiSelectCheckboxGroup
        label="Modele"
        name="models"
        options={models}
        selectedIds={state.modelIds}
        maxHeightClassName={BETS_CHECKBOX_LIST_HEIGHT_CLASS_NAME}
        onChange={(modelIds) => onChange((current) => ({ ...current, modelIds }))}
      />
    </div>
  );
}

function BetsDateSortFields({ state, onChange }: BetsFilterFieldsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div className="space-y-2 text-sm">
        <span className="font-medium text-text">Data od</span>
        <DateInput
          value={state.dateFrom}
          onChange={(dateFrom) => onChange((current) => ({ ...current, dateFrom }))}
          ariaLabel="Data od"
        />
      </div>
      <div className="space-y-2 text-sm">
        <span className="font-medium text-text">Data do</span>
        <DateInput
          value={state.dateTo}
          onChange={(dateTo) => onChange((current) => ({ ...current, dateTo }))}
          ariaLabel="Data do"
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
            onChange((current) => ({
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
            onChange((current) => ({
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
            onChange((current) => ({
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
  );
}

function BetsToggleFilters({ state, onChange }: BetsFilterFieldsProps) {
  return (
    <>
      <div className="flex flex-wrap gap-4 text-sm text-text">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={state.fromNow}
            onChange={(event) =>
              onChange((current) => ({ ...current, fromNow: event.target.checked }))
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
              onChange((current) => ({
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
              onChange((current) => ({
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
            onChange((current) => ({
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
    </>
  );
}
