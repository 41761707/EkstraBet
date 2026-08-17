"use client";

import { useRef, useState } from "react";

import { FavoriteLeagueButton } from "@/components/favorites/FavoriteLeagueButton";
import { ProfileSection } from "@/components/profile/ProfileSection";
import { StatusMessage } from "@/components/StatusMessage";
import {
  addFavoriteLeague,
  removeFavoriteLeague,
} from "@/lib/apiClient";
import type { LeagueSummary } from "@/types/api";

export const FAVORITE_LEAGUES_TITLE = "Ulubione ligi";
export const FAVORITE_LEAGUES_DESCRIPTION =
  "Wybierz swoje ulubione ligi. Ulubione ligi mają pierwszeństwo w widoczności przed pozostałymi ligami.";
export const EMPTY_FAVORITE_LEAGUES_TITLE = "Brak aktywnych lig";
export const EMPTY_FAVORITE_LEAGUES_MESSAGE =
  "API zwróciło pustą listę. Sprawdź dane w backendzie.";
export const FAVORITE_LEAGUES_LOAD_ERROR_TITLE =
  "Nie udało się wczytać listy lig";
export const FAVORITES_UNAVAILABLE_TITLE = "Ulubione ligi są niedostępne";
export const FAVORITES_UNAVAILABLE_MESSAGE =
  "Lista lig jest widoczna, ale stanu ulubionych nie da się teraz odczytać. Odśwież stronę.";
export const FAVORITE_TOGGLE_ERROR_MESSAGE =
  "Nie udało się zapisać zmiany. Spróbuj ponownie.";

interface FavoriteLeaguesSectionProps {
  leagues: LeagueSummary[];
  initialFavoriteIds: number[];
  leaguesError?: string;
  favoritesUnavailable?: boolean;
}

/** Apply an optimistic add/remove without mutating the current list. */
export function nextFavoriteIds(
  currentIds: number[],
  leagueId: number,
  isFavorite: boolean,
): number[] {
  if (isFavorite) {
    return currentIds.includes(leagueId)
      ? currentIds
      : [...currentIds, leagueId];
  }
  return currentIds.filter((id) => id !== leagueId);
}

export function FavoriteLeaguesSection({
  leagues,
  initialFavoriteIds,
  leaguesError,
  favoritesUnavailable = false,
}: FavoriteLeaguesSectionProps) {
  return (
    <ProfileSection
      title={FAVORITE_LEAGUES_TITLE}
      description={FAVORITE_LEAGUES_DESCRIPTION}
    >
      <FavoriteLeaguesBody
        leagues={leagues}
        initialFavoriteIds={initialFavoriteIds}
        leaguesError={leaguesError}
        favoritesUnavailable={favoritesUnavailable}
      />
    </ProfileSection>
  );
}

function FavoriteLeaguesBody({
  leagues,
  initialFavoriteIds,
  leaguesError,
  favoritesUnavailable = false,
}: FavoriteLeaguesSectionProps) {
  const [favoriteIds, setFavoriteIds] = useState(initialFavoriteIds);
  const [pendingIds, setPendingIds] = useState<number[]>([]);
  const [liveMessage, setLiveMessage] = useState<string | null>(null);
  const pendingIdsRef = useRef(new Set<number>());

  async function handleToggle(leagueId: number, nextFavorite: boolean) {
    if (favoritesUnavailable || pendingIdsRef.current.has(leagueId)) {
      return;
    }

    pendingIdsRef.current.add(leagueId);
    setPendingIds([...pendingIdsRef.current]);
    setFavoriteIds((current) =>
      nextFavoriteIds(current, leagueId, nextFavorite),
    );
    setLiveMessage(null);

    try {
      if (nextFavorite) {
        await addFavoriteLeague(leagueId);
      } else {
        await removeFavoriteLeague(leagueId);
      }
    } catch {
      // rollback tylko tej ligi, żeby równoległy toggle innej nie zniknął
      setFavoriteIds((current) =>
        nextFavoriteIds(current, leagueId, !nextFavorite),
      );
      setLiveMessage(FAVORITE_TOGGLE_ERROR_MESSAGE);
    } finally {
      pendingIdsRef.current.delete(leagueId);
      setPendingIds([...pendingIdsRef.current]);
    }
  }

  return (
    <div className="space-y-4">
      <FavoriteLeaguesContent
        leagues={leagues}
        favoriteIds={favoriteIds}
        pendingIds={pendingIds}
        leaguesError={leaguesError}
        favoritesUnavailable={favoritesUnavailable}
        onToggle={handleToggle}
      />
      <p
        aria-live="polite"
        aria-atomic="true"
        className={liveMessage ? "text-sm text-red-300" : "sr-only"}
      >
        {liveMessage ?? ""}
      </p>
    </div>
  );
}

interface FavoriteLeaguesContentProps {
  leagues: LeagueSummary[];
  favoriteIds: number[];
  pendingIds: number[];
  leaguesError?: string;
  favoritesUnavailable: boolean;
  onToggle: (leagueId: number, nextFavorite: boolean) => void;
}

function FavoriteLeaguesContent({
  leagues,
  favoriteIds,
  pendingIds,
  leaguesError,
  favoritesUnavailable,
  onToggle,
}: FavoriteLeaguesContentProps) {
  if (leaguesError) {
    return (
      <StatusMessage
        variant="error"
        title={FAVORITE_LEAGUES_LOAD_ERROR_TITLE}
        message={leaguesError}
      />
    );
  }

  if (leagues.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_FAVORITE_LEAGUES_TITLE}
        message={EMPTY_FAVORITE_LEAGUES_MESSAGE}
      />
    );
  }

  return (
    <div className="space-y-4">
      {favoritesUnavailable ? (
        <StatusMessage
          variant="error"
          title={FAVORITES_UNAVAILABLE_TITLE}
          message={FAVORITES_UNAVAILABLE_MESSAGE}
        />
      ) : null}
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {leagues.map((league) => (
          <li key={league.id}>
            <div className="flex items-center gap-2 rounded-lg border border-slate-700/60 bg-slate-800/40 px-3 py-2 text-sm text-slate-200">
              {league.country_emoji ? (
                <span aria-hidden="true">{league.country_emoji}</span>
              ) : null}
              <span className="min-w-0 flex-1">{league.name}</span>
              {favoritesUnavailable ? null : (
                <FavoriteLeagueButton
                  leagueId={league.id}
                  leagueName={league.name}
                  isFavorite={favoriteIds.includes(league.id)}
                  isPending={pendingIds.includes(league.id)}
                  onToggle={onToggle}
                />
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
