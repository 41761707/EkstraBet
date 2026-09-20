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
  toTipsterCatalogQuery,
} from "@/components/tipsters/tipsterModel";
import {
  ApiError,
  getCurrentUser,
  getFavoriteLeagueIds,
  getLeagues,
  getMyBankroll,
  getMyCoupons,
  getMyPerformance,
  getTipsterCatalog,
  getTipsterProfile,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import { getWarsawDateIso } from "@/lib/date";
import {
  decodeProfileUsername,
  isOwnProfile,
  profilePath,
} from "@/lib/profilePaths";
import { parsePositiveInt } from "@/lib/searchParams";
import type {
  BankrollSettings,
  CatalogMatchesResponse,
  CouponPage,
  FavoriteLeagueIdsResponse,
  LeagueSummary,
  PerformanceBreakdown,
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
    return renderOwnProfile(result.user, query);
  }

  return renderPublicProfile(
    decodeProfileUsername(routeUsername),
    query,
  );
}

async function renderOwnProfile(
  user: UserPublic,
  query: Record<string, string | undefined>,
) {
  const paging = parseCouponPaging(query);
  const favoritesPromise = getFavoriteLeagueIds();
  const [leaguesCatalog, tipster] = await Promise.all([
    loadProfileCatalog(favoritesPromise),
    loadOwnTipsterBundle(paging.page, paging.pageSize, favoritesPromise),
  ]);
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
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={tipster.bankroll}
        bankrollError={tipster.bankrollError}
        coupons={tipster.coupons}
        couponsError={tipster.couponsError}
        performance={tipster.performance}
        performanceError={tipster.performanceError}
        catalog={tipster.catalog}
        catalogError={tipster.catalogError}
        favoriteLeagueIds={tipster.favoriteLeagueIds}
        favoritesUnavailable={tipster.favoritesUnavailable}
        profilePath={profilePath(user.username)}
        searchParams={query}
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

interface OwnTipsterBundle {
  bankroll: BankrollSettings | null;
  bankrollError?: string;
  coupons: CouponPage | null;
  couponsError?: string;
  performance: PerformanceBreakdown | null;
  performanceError?: string;
  catalog: CatalogMatchesResponse | null;
  catalogError?: string;
  favoriteLeagueIds: number[];
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

function parseCouponPaging(query: Record<string, string | undefined>) {
  return {
    page: parsePositiveInt(query.page) ?? DEFAULT_TIPSTER_PAGE,
    pageSize: parsePositiveInt(query.page_size) ?? DEFAULT_TIPSTER_PAGE_SIZE,
  };
}

async function loadProfileCatalog(
  favoritesPromise: Promise<FavoriteLeagueIdsResponse>,
): Promise<ProfileCatalog> {
  const [leaguesResult, favoritesResult] = await Promise.allSettled([
    getLeagues({ active: true }),
    favoritesPromise,
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

async function loadOwnTipsterBundle(
  page: number,
  pageSize: number,
  favoritesPromise: Promise<FavoriteLeagueIdsResponse>,
): Promise<OwnTipsterBundle> {
  const [bankrollResult, couponsResult, performanceResult, favoritesResult] =
    await Promise.allSettled([
      getMyBankroll(),
      getMyCoupons({ page, pageSize }),
      getMyPerformance(),
      favoritesPromise,
    ]);
  const favoriteLeagueIds =
    favoritesResult.status === "fulfilled"
      ? favoritesResult.value.league_ids
      : [];
  const favoritesUnavailable = favoritesResult.status !== "fulfilled";
  const catalogResult = await loadTipsterCatalog(
    favoriteLeagueIds,
    favoritesUnavailable,
  );

  return {
    bankroll: readOptionalBankroll(bankrollResult),
    bankrollError: readBankrollError(bankrollResult),
    coupons: fulfilledOrNull(couponsResult),
    couponsError: rejectedMessage(
      couponsResult,
      "Nie udało się wczytać kuponów.",
    ),
    performance: fulfilledOrNull(performanceResult),
    performanceError: rejectedMessage(
      performanceResult,
      "Nie udało się wczytać analityki.",
    ),
    catalog: fulfilledOrNull(catalogResult),
    catalogError: rejectedMessage(
      catalogResult,
      "Nie udało się wczytać katalogu eventów.",
    ),
    favoriteLeagueIds,
    favoritesUnavailable,
  };
}

async function loadTipsterCatalog(
  favoriteLeagueIds: number[],
  includeAllLeagues = false,
): Promise<PromiseSettledResult<CatalogMatchesResponse>> {
  try {
    const catalog = await getTipsterCatalog(
      toTipsterCatalogQuery(
        getWarsawDateIso(),
        favoriteLeagueIds,
        includeAllLeagues,
      ),
    );
    return { status: "fulfilled", value: catalog };
  } catch (reason) {
    return { status: "rejected", reason };
  }
}

function readOptionalBankroll(
  result: PromiseSettledResult<BankrollSettings>,
): BankrollSettings | null {
  if (result.status === "fulfilled") {
    return result.value;
  }
  return null;
}

function readBankrollError(
  result: PromiseSettledResult<BankrollSettings>,
): string | undefined {
  if (result.status === "fulfilled") {
    return undefined;
  }
  if (result.reason instanceof ApiError && result.reason.status === 404) {
    return undefined;
  }
  return resolveLoadErrorMessage(
    result.reason,
    "Nie udało się wczytać bankrolla.",
  );
}

function fulfilledOrNull<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function rejectedMessage(
  result: PromiseSettledResult<unknown>,
  fallback: string,
): string | undefined {
  if (result.status === "fulfilled") {
    return undefined;
  }
  return resolveLoadErrorMessage(result.reason, fallback);
}
