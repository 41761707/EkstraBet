"use client";

import { useEffect, useRef, useState } from "react";

import { formatIsoDate } from "@/components/filters/dateInputModel";
import { StatusMessage } from "@/components/StatusMessage";
import { ChoiceTabs } from "@/components/tipsters/ChoiceTabs";
import {
  formatResultProfit,
  ResultCalendarGrid,
  type ResultMeasure,
} from "@/components/tipsters/ResultCalendarGrid";
import {
  canShiftForward,
  periodTitle,
  shiftAnchor,
  type ResultGrain,
} from "@/components/tipsters/resultCalendarModel";
import { signedAmountClassName } from "@/components/tipsters/tipsterModel";
import { ApiError, getMyResultCalendar, getProfileResultCalendar } from "@/lib/apiClient";
import type {
  CurrencyCode,
  ResultCalendar as ResultCalendarData,
  ResultCalendarLens,
} from "@/types/api";

const CALENDAR_TITLE = "Wynik w czasie";
const COUPON_LENS_DESCRIPTION =
  "Dzień kuponu to dzień rozpoczęcia jego ostatniego meczu. " +
  "W komórce jest wynik całego kuponu.";
const SINGLE_LENS_DESCRIPTION =
  "Dzień zakładu to dzień rozpoczęcia tego meczu. Wszedł — wynik to kurs " +
  "razy stawka minus stawka, także na przegranym kuponie.";
const WEEK_GRAIN_NOTE =
  "Tydzień liczy się od poniedziałku do niedzieli i należy do roku, " +
  "w którym wypada jego czwartek.";
const LOADING_LABEL = "Wczytywanie…";
const EMPTY_PERIOD_MESSAGE = "Brak rozliczonych wyników w tym okresie.";
const LOAD_ERROR_TITLE = "Nie udało się wczytać wyników";
const LOAD_ERROR_FALLBACK = "Spróbuj odświeżyć stronę.";
const UNIT_TAB_LABEL = "Jednostka";
const PREVIOUS_PERIOD_LABEL = "Poprzedni okres";
const NEXT_PERIOD_LABEL = "Następny okres";

const LENS_TABS: { id: ResultCalendarLens; label: string }[] = [
  { id: "coupon", label: "Kupon" },
  { id: "single", label: "Zakład" },
];

const GRAIN_TABS: { id: ResultGrain; label: string }[] = [
  { id: "day", label: "Dzień" },
  { id: "week", label: "Tydzień" },
  { id: "month", label: "Miesiąc" },
  { id: "year", label: "Rok" },
];

const NAV_BUTTON_CLASS =
  "rounded-md px-2 py-1 text-muted hover:bg-surface-muted " +
  "disabled:cursor-not-allowed disabled:opacity-40";

interface ResultCalendarProps {
  username: string | null;
  applyTax: boolean;
  currency: CurrencyCode;
}

interface CalendarView {
  lens: ResultCalendarLens;
  grain: ResultGrain;
  anchor: string;
  today: string;
  measure: ResultMeasure;
  canUseUnits: boolean;
  calendar: ResultCalendarData | null;
  error: string | null;
  isLoading: boolean;
  setLens: (lens: ResultCalendarLens) => void;
  setGrain: (grain: ResultGrain) => void;
  setMeasure: (measure: ResultMeasure) => void;
  shift: (direction: -1 | 1) => void;
}

export function ResultCalendar({
  username,
  applyTax,
  currency,
}: ResultCalendarProps) {
  const view = useResultCalendar(username, applyTax);
  return (
    <div className="space-y-3 border-t border-border pt-5">
      <CalendarIntro lens={view.lens} grain={view.grain} />
      <CalendarSwitches view={view} currency={currency} />
      <PeriodNavigator view={view} currency={currency} />
      <CalendarBody view={view} currency={currency} />
    </div>
  );
}

function useResultCalendar(
  username: string | null,
  applyTax: boolean,
): CalendarView {
  const [lens, setLens] = useState<ResultCalendarLens>("coupon");
  const [grain, setGrain] = useState<ResultGrain>("day");
  const [anchor, setAnchor] = useState(() => localIsoToday());
  const [today] = useState(() => localIsoToday());
  const [measure, setMeasure] = useState<ResultMeasure>("currency");
  const [unitSize, setUnitSize] = useState<number | null>(null);
  const [calendar, setCalendar] = useState<ResultCalendarData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const requestSeq = useRef(0);

  useEffect(() => {
    const requestId = requestSeq.current + 1;
    requestSeq.current = requestId;
    setIsLoading(true);
    setError(null);
    setCalendar(null);
    const query = { lens, grain, anchor, applyTax };
    // Starsza odpowiedź nie może nadpisać okresu, który użytkownik właśnie wybrał.
    void loadCalendar(username, query)
      .then((response) => {
        if (requestSeq.current !== requestId) {
          return;
        }
        setCalendar(response);
        setUnitSize(response.unit_size);
      })
      .catch((cause: unknown) => {
        if (requestSeq.current !== requestId) {
          return;
        }
        setError(calendarErrorMessage(cause));
      })
      .finally(() => {
        if (requestSeq.current === requestId) {
          setIsLoading(false);
        }
      });
  }, [anchor, applyTax, grain, lens, username]);

  const canUseUnits = unitSize !== null && unitSize > 0;
  return {
    lens,
    grain,
    anchor,
    today,
    measure: canUseUnits ? measure : "currency",
    canUseUnits,
    calendar,
    error,
    isLoading,
    setLens,
    setGrain,
    setMeasure,
    shift(direction) {
      if (direction === 1 && !canShiftForward(grain, anchor, today)) {
        return;
      }
      setAnchor(shiftAnchor(grain, anchor, direction));
    },
  };
}

