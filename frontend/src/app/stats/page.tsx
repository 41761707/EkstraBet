import Link from "next/link";
import { AnalyticsCategoryPanel } from "@/components/stats/AnalyticsCategoryPanel";
import { AggregationsSection } from "@/components/stats/EntityAggregationTable";
import { LeagueCharacteristicsSection } from "@/components/stats/LeagueCharacteristicsSection";
import { ModelLeagueComparisonsPanel } from "@/components/stats/ModelLeagueComparisonsPanel";
import {
  StatsFilters,
  type StatsFilterValues,
} from "@/components/stats/StatsFilters";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getLeagues,
  getLeagueComparisons,
  getModelAnalytics,
  getModels,
  getModelsGroupedByFamily,
  getSeasonOptions,
} from "@/lib/api";
import { hockeyFamilyLabel } from "@/lib/hockeyMarketLabels";
import {
  parseBoolean,
  parseIdList,
  parsePositiveInt,
} from "@/lib/searchParams";
import {
  resolveAnalyticsLeagueIds,
  visibleLeagueFilterIds,
  buildStatsFilterQuery,
} from "@/lib/statsFilterParams";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type AnalyticsAggregationMetric,
  type AnalyticsGroupBy,
  type AnalyticsStatType,
  type FilterOption,
} from "@/types/api";

export const dynamic = "force-dynamic";

const categoryTitles: Record<string, string> = {
  ou: "Over/Under",
  btts: "BTTS",
  result: "1X2",
};

function categoryTitle(key: string): string {
  return categoryTitles[key] ?? hockeyFamilyLabel(key);
}

function resolveStatsSportId(sportId: number): number {
  return sportId === HOCKEY_SPORT_ID ? HOCKEY_SPORT_ID : FOOTBALL_SPORT_ID;
}

interface StatsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

function parseFilters(
  params: Record<string, string | undefined>,
): StatsFilterValues {
  return {
    sportId: parsePositiveInt(params.sport_id) ?? FOOTBALL_SPORT_ID,
    modelIds: parseIdList(params.model_ids),
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
    compareLeagueIds: parseIdList(params.compare_league_ids),
    compareSeasonId: parsePositiveInt(params.compare_season_id),
  };
}

