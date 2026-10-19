import { buildPieSlicesFromSegments } from "@/lib/pieSlices";
import {
  CHART_COLOR_DRAW,
  CHART_LABEL_ON_FILL,
  getTeamComparisonBarColor,
} from "@/lib/chartColors";
import { formatPercent } from "@/lib/format";
import {
  averageHighlights,
  goalBucketViews,
  leagueAverage,
  overUnderHighlights,
  sortBestFirst,
  specialTeamsHighlights,
  teamBarPoints,
  type StatHighlight,
  type TeamBarPoint,
} from "@/lib/hockeyLeagueStatsModel";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  HockeyGoalsDistribution,
  SportLeagueStatRow,
} from "@/types/api";

const BUCKET_COLORS: Record<string, string> = {
  under_5: "#d95757",
  exactly_5: "#4ECDC4",
  exactly_6: "#45B7D1",
  exactly_7: "#96CEB4",
  over_7: "#d9b44a",
};

interface HockeyLeagueStatsPanelsProps {
  category: string;
  rows: SportLeagueStatRow[];
  goalsDistribution?: HockeyGoalsDistribution | null;
}

function HighlightGrid({ items }: { items: StatHighlight[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-xl border border-border bg-surface p-4"
        >
          <p className="text-xs text-muted">{item.label}</p>
          <p className="text-2xl font-semibold text-text">{item.value}</p>
          {item.detail ? (
            <p className="text-sm text-muted">{item.detail}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function barColor(
  value: number,
  average: number,
  higherIsBetter: boolean,
): string {
  if (higherIsBetter) {
    return getTeamComparisonBarColor(value, average);
  }
  return getTeamComparisonBarColor(average, value);
}

function AverageBars({
  title,
  points,
  average,
  higherIsBetter,
  formatValue,
  caption,
  referenceLabel,
}: {
  title: string;
  points: TeamBarPoint[];
  average: number;
  higherIsBetter: boolean;
  formatValue: (value: number) => string;
  caption?: string;
  referenceLabel?: string;
}) {
  if (points.length === 0) {
    return null;
  }
  const sorted = sortBestFirst(points, higherIsBetter);
  const maxValue = Math.max(
    ...sorted.map((point) => point.value),
    average,
    0.01,
  );
  const averagePosition = (average / maxValue) * 100;
  const resolvedCaption =
    caption ??
    (higherIsBetter
      ? "Zielony słupek jest powyżej średniej."
      : "Zielony słupek jest poniżej średniej.");
  const resolvedReference =
    referenceLabel ?? `Średnia: ${formatValue(average)}`;

  return (
    <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-text">{title}</h4>
        <span className="text-xs text-muted">{resolvedReference}</span>
      </div>
      <p className="text-xs text-muted">{resolvedCaption}</p>
      <div className="relative max-h-96 overflow-y-auto pr-1">
        <div
          className="pointer-events-none absolute bottom-0 right-0 top-0"
          style={{ left: "calc(4.5rem + 0.75rem)" }}
        >
          <div
            className="absolute bottom-0 top-0 border-l border-dashed"
            style={{
              left: `${averagePosition}%`,
              borderColor: `${CHART_COLOR_DRAW}cc`,
            }}
          />
        </div>
        <div className="space-y-2">
          {sorted.map((point) => {
            const width = (point.value / maxValue) * 100;
            return (
              <div
                key={point.title}
                className="grid items-center gap-3"
                style={{ gridTemplateColumns: "4.5rem 1fr" }}
              >
                <span
                  className="truncate text-xs text-muted"
                  title={point.title}
                >
                  {point.label}
                </span>
                <div className="relative h-6 rounded-md bg-chart-track">
                  <div
                    className="flex h-6 items-center rounded-md px-2 text-xs font-medium"
                    style={{
                      width: `${Math.max(width, 8)}%`,
                      backgroundColor: barColor(
                        point.value,
                        average,
                        higherIsBetter,
                      ),
                      color: CHART_LABEL_ON_FILL,
                    }}
                  >
                    <span className="whitespace-nowrap">
                      {formatValue(point.value)}
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

function GoalsDistributionChart({
  distribution,
}: {
  distribution: HockeyGoalsDistribution;
}) {
  if (distribution.total_matches <= 0) {
    return null;
  }
  const buckets = goalBucketViews(distribution);
  const slices = buildPieSlicesFromSegments(
    buckets.map((bucket) => ({
      id: bucket.id,
      percent: bucket.piePercent,
    })),
  );
  const ariaLabel = buckets
    .map((bucket) => `${bucket.label}: ${bucket.count}`)
    .join(", ");

  return (
    <article className="rounded-xl border border-border bg-surface p-4">
      <h4 className="mb-3 text-sm font-semibold text-text">
        Rozkład bramek w meczach
      </h4>
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
        <svg
          viewBox="0 0 100 100"
          className="h-36 w-36 shrink-0"
          role="img"
          aria-label={ariaLabel}
        >
          {slices.map((slice) => {
            const fill = BUCKET_COLORS[slice.id] ?? CHART_COLOR_DRAW;
            if (slice.isFullCircle) {
              return (
                <circle key={slice.id} cx="50" cy="50" r="42" fill={fill} />
              );
            }
            if (!slice.path) {
              return null;
            }
            return <path key={slice.id} d={slice.path} fill={fill} />;
          })}
          <circle cx="50" cy="50" r="22" className="fill-surface" />
        </svg>
        <ul className="w-full space-y-2 text-sm">
          {buckets.map((bucket) => (
            <li
              key={bucket.id}
              className="flex items-center justify-between gap-3 text-muted"
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: BUCKET_COLORS[bucket.id] }}
                  aria-hidden
                />
                <span className="truncate">{bucket.label}</span>
              </span>
              <span className="shrink-0 tabular-nums text-text">
                {bucket.count} ({bucket.piePercent}%)
              </span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

function AverageStatPanels({
  kind,
  rows,
}: {
  kind: "shots" | "goals";
  rows: SportLeagueStatRow[];
}) {
  const forAverage = leagueAverage(rows, "avg_for");
  const againstAverage = leagueAverage(rows, "avg_against");
  const formatValue = (value: number) => value.toFixed(2);
  const forTitle =
    kind === "shots"
      ? "Średnia strzałów celnych drużyny"
      : "Średnia bramek zdobytych";
  const againstTitle =
    kind === "shots"
      ? "Średnia strzałów celnych przeciw"
      : "Średnia bramek straconych";

  return (
    <div className="space-y-4">
      <HighlightGrid items={averageHighlights(rows, kind)} />
      {forAverage !== null ? (
        <AverageBars
          title={forTitle}
          points={teamBarPoints(rows, "avg_for")}
          average={forAverage}
          higherIsBetter
          formatValue={formatValue}
        />
      ) : null}
      {againstAverage !== null ? (
        <AverageBars
          title={againstTitle}
          points={teamBarPoints(rows, "avg_against")}
          average={againstAverage}
          higherIsBetter={false}
          formatValue={formatValue}
        />
      ) : null}
    </div>
  );
}

function OverUnderPanels({
  rows,
  distribution,
}: {
  rows: SportLeagueStatRow[];
  distribution: HockeyGoalsDistribution | null;
}) {
  const average = leagueAverage(rows, "over_5_5_pct");
  return (
    <div className="space-y-4">
      <HighlightGrid items={overUnderHighlights(rows, distribution)} />
      {distribution ? (
        <GoalsDistributionChart distribution={distribution} />
      ) : null}
      {average !== null ? (
        <AverageBars
          title="Procent meczów Over 5.5"
          points={teamBarPoints(rows, "over_5_5_pct")}
          average={average}
          higherIsBetter
          formatValue={formatPercent}
        />
      ) : null}
    </div>
  );
}

const HITCHCOCK_REFERENCE = 100;

function recordCell(
  numerator: number | null | undefined,
  denominator: number | null | undefined,
): string {
  if (numerator == null || denominator == null) {
    return "—";
  }
  return `${numerator}/${denominator}`;
}

function SpecialTeamsTable({ rows }: { rows: SportLeagueStatRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-muted">
          <tr>
            <th className="px-3 py-2 text-left">Drużyna</th>
            <th className="px-3 py-2 text-left">Skrót</th>
            <th className="px-3 py-2 text-left">PP</th>
            <th className="px-3 py-2 text-left">PP%</th>
            <th className="px-3 py-2 text-left">PK</th>
            <th className="px-3 py-2 text-left">PK%</th>
            <th className="px-3 py-2 text-left">Hitchcock</th>
            <th className="px-3 py-2 text-left">Mecze</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.team_name}-${row.team_shortcut}`}
              className="border-t border-border text-text"
            >
              <td className="px-3 py-2">{row.team_name}</td>
              <td className="px-3 py-2">{row.team_shortcut || "—"}</td>
              <td className="px-3 py-2">
                {recordCell(row.pp_goals, row.pp_opportunities)}
              </td>
              <td className="px-3 py-2">{formatPercent(row.pp_pct)}</td>
              <td className="px-3 py-2">
                {recordCell(row.pk_kills, row.pk_opportunities)}
              </td>
              <td className="px-3 py-2">{formatPercent(row.pk_pct)}</td>
              <td className="px-3 py-2">{formatPercent(row.hitchcock)}</td>
              <td className="px-3 py-2">{row.matches_played ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SpecialTeamsRateBars({ rows }: { rows: SportLeagueStatRow[] }) {
  const ppAverage = leagueAverage(rows, "pp_pct");
  const pkAverage = leagueAverage(rows, "pk_pct");
  return (
    <>
      {ppAverage !== null ? (
        <AverageBars
          title="Power play (PP)"
          points={teamBarPoints(rows, "pp_pct")}
          average={ppAverage}
          higherIsBetter
          formatValue={formatPercent}
        />
      ) : null}
      {pkAverage !== null ? (
        <AverageBars
          title="Penalty kill (PK)"
          points={teamBarPoints(rows, "pk_pct")}
          average={pkAverage}
          higherIsBetter
          formatValue={formatPercent}
        />
      ) : null}
      <AverageBars
        title="Ken Hitchcock 100 Rule"
        points={teamBarPoints(rows, "hitchcock")}
        average={HITCHCOCK_REFERENCE}
        higherIsBetter
        formatValue={formatPercent}
        caption="Zielony słupek jest powyżej 100. Suma PP% i PK%."
        referenceLabel="Reguła: 100"
      />
    </>
  );
}

function SpecialTeamsPanels({ rows }: { rows: SportLeagueStatRow[] }) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak danych"
        message="Brak statystyk dla wybranego sezonu."
      />
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        PP to bramki w przewadze podzielone przez liczbę przewag. PK to
        zabite przewagi podzielone przez liczbę osłabień. Suma tych
        procentów to reguła Kena Hitchcocka, a punkt odniesienia to 100.
      </p>
      <HighlightGrid items={specialTeamsHighlights(rows)} />
      <SpecialTeamsRateBars rows={rows} />
      <SpecialTeamsTable rows={rows} />
    </div>
  );
}

export function HockeyLeagueStatsPanels({
  category,
  rows,
  goalsDistribution,
}: HockeyLeagueStatsPanelsProps) {
  if (category === "shots" || category === "goals") {
    return <AverageStatPanels kind={category} rows={rows} />;
  }
  if (category === "over_under") {
    return (
      <OverUnderPanels
        rows={rows}
        distribution={goalsDistribution ?? null}
      />
    );
  }
  if (category === "special_teams") {
    return <SpecialTeamsPanels rows={rows} />;
  }
  return null;
}
