import {
  formatRating,
  groupRatingRows,
  ratingScale,
  ratingTooltip,
  type HockeyRatingMetric,
} from "@/components/matches/hockeyGameRatingModel";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type {
  HockeyGameRating,
  HockeyRatedPlayer,
  HockeyRatedTeam,
} from "@/types/api";

const RATING_DESCRIPTION =
  "Liczba jest w skali punktów z protokołu. Trzy punkty przy spokojnej defensywie zostają koło 3.";

const EMPTY_TEAM_LABEL = "Brak oceny";

const CHARTS: readonly { metric: HockeyRatingMetric; title: string }[] = [
  { metric: "total", title: "Ogólna" },
  { metric: "offense", title: "Ofensywa" },
  { metric: "defense", title: "Defensywa" },
];

const GROUP_ORDER: readonly HockeyRatedPlayer["group"][] = [
  "forward",
  "defense",
  "goalie",
];

const GROUP_LABELS: Record<HockeyRatedPlayer["group"], string> = {
  forward: "Napastnicy",
  defense: "Obrońcy",
  goalie: "Bramkarze",
};

interface HockeyGameRatingChartsProps {
  rating: HockeyGameRating | null;
}

/** Two team columns under the box score. Hidden when the match has no rating. */
export function HockeyGameRatingCharts({ rating }: HockeyGameRatingChartsProps) {
  if (!rating) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold text-text">Ocena</h3>
      <p className="text-sm text-muted">{RATING_DESCRIPTION}</p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {rating.teams.map((team) => (
          <HockeyRatingTeamColumn key={team.team_id} team={team} />
        ))}
      </div>
    </section>
  );
}

function HockeyRatingTeamColumn({ team }: { team: HockeyRatedTeam }) {
  const scale = ratingScale(team.players);

  return (
    <div className="min-w-0 space-y-3">
      <h4 className="text-base font-semibold text-text">{team.team_name}</h4>
      {team.players.length === 0 ? (
        <p className="text-sm text-muted">{EMPTY_TEAM_LABEL}</p>
      ) : (
        CHARTS.map((chart) => (
          <HockeyRatingChartCard
            key={chart.metric}
            title={chart.title}
            metric={chart.metric}
            players={team.players}
            scale={scale}
          />
        ))
      )}
    </div>
  );
}

function HockeyRatingChartCard({
  title,
  metric,
  players,
  scale,
}: {
  title: string;
  metric: HockeyRatingMetric;
  players: readonly HockeyRatedPlayer[];
  scale: number;
}) {
  const grouped = groupRatingRows(players, metric);

  return (
    <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <h5 className="text-sm font-semibold text-text">{title}</h5>
      {GROUP_ORDER.map((group) => {
        const rows = grouped[group];
        if (rows.length === 0) {
          return null;
        }
        return (
          <HockeyRatingGroup
            key={group}
            label={GROUP_LABELS[group]}
            rows={rows}
            metric={metric}
            scale={scale}
          />
        );
      })}
    </div>
  );
}

function HockeyRatingGroup({
  label,
  rows,
  metric,
  scale,
}: {
  label: string;
  rows: readonly HockeyRatedPlayer[];
  metric: HockeyRatingMetric;
  scale: number;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted">{label}</p>
      {rows.map((player) => (
        <HockeyRatingBarRow
          key={player.player_id}
          player={player}
          metric={metric}
          scale={scale}
        />
      ))}
    </div>
  );
}

function HockeyRatingBarRow({
  player,
  metric,
  scale,
}: {
  player: HockeyRatedPlayer;
  metric: HockeyRatingMetric;
  scale: number;
}) {
  const value = player[metric];
  const tooltip = ratingTooltip(player.parts);
  const width = (Math.abs(value) / scale) * 50;
  const isNegative = value < 0;

  return (
    <div
      className="grid items-center gap-2"
      style={{ gridTemplateColumns: "minmax(0,8.5rem) minmax(0,1fr) auto" }}
      title={tooltip || undefined}
    >
      <span className="truncate text-xs text-text">{player.player_name}</span>
      <div className="relative h-6 overflow-hidden rounded-md bg-chart-track">
        <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px bg-border" />
        {value === 0 ? null : (
          <div
            className="absolute inset-y-0"
            style={{
              width: `${width}%`,
              backgroundColor: isNegative ? CHART_COLOR_NEGATIVE : CHART_COLOR_POSITIVE,
              ...(isNegative ? { right: "50%" } : { left: "50%" }),
            }}
          />
        )}
      </div>
      <span className="text-xs tabular-nums text-text">{formatRating(value)}</span>
    </div>
  );
}
