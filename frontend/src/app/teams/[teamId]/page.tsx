import Link from "next/link";
import { notFound } from "next/navigation";
import { ExpandableSection } from "@/components/ExpandableSection";
import { MatchCard } from "@/components/MatchCard";
import { StatusMessage } from "@/components/StatusMessage";
import { TeamSeasonChartsSection } from "@/components/teams/TeamSeasonChartsSection";
import { TeamSportSeasonChartsSection } from "@/components/teams/TeamSportSeasonChartsSection";
import { TeamSplitStatsTable } from "@/components/TeamSplitStatsTable";
import {
  ApiError,
  getLeagueDetails,
  getTeamProfile,
} from "@/lib/api";
import { leaguePath } from "@/lib/leaguePaths";
import { BASKETBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/types/api";

interface TeamPageProps {
  params: Promise<{ teamId: string }>;
  searchParams: Promise<{
    season_id?: string;
    league_id?: string;
    opponent_id?: string;
    limit?: string;
  }>;
}

function parsePositiveInt(value: string | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function pickSeasonId(
  seasons: { season_id: number }[],
  currentSeasonId: number | null,
  requestedSeasonId?: string,
): number | null {
  const parsed = parsePositiveInt(requestedSeasonId);
  if (parsed && seasons.some((season) => season.season_id === parsed)) {
    return parsed;
  }

  if (
    currentSeasonId &&
    seasons.some((season) => season.season_id === currentSeasonId)
  ) {
    return currentSeasonId;
  }

  return seasons[0]?.season_id ?? null;
}

function buildTeamQuery(params: {
  seasonId: number;
  leagueId?: number;
  opponentId?: number;
  limit?: number;
}): string {
  const search = new URLSearchParams();
  search.set("season_id", String(params.seasonId));
  if (params.leagueId) {
    search.set("league_id", String(params.leagueId));
  }
  if (params.opponentId) {
    search.set("opponent_id", String(params.opponentId));
  }
  if (params.limit) {
    search.set("limit", String(params.limit));
  }
  return search.toString();
}

export default async function TeamPage({
  params,
  searchParams,
}: TeamPageProps) {
  const { teamId: teamIdParam } = await params;
  const {
    season_id: seasonIdParam,
    league_id: leagueIdParam,
    opponent_id: opponentIdParam,
    limit: limitParam,
  } = await searchParams;

  const teamId = parsePositiveInt(teamIdParam);
  if (!teamId) {
    notFound();
  }

  const leagueId = parsePositiveInt(leagueIdParam);
  const opponentId = parsePositiveInt(opponentIdParam);
  const h2hLimit = parsePositiveInt(limitParam) ?? 5;

  let selectedSeasonId = parsePositiveInt(seasonIdParam);
  let leagueSlug: string | null = null;
  let leagueName: string | null = null;
  let leagueSeasons: { season_id: number; years: string }[] = [];

  if (leagueId) {
    try {
      const league = await getLeagueDetails(leagueId);
      leagueSlug = league.slug;
      leagueName = league.name;
      leagueSeasons = league.seasons;
      if (!selectedSeasonId) {
        selectedSeasonId = pickSeasonId(
          league.seasons,
          league.current_season_id,
          seasonIdParam,
        );
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        notFound();
      }
      throw error;
    }
  }

  if (!selectedSeasonId) {
    return (
      <StatusMessage
        variant="empty"
        title="Season required"
        message="Open this team from a league page or add season_id and league_id to the URL."
      />
    );
  }

  try {
    const profile = await getTeamProfile(teamId, {
      seasonId: selectedSeasonId,
      leagueId: leagueId ?? undefined,
      limit: opponentId ? h2hLimit : undefined,
      opponentId: opponentId ?? undefined,
    });

    const queryBase = {
      seasonId: selectedSeasonId,
      leagueId: leagueId ?? profile.league_id ?? undefined,
    };
    const sportId = profile.team.sport_id;
    const isSportLeagueTeam =
      sportId === HOCKEY_SPORT_ID || sportId === BASKETBALL_SPORT_ID;

    return (
      <div className="space-y-8">
        <section className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm text-sky-300">
            <Link href="/" className="transition hover:text-sky-200">
              ← Leagues
            </Link>
            {leagueId && leagueSlug ? (
              <>
                <span className="text-slate-600">/</span>
                <Link
                  href={leaguePath(leagueSlug, {
                    season_id: selectedSeasonId,
                  })}
                  className="transition hover:text-sky-200"
                >
                  {leagueName}
                </Link>
              </>
            ) : null}
          </div>
          <h1 className="text-3xl font-bold text-white">
            {profile.team.country_emoji ? `${profile.team.country_emoji} ` : ""}
            {profile.team.name}
          </h1>
          <p className="text-slate-300">
            {[profile.team.country_name, profile.team.sport_name]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </section>

        <div className="space-y-4">
          {leagueSeasons.length > 0 ? (
            <ExpandableSection title="Sezon" defaultOpen>
              <div className="flex flex-wrap gap-2">
                {leagueSeasons.map((season) => {
                  const isActive = season.season_id === selectedSeasonId;
                  const query = buildTeamQuery({
                    seasonId: season.season_id,
                    leagueId: leagueId ?? undefined,
                    opponentId: opponentId ?? undefined,
                    limit: opponentId ? h2hLimit : undefined,
                  });
                  return (
                    <Link
                      key={season.season_id}
                      href={`/teams/${teamId}?${query}`}
                      className={`rounded-full px-3 py-1.5 text-sm transition ${
                        isActive
                          ? "bg-sky-600 text-white"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {season.years}
                    </Link>
                  );
                })}
              </div>
            </ExpandableSection>
          ) : null}

          <ExpandableSection title="Statystyki sezonowe" defaultOpen>
            <TeamSplitStatsTable
              overall={profile.overall_stats}
              home={profile.home_stats}
              away={profile.away_stats}
            />
          </ExpandableSection>

          {isSportLeagueTeam && queryBase.leagueId ? (
            <TeamSportSeasonChartsSection
              key={`${teamId}-${selectedSeasonId}-sport`}
              leagueId={queryBase.leagueId}
              teamId={teamId}
              teamName={profile.team.name}
              sportId={sportId!}
              seasonId={selectedSeasonId}
            />
          ) : isSportLeagueTeam ? (
            <StatusMessage
              variant="info"
              title="Wybierz ligę"
              message="Otwórz drużynę ze strony ligi NHL lub NBA, aby zobaczyć wykresy sezonowe."
            />
          ) : (
            <TeamSeasonChartsSection
              key={`${teamId}-${selectedSeasonId}`}
              teamId={teamId}
              teamName={profile.team.name}
              seasonId={selectedSeasonId}
              leagueId={queryBase.leagueId}
              seasonMatches={profile.season_matches}
              recentMatches={profile.recent_matches}
            />
          )}

          {profile.head_to_head ? (
            <ExpandableSection
              title={`Head-to-head vs ${profile.head_to_head.opponent_id}`}
            >
              <div className="space-y-4">
                <div className="grid gap-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4 sm:grid-cols-2 lg:grid-cols-4">
                  <H2HStat label="Played" value={profile.head_to_head.played} />
                  <H2HStat
                    label="Record"
                    value={`${profile.head_to_head.wins}W ${profile.head_to_head.draws}D ${profile.head_to_head.losses}L`}
                  />
                  <H2HStat
                    label="Goals"
                    value={`${profile.head_to_head.goals_for}:${profile.head_to_head.goals_conceded}`}
                  />
                  {sportId !== HOCKEY_SPORT_ID ? (
                    <H2HStat
                      label="BTTS"
                      value={`${profile.head_to_head.btts_percentage.toFixed(1)}%`}
                    />
                  ) : null}
                </div>
                {profile.head_to_head.meetings.length > 0 ? (
                  <div className="grid gap-3">
                    {profile.head_to_head.meetings.map((match) => (
                      <MatchCard
                        key={match.id}
                        match={match}
                        highlightTeamId={teamId}
                        seasonId={selectedSeasonId}
                        leagueId={queryBase.leagueId}
                      />
                    ))}
                  </div>
                ) : (
                  <StatusMessage
                    variant="empty"
                    title="Brak spotkań H2H"
                    message="Nie znaleziono bezpośrednich spotkań z tym przeciwnikiem."
                  />
                )}
              </div>
            </ExpandableSection>
          ) : null}
        </div>
      </div>
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    const message =
      error instanceof ApiError
        ? error.message
        : "Unable to load team profile from the API.";

    return (
      <StatusMessage
        variant="error"
        title="Failed to load team"
        message={message}
      />
    );
  }
}

interface H2HStatProps {
  label: string;
  value: string | number;
}

function H2HStat({ label, value }: H2HStatProps) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
