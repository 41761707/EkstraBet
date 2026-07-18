import type { Metadata } from "next";
import { HomeLeaguesList } from "@/components/home/HomeLeaguesList";
import { HomeSection } from "@/components/home/HomeSection";
import { HomeStaticSections } from "@/components/home/HomeStaticSections";
import { ApiError, getLeagues } from "@/lib/api";
import type { LeagueSummary } from "@/types/api";

export const metadata: Metadata = {
  title: "EkstraBet - Inteligentny Asystent Bukmacherski",
  description:
    "Inteligentny asystent bukmacherski — analizy lig, modele predykcyjne i rekomendacje zakładów.",
};

export default async function HomePage() {
  let leagues: LeagueSummary[] = [];
  let leaguesError: string | undefined;

  try {
    const response = await getLeagues({ active: true });
    leagues = response.leagues;
  } catch (error) {
    leaguesError =
      error instanceof ApiError
        ? error.message
        : "Nie udało się połączyć z API backendu.";
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3 text-center sm:text-left">
        <h1 className="text-3xl font-bold text-white">
          EkstraBet - Inteligentny Asystent Bukmacherski - Sezon 1
        </h1>
        <p className="max-w-3xl text-slate-300">
          Oficjalny start od momentu rozpoczęcia sezonu 2026/2027 dla każdej z
          lig.
        </p>
      </section>

      <div className="space-y-4">
        <HomeSection title="Lista obsługiwanych lig" id="ligy">
          <HomeLeaguesList leagues={leagues} errorMessage={leaguesError} />
        </HomeSection>

        <HomeStaticSections />
      </div>
    </div>
  );
}
