"use client";

import { useMemo, useState } from "react";
import { MatchCard } from "@/components/MatchCard";
import { ExpandableSection } from "@/components/ExpandableSection";
import { HockeyTeamPrematchPanel } from "@/components/matches/HockeyTeamPrematchPanel";
import { MatchTeamPrematchPanel } from "@/components/matches/MatchTeamPrematchPanel";
import {
  MATCH_H2H_DEFAULT,
  MATCH_H2H_MAX,
  MATCH_H2H_MIN,
  MATCH_OU_LINE_DEFAULT,
  MATCH_OU_LINE_MAX,
  MATCH_OU_LINE_MIN,
  MATCH_OU_LINE_STEP,
  resolveMatchLookbackBounds,
} from "@/components/matches/matchChartConfig";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  HeadToHeadSummary,
  MatchSummary,
  TeamSeasonMatchPoint,
} from "@/types/api";
import { HOCKEY_SPORT_ID } from "@/types/api";
import {
  defaultOuLine,
  ouLineBounds,
} from "@/components/teams/sportTeamChartConfig";

interface MatchPrematchStatsSectionProps {
  sportId: number | null;
  homeTeamName: string;
  awayTeamName: string;
  seasonId: number;
  leagueId: number;
  headToHead: HeadToHeadSummary;
  homeTeamHistory: TeamSeasonMatchPoint[];
  awayTeamHistory: TeamSeasonMatchPoint[];
}

function H2HStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

export function MatchPrematchStatsSection({
  sportId,
  homeTeamName,
  awayTeamName,
  seasonId,
  leagueId,
  headToHead,
  homeTeamHistory = [],
  awayTeamHistory = [],
}: MatchPrematchStatsSectionProps) {
  const isHockey = sportId === HOCKEY_SPORT_ID;
  const ouBounds = isHockey ? ouLineBounds(HOCKEY_SPORT_ID) : null;
  const safeHeadToHead = headToHead ?? {
    team_id: 0,
    opponent_id: 0,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_conceded: 0,
    btts_count: 0,
    btts_percentage: 0,
    avg_goals_per_match: 0,
    meetings: [],
  };
  const safeHomeHistory = homeTeamHistory ?? [];
  const safeAwayHistory = awayTeamHistory ?? [];

  const [h2hLimit, setH2hLimit] = useState(MATCH_H2H_DEFAULT);
  const [ouLine, setOuLine] = useState(() =>
    isHockey ? defaultOuLine(HOCKEY_SPORT_ID) : MATCH_OU_LINE_DEFAULT,
  );

  const lookbackBounds = useMemo(() => {
    const maxAvailable = Math.max(
      safeHomeHistory.length,
      safeAwayHistory.length,
    );
    return resolveMatchLookbackBounds(maxAvailable);
  }, [safeAwayHistory.length, safeHomeHistory.length]);

  const [lookback, setLookback] = useState(lookbackBounds.defaultValue);

  const effectiveLookback = Math.min(
    Math.max(lookback, lookbackBounds.min || 1),
    lookbackBounds.max,
  );

  const displayedMeetings = useMemo(
    () => (safeHeadToHead.meetings ?? []).slice(0, h2hLimit),
    [safeHeadToHead.meetings, h2hLimit],
  );

  return (
    <div className="space-y-4">
      <ExpandableSection title="Konfiguracja analizy" defaultOpen>
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-slate-200">
                Liczba prezentowanych spotkań H2H
              </span>
              <span className="font-semibold text-white">{h2hLimit}</span>
            </div>
            <input
              type="range"
              min={MATCH_H2H_MIN}
              max={MATCH_H2H_MAX}
              step={1}
              value={h2hLimit}
              onChange={(event) => setH2hLimit(Number(event.target.value))}
              className="w-full accent-sky-400"
            />
          </label>

          <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-slate-200">
                Linia Over/Under
              </span>
              <span className="font-semibold text-white">
                {ouLine.toFixed(1)}
              </span>
            </div>
            <input
              type="range"
              min={isHockey ? ouBounds!.min : MATCH_OU_LINE_MIN}
              max={isHockey ? ouBounds!.max : MATCH_OU_LINE_MAX}
              step={isHockey ? ouBounds!.step : MATCH_OU_LINE_STEP}
              value={ouLine}
              onChange={(event) => setOuLine(Number(event.target.value))}
              className="w-full accent-sky-400"
            />
          </label>

          <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-slate-200">
                Liczba analizowanych spotkań wstecz
              </span>
              <span className="font-semibold text-white">
                {effectiveLookback}
              </span>
            </div>
            <input
              type="range"
              min={lookbackBounds.min}
              max={lookbackBounds.max}
              step={1}
              value={lookback}
              onChange={(event) => setLookback(Number(event.target.value))}
              className="w-full accent-sky-400"
              disabled={lookbackBounds.max <= 0}
            />
            <p className="text-xs text-slate-500">
              Wykresy budowane ze wszystkich meczów przed datą tego spotkania.
            </p>
          </label>
        </div>
      </ExpandableSection>

      {h2hLimit > 0 ? (
        <ExpandableSection
          title={`Bezpośrednie spotkania (H2H) — ${Math.min(h2hLimit, safeHeadToHead.meetings.length)}`}
          defaultOpen
        >
          {safeHeadToHead.played > 0 ? (
            <div className="mb-4 grid gap-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4 sm:grid-cols-2 lg:grid-cols-4">
              <H2HStat label="Rozegrane" value={safeHeadToHead.played} />
              <H2HStat
                label="Bilans (gospodarz)"
                value={`${safeHeadToHead.wins}W ${safeHeadToHead.draws}D ${safeHeadToHead.losses}L`}
              />
              <H2HStat
                label="Bramki"
                value={`${safeHeadToHead.goals_for}:${safeHeadToHead.goals_conceded}`}
              />
              {!isHockey ? (
                <H2HStat
                  label="BTTS"
                  value={`${safeHeadToHead.btts_percentage.toFixed(1)}%`}
                />
              ) : null}
            </div>
          ) : null}
          {displayedMeetings.length > 0 ? (
            <div className="grid gap-3">
              {displayedMeetings.map((match: MatchSummary) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  seasonId={seasonId}
                  leagueId={leagueId}
                />
              ))}
            </div>
          ) : (
            <StatusMessage
              variant="empty"
              title="Brak spotkań H2H"
              message="Brak bezpośrednich spotkań między drużynami w bazie danych."
            />
          )}
        </ExpandableSection>
      ) : null}

      <ExpandableSection title={homeTeamName} defaultOpen>
        {isHockey ? (
          <HockeyTeamPrematchPanel
            teamName={homeTeamName}
            history={safeHomeHistory}
            lookback={effectiveLookback}
            ouLine={ouLine}
          />
        ) : (
          <MatchTeamPrematchPanel
            teamName={homeTeamName}
            history={safeHomeHistory}
            lookback={effectiveLookback}
            ouLine={ouLine}
          />
        )}
      </ExpandableSection>

      <ExpandableSection title={awayTeamName} defaultOpen>
        {isHockey ? (
          <HockeyTeamPrematchPanel
            teamName={awayTeamName}
            history={safeAwayHistory}
            lookback={effectiveLookback}
            ouLine={ouLine}
          />
        ) : (
          <MatchTeamPrematchPanel
            teamName={awayTeamName}
            history={safeAwayHistory}
            lookback={effectiveLookback}
            ouLine={ouLine}
          />
        )}
      </ExpandableSection>
    </div>
  );
}
