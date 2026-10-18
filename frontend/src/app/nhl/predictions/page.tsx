import type { Metadata } from "next";

import { HockeyEventRankingGrid } from "@/components/hockey/HockeyEventRankingBoard";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getHockeyPlayerEventRankings } from "@/lib/api";
import type { HockeyPlayerEventRankingsResponse } from "@/types/api";

export const metadata: Metadata = {
  title: "Przewidywane zdarzenia NHL | EkstraBet",
  description:
    "Rankingi prawdopodobieństwa punktu, gola, asysty i strzału dla nierozgranych meczów NHL.",
};

const BETA_NOTE =
  "Beta: prawdopodobieństwa statystyk zawodnika, bez kursów i bez rozliczania.";

const EMPTY_TITLE = "Brak predykcji zawodników";
const EMPTY_MESSAGE =
  "Żaden nierozgrany mecz nie ma jeszcze policzonych statystyk.";

export default async function NhlPredictionsPage() {
  const loaded = await loadRankings();

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-text">
        Przewidywane zdarzenia NHL
      </h1>
      <RankingsBody loaded={loaded} />
    </div>
  );
}

async function loadRankings(): Promise<
  | { rankings: HockeyPlayerEventRankingsResponse }
  | { errorMessage: string }
> {
  try {
    return { rankings: await getHockeyPlayerEventRankings() };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? error.message
        : "Nie udało się połączyć z API backendu.";
    return { errorMessage };
  }
}

function RankingsBody({
  loaded,
}: {
  loaded:
    | { rankings: HockeyPlayerEventRankingsResponse }
    | { errorMessage: string };
}) {
  if ("errorMessage" in loaded) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać rankingu"
        message={loaded.errorMessage}
      />
    );
  }

  if (loaded.rankings.match_count === 0) {
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_TITLE}
        message={EMPTY_MESSAGE}
      />
    );
  }

  return (
    <>
      <p className="text-sm text-muted">{BETA_NOTE}</p>
      <HockeyEventRankingGrid rankings={loaded.rankings.rankings} />
    </>
  );
}
