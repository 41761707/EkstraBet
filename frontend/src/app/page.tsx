import type { Metadata } from "next";
import { HomeLeaguesList } from "@/components/home/HomeLeaguesList";
import { HomeSection } from "@/components/home/HomeSection";
import { HomeStaticSections } from "@/components/home/HomeStaticSections";
import { HomeTodayMatches } from "@/components/home/HomeTodayMatches";
import {
  ApiError,
  getDailyMatches,
  getFavoriteLeagueIds,
  getLeagues,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import { getWarsawDateIso } from "@/lib/dailyMatches";
import type { DailyMatchSummary, LeagueSummary } from "@/types/api";

export const metadata: Metadata = {
  title: "EkstraBet - Asystent Statystyczno-Predykcyjny",
  description:
    "Asystent statystyczno-predykcyjny — analizy lig, modele predykcyjne i rekomendacje zakładów sportowych.",
};

function resolveLoadErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

interface HomePageData {
  matchDate: string;
  leagues: LeagueSummary[];
  leaguesError?: string;
  matches: DailyMatchSummary[];
  matchesError?: string;
  favoriteIds: number[];
  favoritesEnabled: boolean;
  favoritesUnavailable: boolean;
}

async function loadHomePageData(): Promise<HomePageData> {
  const matchDate = getWarsawDateIso();
  const favoritesEnabled = isAuthEnabled();
  const [leaguesResult, matchesResult, favoritesResult] =
    await Promise.allSettled([
      getLeagues({ active: true }),
      getDailyMatches(matchDate),
      favoritesEnabled
        ? getFavoriteLeagueIds()
        : Promise.resolve({ league_ids: [] }),
    ]);

  const data: HomePageData = {
    matchDate,
    leagues: [],
    matches: [],
    favoriteIds: [],
    favoritesEnabled,
    favoritesUnavailable: false,
  };

  if (leaguesResult.status === "fulfilled") {
    data.leagues = leaguesResult.value.leagues;
  } else {
    data.leaguesError = resolveLoadErrorMessage(
      leaguesResult.reason,
      "Nie udało się połączyć z API backendu.",
    );
  }

  if (matchesResult.status === "fulfilled") {
    data.matches = matchesResult.value.matches;
  } else {
    data.matchesError = resolveLoadErrorMessage(
      matchesResult.reason,
      "Nie udało się połączyć z API backendu.",
    );
  }

  if (favoritesEnabled) {
    if (favoritesResult.status === "fulfilled") {
      data.favoriteIds = favoritesResult.value.league_ids;
    } else {
      data.favoritesUnavailable = true;
    }
  }

  return data;
}

export default async function HomePage() {
  const {
    matchDate,
    leagues,
    leaguesError,
    matches,
    matchesError,
    favoriteIds,
    favoritesEnabled,
    favoritesUnavailable,
  } = await loadHomePageData();

  return (
    <div className="space-y-8">
      <section className="space-y-3 text-center sm:text-left">
        <h1 className="text-3xl font-bold text-text">
          EkstraBet - Asystent Statystyczno-Predykcyjny - Sezon 1
        </h1>
        <p className="max-w-3xl text-muted">
          Oficjalny start od momentu rozpoczęcia sezonu 2026/2027 dla każdej z
          lig.
        </p>
      </section>

      <div className="space-y-4">
        <HomeSection title="Lista obsługiwanych lig" id="ligi" defaultOpen>
          <HomeLeaguesList
            leagues={leagues}
            errorMessage={leaguesError}
            initialFavoriteIds={favoriteIds}
            favoritesEnabled={favoritesEnabled}
            favoritesUnavailable={favoritesUnavailable}
          />
        </HomeSection>

        <HomeSection title="Dzisiejsze mecze" id="dzisiejsze-mecze">
          <HomeTodayMatches
            matches={matches}
            matchDate={matchDate}
            errorMessage={matchesError}
          />
        </HomeSection>

        <HomeStaticSections />
      </div>
    </div>
  );
}
