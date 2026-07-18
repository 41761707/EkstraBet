import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
  getTeamComparisonBarColor,
} from "@/lib/chartColors";
import { formatPercent } from "@/lib/format";

export interface TeamComparisonPoint {
  teamName: string;
  value: number;
}

interface TeamLeagueComparisonChartProps {
  title: string;
  teams: TeamComparisonPoint[];
  leagueAverage: number;
  averageLabel?: string;
}

export function TeamLeagueComparisonChart({
  title,
  teams,
  leagueAverage,
  averageLabel = "Średnia ligi",
}: TeamLeagueComparisonChartProps) {
  if (teams.length === 0) {
    return null;
  }

  const sorted = [...teams].sort((left, right) => left.value - right.value);
  const maxValue = Math.max(
    ...sorted.map((team) => team.value),
    leagueAverage,
    1,
  );
  const averagePosition = (leagueAverage / maxValue) * 100;

  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-white">{title}</h4>
        <span className="text-xs text-slate-400">
          {averageLabel}: {formatPercent(leagueAverage)}
        </span>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_POSITIVE }}
          />
          Powyżej średniej
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_NEGATIVE }}
          />
          Poniżej średniej
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_DRAW }}
          />
          Na średniej
        </span>
      </div>

      <div className="relative max-h-96 overflow-y-auto pr-1">
        <div className="pointer-events-none absolute bottom-0 left-[7.75rem] right-0 top-0">
          <div
            className="absolute bottom-0 top-0 border-l border-dashed"
            style={{
              left: `${averagePosition}%`,
              borderColor: `${CHART_COLOR_DRAW}cc`,
            }}
            title={`${averageLabel}: ${formatPercent(leagueAverage)}`}
          />
        </div>

        <div className="space-y-2">
          {sorted.map((team) => {
            const width = (team.value / maxValue) * 100;
            return (
              <div
                key={team.teamName}
                className="grid grid-cols-[7.5rem_1fr] items-center gap-3"
              >
                <span
                  className="truncate text-xs text-slate-300"
                  title={team.teamName}
                >
                  {team.teamName}
                </span>
                <div className="relative h-6 rounded-md bg-slate-800/80">
                  <div
                    className="flex h-6 items-center rounded-md px-2 text-xs font-medium text-slate-950"
                    style={{
                      width: `${Math.max(width, 4)}%`,
                      backgroundColor: getTeamComparisonBarColor(
                        team.value,
                        leagueAverage,
                      ),
                    }}
                  >
                    <span className="whitespace-nowrap">
                      {formatPercent(team.value)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
