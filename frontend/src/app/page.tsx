import type { Metadata } from "next";
import { HomeLeaguesList } from "@/components/home/HomeLeaguesList";
import { HomeSection } from "@/components/home/HomeSection";
import { HomeStaticSections } from "@/components/home/HomeStaticSections";
import { HomeTodayMatches } from "@/components/home/HomeTodayMatches";
import { ApiError, getDailyMatches, getLeagues } from "@/lib/api";
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

export default async function HomePage() {
  const matchDate = getWarsawDateIso();

  const [leaguesResult, matchesResult] = await Promise.allSettled([
    getLeagues({ active: true }),
    getDailyMatches(matchDate),
  ]);

  let leagues: LeagueSummary[] = [];
  let leaguesError: string | undefined;
  let matches: DailyMatchSummary[] = [];
  let matchesError: string | undefined;

  if (leaguesResult.status === "fulfilled") {
    leagues = leaguesResult.value.leagues;
  } else {
    leaguesError = resolveLoadErrorMessage(
      leaguesResult.reason,
      "Nie udało się połączyć z API backendu.",
    );
  }

  if (matchesResult.status === "fulfilled") {
    matches = matchesResult.value.matches;
  } else {
    matchesError = resolveLoadErrorMessage(
      matchesResult.reason,
      "Nie udało się połączyć z API backendu.",
    );
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3 text-center sm:text-left">
        <h1 className="text-3xl font-bold text-white">
          EkstraBet - Asystent Statystyczno-Predykcyjny - Sezon 1
        </h1>
        <p className="max-w-3xl text-slate-300">
          Oficjalny start od momentu rozpoczęcia sezonu 2026/2027 dla każdej z
          lig.
        </p>
      </section>

      <div className="space-y-4">

        <HomeSection title="Lista obsługiwanych lig" id="ligy" defaultOpen>
          <HomeLeaguesList leagues={leagues} errorMessage={leaguesError} />
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
