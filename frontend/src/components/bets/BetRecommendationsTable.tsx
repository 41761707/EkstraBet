import Link from "next/link";
import {
  formatEv,
  formatMatchDateTime,
  formatOdds,
  formatPercent,
} from "@/lib/format";
import type { BetRecommendation, SettlementStatus } from "@/types/api";

interface BetRecommendationsTableProps {
  recommendations: BetRecommendation[];
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

export function BetRecommendationsTable({
  recommendations,
  applyTax,
}: BetRecommendationsTableProps) {
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
          {recommendations.map((bet) => {
            const evValue = applyTax ? bet.ev_after_tax : bet.ev;
            const evClassName =
              evValue !== null && evValue !== undefined && evValue > 0
                ? "text-success"
                : evValue !== null && evValue !== undefined && evValue < 0
                  ? "text-danger"
                  : "text-text";

            return (
              <tr
                key={bet.bet_id}
                className="border-t border-border hover:bg-surface-muted/50"
              >
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
                <td className="px-4 py-3 text-muted">{bet.event_name}</td>
                <td className="px-4 py-3 text-muted">{bet.model_name}</td>
                <td className="px-4 py-3 text-muted">
                  {bet.bookmaker_name ?? "—"}
                </td>
                <td className="px-4 py-3 text-right text-text">
                  {formatOdds(bet.odds)}
                </td>
                <td className="px-4 py-3 text-right text-text">
                  {formatPercent(bet.probability_pct)}
                </td>
                <td className={`px-4 py-3 text-right font-medium ${evClassName}`}>
                  {formatEv(evValue)}
                </td>
                <td
                  className={`px-4 py-3 ${settlementStyles[bet.settlement_status] ?? "text-muted"}`}
                >
                  {settlementLabels[bet.settlement_status] ??
                    bet.settlement_status}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
