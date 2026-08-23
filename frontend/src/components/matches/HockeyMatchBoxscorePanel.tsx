"use client";

import type {
  HockeyGoalieBoxscoreRow,
  HockeyMatchBoxscore,
  HockeySkaterBoxscoreRow,
} from "@/types/api";

interface HockeyMatchBoxscorePanelProps {
  boxscore: HockeyMatchBoxscore;
}

function formatValue(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return String(value);
}

function plusMinusClassName(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) {
    return "text-text";
  }
  if (value > 0) {
    return "bg-success-bg font-semibold text-success-text";
  }
  return "bg-danger-bg font-semibold text-danger-text";
}

function GoaliesTable({ rows }: { rows: HockeyGoalieBoxscoreRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted">
        Brak statystyk bramkarzy dla tego meczu.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">Drużyna</th>
            <th className="px-3 py-2 font-medium">Zawodnik</th>
            <th className="px-3 py-2 text-center font-medium">Pkt</th>
            <th className="px-3 py-2 text-center font-medium">Kary (MIN)</th>
            <th className="px-3 py-2 text-center font-medium">TOI</th>
            <th className="px-3 py-2 text-center font-medium">Strzały</th>
            <th className="px-3 py-2 text-center font-medium">Obronione</th>
            <th className="px-3 py-2 text-center font-medium">Obrony (%)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={`${row.player_id}-${row.team_id}`}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-3 py-2 text-subtle">{index + 1}</td>
              <td className="px-3 py-2 text-muted">{row.team_name}</td>
              <td className="px-3 py-2 font-medium text-text">
                {row.player_name}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.points)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.penalty_minutes)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.time_on_ice)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.shots_against)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.shots_saved)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {row.saves_accuracy !== null
                  ? row.saves_accuracy.toFixed(2)
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SkatersTable({ rows }: { rows: HockeySkaterBoxscoreRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted">
        Brak statystyk zawodników z pola dla tego meczu.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">Drużyna</th>
            <th className="px-3 py-2 font-medium">Zawodnik</th>
            <th className="px-3 py-2 text-center font-medium">B</th>
            <th className="px-3 py-2 text-center font-medium">A</th>
            <th className="px-3 py-2 text-center font-medium">Pkt</th>
            <th className="px-3 py-2 text-center font-medium">+/-</th>
            <th className="px-3 py-2 text-center font-medium">Kary (MIN)</th>
            <th className="px-3 py-2 text-center font-medium">SOG</th>
            <th className="px-3 py-2 text-center font-medium">TOI</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={`${row.player_id}-${row.team_id}`}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-3 py-2 text-subtle">{index + 1}</td>
              <td className="px-3 py-2 text-muted">{row.team_name}</td>
              <td className="px-3 py-2 font-medium text-text">
                {row.player_name}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.goals)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.assists)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.points)}
              </td>
              <td
                className={`px-3 py-2 text-center ${plusMinusClassName(
                  row.plus_minus,
                )}`}
              >
                {formatValue(row.plus_minus)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.penalty_minutes)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.shots_on_goal)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatValue(row.time_on_ice)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function HockeyMatchBoxscorePanel({
  boxscore,
}: HockeyMatchBoxscorePanelProps) {
  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-text">Bramkarze</h3>
        <GoaliesTable rows={boxscore.goalies} />
      </section>

      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-text">Zawodnicy</h3>
        <SkatersTable rows={boxscore.skaters} />
      </section>
    </div>
  );
}
