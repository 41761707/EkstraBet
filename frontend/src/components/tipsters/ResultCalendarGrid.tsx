import {
  formatIsoDate,
  parseIsoDate,
  WEEKDAY_LABELS,
} from "@/components/filters/dateInputModel";
import {
  dayGrid,
  intensityStep,
  monthSlots,
  weekSlots,
  yearSlots,
  type CalendarSlot,
} from "@/components/tipsters/resultCalendarModel";
import {
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterUnits,
  toPerformanceUnits,
} from "@/components/tipsters/tipsterModel";
import type {
  CurrencyCode,
  ResultCalendar,
  ResultCalendarBucket,
  ResultCalendarLens,
} from "@/types/api";

export type ResultMeasure = "currency" | "unit";

const POSITIVE_BACKGROUNDS = [
  "bg-surface",
  "bg-success-bg/40",
  "bg-success-bg/70",
  "bg-success-bg",
] as const;

const NEGATIVE_BACKGROUNDS = [
  "bg-surface",
  "bg-danger-bg/40",
  "bg-danger-bg/70",
  "bg-danger-bg",
] as const;

const WEEK_COLUMNS = "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4";
const YEAR_COLUMNS = "grid-cols-2 sm:grid-cols-4";

interface ResultCalendarGridProps {
  calendar: ResultCalendar;
  measure: ResultMeasure;
  currency: CurrencyCode;
  today: string;
}

interface AmountContext {
  lens: ResultCalendarLens;
  measure: ResultMeasure;
  currency: CurrencyCode;
  unitSize: number | null;
  maxAbs: number;
}

/** Signed profit in currency, or in the current unit when that measure is on. */
export function formatResultProfit(
  amount: number,
  measure: ResultMeasure,
  currency: CurrencyCode,
  unitSize: number | null,
): string {
  if (measure === "unit" && unitSize !== null && unitSize > 0) {
    return formatTipsterUnits(toPerformanceUnits(amount, unitSize), true);
  }
  return formatTipsterProfit(amount, currency);
}

export function ResultCalendarGrid({
  calendar,
  measure,
  currency,
  today,
}: ResultCalendarGridProps) {
  const amounts: AmountContext = {
    lens: calendar.lens,
    measure,
    currency,
    unitSize: calendar.unit_size,
    maxAbs: maxAbsoluteProfit(calendar.buckets),
  };
  if (calendar.grain === "day") {
    return <DayGrid anchor={calendar.anchor} buckets={calendar.buckets} amounts={amounts} />;
  }
  if (calendar.grain === "week") {
    return <WeekGrid anchor={calendar.anchor} buckets={calendar.buckets} amounts={amounts} />;
  }
  if (calendar.grain === "month") {
    return <MonthGrid anchor={calendar.anchor} buckets={calendar.buckets} amounts={amounts} />;
  }
  return <YearGrid buckets={calendar.buckets} today={today} amounts={amounts} />;
}

