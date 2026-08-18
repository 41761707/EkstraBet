"use client";

import type { MouseEvent } from "react";

interface FavoriteLeagueButtonProps {
  leagueId: number;
  leagueName: string;
  isFavorite: boolean;
  isPending?: boolean;
  isDisabled?: boolean;
  onToggle: (leagueId: number, nextFavorite: boolean) => void;
}

/** Accessible label for the favorite-league star control. */
export function favoriteLeagueButtonLabel(
  leagueName: string,
  isFavorite: boolean,
): string {
  if (isFavorite) {
    return `Usuń ${leagueName} z ulubionych`;
  }
  return `Dodaj ${leagueName} do ulubionych`;
}

export function FavoriteLeagueButton({
  leagueId,
  leagueName,
  isFavorite,
  isPending = false,
  isDisabled = false,
  onToggle,
}: FavoriteLeagueButtonProps) {
  const label = favoriteLeagueButtonLabel(leagueName, isFavorite);
  const isBlocked = isPending || isDisabled;
  const colorClass = isFavorite ? "text-sky-300" : "text-slate-400";

  function handleClick(event: MouseEvent<HTMLButtonElement>) {
    // obrona na wypadek zagnieżdżenia w Link — gwiazdka nie może nawigować
    event.preventDefault();
    event.stopPropagation();
    if (isBlocked) {
      return;
    }
    onToggle(leagueId, !isFavorite);
  }

  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={isFavorite}
      title={label}
      disabled={isBlocked}
      onClick={handleClick}
      className={
        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md " +
        `transition hover:bg-slate-800 hover:text-sky-300 ${colorClass} ` +
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
      }
    >
      <StarIcon isFilled={isFavorite} />
    </button>
  );
}

function StarIcon({ isFilled }: { isFilled: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill={isFilled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M12 3.2l2.47 5.01 5.53.8-4 3.9.94 5.5L12 16.9l-4.94 2.51.94-5.5-4-3.9 5.53-.8L12 3.2z" />
    </svg>
  );
}
