import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { FavoriteLeaguesSection } from "@/components/profile/FavoriteLeaguesSection";
import { ProfilePage } from "@/components/profile/ProfilePage";
import { ProfileSettingsSection } from "@/components/profile/ProfileSettingsSection";
import { StatusMessage } from "@/components/StatusMessage";
import { MyBetsSection } from "@/components/tipsters/MyBetsSection";
import {
  DEFAULT_TIPSTER_PAGE,
  DEFAULT_TIPSTER_PAGE_SIZE,
  isMissingTipsterProfileError,
} from "@/components/tipsters/tipsterModel";
import {
  ApiError,
  getCurrentUser,
  getFavoriteLeagueIds,
  getLeagues,
  getTipsterProfile,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import {
  decodeProfileUsername,
  isOwnProfile,
  profilePath,
} from "@/lib/profilePaths";
import { parsePositiveInt } from "@/lib/searchParams";
import type {
  LeagueSummary,
  TipsterProfileResponse,
  UserPublic,
} from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Profil | EkstraBet",
  description: "Profil użytkownika EkstraBet.",
};

interface ProfileUsernamePageProps {
  params: Promise<{ username: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}

export default async function ProfileUsernamePage({
  params,
  searchParams,
}: ProfileUsernamePageProps) {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const { username: routeUsername } = await params;
  const query = await searchParams;
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

  if (isOwnProfile(routeUsername, result.user.username)) {
    return renderOwnProfile(result.user);
  }

  return renderPublicProfile(
    decodeProfileUsername(routeUsername),
    query,
  );
}

async function renderOwnProfile(user: UserPublic) {
  const leaguesCatalog = await loadProfileCatalog();
  const displayName = user.display_name?.trim() || user.username;

  return (
    <ProfilePage username={user.username} displayName={displayName}>
      <ProfileSettingsSection />
      <FavoriteLeaguesSection
        leagues={leaguesCatalog.leagues}
        initialFavoriteIds={leaguesCatalog.favoriteIds}
        leaguesError={leaguesCatalog.leaguesError}
        favoritesUnavailable={leaguesCatalog.favoritesUnavailable}
      />
    </ProfilePage>
  );
}

async function renderPublicProfile(
  username: string,
  query: Record<string, string | undefined>,
) {
  const paging = parseCouponPaging(query);
  try {
    const profile = await getTipsterProfile(username, {
      page: paging.page,
      pageSize: paging.pageSize,
    });
    return <PublicProfileView profile={profile} query={query} />;
  } catch (error) {
    if (isMissingTipsterProfileError(error)) {
      notFound();
    }
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać profilu"
        message={resolveLoadErrorMessage(
          error,
          "Nie udało się wczytać publicznego profilu typerów.",
        )}
      />
    );
  }
}

function PublicProfileView({
  profile,
  query,
}: {
  profile: TipsterProfileResponse;
  query: Record<string, string | undefined>;
}) {
  const displayName = profile.display_name?.trim() || profile.username;
  return (
    <ProfilePage username={profile.username} displayName={displayName}>
      <MyBetsSection
        isOwnProfile={false}
        isSystemProfile={profile.is_system}
        bankroll={profile.bankroll}
        coupons={profile.coupons}
        performance={profile.performance}
        catalog={null}
        profilePath={profilePath(profile.username)}
        searchParams={query}
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

function parseCouponPaging(query: Record<string, string | undefined>) {
  return {
    page: parsePositiveInt(query.page) ?? DEFAULT_TIPSTER_PAGE,
    pageSize: parsePositiveInt(query.page_size) ?? DEFAULT_TIPSTER_PAGE_SIZE,
  };
}
