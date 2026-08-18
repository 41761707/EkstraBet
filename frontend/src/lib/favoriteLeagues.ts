import type { LeagueSummary } from "@/types/api";

export const FAVORITE_TOGGLE_ERROR_MESSAGE =
  "Nie udało się zapisać zmiany. Spróbuj ponownie.";
export const FAVORITES_UNAVAILABLE_TITLE = "Ulubione ligi są niedostępne";
export const FAVORITES_UNAVAILABLE_MESSAGE =
  "Lista lig jest widoczna, ale stanu ulubionych nie da się teraz odczytać. Odśwież stronę.";

/**
 * Lift favorite leagues to the front without changing order inside either group.
 */
export function orderLeaguesByFavorites(
  leagues: LeagueSummary[],
  favoriteIds: Iterable<number>,
): LeagueSummary[] {
  const favoriteSet = new Set(favoriteIds);
  const favorites: LeagueSummary[] = [];
  const rest: LeagueSummary[] = [];

  for (const league of leagues) {
    if (favoriteSet.has(league.id)) {
      favorites.push(league);
    } else {
      rest.push(league);
    }
  }

  return [...favorites, ...rest];
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
