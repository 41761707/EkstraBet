import Link from "next/link";

import { ExpandableSection } from "@/components/ExpandableSection";
import { HockeyEventRankingGrid } from "@/components/hockey/HockeyEventRankingBoard";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getHockeyPlayerEventRankings } from "@/lib/api";
import type { HockeyPlayerEventRankingsResponse } from "@/types/api";

const BETA_NOTE =
  "Beta: prawdopodobieństwa statystyk zawodnika, bez kursów i bez rozliczania.";

const EMPTY_TITLE = "Brak predykcji zawodników";
const EMPTY_MESSAGE =
  "Żaden nierozgrany mecz nie ma jeszcze policzonych statystyk.";

export async function HockeyLeagueEventRankings() {
  const loaded = await loadPreview();

  return (
    <ExpandableSection
      title="Przewidywane zdarzenia"
      id="przewidywane-zdarzenia"
    >
      <RankingsPreview loaded={loaded} />
    </ExpandableSection>
  );
}

async function loadPreview(): Promise<
  | { rankings: HockeyPlayerEventRankingsResponse }
  | { errorMessage: string }
> {
  try {
    return { rankings: await getHockeyPlayerEventRankings(10) };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? error.message
        : "Nie udało się połączyć z API backendu.";
    return { errorMessage };
  }
}

function RankingsPreview({
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
    <div className="space-y-4">
      <p className="text-sm text-muted">{BETA_NOTE}</p>
      <HockeyEventRankingGrid rankings={loaded.rankings.rankings} />
      <Link
        href="/nhl/predictions"
        className="inline-block text-sm font-semibold text-accent-text transition hover:text-accent-text-hover"
      >
        Wszystkie rankingi
      </Link>
    </div>
  );
}
