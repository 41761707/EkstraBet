"use client";

import { HockeyMatchBoxscorePanel } from "@/components/matches/HockeyMatchBoxscorePanel";
import { HockeyMatchEventsPanel } from "@/components/matches/HockeyMatchEventsPanel";
import { HockeyMatchStatsPanel } from "@/components/matches/HockeyMatchStatsPanel";
import { HockeyPlayerPredictionsPanel } from "@/components/matches/HockeyPlayerPredictionsPanel";
import { MatchBoxscorePanel } from "@/components/matches/MatchBoxscorePanel";
import { MatchLineupsTabContent } from "@/components/matches/MatchLineupsTabContent";
import { MatchPrematchStatsSection } from "@/components/matches/MatchPrematchStatsSection";
import { MatchOddsGroupedTables } from "@/components/MatchOddsGroupedTables";
import { buildUstaloneMarketPredictions } from "@/components/matchOddsTableModel";
import { MatchPredictionsTable } from "@/components/MatchPredictionsTable";
import { MatchStatsPanel } from "@/components/MatchStatsPanel";
import { PlayedBetterAssessmentPanel } from "@/components/matches/PlayedBetterAssessmentPanel";
import { ExpandableSection } from "@/components/ExpandableSection";
import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import { teamChartLabel } from "@/components/predictions/predictionChartModel";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type MatchDetails,
} from "@/types/api";

export type MatchTab =
  | "prematch"
  | "predictions"
  | "lineups"
  | "players"
  | "events"
  | "stats"
  | "boxscore";

interface MatchDetailTabPanelProps {
  match: MatchDetails;
  tab: MatchTab;
}

export function MatchDetailTabPanel({ match, tab }: MatchDetailTabPanelProps) {
  if (tab === "prematch") {
    return <PrematchTab match={match} />;
  }
  if (tab === "predictions") {
    return <PredictionsTab match={match} />;
  }
  if (tab === "lineups") {
    return <MatchLineupsTabContent match={match} />;
  }
  if (tab === "players") {
    return <PlayersTab match={match} />;
  }
  if (tab === "events") {
    return <EventsTab match={match} />;
  }
  if (tab === "stats") {
    return <PlayedStatsTab match={match} />;
  }
  if (tab === "boxscore") {
    return <BoxscoreTab match={match} />;
  }
  return null;
}

function PrematchTab({ match }: { match: MatchDetails }) {
  return (
    <MatchPrematchStatsSection
      sportId={match.sport_id}
      homeTeamName={match.home_team.name}
      awayTeamName={match.away_team.name}
      seasonId={match.season_id}
      leagueId={match.league_id}
      headToHead={match.head_to_head}
      homeTeamHistory={match.home_team_history}
      awayTeamHistory={match.away_team_history}
      hockeyScheduleContext={match.hockey_schedule_context}
    />
  );
}

function PredictionsTab({ match }: { match: MatchDetails }) {
  const { preferences } = usePreferences();
  const homeTeamLabel = teamChartLabel(
    match.home_team,
    preferences.teamNameDisplay,
  );
  const awayTeamLabel = teamChartLabel(
    match.away_team,
    preferences.teamNameDisplay,
  );

  return (
    <div className="space-y-4">
      {match.prediction_analysis ? (
        <PredictionSimulationResult
          result={match.prediction_analysis}
          homeTeamLabel={homeTeamLabel}
          awayTeamLabel={awayTeamLabel}
          title="Analiza predykcji"
        />
      ) : null}
      <ExpandableSection
        title={`Predykcje (${match.final_predictions.length})`}
        defaultOpen
      >
        {match.final_predictions.length === 0 ? (
          <StatusMessage
            variant="empty"
            title="Brak predykcji"
            message="Predykcje końcowe nie są dostępne dla tego meczu."
          />
        ) : (
          <MatchPredictionsTable predictions={match.final_predictions} />
        )}
      </ExpandableSection>
      <OddsSection match={match} />
    </div>
  );
}

function OddsSection({ match }: { match: MatchDetails }) {
  const predictions = buildUstaloneMarketPredictions(
    match.prediction_analysis,
    match.final_predictions,
  );
  const sportId = match.sport_id ?? FOOTBALL_SPORT_ID;
  const hasHockeyPredictions =
    sportId === HOCKEY_SPORT_ID && predictions.length > 0;
  const hasOdds = match.odds.length > 0 || hasHockeyPredictions;

  return (
    <ExpandableSection title={`Kursy (${match.odds.length})`} defaultOpen>
      {hasOdds ? (
        <MatchOddsGroupedTables
          odds={match.odds}
          predictions={predictions}
          sportId={sportId}
        />
      ) : (
        <StatusMessage
          variant="empty"
          title="Brak kursów"
          message="Kursy bukmacherskie nie są dostępne dla tego meczu."
        />
      )}
    </ExpandableSection>
  );
}

function PlayersTab({ match }: { match: MatchDetails }) {
  return (
    <HockeyPlayerPredictionsPanel
      predictions={match.hockey_player_predictions}
      homeTeamName={match.home_team.name}
      awayTeamName={match.away_team.name}
      predictionStage={match.hockey_prediction_stage}
    />
  );
}

function EventsTab({ match }: { match: MatchDetails }) {
  return (
    <HockeyMatchEventsPanel
      events={match.hockey_events ?? []}
      homeTeamName={match.home_team.name}
      awayTeamName={match.away_team.name}
    />
  );
}

function PlayedStatsTab({ match }: { match: MatchDetails }) {
  if (match.hockey_stats) {
    return (
      <HockeyMatchStatsPanel
        stats={match.hockey_stats}
        homeTeamName={match.home_team.name}
        awayTeamName={match.away_team.name}
      />
    );
  }
  if (!match.stats) {
    return null;
  }
  return (
    <div className="space-y-6">
      <MatchStatsPanel
        stats={match.stats}
        homeTeamName={match.home_team.name}
        awayTeamName={match.away_team.name}
      />
      <PlayedBetterAssessmentPanel
        assessments={match.model_assessments}
        homeTeamName={match.home_team.name}
        awayTeamName={match.away_team.name}
        homeGoals={match.home_goals}
        awayGoals={match.away_goals}
      />
    </div>
  );
}

function BoxscoreTab({ match }: { match: MatchDetails }) {
  if (!match.has_player_stats) {
    return null;
  }
  if (match.hockey_boxscore) {
    return <HockeyMatchBoxscorePanel boxscore={match.hockey_boxscore} />;
  }
  if (match.boxscore && match.boxscore.length > 0) {
    return (
      <MatchBoxscorePanel
        homeTeamId={match.home_team.id}
        homeTeamName={match.home_team.name}
        awayTeamId={match.away_team.id}
        awayTeamName={match.away_team.name}
        players={match.boxscore}
      />
    );
  }
  return (
    <StatusMessage
      variant="empty"
      title="Brak statystyk zawodników"
      message="Statystyki zawodników nie są dostępne dla tego meczu."
    />
  );
}
