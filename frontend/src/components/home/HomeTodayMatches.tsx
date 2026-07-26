import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { StatusMessage } from "@/components/StatusMessage";
import {
  groupDailyMatches,
  type DailyMatchGroup,
  type DailyMatchLeagueGroup,
} from "@/lib/dailyMatches";
import { hasWarsawNaiveDateTimePassed } from "@/lib/date";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type DailyMatchSummary,
} from "@/types/api";

interface HomeTodayMatchesProps {
  matches: DailyMatchSummary[];
  matchDate: string;
  errorMessage?: string;
  /** Optional clock for deterministic awaiting-result checks. */
  now?: Date;
}

type MatchPulseStatus = "score" | "vs" | "awaiting";

const FOOTBALL_SPORT_ID = 1;

const SPORT_ACCENT: Record<number, string> = {
  [FOOTBALL_SPORT_ID]: "border-sky-500/45 bg-sky-950/35 text-sky-200",
  [HOCKEY_SPORT_ID]: "border-slate-400/45 bg-slate-800/55 text-slate-200",
  [BASKETBALL_SPORT_ID]: "border-sky-400/35 bg-slate-900/70 text-sky-100",
};

const DEFAULT_SPORT_ACCENT =
  "border-slate-500/40 bg-slate-900/50 text-slate-200";

function formatPolishFullDate(isoDate: string): string {
  const date = new Date(`${isoDate}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }

  const formatted = date.toLocaleDateString("pl-PL", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

  return formatted.charAt(0).toLocaleUpperCase("pl-PL") + formatted.slice(1);
}

function formatMatchCountLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (count === 1) {
    return "1 mecz";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} mecze`;
  }
  return `${count} meczów`;
}

function extractKickoffTime(gameDate: string): string {
  const timeMatch = /[T ](\d{2}:\d{2})/.exec(gameDate);
  return timeMatch?.[1] ?? "—";
}

function resolveMatchPulseStatus(
  match: DailyMatchSummary,
  now: Date,
): MatchPulseStatus {
  if (match.is_played) {
    return "score";
  }
  if (hasWarsawNaiveDateTimePassed(match.game_date, now)) {
    return "awaiting";
  }
  return "vs";
}

function teamHref(
  teamId: number,
  seasonId: number,
  leagueId: number,
): string {
  const params = new URLSearchParams({
    season_id: String(seasonId),
    league_id: String(leagueId),
  });
  return `/teams/${teamId}?${params.toString()}`;
}

function MatchPulseRow({
  match,
  now,
}: {
  match: DailyMatchSummary;
  now: Date;
}) {
  const status = resolveMatchPulseStatus(match, now);
  const timelineLabel = match.is_played
    ? "Koniec"
    : extractKickoffTime(match.game_date);

  return (
    <article className="relative rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-3 sm:px-4">
      <div className="flex flex-col gap-3 sm:grid sm:grid-cols-[5rem_minmax(0,1fr)_auto] sm:items-center sm:gap-4">
        <div className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-2">
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              status === "awaiting"
                ? "bg-slate-300/80"
                : "bg-slate-500/80"
            }`}
            aria-hidden="true"
          />
          <time
            dateTime={match.game_date}
            className="font-mono text-sm font-medium text-slate-300"
          >
            {timelineLabel}
          </time>
        </div>

        <div className="min-w-0 space-y-1 border-l border-slate-700/80 pl-3 sm:border-l-0 sm:pl-0">
          <Link
            href={teamHref(
              match.home_team.id,
              match.season_id,
              match.league_id,
            )}
            className="block truncate text-sm font-medium text-white transition hover:text-sky-200"
          >
            {match.home_team.name}
          </Link>
          <Link
            href={teamHref(
              match.away_team.id,
              match.season_id,
              match.league_id,
            )}
            className="block truncate text-sm font-medium text-slate-200 transition hover:text-sky-200"
          >
            {match.away_team.name}
          </Link>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-center sm:gap-2">
          <div className="min-w-[4.5rem] text-sm font-semibold text-slate-100 sm:text-right">
            {status === "score" ? (
              <MatchScoreDisplay match={match} size="sm" />
            ) : null}
            {status === "vs" ? (
              <span className="text-slate-400">vs</span>
            ) : null}
            {status === "awaiting" ? (
              <span className="text-xs font-medium text-slate-400">
                Oczekuje na wynik
              </span>
            ) : null}
          </div>
          <Link
            href={`/matches/${match.id}`}
            className="text-xs font-medium text-sky-300 transition hover:text-sky-200"
          >
            Szczegóły
          </Link>
        </div>
      </div>
    </article>
  );
}

function MatchPulseLeagueCard({
  league,
  now,
}: {
  league: DailyMatchLeagueGroup;
  now: Date;
}) {
  return (
    <section className="space-y-3 rounded-xl border border-slate-700/60 bg-slate-900/35 p-3 sm:p-4">
      <div className="flex items-baseline justify-between gap-3">
        <Link
          href={`/leagues/${league.leagueId}`}
          className="text-sm font-semibold text-sky-200 transition hover:text-sky-100"
        >
          {league.leagueName}
        </Link>
        <span className="text-xs text-slate-500">
          {formatMatchCountLabel(league.matches.length)}
        </span>
      </div>
      <div className="space-y-2">
        {league.matches.map((match) => (
          <MatchPulseRow key={match.id} match={match} now={now} />
        ))}
      </div>
    </section>
  );
}

function MatchPulseSportGroup({
  group,
  now,
}: {
  group: DailyMatchGroup;
  now: Date;
}) {
  const accent = SPORT_ACCENT[group.sportId] ?? DEFAULT_SPORT_ACCENT;
  const matchCount = group.leagues.reduce(
    (sum, league) => sum + league.matches.length,
    0,
  );

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold tracking-wide ${accent}`}
        >
          {group.sportName}
        </span>
        <span className="text-xs text-slate-500">
          {formatMatchCountLabel(matchCount)}
        </span>
      </div>
      <div className="space-y-3">
        {group.leagues.map((league) => (
          <MatchPulseLeagueCard
            key={league.leagueId}
            league={league}
            now={now}
          />
        ))}
      </div>
    </section>
  );
}

export function HomeTodayMatches({
  matches,
  matchDate,
  errorMessage,
  now = new Date(),
}: HomeTodayMatchesProps) {
  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować dzisiejszych meczów"
        message={errorMessage}
      />
    );
  }

  if (matches.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak meczów na dziś"
        message="Żadna aktywna liga nie ma zaplanowanych spotkań w tym dniu."
      />
    );
  }

  const groups = groupDailyMatches(matches);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-2 border-b border-slate-700/60 pb-3">
        <div>
          <p className="text-sm font-medium text-slate-200">
            {formatPolishFullDate(matchDate)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            Mecze wszystkich aktywnych lig
          </p>
        </div>
        <p className="text-sm font-semibold text-sky-300">
          {formatMatchCountLabel(matches.length)}
        </p>
      </header>

      <div className="space-y-6">
        {groups.map((group) => (
          <MatchPulseSportGroup
            key={group.sportId}
            group={group}
            now={now}
          />
        ))}
      </div>
    </div>
  );
}
