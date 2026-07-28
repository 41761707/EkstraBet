import { ExpandableSection } from "@/components/ExpandableSection";
import { TeamLeagueComparisonChart } from "@/components/charts/TeamLeagueComparisonChart";
import type { LeagueComparisons } from "@/types/api";

interface LeagueComparisonsPanelProps {
  comparisons: LeagueComparisons;
}

export function LeagueComparisonsPanel({
  comparisons,
}: LeagueComparisonsPanelProps) {
  const leaguePoints = comparisons.leagues.map((league) => ({
    name: league.league_name,
    btts: league.btts_yes_pct,
    over: league.over_2_5_pct,
    home: league.home_win_pct,
    away: league.away_win_pct,
  }));

  return (
    <ExpandableSection
      title="Porównanie lig ze średnią"
      defaultOpen
    >
      <div className="space-y-3">
        <p className="text-sm text-slate-400">
          Wykresy pokazują wskaźniki wybranych lig na tle średniej ważonej liczbą
          meczów (linia przerywana). Bez wybranego sezonu używany jest
          najnowszy sezon każdej ligi.
        </p>

        <ExpandableSection title="BTTS — udział meczów z golami obu drużyn">
          <TeamLeagueComparisonChart
            title="BTTS tak (%)"
            leagueAverage={comparisons.averages.btts_yes_pct}
            averageLabel="Średnia wybranych"
            labelWidthClassName="10rem"
            teams={leaguePoints.map((league) => ({
              teamName: league.name,
              value: league.btts,
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Over 2.5 — mecze z co najmniej 3 bramkami">
          <TeamLeagueComparisonChart
            title="Over 2.5 (%)"
            leagueAverage={comparisons.averages.over_2_5_pct}
            averageLabel="Średnia wybranych"
            labelWidthClassName="10rem"
            teams={leaguePoints.map((league) => ({
              teamName: league.name,
              value: league.over,
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Zwycięstwa gospodarzy">
          <TeamLeagueComparisonChart
            title="Wygrane gospodarzy (%)"
            leagueAverage={comparisons.averages.home_win_pct}
            averageLabel="Średnia wybranych"
            labelWidthClassName="10rem"
            teams={leaguePoints.map((league) => ({
              teamName: league.name,
              value: league.home,
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Zwycięstwa gości">
          <TeamLeagueComparisonChart
            title="Wygrane gości (%)"
            leagueAverage={comparisons.averages.away_win_pct}
            averageLabel="Średnia wybranych"
            labelWidthClassName="10rem"
            teams={leaguePoints.map((league) => ({
              teamName: league.name,
              value: league.away,
            }))}
          />
        </ExpandableSection>
      </div>
    </ExpandableSection>
  );
}
