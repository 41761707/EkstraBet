"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { PlayerProfileSearchField } from "@/components/players/PlayerProfileSearchField";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  buildPlayerProfileQuery,
  PROFILE_MATCH_WINDOWS,
  type PlayerProfileParams,
} from "@/lib/playerProfileParams";
import { parsePositiveInt } from "@/lib/searchParams";
import type { PlayerSeasonOption, PlayerTeamOption } from "@/types/api";

interface PlayerProfileFiltersProps {
  playerId: number;
  sportId: number | null;
  seasons: PlayerSeasonOption[];
  teams: PlayerTeamOption[];
  values: PlayerProfileParams;
}

interface FilterOption {
  id: number;
  label: string;
}

const FIELD_CLASS_NAME = `h-10 w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;
const WINDOW_LABELS: Record<(typeof PROFILE_MATCH_WINDOWS)[number], string> = {
  5: "Ostatnie 5 meczów",
  10: "Ostatnie 10 meczów",
  15: "Ostatnie 15 meczów",
};

export function PlayerProfileFilters({
  playerId,
  sportId,
  seasons,
  teams,
  values,
}: PlayerProfileFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next: PlayerProfileParams = {
      ...state,
      teammateLabel: state.teammateId == null ? null : state.teammateLabel,
    };
    const query = buildPlayerProfileQuery(next);
    const path = query ? `/players/${playerId}?${query}` : `/players/${playerId}`;
    navigateSearch(path, router);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-border bg-surface p-5"
    >
      <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-4">
        <FilterSelect
          label="Sezon"
          value={state.seasonId}
          emptyLabel="Wszystkie sezony"
          options={seasons.map((season) => ({
            id: season.season_id,
            label: season.years,
          }))}
          onChange={(seasonId) =>
            setState((current) => ({ ...current, seasonId }))
          }
        />
        <FilterSelect
          label="Liczba meczów"
          value={state.matchLimit}
          emptyLabel="Cały sezon"
          options={PROFILE_MATCH_WINDOWS.map((limit) => ({
            id: limit,
            label: WINDOW_LABELS[limit],
          }))}
          onChange={(matchLimit) =>
            setState((current) => ({ ...current, matchLimit }))
          }
        />
        <FilterSelect
          label="Rywal"
          value={state.opponentTeamId}
          emptyLabel="Każdy rywal"
          options={teams.map((team) => ({ id: team.id, label: team.name }))}
          onChange={(opponentTeamId) =>
            setState((current) => ({ ...current, opponentTeamId }))
          }
        />
        <PlayerProfileSearchField
          playerId={playerId}
          sportId={sportId}
          teammateId={state.teammateId}
          teammateLabel={state.teammateLabel}
          onChange={(selection) =>
            setState((current) => ({ ...current, ...selection }))
          }
        />
      </div>
      <button
        type="submit"
        className={
          "rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
          "transition hover:bg-accent-hover"
        }
      >
        Zastosuj filtry
      </button>
    </form>
  );
}

function FilterSelect({
  label,
  value,
  emptyLabel,
  options,
  onChange,
}: {
  label: string;
  value: number | null;
  emptyLabel: string;
  options: FilterOption[];
  onChange: (value: number | null) => void;
}) {
  return (
    <label className="block space-y-2 text-sm text-muted">
      <span className="block font-medium text-text">{label}</span>
      <select
        className={FIELD_CLASS_NAME}
        value={value ?? ""}
        onChange={(event) => onChange(parsePositiveInt(event.target.value))}
      >
        <option value="">{emptyLabel}</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
