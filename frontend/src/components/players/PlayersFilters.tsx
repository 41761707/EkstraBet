"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  getMatchLimitOptions,
  MATCH_LIMIT_OPTIONS,
} from "@/components/players/playerStatsConfig";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { navigateSearch } from "@/lib/clientNavigation";
import {
  FOOTBALL_SPORT_ID,
  selectCountryFilter,
  teamsForCountry,
  type PlayersFilterValues,
} from "@/lib/playerFilterParams";
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

const FILTER_INPUT_CLASS_NAME = `w-full rounded-lg text-sm ${INPUT_CLASS_NAME}`;

function defaultMatchLimit(sportId: number): number {
  return (
    getMatchLimitOptions(sportId).find(
      (option) => option.label === MATCH_LIMIT_OPTIONS[0].label,
    )?.value ?? 50
  );
}

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
    if (nextState.matchLimit !== defaultMatchLimit(nextState.sportId)) {
      params.set("match_limit", String(nextState.matchLimit));
    }
    if (nextState.search.trim()) {
      params.set("search", nextState.search.trim());
    }

    const query = params.toString();
    navigateSearch(query ? `/players?${query}` : "/players", router);
  }

  function patchState(partial: Partial<PlayersFilterValues>) {
    setState((current) => ({ ...current, ...partial }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(state);
  }

  function handleReset() {
    const defaultCountryId = countries[0]?.id ?? null;
    const resetState: PlayersFilterValues = {
      sportId: state.sportId,
      countryId: defaultCountryId,
      teamId: teamsForCountry(teams, defaultCountryId)[0]?.id ?? null,
      seasonId: seasons[0]?.season_id ?? null,
      matchLimit: defaultMatchLimit(state.sportId),
      search: "",
    };
    setState(resetState);
    const path =
      resetState.sportId !== FOOTBALL_SPORT_ID
        ? `/players?sport_id=${resetState.sportId}`
        : "/players";
    navigateSearch(path, router);
  }

  const visibleTeams = teamsForCountry(teams, state.countryId);

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-border bg-surface p-5"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {countries.length > 0 ? (
          <label className="space-y-2 text-sm text-muted">
            <span className="font-medium text-text">Wybierz kraj</span>
            <select
              className={FILTER_INPUT_CLASS_NAME}
              value={state.countryId ?? ""}
              onChange={(event) =>
                setState((current) =>
                  selectCountryFilter(
                    current,
                    Number(event.target.value) || null,
                    teams,
                  ),
                )
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

        <label className="space-y-2 text-sm text-muted">
          <span className="font-medium text-text">Wybierz drużynę</span>
          <select
            className={FILTER_INPUT_CLASS_NAME}
            value={state.teamId ?? ""}
            disabled={visibleTeams.length === 0}
            onChange={(event) =>
              patchState({
                teamId: Number(event.target.value) || null,
              })
            }
          >
            {visibleTeams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2 text-sm text-muted">
          <span className="font-medium text-text">Sezon</span>
          <select
            className={FILTER_INPUT_CLASS_NAME}
            value={state.seasonId ?? ""}
            onChange={(event) =>
              patchState({
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

        <label className="space-y-2 text-sm text-muted">
          <span className="font-medium text-text">Liczba meczów</span>
          <select
            className={FILTER_INPUT_CLASS_NAME}
            value={state.matchLimit}
            onChange={(event) =>
              patchState({
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

        <label className="space-y-2 text-sm text-muted">
          <span className="font-medium text-text">
            Wpisz nazwę zawodnika
          </span>
          <input
            type="search"
            className={FILTER_INPUT_CLASS_NAME}
            value={state.search}
            placeholder="Szukaj po nazwie..."
            onChange={(event) =>
              patchState({ search: event.target.value })
            }
          />
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
