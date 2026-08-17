import { LeagueComparisonFilters } from "@/components/stats/LeagueComparisonFilters";
import { LeagueComparisonsPanel } from "@/components/stats/LeagueComparisonsPanel";
import { StatusMessage } from "@/components/StatusMessage";
import type { StatsFilterValues } from "@/lib/statsFilterParams";
import type { FilterOption, LeagueComparisons } from "@/types/api";

interface LeagueCharacteristicsSectionProps {
  leagues: FilterOption[];
  seasons: FilterOption[];
  values: StatsFilterValues;
  comparisons: LeagueComparisons | null;
  errorMessage: string | null;
}

export function LeagueCharacteristicsSection({
  leagues,
  seasons,
  values,
  comparisons,
  errorMessage,
}: LeagueCharacteristicsSectionProps) {
  return (
    <section className="space-y-6 border-t border-slate-600 pt-10">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Dane z meczów
        </p>
        <h2 className="text-2xl font-semibold text-white">
          Porównanie lig ze średnią
        </h2>
        <p className="text-slate-300">
          Częstość zdarzeń w rozegranych meczach — niezależnie od modeli,
          zakładów i filtrów powyżej.
        </p>
      </div>

      <div className="space-y-4 rounded-xl border border-slate-700/80 bg-slate-950/40 p-5">
        <h3 className="text-lg font-semibold text-white">
          Filtry porównania lig
        </h3>
        <LeagueComparisonFilters
          leagues={leagues}
          seasons={seasons}
          values={values}
        />
      </div>

      {errorMessage ? (
        <StatusMessage
          variant="error"
          title="Nie udało się załadować porównania lig"
          message={errorMessage}
        />
      ) : comparisons ? (
        <LeagueComparisonsPanel comparisons={comparisons} />
      ) : (
        <StatusMessage
          variant="empty"
          title="Za mało lig do porównania"
          message="Wybierz co najmniej dwie ligi, aby zobaczyć wykresy na tle średniej."
        />
      )}
    </section>
  );
}
