"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DateInput } from "@/components/filters/DateInput";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import {
  createDefaultTipsterLeaderboardFilters,
  parseIsSystemFilter,
  parseLeaderboardSortBy,
  parseLeaderboardSortOrder,
  tipsterLeaderboardPath,
  TYPERS_PATH,
  type TipsterLeaderboardFilters,
} from "@/components/tipsters/tipsterModel";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  groupBetEventOptions,
  type EventFilterOption,
} from "@/lib/betEventOptions";
import type { FilterOption, LeaderboardSortBy } from "@/types/api";

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;
const LEAGUE_CHECKBOX_HEIGHT_CLASS_NAME = "h-45";

const SORT_BY_OPTIONS: ReadonlyArray<{ value: LeaderboardSortBy; label: string }> = [
  { value: "profit_total", label: "Wynik" },
  { value: "roi_pct", label: "ROI" },
  { value: "accuracy_pct", label: "Skuteczność" },
  { value: "avg_profit", label: "Średni wynik" },
  { value: "avg_odds", label: "Średni kurs" },
  { value: "bets_count", label: "Liczba kuponów" },
  { value: "current_balance", label: "Saldo" },
];

const TIER_OPTIONS: ReadonlyArray<{ value: number; label: string }> = [
  { value: 1, label: "Poziom 1" },
  { value: 2, label: "Poziom 2" },
  { value: 100, label: "Liga Mistrzów" },
  { value: 101, label: "Liga Europy" },
  { value: 102, label: "Liga Konferencji" },
];

interface TipsterFiltersProps {
  values: TipsterLeaderboardFilters;
  leagues: FilterOption[];
  events: EventFilterOption[];
}

export function TipsterFilters({
  values,
  leagues,
  events,
}: TipsterFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: TipsterLeaderboardFilters) {
    navigateSearch(tipsterLeaderboardPath(nextState), router);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters({ ...state, page: 1 });
  }

  function handleReset() {
    const resetState = createDefaultTipsterLeaderboardFilters();
    setState(resetState);
    navigateSearch(TYPERS_PATH, router);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <TipsterAccountAndTier state={state} onChange={setState} />
      <div className="grid gap-4 md:grid-cols-2">
        <MultiSelectCheckboxGroup
          label="Ligi"
          name="tipster-leagues"
          options={leagues}
          selectedIds={state.leagueIds}
          showClearAll
          maxHeightClassName={LEAGUE_CHECKBOX_HEIGHT_CLASS_NAME}
          onChange={(leagueIds) =>
            setState((current) => ({ ...current, leagueIds }))
          }
        />
        <TipsterEventFilters
          events={events}
          selectedIds={state.eventIds}
          onChange={(eventIds) =>
            setState((current) => ({
              ...current,
              eventIds,
              eventFamily: null,
            }))
          }
        />
      </div>
      <TipsterDateFields state={state} onChange={setState} />
      <TipsterSortFields state={state} onChange={setState} />
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

interface TipsterFilterFieldsProps {
  state: TipsterLeaderboardFilters;
  onChange: (
    updater: (current: TipsterLeaderboardFilters) => TipsterLeaderboardFilters,
  ) => void;
}

function TipsterAccountAndTier({ state, onChange }: TipsterFilterFieldsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="space-y-2 text-sm">
        <span className="font-medium text-text">Konto</span>
        <select
          value={state.isSystem === null ? "" : String(state.isSystem)}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              isSystem: parseIsSystemFilter(event.target.value),
            }))
          }
          className={FILTER_INPUT_CLASS_NAME}
        >
          <option value="">Wszyscy</option>
          <option value="0">Ludzie</option>
          <option value="1">Konta systemowe</option>
        </select>
      </label>
      <label className="space-y-2 text-sm">
        <span className="font-medium text-text">Poziom ligi</span>
        <select
          value={state.tier === null ? "" : String(state.tier)}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              tier: parseTierSelect(event.target.value),
            }))
          }
          className={FILTER_INPUT_CLASS_NAME}
        >
          <option value="">Wszystkie</option>
          {TIER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function TipsterEventFilters({
  events,
  selectedIds,
  onChange,
}: {
  events: EventFilterOption[];
  selectedIds: number[];
  onChange: (eventIds: number[]) => void;
}) {
  const groupedEvents = groupBetEventOptions(events);
  return (
    <MultiSelectCheckboxGroup
      label="Zdarzenia"
      name="tipster-events"
      sections={[
        { title: "Najpopularniejsze", options: groupedEvents.popular },
        { title: "Pozostałe", options: groupedEvents.niche },
      ]}
      selectedIds={selectedIds}
      maxHeightClassName={LEAGUE_CHECKBOX_HEIGHT_CLASS_NAME}
      onChange={onChange}
    />
  );
}

function TipsterDateFields({ state, onChange }: TipsterFilterFieldsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-2 text-sm">
        <span className="font-medium text-text">Data od</span>
        <DateInput
          value={state.dateFrom}
          onChange={(dateFrom) =>
            onChange((current) => ({ ...current, dateFrom }))
          }
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
    </div>
  );
}

function TipsterSortFields({ state, onChange }: TipsterFilterFieldsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <label className="space-y-2 text-sm">
        <span className="font-medium text-text">Sortuj według</span>
        <select
          value={state.sortBy}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              sortBy: parseLeaderboardSortBy(event.target.value),
            }))
          }
          className={FILTER_INPUT_CLASS_NAME}
        >
          {SORT_BY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-2 text-sm">
        <span className="font-medium text-text">Kolejność</span>
        <select
          value={state.sortOrder}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              sortOrder: parseLeaderboardSortOrder(event.target.value),
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

function parseTierSelect(value: string): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}
