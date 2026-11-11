import Link from "next/link";

import {
  formatEv,
  formatMatchDateTime,
  formatOdds,
  formatPercent,
} from "@/lib/format";
import type { PlayerPropRecommendation, SettlementStatus } from "@/types/api";

interface PlayerBetRecommendationsTableProps {
  recommendations: PlayerPropRecommendation[];
  applyTax: boolean;
}

const settlementStyles: Record<string, string> = {
  pending: "text-warning",
  won: "text-success",
  lost: "text-danger",
};

const settlementLabels: Record<SettlementStatus, string> = {
  pending: "Oczekujący",
  won: "Wygrany",
  lost: "Przegrany",
};

export function PlayerBetRecommendationsTable({
  recommendations,
  applyTax,
}: PlayerBetRecommendationsTableProps) {
  if (recommendations.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Data</th>
            <th className="px-4 py-3 font-medium">Liga</th>
            <th className="px-4 py-3 font-medium">Mecz</th>
            <th className="px-4 py-3 font-medium">Zawodnik</th>
            <th className="px-4 py-3 font-medium">Zdarzenie</th>
            <th className="px-4 py-3 font-medium">Model</th>
            <th className="px-4 py-3 font-medium">Bukmacher</th>
            <th className="px-4 py-3 text-right font-medium">Kurs</th>
            <th className="px-4 py-3 text-right font-medium">Prawd.</th>
            <th className="px-4 py-3 text-right font-medium">EV</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {recommendations.map((bet) => (
            <PlayerBetRow
              key={`${bet.line_id}-${bet.model_id}`}
              bet={bet}
              applyTax={applyTax}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayerBetRow({
  bet,
  applyTax,
}: {
  bet: PlayerPropRecommendation;
  applyTax: boolean;
}) {
  const evValue = applyTax ? bet.ev_after_tax : bet.ev;
  return (
    <tr className="border-t border-border hover:bg-surface-muted/50">
      <td className="px-4 py-3 text-muted">
        <Link
          href={`/matches/${bet.match_id}`}
          className="transition hover:text-accent-text-hover"
        >
          {formatMatchDateTime(bet.game_date)}
        </Link>
      </td>
      <td className="px-4 py-3 text-muted">{bet.league_name}</td>
      <td className="px-4 py-3 font-medium text-text">
        <Link
          href={`/matches/${bet.match_id}`}
          className="transition hover:text-accent-text-hover"
        >
          {bet.home_team.name} – {bet.away_team.name}
        </Link>
      </td>
      <td className="px-4 py-3 text-text">{bet.player_name}</td>
      <td className="px-4 py-3 text-muted">{bet.event_name}</td>
      <td className="px-4 py-3 text-muted">{bet.model_name}</td>
      <td className="px-4 py-3 text-muted">{bet.bookmaker_name ?? "—"}</td>
      <td className="px-4 py-3 text-right text-text">{formatOdds(bet.odds)}</td>
      <td className="px-4 py-3 text-right text-text">
        {formatPercent(bet.probability_pct)}
      </td>
      <td className={`px-4 py-3 text-right font-medium ${evTone(evValue)}`}>
        {formatEv(evValue)}
      </td>
      <td
        className={`px-4 py-3 ${settlementStyles[bet.settlement_status] ?? "text-muted"}`}
      >
        {settlementLabels[bet.settlement_status] ?? bet.settlement_status}
      </td>
    </tr>
  );
}

function evTone(evValue: number | null | undefined): string {
  if (evValue != null && evValue > 0) {
    return "text-success";
  }
  if (evValue != null && evValue < 0) {
    return "text-danger";
  }
  return "text-text";
}
