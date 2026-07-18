import Link from "next/link";
import { AnalyticsCategoryPanel } from "@/components/stats/AnalyticsCategoryPanel";
import { AggregationsSection } from "@/components/stats/EntityAggregationTable";
import { LeagueCharacteristicsPanel } from "@/components/stats/LeagueCharacteristicsPanel";
import {
  StatsFilters,
  type StatsFilterValues,
} from "@/components/stats/StatsFilters";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getLeagues,
  getModelAnalytics,
  getModelsGroupedByFamily,
  getSeasonOptions,
} from "@/lib/api";
import {
  parseBoolean,
  parseIdList,
  parsePositiveInt,
} from "@/lib/searchParams";
import type {
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
} from "@/types/api";

const categoryTitles: Record<string, string> = {
  ou: "Over/Under",
  btts: "BTTS",
  result: "1X2",
};

interface StatsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

function parseFilters(
  params: Record<string, string | undefined>,
): StatsFilterValues {
  return {
    leagueIds: parseIdList(params.league_ids),
    seasonId: parsePositiveInt(params.season_id),
    modelResultIds: parseIdList(params.model_result_ids),
    modelOuIds: parseIdList(params.model_ou_ids),
    modelBttsIds: parseIdList(params.model_btts_ids),
    dateFrom: params.date_from ?? "",
    dateTo: params.date_to ?? "",
    roundFrom: params.round_from ?? "",
    roundTo: params.round_to ?? "",
    statType: (params.stat_type as AnalyticsStatType | undefined) ?? "all",
    settledOnly: params.settled_only === undefined
      ? true
      : parseBoolean(params.settled_only, true),
    positiveEvOnly: parseBoolean(params.positive_ev_only),
    applyTax: parseBoolean(params.apply_tax),
    groupBy: (params.group_by as AnalyticsGroupBy | undefined) ?? "none",
    aggregationMetric:
      (params.aggregation_metric as AnalyticsAggregationMetric | undefined) ??
      "accuracy",
    includeLeagueCharacteristics: parseBoolean(
      params.include_league_characteristics,
    ),
  };
}

function pickDefaultModelIds(
  selectedIds: number[],
  available: { id: number }[],
): number[] | undefined {
  if (selectedIds.length > 0) {
    return selectedIds;
  }
  const first = available[0];
  return first ? [first.id] : undefined;
}

export default async function StatsPage({ searchParams }: StatsPageProps) {
  const params = await searchParams;
  const filters = parseFilters(params);

  let leagues: { id: number; label: string }[] = [];
  let seasons: { id: number; label: string }[] = [];
  let modelsByFamily = {
    result: [] as { id: number; label: string }[],
    ou: [] as { id: number; label: string }[],
    btts: [] as { id: number; label: string }[],
  };

  try {
    const [leaguesResponse, seasonOptions, groupedModels] = await Promise.all([
      getLeagues({ active: true }),
      getSeasonOptions(),
      getModelsGroupedByFamily(),
    ]);

    leagues = leaguesResponse.leagues.map((league) => ({
      id: league.id,
      label: league.name,
    }));
    seasons = seasonOptions;
    modelsByFamily = groupedModels;
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Unable to load filter options from the API.";

    return (
      <StatusMessage
        variant="error"
        title="Failed to load statistics filters"
        message={message}
      />
    );
  }

  const effectiveFilters: StatsFilterValues = {
    ...filters,
    modelResultIds:
      filters.modelResultIds.length > 0
        ? filters.modelResultIds
        : modelsByFamily.result.slice(0, 1).map((model) => model.id),
    modelOuIds:
      filters.modelOuIds.length > 0
        ? filters.modelOuIds
        : modelsByFamily.ou.slice(0, 1).map((model) => model.id),
    modelBttsIds:
      filters.modelBttsIds.length > 0
        ? filters.modelBttsIds
        : modelsByFamily.btts.slice(0, 1).map((model) => model.id),
  };

  try {
    const analytics = await getModelAnalytics({
      statType: effectiveFilters.statType,
      modelResultIds: pickDefaultModelIds(
        effectiveFilters.modelResultIds,
        modelsByFamily.result,
      ),
      modelOuIds: pickDefaultModelIds(
        effectiveFilters.modelOuIds,
        modelsByFamily.ou,
      ),
      modelBttsIds: pickDefaultModelIds(
        effectiveFilters.modelBttsIds,
        modelsByFamily.btts,
      ),
      leagueIds:
        effectiveFilters.leagueIds.length > 0
          ? effectiveFilters.leagueIds
          : undefined,
      seasonId: effectiveFilters.seasonId ?? undefined,
      dateFrom: effectiveFilters.dateFrom || undefined,
      dateTo: effectiveFilters.dateTo || undefined,
      roundFrom: parsePositiveInt(effectiveFilters.roundFrom) ?? undefined,
      roundTo: parsePositiveInt(effectiveFilters.roundTo) ?? undefined,
      settledOnly: effectiveFilters.settledOnly,
      positiveEvOnly: effectiveFilters.positiveEvOnly,
      applyTax: effectiveFilters.applyTax,
      groupBy: effectiveFilters.groupBy,
      aggregationMetric: effectiveFilters.aggregationMetric,
      includeLeagueCharacteristics:
        effectiveFilters.includeLeagueCharacteristics,
    });

    const categories = Object.entries(analytics.categories);

    return (
      <div className="space-y-8">
        <section className="space-y-2">
          <Link
            href="/"
            className="text-sm text-sky-300 transition hover:text-sky-200"
          >
            ← Back to leagues
          </Link>
          <h1 className="text-3xl font-bold text-white">Statistics corner</h1>
          <p className="text-slate-300">
            Model effectiveness for predictions and bets with chart-ready
            analytics from the API.
          </p>
        </section>

        <section className="space-y-4 rounded-xl border border-slate-700/80 bg-slate-950/40 p-5">
          <h2 className="text-lg font-semibold text-white">Filters</h2>
          <StatsFilters
            leagues={leagues}
            seasons={seasons}
            resultModels={modelsByFamily.result}
            ouModels={modelsByFamily.ou}
            bttsModels={modelsByFamily.btts}
            values={effectiveFilters}
          />
        </section>

        {categories.length === 0 ? (
          <StatusMessage
            variant="empty"
            title="No statistics"
            message="No analytics data matched the selected filters."
          />
        ) : (
          <div className="space-y-10">
            {categories.map(([key, category]) => (
              <AnalyticsCategoryPanel
                key={key}
                title={categoryTitles[key] ?? key.toUpperCase()}
                category={category}
              />
            ))}
          </div>
        )}

        <AggregationsSection
          byTeam={analytics.aggregations.by_team}
          byLeague={analytics.aggregations.by_league}
        />

        {analytics.league_characteristics ? (
          <LeagueCharacteristicsPanel
            characteristics={analytics.league_characteristics}
          />
        ) : null}
      </div>
    );
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Unable to load model analytics from the API.";

    return (
      <StatusMessage
        variant="error"
        title="Failed to load statistics"
        message={message}
      />
    );
  }
}
