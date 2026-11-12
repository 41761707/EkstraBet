import Link from "next/link";
import { notFound } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { PlayerProfileFilters } from "@/components/players/PlayerProfileFilters";
import {
  loadPlayerProfilePage,
  type PlayerProfilePageResult,
} from "@/app/players/[playerId]/loadPlayerProfilePage";
import {
  buildPlayerProfileQuery,
  parsePlayerProfileParams,
} from "@/lib/playerProfileParams";
import { parsePositiveInt } from "@/lib/searchParams";
import { HOCKEY_SPORT_ID, type PlayerProfileResponse } from "@/types/api";

export const dynamic = "force-dynamic";

interface PlayerProfilePageProps {
  params: Promise<{ playerId: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}

export default async function PlayerProfilePage({
  params,
  searchParams,
}: PlayerProfilePageProps) {
  const [{ playerId: playerIdParam }, query] = await Promise.all([
    params,
    searchParams,
  ]);
  const playerId = parsePositiveInt(playerIdParam);
  if (!playerId) {
    notFound();
  }

  const profileParams = parsePlayerProfileParams(query);
  const loaded = await loadPlayerProfilePage(playerId, profileParams);
  if (loaded.kind === "notFound") {
    notFound();
  }

  const playerName = loaded.kind === "ready" ? loaded.profile.player_name : null;
  const sportId = loaded.kind === "ready" ? loaded.profile.sport_id : null;

  return (
    <div className="space-y-6">
      <PlayerProfileHeader playerName={playerName} />
      <PlayerProfileFilters
        key={buildPlayerProfileQuery(profileParams)}
        playerId={playerId}
        sportId={sportId}
        seasons={loaded.kind === "ready" ? loaded.seasons : []}
        teams={loaded.kind === "ready" ? loaded.teams : []}
        values={profileParams}
      />
      {loaded.kind === "error" ? (
        <StatusMessage
          variant="error"
          title="Błąd ładowania"
          message={loaded.sliceError}
        />
      ) : (
        <PlayerProfileContent loaded={loaded} />
      )}
    </div>
  );
}

function PlayerProfileHeader({ playerName }: { playerName: string | null }) {
  return (
    <header className="space-y-2">
      <Link
        href="/players"
        className="text-sm text-accent-text transition hover:text-accent-text-hover"
      >
        Wróć do zawodników
      </Link>
      <h1 className="text-3xl font-bold text-text">
        {playerName ?? "Profil zawodnika"}
      </h1>
    </header>
  );
}

function PlayerProfileContent({
  loaded,
}: {
  loaded: Extract<PlayerProfilePageResult, { kind: "ready" }>;
}) {
  const { profile } = loaded;
  return (
    <>
      {loaded.dictionariesError ? (
        <StatusMessage
          variant="error"
          title="Błąd ładowania"
          message={loaded.dictionariesError}
        />
      ) : null}
      {profile.match_count === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak meczów"
          message="W wybranym przekroju nie ma meczów."
        />
      ) : null}
      {profile.truncated ? (
        <StatusMessage
          variant="info"
          title="Obcięty przekrój"
          message="Pokazano tylko część meczów. Podsumowanie liczy widoczne mecze."
        />
      ) : null}
      <PlayerProfileSportBody profile={profile} />
    </>
  );
}

function PlayerProfileSportBody({
  profile,
}: {
  profile: PlayerProfileResponse;
}) {
  if (profile.body.sport_id === HOCKEY_SPORT_ID) {
    // Kafelki, zdarzenia i log dochodzą w SZP-367.
    return null;
  }
  return (
    <StatusMessage
      variant="info"
      title="Profil tego sportu nie jest jeszcze dostępny"
    />
  );
}
