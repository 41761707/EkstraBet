import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { FavoriteLeaguesSection } from "@/components/profile/FavoriteLeaguesSection";
import { ProfilePage } from "@/components/profile/ProfilePage";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getCurrentUser,
  getFavoriteLeagueIds,
  getLeagues,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import { isOwnProfile } from "@/lib/profilePaths";
import type { LeagueSummary, UserPublic } from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Profil | EkstraBet",
  description: "Panel ustawień zalogowanego użytkownika.",
};

interface ProfileUsernamePageProps {
  params: Promise<{ username: string }>;
}

export default async function ProfileUsernamePage({
  params,
}: ProfileUsernamePageProps) {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const { username: routeUsername } = await params;
  const result = await loadProfileUser();
  if (result.kind === "unauthenticated") {
    redirect("/login");
  }
  if (result.kind === "unknown") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać profilu"
        message="Spróbuj odświeżyć stronę. Jeśli problem wraca, wyloguj się i zaloguj ponownie."
      />
    );
  }

  if (!isOwnProfile(routeUsername, result.user.username)) {
    notFound();
  }

  const displayName =
    result.user.display_name?.trim() || result.user.username;
  const catalog = await loadProfileCatalog();

  return (
    <ProfilePage
      username={result.user.username}
      displayName={displayName}
    >
      <FavoriteLeaguesSection
        leagues={catalog.leagues}
        initialFavoriteIds={catalog.favoriteIds}
        leaguesError={catalog.leaguesError}
        favoritesUnavailable={catalog.favoritesUnavailable}
      />
    </ProfilePage>
  );
}

type ProfileUserResult =
  | { kind: "ok"; user: UserPublic }
  | { kind: "unauthenticated" }
  | { kind: "unknown" };

interface ProfileCatalog {
  leagues: LeagueSummary[];
  favoriteIds: number[];
  leaguesError?: string;
  favoritesUnavailable: boolean;
}

async function loadProfileUser(): Promise<ProfileUserResult> {
  try {
    const user = await getCurrentUser();
    return { kind: "ok", user };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthenticated" };
    }
    return { kind: "unknown" };
  }
}

function resolveLoadErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

async function loadProfileCatalog(): Promise<ProfileCatalog> {
  const [leaguesResult, favoritesResult] = await Promise.allSettled([
    getLeagues({ active: true }),
    getFavoriteLeagueIds(),
  ]);

  const catalog: ProfileCatalog = {
    leagues: [],
    favoriteIds: [],
    favoritesUnavailable: false,
  };

  if (leaguesResult.status === "fulfilled") {
    catalog.leagues = leaguesResult.value.leagues;
  } else {
    catalog.leaguesError = resolveLoadErrorMessage(
      leaguesResult.reason,
      "Nie udało się połączyć z API backendu.",
    );
  }

  if (favoritesResult.status === "fulfilled") {
    catalog.favoriteIds = favoritesResult.value.league_ids;
  } else {
    catalog.favoritesUnavailable = true;
  }

  return catalog;
}
