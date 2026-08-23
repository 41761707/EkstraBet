"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { FavoriteLeagueButton } from "@/components/favorites/FavoriteLeagueButton";
import { StatusMessage } from "@/components/StatusMessage";
import {
  addFavoriteLeague,
  removeFavoriteLeague,
} from "@/lib/apiClient";
import {
  FAVORITE_TOGGLE_ERROR_MESSAGE,
  FAVORITES_UNAVAILABLE_MESSAGE,
  FAVORITES_UNAVAILABLE_TITLE,
  nextFavoriteIds,
  orderLeaguesByFavorites,
} from "@/lib/favoriteLeagues";
import { leaguePath } from "@/lib/leaguePaths";
import type { LeagueSummary } from "@/types/api";

interface HomeLeaguesListProps {
  leagues: LeagueSummary[];
  errorMessage?: string;
  initialFavoriteIds?: number[];
  favoritesEnabled?: boolean;
  favoritesUnavailable?: boolean;
}

export function HomeLeaguesList({
  leagues,
  errorMessage,
  initialFavoriteIds = [],
  favoritesEnabled = false,
  favoritesUnavailable = false,
}: HomeLeaguesListProps) {
  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować lig"
        message={errorMessage}
      />
    );
  }

  if (leagues.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak aktywnych lig"
        message="API zwróciło pustą listę. Sprawdź dane w backendzie."
      />
    );
  }

  return (
    <HomeLeaguesInteractive
      leagues={leagues}
      initialFavoriteIds={initialFavoriteIds}
      favoritesEnabled={favoritesEnabled}
      favoritesUnavailable={favoritesUnavailable}
    />
  );
}

interface HomeLeaguesInteractiveProps {
  leagues: LeagueSummary[];
  initialFavoriteIds: number[];
  favoritesEnabled: boolean;
  favoritesUnavailable: boolean;
}

function HomeLeaguesInteractive({
  leagues,
  initialFavoriteIds,
  favoritesEnabled,
  favoritesUnavailable,
}: HomeLeaguesInteractiveProps) {
  const [favoriteIds, setFavoriteIds] = useState(initialFavoriteIds);
  const [pendingIds, setPendingIds] = useState<number[]>([]);
  const [liveMessage, setLiveMessage] = useState<string | null>(null);
  const pendingIdsRef = useRef(new Set<number>());
  const showStars = favoritesEnabled && !favoritesUnavailable;
  const visibleLeagues = showStars
    ? orderLeaguesByFavorites(leagues, favoriteIds)
    : leagues;

  async function handleToggle(leagueId: number, nextFavorite: boolean) {
    if (!showStars || pendingIdsRef.current.has(leagueId)) {
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
      {favoritesUnavailable ? (
        <StatusMessage
          variant="error"
          title={FAVORITES_UNAVAILABLE_TITLE}
          message={FAVORITES_UNAVAILABLE_MESSAGE}
        />
      ) : null}
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {visibleLeagues.map((league) => (
          <HomeLeagueItem
            key={league.id}
            league={league}
            showStars={showStars}
            isFavorite={favoriteIds.includes(league.id)}
            isPending={pendingIds.includes(league.id)}
            onToggle={handleToggle}
          />
        ))}
      </ul>
      <p
        aria-live="polite"
        aria-atomic="true"
        className={liveMessage ? "text-sm text-danger" : "sr-only"}
      >
        {liveMessage ?? ""}
      </p>
    </div>
  );
}

interface HomeLeagueItemProps {
  league: LeagueSummary;
  showStars: boolean;
  isFavorite: boolean;
  isPending: boolean;
  onToggle: (leagueId: number, nextFavorite: boolean) => void;
}

function HomeLeagueItem({
  league,
  showStars,
  isFavorite,
  isPending,
  onToggle,
}: HomeLeagueItemProps) {
  const leagueLabel = (
    <>
      {league.country_emoji ? (
        <span aria-hidden="true">{league.country_emoji}</span>
      ) : null}
      <span>{league.name}</span>
    </>
  );

  if (!showStars) {
    return (
      <li>
        <Link
          href={leaguePath(league.slug)}
          className="flex items-center gap-2 rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-text transition hover:border-accent/40 hover:bg-surface-muted hover:text-text"
        >
          {leagueLabel}
        </Link>
      </li>
    );
  }

  return (
    <li>
      <div className="flex items-center rounded-lg border border-border bg-surface-muted transition hover:border-accent/40 hover:bg-surface-muted">
        <Link
          href={leaguePath(league.slug)}
          className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm text-text transition hover:text-text"
        >
          {leagueLabel}
        </Link>
        <FavoriteLeagueButton
          leagueId={league.id}
          leagueName={league.name}
          isFavorite={isFavorite}
          isPending={isPending}
          onToggle={onToggle}
        />
      </div>
    </li>
  );
}
