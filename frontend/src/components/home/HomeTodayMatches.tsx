import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { StatusMessage } from "@/components/StatusMessage";
import {
  groupDailyMatches,
  type DailyMatchGroup,
  type DailyMatchLeagueGroup,
} from "@/lib/dailyMatches";
import {
  isWarsawNaiveMatchInProgress,
  isWarsawNaiveMatchPastResultWindow,
} from "@/lib/date";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type DailyMatchSummary,
} from "@/types/api";

interface HomeTodayMatchesProps {
  matches: DailyMatchSummary[];
  matchDate: string;
  errorMessage?: string;
  /** Optional clock for deterministic in-progress checks. */
  now?: Date;
}

const FOOTBALL_SPORT_ID = 1;

const SPORT_ACCENT: Record<number, string> = {
  [FOOTBALL_SPORT_ID]: "border-accent/45 bg-accent-soft text-accent-text",
  [HOCKEY_SPORT_ID]: "border-border bg-surface-muted text-text",
  [BASKETBALL_SPORT_ID]: "border-accent/35 bg-surface text-accent-text",
};

const DEFAULT_SPORT_ACCENT = "border-border bg-surface text-text";

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

type MatchPulseDotTone = "default" | "live" | "missingResult";

function resolveMatchPulseDotTone(
  match: DailyMatchSummary,
  now: Date,
): MatchPulseDotTone {
  if (match.is_played) {
    return "default";
  }
  if (isWarsawNaiveMatchInProgress(match.game_date, now)) {
    return "live";
  }
  if (isWarsawNaiveMatchPastResultWindow(match.game_date, now)) {
    return "missingResult";
  }
  return "default";
}

const MATCH_PULSE_DOT_CLASS: Record<MatchPulseDotTone, string> = {
  default: "bg-subtle",
  live: "bg-danger",
  missingResult: "bg-warning",
};

const MATCH_PULSE_ROW_CLASS: Record<MatchPulseDotTone, string> = {
  default:
    "border-border/70 bg-surface-muted hover:border-accent/40 hover:bg-surface-muted/55",
  live: "border-border/70 bg-surface-muted hover:border-accent/40 hover:bg-surface-muted/55",
  missingResult:
    "border-warning-border bg-warning-bg hover:border-warning hover:bg-warning-bg",
};

function MatchPulseRow({
  match,
  now,
}: {
  match: DailyMatchSummary;
  now: Date;
}) {
  const dotTone = resolveMatchPulseDotTone(match, now);
  const timelineLabel = match.is_played
    ? "Koniec"
    : extractKickoffTime(match.game_date);

  return (
    <Link
      href={`/matches/${match.id}`}
      className={`relative block rounded-lg border px-3 py-3 transition sm:px-4 ${MATCH_PULSE_ROW_CLASS[dotTone]}`}
      aria-label={`${match.home_team.name} vs ${match.away_team.name}`}
    >
      <div className="flex flex-col gap-3 sm:grid sm:grid-cols-[5rem_minmax(0,1fr)_auto] sm:items-center sm:gap-4">
        <div className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-2">
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${MATCH_PULSE_DOT_CLASS[dotTone]}`}
            aria-hidden="true"
          />
          <time
            dateTime={match.game_date}
            className="font-mono text-sm font-medium text-muted"
          >
            {timelineLabel}
          </time>
        </div>

        <div className="min-w-0 space-y-1 border-l border-border pl-3 sm:border-l-0 sm:pl-0">
          <p className="truncate text-sm font-medium text-text">
            {match.home_team.name}
          </p>
          <p className="truncate text-sm font-medium text-text">
            {match.away_team.name}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-center sm:gap-2">
          {match.is_played ? (
            <div className="min-w-[4.5rem] text-sm font-semibold text-text sm:text-right">
              <MatchScoreDisplay match={match} size="sm" />
            </div>
          ) : null}
          <span className="text-xs font-medium text-accent-text">Szczegóły</span>
        </div>
      </div>
    </Link>
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
    <section className="space-y-3 rounded-xl border border-border bg-surface p-3 sm:p-4">
      <div className="flex items-baseline justify-between gap-3">
        <Link
          href={`/leagues/${league.leagueId}`}
          className="text-sm font-semibold text-accent-text transition hover:text-accent-text-hover"
        >
          {league.leagueName}
        </Link>
        <span className="text-xs text-subtle">
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
        <span className="text-xs text-subtle">
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
      <header className="flex flex-wrap items-end justify-between gap-2 border-b border-border pb-3">
        <div>
          <p className="text-sm font-medium text-text">
            {formatPolishFullDate(matchDate)}
          </p>
          <p className="mt-0.5 text-xs text-subtle">
            Mecze wszystkich aktywnych lig
          </p>
        </div>
        <p className="text-sm font-semibold text-accent-text">
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
