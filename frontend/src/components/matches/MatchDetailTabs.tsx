"use client";

import { useState } from "react";
import { HockeyMatchBoxscorePanel } from "@/components/matches/HockeyMatchBoxscorePanel";
import { MatchBoxscorePanel } from "@/components/matches/MatchBoxscorePanel";
import { HockeyMatchStatsPanel } from "@/components/matches/HockeyMatchStatsPanel";
import { MatchPrematchStatsSection } from "@/components/matches/MatchPrematchStatsSection";
import { MatchOddsGroupedTables } from "@/components/MatchOddsGroupedTables";
import { MatchPredictionsTable } from "@/components/MatchPredictionsTable";
import { MatchStatsPanel } from "@/components/MatchStatsPanel";
import { PlayedBetterAssessmentPanel } from "@/components/matches/PlayedBetterAssessmentPanel";
import { ExpandableSection } from "@/components/ExpandableSection";
import { StatusMessage } from "@/components/StatusMessage";
import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import { teamChartLabel } from "@/components/predictions/predictionChartModel";
import type { MatchDetails } from "@/types/api";

interface MatchDetailTabsProps {
  match: MatchDetails;
}

type MatchTab = "prematch" | "predictions" | "stats" | "boxscore";

export function MatchDetailTabs({ match }: MatchDetailTabsProps) {
  const [activeTab, setActiveTab] = useState<MatchTab>("prematch");

  const tabs: { id: MatchTab; label: string; visible: boolean }[] = [
    { id: "prematch", label: "Statystyki przedmeczowe", visible: true },
    { id: "predictions", label: "Predykcje i kursy", visible: true },
    {
      id: "stats",
      label: "Statystyki pomeczowe",
      visible:
        match.is_played &&
        (match.stats !== null || match.hockey_stats !== null),
    },
    {
      id: "boxscore",
      label: "Boxscore - statystyki zawodników",
      visible: match.has_player_stats && match.is_played,
    },
  ];

  const visibleTabs = tabs.filter((tab) => tab.visible);
  const homeTeamLabel = teamChartLabel(match.home_team);
  const awayTeamLabel = teamChartLabel(match.away_team);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 border-b border-slate-700/80 pb-1">
        {visibleTabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? "border-sky-400 text-sky-200"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === "prematch" ? (
        <MatchPrematchStatsSection
          sportId={match.sport_id}
          homeTeamName={match.home_team.name}
          awayTeamName={match.away_team.name}
          seasonId={match.season_id}
          leagueId={match.league_id}
          headToHead={match.head_to_head}
          homeTeamHistory={match.home_team_history}
          awayTeamHistory={match.away_team_history}
        />
      ) : null}

      {activeTab === "predictions" ? (
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
                title="No predictions"
                message="Final predictions are not available for this match."
              />
            ) : (
              <MatchPredictionsTable predictions={match.final_predictions} />
            )}
          </ExpandableSection>

          <ExpandableSection title={`Kursy (${match.odds.length})`} defaultOpen>
            {match.odds.length === 0 ? (
              <StatusMessage
                variant="empty"
                title="No odds"
                message="Bookmaker odds are not available for this match."
              />
            ) : (
              <MatchOddsGroupedTables
                odds={match.odds}
                predictions={match.final_predictions}
              />
            )}
          </ExpandableSection>
        </div>
      ) : null}

      {activeTab === "stats" && match.hockey_stats ? (
        <HockeyMatchStatsPanel
          stats={match.hockey_stats}
          homeTeamName={match.home_team.name}
          awayTeamName={match.away_team.name}
        />
      ) : null}

      {activeTab === "stats" && !match.hockey_stats && match.stats ? (
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
      ) : null}

      {activeTab === "boxscore" && match.has_player_stats ? (
        match.hockey_boxscore ? (
          <HockeyMatchBoxscorePanel boxscore={match.hockey_boxscore} />
        ) : match.boxscore && match.boxscore.length > 0 ? (
          <MatchBoxscorePanel
            homeTeamId={match.home_team.id}
            homeTeamName={match.home_team.name}
            awayTeamId={match.away_team.id}
            awayTeamName={match.away_team.name}
            players={match.boxscore}
          />
        ) : (
          <StatusMessage
            variant="empty"
            title="Brak statystyk zawodników"
            message="Statystyki zawodników nie są dostępne dla tego meczu."
          />
        )
      ) : null}
    </div>
  );
}