function errorMessageFromReason(reason: unknown, fallback: string): string {
  return reason instanceof ApiError ? reason.message : fallback;
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
  const sportId = resolveStatsSportId(filters.sportId);
  const isHockey = sportId === HOCKEY_SPORT_ID;

  let leagues: FilterOption[] = [];
  let seasons: FilterOption[] = [];
  let hockeyModels: FilterOption[] = [];
  let modelsByFamily = {
    result: [] as FilterOption[],
    ou: [] as FilterOption[],
    btts: [] as FilterOption[],
  };

  try {
    const [leaguesResponse, seasonOptions, groupedModels, modelsResponse] =
      await Promise.all([
        getLeagues({ active: true, sportId }),
        getSeasonOptions(sportId),
        isHockey
          ? Promise.resolve(modelsByFamily)
          : getModelsGroupedByFamily(sportId),
        isHockey ? getModels() : Promise.resolve(null),
      ]);

    leagues = leaguesResponse.leagues.map((league) => ({
      id: league.id,
      label: league.name,
    }));
    seasons = seasonOptions;
    modelsByFamily = groupedModels;
    hockeyModels = (modelsResponse?.models ?? [])
      .filter((model) => model.active === 1 && model.sport_id === HOCKEY_SPORT_ID)
      .map((model) => ({ id: model.id, label: model.name }))
      .sort((left, right) => left.label.localeCompare(right.label, "pl"));
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować opcji filtrów z API.";

    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować filtrów statystyk"
        message={message}
      />
    );
  }

  const allFootballLeagueIds = leagues.map((league) => league.id);
  const footballLeagueIds = new Set(allFootballLeagueIds);
  const selectedFootballLeagueIds = filters.leagueIds.filter((id) =>
    footballLeagueIds.has(id),
  );
  const apiLeagueIds = resolveAnalyticsLeagueIds(
    selectedFootballLeagueIds,
    allFootballLeagueIds,
  );

  const selectedCompareLeagueIds = filters.compareLeagueIds.filter((id) =>
    footballLeagueIds.has(id),
  );
  const compareApiLeagueIds = resolveAnalyticsLeagueIds(
    selectedCompareLeagueIds,
    allFootballLeagueIds,
  );

  const selectedHockeyModelIds =
    filters.modelIds.length > 0
      ? filters.modelIds.filter((id) =>
          hockeyModels.some((model) => model.id === id),
        )
      : hockeyModels.map((model) => model.id);

  const effectiveFilters: StatsFilterValues = {
    ...filters,
    sportId,
    modelIds: isHockey ? selectedHockeyModelIds : [],
    leagueIds: visibleLeagueFilterIds(
      selectedFootballLeagueIds,
      allFootballLeagueIds,
    ),
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
    compareLeagueIds: visibleLeagueFilterIds(
      selectedCompareLeagueIds,
      allFootballLeagueIds,
    ),
  };

  const statsFilterKey =
    buildStatsFilterQuery(effectiveFilters, allFootballLeagueIds) || "default";

  try {
    const [analyticsResult, comparisonResult] = await Promise.allSettled([
      getModelAnalytics(
        isHockey
          ? {
              sportId: HOCKEY_SPORT_ID,
              modelIds: effectiveFilters.modelIds,
              leagueIds: apiLeagueIds.length > 0 ? apiLeagueIds : undefined,
              seasonId: effectiveFilters.seasonId ?? undefined,
              dateFrom: effectiveFilters.dateFrom || undefined,
              dateTo: effectiveFilters.dateTo || undefined,
              roundFrom:
                parsePositiveInt(effectiveFilters.roundFrom) ?? undefined,
              roundTo: parsePositiveInt(effectiveFilters.roundTo) ?? undefined,
              settledOnly: effectiveFilters.settledOnly,
              positiveEvOnly: effectiveFilters.positiveEvOnly,
              applyTax: effectiveFilters.applyTax,
              statType: "all",
              groupBy: "none",
            }
          : {
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
              leagueIds: apiLeagueIds.length > 0 ? apiLeagueIds : undefined,
              seasonId: effectiveFilters.seasonId ?? undefined,
              dateFrom: effectiveFilters.dateFrom || undefined,
              dateTo: effectiveFilters.dateTo || undefined,
              roundFrom:
                parsePositiveInt(effectiveFilters.roundFrom) ?? undefined,
              roundTo: parsePositiveInt(effectiveFilters.roundTo) ?? undefined,
              settledOnly: effectiveFilters.settledOnly,
              positiveEvOnly: effectiveFilters.positiveEvOnly,
              applyTax: effectiveFilters.applyTax,
              groupBy: effectiveFilters.groupBy,
              aggregationMetric: effectiveFilters.aggregationMetric,
            },
      ),
      isHockey
        ? Promise.resolve({ comparisons: null })
        : getLeagueComparisons({
            leagueIds:
              compareApiLeagueIds.length > 0 ? compareApiLeagueIds : undefined,
            seasonId: effectiveFilters.compareSeasonId ?? undefined,
          }),
    ]);

    if (analyticsResult.status === "rejected") {
      return (
        <StatusMessage
          variant="error"
          title="Nie udało się załadować statystyk"
          message={errorMessageFromReason(
            analyticsResult.reason,
            "Nie udało się załadować analityki modeli z API.",
          )}
        />
      );
    }

    const analytics = analyticsResult.value;
    const leagueComparisons =
      comparisonResult.status === "fulfilled"
        ? comparisonResult.value.comparisons
        : null;
    const leagueComparisonsError =
      comparisonResult.status === "rejected"
        ? errorMessageFromReason(
            comparisonResult.reason,
            "Nie udało się załadować porównania lig z API.",
          )
        : null;

    const categories = Object.entries(analytics.categories);

    return (
      <div className="space-y-8">
        <section className="space-y-2">
          <Link
            href="/"
            className="text-sm text-accent-text transition hover:text-accent-text-hover"
          >
            Powrót do lig
          </Link>
          <h1 className="text-3xl font-bold text-text">Kącik statystyczny</h1>
          <p className="text-muted">
            Góra strony to skuteczność tego, co liczą modele. Na dole —
            charakterystyka lig z rozegranych meczów.
          </p>
        </section>

        <section className="space-y-8">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-subtle">
              Predykcje i zakłady
            </p>
            <h2 className="text-2xl font-semibold text-text">
              Statystyki modeli
            </h2>
            <p className="text-muted">
              Skuteczność predykcji i profit zakładów według wybranych filtrów.
            </p>
          </div>

          <div className="space-y-4 rounded-xl border border-border bg-surface-muted p-5">
            <h3 className="text-lg font-semibold text-text">
              Filtry modeli
            </h3>
            <StatsFilters
              key={statsFilterKey}
              leagues={leagues}
              seasons={seasons}
              resultModels={modelsByFamily.result}
              ouModels={modelsByFamily.ou}
              bttsModels={modelsByFamily.btts}
              hockeyModels={hockeyModels}
              values={effectiveFilters}
            />
          </div>

          {categories.length === 0 ? (
            <StatusMessage
              variant="empty"
              title="Brak statystyk"
              message="Brak danych analitycznych dla wybranych filtrów."
            />
          ) : (
            <div className="space-y-10">
              {categories.map(([key, category]) => (
                <AnalyticsCategoryPanel
                  key={key}
                  title={categoryTitle(key)}
                  category={category}
                />
              ))}
            </div>
          )}

          <AggregationsSection
            byTeam={analytics.aggregations.by_team}
            byLeague={analytics.aggregations.by_league}
          />

          {analytics.model_league_comparisons ? (
            <ModelLeagueComparisonsPanel
              comparisons={analytics.model_league_comparisons}
            />
          ) : null}
        </section>

        {isHockey ? null : (
          <LeagueCharacteristicsSection
            leagues={leagues}
            seasons={seasons}
            values={effectiveFilters}
            comparisons={leagueComparisons}
            errorMessage={leagueComparisonsError}
          />
        )}
      </div>
    );
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować analityki modeli z API.";

    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować statystyk"
        message={message}
      />
    );
  }
}
