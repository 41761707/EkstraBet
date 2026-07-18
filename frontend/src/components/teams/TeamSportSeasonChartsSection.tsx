"use client";

import { useEffect, useMemo, useState } from "react";
import { BasketballTeamCharts } from "@/components/sport-leagues/BasketballTeamCharts";
import { HockeyTeamCharts } from "@/components/sport-leagues/HockeyTeamCharts";
import { ExpandableSection } from "@/components/ExpandableSection";
import { StatusMessage } from "@/components/StatusMessage";
import {
  BASKETBALL_DEFAULT_STATS,
  BASKETBALL_STAT_OPTIONS,
  defaultOuLine,
  HOCKEY_DEFAULT_STATS,
  HOCKEY_STAT_OPTIONS,
  ouLineBounds,
  SPORT_LOOKBACK_DEFAULT,
  SPORT_LOOKBACK_MAX,
  SPORT_LOOKBACK_MIN,
} from "@/components/teams/sportTeamChartConfig";
import { ApiError, getSportTeamHistory } from "@/lib/api";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type BasketballTeamHistoryPoint,
  type HockeyTeamHistoryPoint,
} from "@/types/api";

interface TeamSportSeasonChartsSectionProps {
  leagueId: number;
  teamId: number;
  teamName: string;
  sportId: number;
  seasonId: number;
  phase?: number;
}

export function TeamSportSeasonChartsSection({
  leagueId,
  teamId,
  teamName,
  sportId,
  seasonId,
  phase,
}: TeamSportSeasonChartsSectionProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hockeyHistory, setHockeyHistory] = useState<HockeyTeamHistoryPoint[]>(
    [],
  );
  const [basketballHistory, setBasketballHistory] = useState<
    BasketballTeamHistoryPoint[]
  >([]);

  const statOptions =
    sportId === HOCKEY_SPORT_ID
      ? HOCKEY_STAT_OPTIONS
      : BASKETBALL_STAT_OPTIONS;
  const defaultStats =
    sportId === HOCKEY_SPORT_ID
      ? HOCKEY_DEFAULT_STATS
      : BASKETBALL_DEFAULT_STATS;
  const ouBounds = ouLineBounds(sportId);

  const [ouLine, setOuLine] = useState(() => defaultOuLine(sportId));
  const [lookback, setLookback] = useState(SPORT_LOOKBACK_DEFAULT);
  const [selectedStats, setSelectedStats] = useState<string[]>(defaultStats);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getSportTeamHistory(leagueId, teamId, seasonId, {
      phase,
      lookback: SPORT_LOOKBACK_MAX,
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        setHockeyHistory(response.hockey_history ?? []);
        setBasketballHistory(response.basketball_history ?? []);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Nie udało się załadować historii meczów.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId, teamId, seasonId, phase]);

  const slicedHockeyHistory = useMemo(
    () => hockeyHistory.slice(0, lookback),
    [hockeyHistory, lookback],
  );
  const slicedBasketballHistory = useMemo(
    () => basketballHistory.slice(0, lookback),
    [basketballHistory, lookback],
  );

  function toggleStat(stat: string) {
    setSelectedStats((current) =>
      current.includes(stat)
        ? current.filter((item) => item !== stat)
        : [...current, stat],
    );
  }

  if (loading) {
    return <p className="text-sm text-slate-400">Ładowanie statystyk…</p>;
  }
  if (error) {
    return <StatusMessage variant="error" title="Błąd" message={error} />;
  }

  const hasHistory =
    sportId === HOCKEY_SPORT_ID
      ? slicedHockeyHistory.length > 0
      : slicedBasketballHistory.length > 0;

  if (!hasHistory) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak meczów"
        message="Nie znaleziono rozegranych meczów w wybranym sezonie."
      />
    );
  }

  return (
    <div className="space-y-4">
      <ExpandableSection title="Konfiguracja analizy" defaultOpen>
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-slate-200">
                  Linia Over/Under
                </span>
                <span className="font-semibold text-white">
                  {ouLine.toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min={ouBounds.min}
                max={ouBounds.max}
                step={ouBounds.step}
                value={ouLine}
                onChange={(event) => setOuLine(Number(event.target.value))}
                className="w-full accent-sky-400"
              />
            </label>

            <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-slate-200">
                  Liczba analizowanych spotkań wstecz
                </span>
                <span className="font-semibold text-white">{lookback}</span>
              </div>
              <input
                type="range"
                min={SPORT_LOOKBACK_MIN}
                max={SPORT_LOOKBACK_MAX}
                value={lookback}
                onChange={(event) => setLookback(Number(event.target.value))}
                className="w-full accent-sky-400"
              />
            </label>
          </div>

          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-slate-200">
              Statystyki do wyświetlania
            </h4>
            <div className="flex flex-wrap gap-2">
              {statOptions.map((stat) => {
                const active = selectedStats.includes(stat);
                return (
                  <button
                    key={stat}
                    type="button"
                    onClick={() => toggleStat(stat)}
                    className={`rounded-full px-3 py-1.5 text-sm transition ${
                      active
                        ? "bg-sky-600 text-white"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {stat}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </ExpandableSection>

      {sportId === HOCKEY_SPORT_ID ? (
        <HockeyTeamCharts
          teamName={teamName}
          history={slicedHockeyHistory}
          ouLine={ouLine}
          selectedStats={selectedStats}
        />
      ) : (
        <BasketballTeamCharts
          teamName={teamName}
          history={slicedBasketballHistory}
          ouLine={ouLine}
          selectedStats={selectedStats}
        />
      )}
    </div>
  );
}
