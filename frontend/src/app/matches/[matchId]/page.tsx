import Link from "next/link";
import { notFound } from "next/navigation";
import { MatchDetailTabs } from "@/components/matches/MatchDetailTabs";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getLeagueDetails,
  getMatchDetails,
} from "@/lib/api";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { formatMatchDateTime } from "@/lib/format";
import { leaguePath } from "@/lib/leaguePaths";

interface MatchPageProps {
  params: Promise<{ matchId: string }>;
  searchParams: Promise<{ model_ids?: string }>;
}

function parsePositiveInt(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function parseModelIds(value: string | undefined): number[] | undefined {
  if (!value) {
    return undefined;
  }
  const ids = value
    .split(",")
    .map((part) => parsePositiveInt(part.trim()))
    .filter((id): id is number => id !== null);
  return ids.length > 0 ? ids : undefined;
}

export default async function MatchPage({
  params,
  searchParams,
}: MatchPageProps) {
  const { matchId: matchIdParam } = await params;
  const { model_ids: modelIdsParam } = await searchParams;

  const matchId = parsePositiveInt(matchIdParam);
  if (!matchId) {
    notFound();
  }

  const modelIds = parseModelIds(modelIdsParam);

  try {
    const match = await getMatchDetails(matchId, modelIds);
    const league = await getLeagueDetails(match.league_id);
    const leagueHref = leaguePath(league.slug, { season_id: match.season_id });
    const teamQuery = `season_id=${match.season_id}&league_id=${match.league_id}`;

    return (
      <div className="space-y-8">
        <section className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm text-sky-300">
            <Link href="/" className="transition hover:text-sky-200">
              ← Leagues
            </Link>
            <span className="text-slate-600">/</span>
            <Link href={leagueHref} className="transition hover:text-sky-200">
              {league.name}
            </Link>
          </div>
          <p className="text-sm text-slate-400">
            {formatMatchDateTime(match.game_date)}
            {match.round_label !== null ? ` · ${match.round_label}` : ""}
          </p>
        </section>

        <section className="rounded-xl border border-slate-700/80 bg-slate-900/50 p-6">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
            <Link
              href={`/teams/${match.home_team.id}?${teamQuery}`}
              className="text-right text-xl font-semibold text-white transition hover:text-sky-200 sm:text-2xl"
            >
              {match.home_team.name}
            </Link>
            <div className="text-center">
              <MatchScoreDisplay match={match} size="lg" />
            </div>
            <Link
              href={`/teams/${match.away_team.id}?${teamQuery}`}
              className="text-xl font-semibold text-white transition hover:text-sky-200 sm:text-2xl"
            >
              {match.away_team.name}
            </Link>
          </div>
        </section>

        <MatchDetailTabs match={match} />
      </div>
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    const message =
      error instanceof ApiError
        ? error.message
        : "Unable to load match details from the API.";

    return (
      <StatusMessage
        variant="error"
        title="Failed to load match"
        message={message}
      />
    );
  }
}
