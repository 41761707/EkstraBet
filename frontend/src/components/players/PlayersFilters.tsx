"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  getMatchLimitOptions,
  MATCH_LIMIT_OPTIONS,
} from "@/components/players/playerStatsConfig";
import type { PlayersFilterValues } from "@/lib/playerFilterParams";
import { FOOTBALL_SPORT_ID } from "@/lib/playerFilterParams";
import type {
  PlayerCountryOption,
  PlayerSeasonOption,
  PlayerTeamOption,
} from "@/types/api";

export type { PlayersFilterValues };

interface PlayersFiltersProps {
  countries: PlayerCountryOption[];
  teams: PlayerTeamOption[];
  seasons: PlayerSeasonOption[];
  values: PlayersFilterValues;
}

const inputClassName =
  "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100";

export function PlayersFilters({
  countries,
  teams,
  seasons,
  values,
}: PlayersFiltersProps) {
  const router = useRouter();
  const [state, setState] = useState(values);

  function applyFilters(nextState: PlayersFilterValues) {
    const params = new URLSearchParams();
    if (nextState.sportId !== FOOTBALL_SPORT_ID) {
      params.set("sport_id", String(nextState.sportId));
    }
    if (nextState.countryId) {
      params.set("country_id", String(nextState.countryId));
    }
    if (nextState.teamId) {
      params.set("team_id", String(nextState.teamId));
    }
    if (nextState.seasonId) {
      params.set("season_id", String(nextState.seasonId));
    }
    const defaultLimit =
      getMatchLimitOptions(nextState.sportId).find((option) =>
        option.label === MATCH_LIMIT_OPTIONS[0].label,
      )?.value ?? 50;
    if (nextState.matchLimit !== defaultLimit) {
      params.set("match_limit", String(nextState.matchLimit));
    }
    if (nextState.search.trim()) {
      params.set("search", nextState.search.trim());
    }

    const query = params.toString();
    router.push(query ? `/players?${query}` : "/players");
  }

  function updateState(partial: Partial<PlayersFilterValues>) {
    const nextState = { ...state, ...partial };
    if (partial.countryId !== undefined && partial.countryId !== state.countryId) {
      nextState.teamId = null;
    }
    setState(nextState);
    applyFilters(nextState);
  }

  return (
    <div className="grid gap-4 rounded-xl border border-slate-700/80 bg-slate-900/40 p-5 md:grid-cols-2 xl:grid-cols-5">
      {countries.length > 0 ? (
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium text-slate-200">Wybierz kraj</span>
          <select
            className={inputClassName}
            value={state.countryId ?? ""}
            onChange={(event) =>
              updateState({
                countryId: Number(event.target.value) || null,
              })
            }
          >
            {countries.map((country) => (
              <option key={country.id} value={country.id}>
                {country.emoji ? `${country.emoji} ` : ""}
                {country.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <label className="space-y-2 text-sm text-slate-300">
        <span className="font-medium text-slate-200">Wybierz drużynę</span>
        <select
          className={inputClassName}
          value={state.teamId ?? ""}
          disabled={teams.length === 0}
          onChange={(event) =>
            updateState({
              teamId: Number(event.target.value) || null,
            })
          }
        >
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span className="font-medium text-slate-200">Sezon</span>
        <select
          className={inputClassName}
          value={state.seasonId ?? ""}
          onChange={(event) =>
            updateState({
              seasonId: Number(event.target.value) || null,
            })
          }
        >
          {seasons.map((season) => (
            <option key={season.season_id} value={season.season_id}>
              {season.years}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span className="font-medium text-slate-200">Liczba meczów</span>
        <select
          className={inputClassName}
          value={state.matchLimit}
          onChange={(event) =>
            updateState({
              matchLimit: Number(event.target.value),
            })
          }
        >
          {getMatchLimitOptions(state.sportId).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span className="font-medium text-slate-200">
          Wpisz nazwę zawodnika
        </span>
        <input
          type="search"
          className={inputClassName}
          value={state.search}
          placeholder="Szukaj po nazwie..."
          onChange={(event) =>
            setState((current) => ({ ...current, search: event.target.value }))
          }
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              applyFilters(state);
            }
          }}
          onBlur={() => applyFilters(state)}
        />
      </label>
    </div>
  );
}
