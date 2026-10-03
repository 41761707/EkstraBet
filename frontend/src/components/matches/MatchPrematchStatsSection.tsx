"use client";

import { useMemo, useState } from "react";

import { ExpandableSection } from "@/components/ExpandableSection";
import { HockeyTeamPrematchPanel } from "@/components/matches/HockeyTeamPrematchPanel";
import { MatchTeamPrematchPanel } from "@/components/matches/MatchTeamPrematchPanel";
import {
  MATCH_H2H_DEFAULT,
  MATCH_OU_LINE_DEFAULT,
  resolveMatchLookbackBounds,
} from "@/components/matches/matchChartConfig";
import { PrematchAnalysisControls } from "@/components/matches/PrematchAnalysisControls";
import { PrematchHeadToHeadSection } from "@/components/matches/PrematchHeadToHeadSection";
import {
  HOCKEY_SPORT_ID,
  type HeadToHeadSummary,
  type HockeyScheduleContext,
  type HockeyScheduleSide,
  type TeamSeasonMatchPoint,
} from "@/types/api";
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
  hockeyScheduleContext?: HockeyScheduleContext | null;
}

function emptyHeadToHead(): HeadToHeadSummary {
  return {
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
}

function PrematchTeamColumn({
  teamName,
  history,
  isHockey,
  lookback,
  ouLine,
  schedule,
}: {
  teamName: string;
  history: TeamSeasonMatchPoint[];
  isHockey: boolean;
  lookback: number;
  ouLine: number;
  schedule: HockeyScheduleSide | null;
}) {
  return (
    <ExpandableSection title={teamName} defaultOpen>
      {isHockey ? (
        <HockeyTeamPrematchPanel
          teamName={teamName}
          history={history}
          lookback={lookback}
          ouLine={ouLine}
          schedule={schedule}
        />
      ) : (
        <MatchTeamPrematchPanel
          teamName={teamName}
          history={history}
          lookback={lookback}
          ouLine={ouLine}
        />
      )}
    </ExpandableSection>
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
  hockeyScheduleContext = null,
}: MatchPrematchStatsSectionProps) {
  const isHockey = sportId === HOCKEY_SPORT_ID;
  const safeHeadToHead = headToHead ?? emptyHeadToHead();
  const safeHomeHistory = homeTeamHistory ?? [];
  const safeAwayHistory = awayTeamHistory ?? [];
  const [h2hLimit, setH2hLimit] = useState(MATCH_H2H_DEFAULT);
  const [ouLine, setOuLine] = useState(() =>
    isHockey ? defaultOuLine(HOCKEY_SPORT_ID) : MATCH_OU_LINE_DEFAULT,
  );
  const lookbackBounds = useMemo(() => {
    const maxAvailable = Math.max(safeHomeHistory.length, safeAwayHistory.length);
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
  const meetingCount = Math.min(h2hLimit, safeHeadToHead.meetings.length);

  return (
    <div className="min-w-0 space-y-4">
      <ExpandableSection title="Konfiguracja analizy" defaultOpen>
        <PrematchAnalysisControls
          h2hLimit={h2hLimit}
          ouLine={ouLine}
          lookback={lookback}
          effectiveLookback={effectiveLookback}
          isHockey={isHockey}
          ouBounds={isHockey ? ouLineBounds(HOCKEY_SPORT_ID) : null}
          lookbackBounds={lookbackBounds}
          onH2hLimitChange={setH2hLimit}
          onOuLineChange={setOuLine}
          onLookbackChange={setLookback}
        />
      </ExpandableSection>
      {h2hLimit > 0 ? (
        <ExpandableSection
          title={`Bezpośrednie spotkania (H2H) — ${meetingCount}`}
          defaultOpen
        >
          <PrematchHeadToHeadSection
            headToHead={safeHeadToHead}
            meetings={displayedMeetings}
            isHockey={isHockey}
            seasonId={seasonId}
            leagueId={leagueId}
          />
        </ExpandableSection>
      ) : null}
      <PrematchTeamColumn
        teamName={homeTeamName}
        history={safeHomeHistory}
        isHockey={isHockey}
        lookback={effectiveLookback}
        ouLine={ouLine}
        schedule={hockeyScheduleContext?.home ?? null}
      />
      <PrematchTeamColumn
        teamName={awayTeamName}
        history={safeAwayHistory}
        isHockey={isHockey}
        lookback={effectiveLookback}
        ouLine={ouLine}
        schedule={hockeyScheduleContext?.away ?? null}
      />
    </div>
  );
}
