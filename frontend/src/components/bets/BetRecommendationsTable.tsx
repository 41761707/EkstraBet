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
  pending: "text-amber-300",
  won: "text-emerald-300",
  lost: "text-red-300",
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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Data</th>
            <th className="px-4 py-3 font-medium">Liga</th>
            <th className="px-4 py-3 font-medium">Mecz</th>
            <th className="px-4 py-3 font-medium">Wydarzenie</th>
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
                ? "text-emerald-300"
                : evValue !== null && evValue !== undefined && evValue < 0
                  ? "text-red-300"
                  : "text-slate-200";

            return (
              <tr
                key={bet.bet_id}
                className="border-t border-slate-800/80 hover:bg-slate-900/50"
              >
                <td className="px-4 py-3 text-slate-300">
                  <Link
                    href={`/matches/${bet.match_id}`}
                    className="transition hover:text-sky-200"
                  >
                    {formatMatchDateTime(bet.game_date)}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-300">{bet.league_name}</td>
                <td className="px-4 py-3 font-medium text-white">
                  <Link
                    href={`/matches/${bet.match_id}`}
                    className="transition hover:text-sky-200"
                  >
                    {bet.home_team.name} – {bet.away_team.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-300">{bet.event_name}</td>
                <td className="px-4 py-3 text-slate-300">{bet.model_name}</td>
                <td className="px-4 py-3 text-slate-300">
                  {bet.bookmaker_name ?? "—"}
                </td>
                <td className="px-4 py-3 text-right text-slate-200">
                  {formatOdds(bet.odds)}
                </td>
                <td className="px-4 py-3 text-right text-slate-200">
                  {formatPercent(bet.probability_pct)}
                </td>
                <td className={`px-4 py-3 text-right font-medium ${evClassName}`}>
                  {formatEv(evValue)}
                </td>
                <td
                  className={`px-4 py-3 ${settlementStyles[bet.settlement_status] ?? "text-slate-300"}`}
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