function DayGrid({
  anchor,
  buckets,
  amounts,
}: {
  anchor: string;
  buckets: ResultCalendarBucket[];
  amounts: AmountContext;
}) {
  const slots = dayGrid(anchor, buckets);
  return (
    <div className="space-y-1">
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted">
        {WEEKDAY_LABELS.map((label) => (
          <div key={label}>{label}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {slots.map((slot, index) => (
          <DayCell key={slot.start ?? `blank-${index}`} slot={slot} amounts={amounts} />
        ))}
      </div>
    </div>
  );
}

function DayCell({ slot, amounts }: { slot: CalendarSlot; amounts: AmountContext }) {
  if (!slot.start || !slot.bucket) {
    return <div className="min-h-12" />;
  }
  const step = intensityStep(slot.bucket.profit, amounts.maxAbs);
  return (
    <div
      title={cellTitle(slot.bucket, amounts)}
      className={`min-h-12 px-1 py-1 ${filledCellClassName(slot.bucket.profit, step)}`}
    >
      <p className="text-xs text-muted">{dayNumber(slot.start)}</p>
      <p className={`text-xs font-medium leading-tight ${cellAmountClass(slot.bucket.profit)}`}>
        {formatResultProfit(
          slot.bucket.profit,
          amounts.measure,
          amounts.currency,
          amounts.unitSize,
        )}
      </p>
    </div>
  );
}

function WeekGrid({
  anchor,
  buckets,
  amounts,
}: {
  anchor: string;
  buckets: ResultCalendarBucket[];
  amounts: AmountContext;
}) {
  return (
    <CardGrid
      slots={weekSlots(anchor, buckets)}
      columnsClassName={WEEK_COLUMNS}
      labelFor={weekSlotLabel}
      amounts={amounts}
    />
  );
}

function MonthGrid({
  anchor,
  buckets,
  amounts,
}: {
  anchor: string;
  buckets: ResultCalendarBucket[];
  amounts: AmountContext;
}) {
  return (
    <CardGrid
      slots={monthSlots(anchor, buckets)}
      columnsClassName="grid-cols-4"
      labelFor={(slot) => (slot.start ? monthCardLabel(slot.start) : "")}
      amounts={amounts}
    />
  );
}

function YearGrid({
  buckets,
  today,
  amounts,
}: {
  buckets: ResultCalendarBucket[];
  today: string;
  amounts: AmountContext;
}) {
  return (
    <CardGrid
      slots={yearSlots(buckets, today)}
      columnsClassName={YEAR_COLUMNS}
      labelFor={(slot) => (slot.start ? yearLabel(slot.start) : "")}
      amounts={amounts}
    />
  );
}

function CardGrid({
  slots,
  columnsClassName,
  labelFor,
  amounts,
}: {
  slots: CalendarSlot[];
  columnsClassName: string;
  labelFor: (slot: CalendarSlot) => string;
  amounts: AmountContext;
}) {
  return (
    <div className={`grid gap-2 ${columnsClassName}`}>
      {slots.map((slot) => (
        <ResultCard
          key={slot.start ?? "blank"}
          label={labelFor(slot)}
          slot={slot}
          amounts={amounts}
        />
      ))}
    </div>
  );
}

function ResultCard({
  label,
  slot,
  amounts,
}: {
  label: string;
  slot: CalendarSlot;
  amounts: AmountContext;
}) {
  if (!slot.bucket) {
    return (
      <div className="min-h-16 px-2 py-2">
        <p className="text-xs text-muted">{label}</p>
      </div>
    );
  }
  const step = intensityStep(slot.bucket.profit, amounts.maxAbs);
  return (
    <div
      title={cellTitle(slot.bucket, amounts)}
      className={`min-h-16 px-2 py-2 ${filledCellClassName(slot.bucket.profit, step)}`}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-sm font-medium ${cellAmountClass(slot.bucket.profit)}`}>
        {formatResultProfit(
          slot.bucket.profit,
          amounts.measure,
          amounts.currency,
          amounts.unitSize,
        )}
      </p>
    </div>
  );
}

function formatResultStake(
  amount: number,
  measure: ResultMeasure,
  currency: CurrencyCode,
  unitSize: number | null,
): string {
  if (measure === "unit" && unitSize !== null && unitSize > 0) {
    return formatTipsterUnits(toPerformanceUnits(amount, unitSize));
  }
  return formatTipsterAmount(amount, currency);
}

function cellTitle(bucket: ResultCalendarBucket, amounts: AmountContext): string {
  const noun = amounts.lens === "coupon" ? "Kupony" : "Zakłady";
  const stake = formatResultStake(
    bucket.stake,
    amounts.measure,
    amounts.currency,
    amounts.unitSize,
  );
  const profit = formatResultProfit(
    bucket.profit,
    amounts.measure,
    amounts.currency,
    amounts.unitSize,
  );
  return `${noun}: ${bucket.count}, stawka ${stake}, wynik ${profit}`;
}

function maxAbsoluteProfit(buckets: ResultCalendarBucket[]): number {
  let maxAbs = 0;
  for (const bucket of buckets) {
    maxAbs = Math.max(maxAbs, Math.abs(bucket.profit));
  }
  return maxAbs;
}

function filledCellClassName(profit: number, step: 0 | 1 | 2 | 3): string {
  return `rounded-md border border-border ${cellBackground(profit, step)}`;
}

function cellBackground(profit: number, step: 0 | 1 | 2 | 3): string {
  if (profit > 0) {
    return POSITIVE_BACKGROUNDS[step];
  }
  if (profit < 0) {
    return NEGATIVE_BACKGROUNDS[step];
  }
  return "bg-surface";
}

// Na tle success-bg czytelny jest token tekstu, nie pełne text-success.
function cellAmountClass(profit: number): string {
  if (profit > 0) {
    return "text-success-text";
  }
  if (profit < 0) {
    return "text-danger-text";
  }
  return "text-text";
}

function dayNumber(iso: string): string {
  const parts = parseIsoDate(iso);
  return parts ? String(parts.day) : iso;
}

function weekSlotLabel(slot: CalendarSlot): string {
  if (!slot.start) {
    return "";
  }
  const end = slot.bucket?.end ?? addDaysIso(slot.start, 6);
  return weekRangeLabel(slot.start, end);
}

function weekRangeLabel(start: string, end: string): string {
  const startParts = parseIsoDate(start);
  const endParts = parseIsoDate(end);
  if (!startParts || !endParts) {
    return start;
  }
  const startDate = new Date(startParts.year, startParts.month - 1, startParts.day);
  const endDate = new Date(endParts.year, endParts.month - 1, endParts.day);
  const startMonth = shortMonth(startDate);
  const endMonth = shortMonth(endDate);
  if (startParts.year === endParts.year && startParts.month === endParts.month) {
    return `${startParts.day}–${endParts.day} ${startMonth}`;
  }
  return `${startParts.day} ${startMonth} – ${endParts.day} ${endMonth}`;
}

function monthCardLabel(iso: string): string {
  const parts = parseIsoDate(iso);
  if (!parts) {
    return iso;
  }
  return shortMonth(new Date(parts.year, parts.month - 1, 1));
}

function yearLabel(iso: string): string {
  const parts = parseIsoDate(iso);
  return parts ? String(parts.year) : iso;
}

function shortMonth(date: Date): string {
  return new Intl.DateTimeFormat("pl-PL", { month: "short" }).format(date).replace(".", "");
}

function addDaysIso(iso: string, days: number): string {
  const parts = parseIsoDate(iso);
  if (!parts) {
    return iso;
  }
  const date = new Date(parts.year, parts.month - 1, parts.day + days);
  return formatIsoDate(date.getFullYear(), date.getMonth() + 1, date.getDate());
}
