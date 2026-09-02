import {
  getAdminCountries,
  getAdminLeagues,
  getAdminSeasons,
  getAdminSports,
  getAdminUsers,
  getCurrentUser,
} from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  AdminUser,
  UserPublic,
} from "@/types/api";

export type AdminPageResult =
  | {
      kind: "ok";
      currentUser: UserPublic;
      users: AdminUser[];
      usersError: string | null;
      leagues: AdminLeague[];
      leaguesError: string | null;
      countries: AdminCountry[];
      sports: AdminSport[];
      seasons: AdminSeason[];
      dictionariesError: string | null;
      seasonsError: string | null;
    }
  | { kind: "unauthenticated" }
  | { kind: "forbidden" }
  | { kind: "error"; message: string };

type CollectionLoad<T> =
  | { kind: "ok"; items: T[] }
  | { kind: "loadError"; message: string }
  | { kind: "unauthenticated" }
  | { kind: "forbidden" };

const GENERIC_ADMIN_LOAD_ERROR =
  "Spróbuj odświeżyć stronę. Jeśli problem wraca, zaloguj się ponownie.";

/** Gates `/admin` on the current user and bootstraps users, leagues and dropdowns. */
export async function loadAdminPage(): Promise<AdminPageResult> {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser.is_admin) {
      return { kind: "forbidden" };
    }
    return await loadAdminBootstrap(currentUser);
  } catch (error) {
    return mapAdminGateError(error);
  }
}

async function loadAdminBootstrap(
  currentUser: UserPublic,
): Promise<AdminPageResult> {
  const [users, leagues, countries, sports, seasons] = await Promise.all([
    loadCollection(getAdminUsers),
    loadCollection(getAdminLeagues),
    loadCollection(getAdminCountries),
    loadCollection(getAdminSports),
    loadCollection(getAdminSeasons),
  ]);
  const gate =
    asGate(users) ??
    asGate(leagues) ??
    asGate(countries) ??
    asGate(sports) ??
    asGate(seasons);
  if (gate) {
    return gate;
  }
  return {
    kind: "ok",
    currentUser,
    users: itemsOrEmpty(users),
    usersError: loadErrorMessage(users),
    leagues: itemsOrEmpty(leagues),
    leaguesError: loadErrorMessage(leagues),
    countries: itemsOrEmpty(countries),
    sports: itemsOrEmpty(sports),
    seasons: itemsOrEmpty(seasons),
    dictionariesError: loadErrorMessage(countries) ?? loadErrorMessage(sports),
    seasonsError: loadErrorMessage(seasons),
  };
}

async function loadCollection<T>(
  loader: () => Promise<T[]>,
): Promise<CollectionLoad<T>> {
  try {
    return { kind: "ok", items: await loader() };
  } catch (error) {
    return mapCollectionError(error);
  }
}

function mapCollectionError(error: unknown): CollectionLoad<never> {
  if (error instanceof ApiError && error.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (error instanceof ApiError && error.status === 403) {
    return { kind: "forbidden" };
  }
  const message =
    error instanceof ApiError ? error.message : GENERIC_ADMIN_LOAD_ERROR;
  return { kind: "loadError", message };
}

function asGate(
  result: CollectionLoad<unknown>,
): Extract<AdminPageResult, { kind: "unauthenticated" | "forbidden" }> | null {
  if (result.kind === "unauthenticated" || result.kind === "forbidden") {
    return result;
  }
  return null;
}

function itemsOrEmpty<T>(result: CollectionLoad<T>): T[] {
  return result.kind === "ok" ? result.items : [];
}

function loadErrorMessage(result: CollectionLoad<unknown>): string | null {
  return result.kind === "loadError" ? result.message : null;
}

function mapAdminGateError(error: unknown): AdminPageResult {
  if (error instanceof ApiError && error.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (error instanceof ApiError && error.status === 403) {
    return { kind: "forbidden" };
  }
  const message =
    error instanceof ApiError ? error.message : GENERIC_ADMIN_LOAD_ERROR;
  return { kind: "error", message };
}
