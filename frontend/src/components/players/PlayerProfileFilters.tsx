"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { PlayerProfileSearchField } from "@/components/players/PlayerProfileSearchField";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  buildPlayerProfileQuery,
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

const FIELD_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;
const SAME_CLUB_MESSAGE = "Rywal i klub muszą być różnymi drużynami.";

export function PlayerProfileFilters({
  playerId,
  sportId,
  seasons,
  teams,
  values,
}: PlayerProfileFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);
  const [formError, setFormError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.opponentTeamId != null && state.opponentTeamId === state.ownTeamId) {
      setFormError(SAME_CLUB_MESSAGE);
      return;
    }
    setFormError(null);
    const next: PlayerProfileParams = {
      ...state,
      teammateLabel: state.teammateId == null ? null : state.teammateLabel,
    };
    const query = buildPlayerProfileQuery(next);
    const path = query ? `/players/${playerId}?${query}` : `/players/${playerId}`;
    navigateSearch(path, router);
  }

  function selectOpponent(opponentTeamId: number | null) {
    setFormError(null);
    setState((current) => ({ ...current, opponentTeamId }));
  }

  function selectOwnTeam(ownTeamId: number | null) {
    setFormError(null);
    setState((current) => ({ ...current, ownTeamId }));
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-border bg-surface p-5"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
          label="Rywal"
          value={state.opponentTeamId}
          emptyLabel="Każdy rywal"
          options={teams.map((team) => ({ id: team.id, label: team.name }))}
          onChange={selectOpponent}
        />
        <FilterSelect
          label="Klub"
          value={state.ownTeamId}
          emptyLabel="Każdy klub"
          options={teams.map((team) => ({ id: team.id, label: team.name }))}
          onChange={selectOwnTeam}
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
      {formError ? <p className="text-sm text-danger-text">{formError}</p> : null}
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
    <label className="space-y-2 text-sm text-muted">
      <span className="font-medium text-text">{label}</span>
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
