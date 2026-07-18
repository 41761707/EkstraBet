import { ExpandableSection } from "@/components/ExpandableSection";
import { TeamLeagueComparisonChart } from "@/components/charts/TeamLeagueComparisonChart";
import { winRatePercentage } from "@/components/leagues/leagueStatsUtils";
import type {
  LeagueCharacteristics,
  OuBttsStandingRow,
  TraditionalStandingRow,
} from "@/types/api";

interface LeagueTeamComparisonsSectionProps {
  characteristics: LeagueCharacteristics;
  ouBtts: OuBttsStandingRow[];
  homeStandings: TraditionalStandingRow[];
  awayStandings: TraditionalStandingRow[];
}

export function LeagueTeamComparisonsSection({
  characteristics,
  ouBtts,
  homeStandings,
  awayStandings,
}: LeagueTeamComparisonsSectionProps) {
  const bttsAverage = characteristics.btts.yes?.percentage ?? 0;
  const ouAverage = characteristics.ou.over_2_5?.percentage ?? 0;
  const homeAverage = characteristics.result.home?.percentage ?? 0;
  const awayAverage = characteristics.result.away?.percentage ?? 0;

  return (
    <ExpandableSection title="Porównanie drużyn ze średnią ligową">
      <div className="space-y-3">
        <p className="text-sm text-slate-400">
          Wykresy pokazują, jak procentowe wskaźniki drużyn wypadają na tle
          średniej ligowej (linia przerywana). Zielony — powyżej średniej,
          czerwony — poniżej.
        </p>

        <ExpandableSection title="BTTS — udział meczów z golami obu drużyn">
          <TeamLeagueComparisonChart
            title="BTTS tak (%)"
            leagueAverage={bttsAverage}
            teams={ouBtts.map((team) => ({
              teamName: team.team_name,
              value: team.btts_percentage,
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Over 2.5 — mecze z co najmniej 3 bramkami">
          <TeamLeagueComparisonChart
            title="Over 2.5 (%)"
            leagueAverage={ouAverage}
            teams={ouBtts.map((team) => ({
              teamName: team.team_name,
              value: team.over_2_5_percentage,
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Zwycięstwa u siebie">
          <TeamLeagueComparisonChart
            title="Wygrane u siebie (%)"
            leagueAverage={homeAverage}
            teams={homeStandings.map((team) => ({
              teamName: team.team_name,
              value: winRatePercentage(team.wins, team.played),
            }))}
          />
        </ExpandableSection>

        <ExpandableSection title="Zwycięstwa na wyjeździe">
          <TeamLeagueComparisonChart
            title="Wygrane na wyjeździe (%)"
            leagueAverage={awayAverage}
            teams={awayStandings.map((team) => ({
              teamName: team.team_name,
              value: winRatePercentage(team.wins, team.played),
            }))}
          />
        </ExpandableSection>
      </div>
    </ExpandableSection>
  );
}