function CalendarIntro({
  lens,
  grain,
}: {
  lens: ResultCalendarLens;
  grain: ResultGrain;
}) {
  return (
    <div className="space-y-1">
      <h3 className="text-base font-semibold text-text">{CALENDAR_TITLE}</h3>
      <p className="text-sm leading-relaxed text-muted">
        {lens === "coupon" ? COUPON_LENS_DESCRIPTION : SINGLE_LENS_DESCRIPTION}
      </p>
      {grain === "week" ? (
        <p className="text-sm leading-relaxed text-muted">{WEEK_GRAIN_NOTE}</p>
      ) : null}
    </div>
  );
}

function CalendarSwitches({
  view,
  currency,
}: {
  view: CalendarView;
  currency: CurrencyCode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <ChoiceTabs
        label="Soczewka"
        tabs={LENS_TABS}
        value={view.lens}
        onChange={view.setLens}
      />
      <ChoiceTabs
        label="Ziarno"
        tabs={GRAIN_TABS}
        value={view.grain}
        onChange={view.setGrain}
      />
      {view.canUseUnits ? (
        <ChoiceTabs
          label="Miara"
          tabs={[
            { id: "currency", label: currency },
            { id: "unit", label: UNIT_TAB_LABEL },
          ]}
          value={view.measure}
          onChange={view.setMeasure}
        />
      ) : null}
    </div>
  );
}

function PeriodNavigator({
  view,
  currency,
}: {
  view: CalendarView;
  currency: CurrencyCode;
}) {
  const showTotals = view.calendar !== null && !view.isLoading && view.error === null;
  const profit = showTotals ? view.calendar?.profit_total ?? null : null;
  const canGoForward = canShiftForward(view.grain, view.anchor, view.today);
  return (
    <div className="flex items-center justify-between gap-3">
      <button
        type="button"
        aria-label={PREVIOUS_PERIOD_LABEL}
        onClick={() => view.shift(-1)}
        className={NAV_BUTTON_CLASS}
      >
        ‹
      </button>
      <div className="min-w-0 flex-1 text-center">
        <p className="text-sm font-medium text-text">
          {periodTitle(view.grain, view.anchor)}
          {profit !== null && view.calendar ? (
            <span className={`ml-2 ${signedAmountClassName(profit)}`}>
              {formatResultProfit(
                profit,
                view.measure,
                currency,
                view.calendar.unit_size,
              )}
            </span>
          ) : null}
        </p>
        {showTotals && view.calendar ? (
          <p className="text-xs text-muted">
            {countLabel(view.calendar.lens, view.calendar.count)}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        aria-label={NEXT_PERIOD_LABEL}
        disabled={!canGoForward}
        onClick={() => view.shift(1)}
        className={NAV_BUTTON_CLASS}
      >
        ›
      </button>
    </div>
  );
}

function CalendarBody({
  view,
  currency,
}: {
  view: CalendarView;
  currency: CurrencyCode;
}) {
  if (view.isLoading) {
    return (
      <p className="text-sm text-muted" role="status">
        {LOADING_LABEL}
      </p>
    );
  }
  if (view.error) {
    return (
      <StatusMessage
        variant="error"
        title={LOAD_ERROR_TITLE}
        message={view.error}
      />
    );
  }
  if (!view.calendar) {
    return null;
  }
  return (
    <>
      <ResultCalendarGrid
        calendar={view.calendar}
        measure={view.measure}
        currency={currency}
        today={view.today}
      />
      {view.calendar.count === 0 ? (
        <p className="text-sm text-muted">{EMPTY_PERIOD_MESSAGE}</p>
      ) : null}
    </>
  );
}

function loadCalendar(
  username: string | null,
  query: {
    lens: ResultCalendarLens;
    grain: ResultGrain;
    anchor: string;
    applyTax: boolean;
  },
): Promise<ResultCalendarData> {
  if (username === null) {
    return getMyResultCalendar(query);
  }
  return getProfileResultCalendar(username, query);
}

function calendarErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return LOAD_ERROR_FALLBACK;
}

function countLabel(lens: ResultCalendarLens, count: number): string {
  const noun = lens === "coupon" ? "Kupony" : "Zakłady";
  return `${noun}: ${count}`;
}

// Składniki lokalne, nie toISOString: po północy w Polsce UTC cofa dzień.
function localIsoToday(): string {
  const now = new Date();
  return formatIsoDate(now.getFullYear(), now.getMonth() + 1, now.getDate());
}
