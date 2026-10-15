import { HorizontalExpectedValueBars } from "@/components/charts/HorizontalExpectedValueBars";
import { HorizontalProbabilityBars } from "@/components/charts/HorizontalProbabilityBars";
import { predictionStageLabel } from "@/components/matches/hockeyLineupModel";
import {
  buildExpectedGoalBars,
  buildExpectedShotBars,
  buildPlayerProbabilityBars,
  formatExpectedShots,
  hasHockeyPlayerPredictions,
  toPropColumns,
  type HockeyPlayerPropColumns,
} from "@/components/matches/hockeyPlayerPredictionsModel";
import { StatusMessage } from "@/components/StatusMessage";
import { formatPercent } from "@/lib/format";
import type {
  HockeyPlayerPrediction,
  HockeyPlayerPredictions,
  HockeyPredictionStage,
} from "@/types/api";

interface HockeyPlayerPredictionsPanelProps {
  predictions: HockeyPlayerPredictions | null;
  homeTeamName: string;
  awayTeamName: string;
  predictionStage?: HockeyPredictionStage | null;
}

const STAGE_BADGE_CLASS =
  "rounded border border-info-border bg-info-bg px-1.5 py-0.5 text-xs font-medium text-info-text";

export function HockeyPlayerPredictionsPanel({
  predictions,
  homeTeamName,
  awayTeamName,
  predictionStage = null,
}: HockeyPlayerPredictionsPanelProps) {
  const stageLabel = predictionStageLabel(predictionStage);

  if (!hasHockeyPlayerPredictions(predictions)) {
    return (
      <div className="space-y-3">
        {stageLabel ? <StageBadge label={stageLabel} /> : null}
        <StatusMessage
          variant="empty"
          title="Brak predykcji zawodników"
          message="Prawdopodobieństwa statystyk nie są jeszcze policzone dla tego meczu."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {stageLabel ? <StageBadge label={stageLabel} /> : null}
      <p className="text-sm text-muted">
        Beta: prawdopodobieństwa statystyk zawodnika, bez kursów i bez
        rozliczania.
      </p>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <TeamColumn
          teamName={homeTeamName}
          players={predictions?.home ?? []}
        />
        <TeamColumn
          teamName={awayTeamName}
          players={predictions?.away ?? []}
        />
      </div>
    </div>
  );
}

function StageBadge({ label }: { label: string }) {
  return <p className={STAGE_BADGE_CLASS}>{label}</p>;
}

const TEAM_COLUMN_CLASS = [
  "grid min-w-0 gap-4",
  "grid-rows-[auto_auto_auto_auto_auto_auto_auto]",
  "xl:grid-rows-subgrid xl:row-span-7",
].join(" ");

function TeamColumn({
  teamName,
  players,
}: {
  teamName: string;
  players: HockeyPlayerPrediction[];
}) {
  return (
    <section className={TEAM_COLUMN_CLASS}>
      <h3 className="text-lg font-semibold text-text">{teamName}</h3>
      <TeamCharts players={players} />
      {players.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak predykcji"
          message="Ta drużyna nie ma predykcji zawodników."
        />
      ) : (
        <PredictionsTable rows={players.map(toPropColumns)} />
      )}
    </section>
  );
}

function TeamCharts({ players }: { players: HockeyPlayerPrediction[] }) {
  return (
    <>
      <HorizontalExpectedValueBars
        title="Oczekiwane strzały"
        points={buildExpectedShotBars(players)}
        emptyMessage="Brak oczekiwanych strzałów."
      />
      <HorizontalExpectedValueBars
        title="Oczekiwane gole"
        points={buildExpectedGoalBars(players)}
        emptyMessage="Brak oczekiwanych goli."
      />
      <HorizontalProbabilityBars
        title="Prawdopodobieństwo gola"
        points={buildPlayerProbabilityBars(players, "goal")}
        emptyMessage="Brak prawdopodobieństw gola."
      />
      <HorizontalProbabilityBars
        title="Prawdopodobieństwo asysty"
        points={buildPlayerProbabilityBars(players, "assist")}
        emptyMessage="Brak prawdopodobieństw asysty."
      />
      <HorizontalProbabilityBars
        title="Prawdopodobieństwo punktu"
        points={buildPlayerProbabilityBars(players, "point")}
        emptyMessage="Brak prawdopodobieństw punktu."
      />
    </>
  );
}

function PredictionsTable({ rows }: { rows: HockeyPlayerPropColumns[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full table-fixed text-sm">
        <colgroup>
          <col className="w-[24%]" />
          <col className="w-[12%]" />
          <col className="w-[14%]" />
          <col className="w-[12%]" />
          <col className="w-[13%]" />
          <col className="w-[13%]" />
          <col className="w-[12%]" />
        </colgroup>
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-2 py-2 font-medium">Zawodnik</th>
            <th className="px-2 py-2 text-center font-medium">E[SOG]</th>
            <th className="px-2 py-2 text-center font-medium">P(SOG &gt; 2.5)</th>
            <th className="px-2 py-2 text-center font-medium">P(gol)</th>
            <th className="px-2 py-2 text-center font-medium">P(asysta)</th>
            <th className="px-2 py-2 text-center font-medium">P(punkt)</th>
            <th className="px-2 py-2 text-center font-medium">P(2+ pkt)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.playerId}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-2 py-2 font-medium text-text">{row.playerName}</td>
              <td className="px-2 py-2 text-center text-text">
                {formatExpectedShots(row.expectedShots)}
              </td>
              <td className="px-2 py-2 text-center text-text">
                {formatPercent(row.shotsOver25)}
              </td>
              <td className="px-2 py-2 text-center text-text">
                {formatPercent(row.goalProbability)}
              </td>
              <td className="px-2 py-2 text-center text-text">
                {formatPercent(row.assistProbability)}
              </td>
              <td className="px-2 py-2 text-center text-text">
                {formatPercent(row.pointProbability)}
              </td>
              <td className="px-2 py-2 text-center text-text">
                {formatPercent(row.twoPointProbability)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
