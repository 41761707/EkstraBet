"use client";

import { useState } from "react";
import { OuBttsStandingsTable } from "@/components/OuBttsStandingsTable";
import { StandingsTable } from "@/components/StandingsTable";
import type {
  OuBttsStandingRow,
  StandingScope,
  TraditionalStandingRow,
} from "@/types/api";

const TAB_LABELS: Record<StandingScope, string> = {
  overall: "Tabela ligowa",
  home: "Tabela domowa",
  away: "Tabela wyjazdowa",
  ou_btts: "Tabela OU / BTTS",
};

interface LeagueStandingsSectionProps {
  overall: TraditionalStandingRow[];
  home: TraditionalStandingRow[];
  away: TraditionalStandingRow[];
  ouBtts: OuBttsStandingRow[];
  seasonId: number;
  leagueId: number;
  embedded?: boolean;
}

export function LeagueStandingsSection({
  overall,
  home,
  away,
  ouBtts,
  seasonId,
  leagueId,
  embedded = false,
}: LeagueStandingsSectionProps) {
  const [activeScope, setActiveScope] = useState<StandingScope>("overall");

  const traditionalByScope: Record<
    "overall" | "home" | "away",
    TraditionalStandingRow[]
  > = {
    overall,
    home,
    away,
  };

  return (
    <section className="space-y-4">
      {embedded ? null : (
        <h2 className="text-lg font-semibold text-white">Tabele ligowe</h2>
      )}
      <div className="flex flex-wrap gap-2 border-b border-slate-700/80 pb-3">
        {(Object.keys(TAB_LABELS) as StandingScope[]).map((scope) => (
          <button
            key={scope}
            type="button"
            onClick={() => setActiveScope(scope)}
            className={`rounded-full px-3 py-1.5 text-sm transition ${
              activeScope === scope
                ? "bg-sky-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {TAB_LABELS[scope]}
          </button>
        ))}
      </div>

      {activeScope === "ou_btts" ? (
        <>
          <OuBttsStandingsTable
            standings={ouBtts}
            seasonId={seasonId}
            leagueId={leagueId}
          />
          <p className="text-sm text-slate-500">
            Drużyny prezentowane są w kolejności alfabetycznej.
          </p>
        </>
      ) : (
        <StandingsTable
          standings={traditionalByScope[activeScope]}
          seasonId={seasonId}
          leagueId={leagueId}
        />
      )}
    </section>
  );
}
