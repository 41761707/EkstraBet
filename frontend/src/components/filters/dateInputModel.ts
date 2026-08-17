/** Calendar-grid helpers for the shared date picker. Dates are ISO YYYY-MM-DD. */

const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const CALENDAR_CELL_COUNT = 42;

export const WEEKDAY_LABELS = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"] as const;

export interface CalendarDate {
  year: number;
  month: number;
  day: number;
}

export interface CalendarCell {
  isoDate: string;
  day: number;
  inCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
}

export function parseIsoDate(value: string): CalendarDate | null {
  const match = ISO_DATE_PATTERN.exec(value);
  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!isValidCalendarDate(year, month, day)) {
    return null;
  }
  return { year, month, day };
}

export function formatIsoDate(year: number, month: number, day: number): string {
  const yyyy = String(year).padStart(4, "0");
  const mm = String(month).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function formatIsoDatePl(value: string): string {
  const parsed = parseIsoDate(value);
  if (!parsed) {
    return "";
  }
  const dd = String(parsed.day).padStart(2, "0");
  const mm = String(parsed.month).padStart(2, "0");
  return `${dd}.${mm}.${parsed.year}`;
}

export function formatMonthTitle(year: number, month: number): string {
  const utc = new Date(Date.UTC(year, month - 1, 1));
  const title = utc.toLocaleDateString("pl-PL", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
  return title.charAt(0).toLocaleUpperCase("pl-PL") + title.slice(1);
}

export function shiftCalendarMonth(
  year: number,
  month: number,
  delta: number,
): CalendarDate {
  const utc = new Date(Date.UTC(year, month - 1 + delta, 1));
  return {
    year: utc.getUTCFullYear(),
    month: utc.getUTCMonth() + 1,
    day: 1,
  };
}

export function isIsoDateInRange(
  isoDate: string,
  min?: string,
  max?: string,
): boolean {
  if (!parseIsoDate(isoDate)) {
    return false;
  }
  if (min && isoDate < min) {
    return false;
  }
  if (max && isoDate > max) {
    return false;
  }
  return true;
}

export function buildCalendarGrid(
  year: number,
  month: number,
  selectedIso: string,
  todayIso: string,
): CalendarCell[] {
  const firstOfMonth = new Date(Date.UTC(year, month - 1, 1));
  const mondayOffset = (firstOfMonth.getUTCDay() + 6) % 7;
  const startDay = firstOfMonth.getUTCDate() - mondayOffset;

  const cells: CalendarCell[] = [];
  for (let index = 0; index < CALENDAR_CELL_COUNT; index += 1) {
    const cellDate = new Date(Date.UTC(year, month - 1, startDay + index));
    const isoDate = formatIsoDate(
      cellDate.getUTCFullYear(),
      cellDate.getUTCMonth() + 1,
      cellDate.getUTCDate(),
    );
    cells.push({
      isoDate,
      day: cellDate.getUTCDate(),
      inCurrentMonth: cellDate.getUTCMonth() === month - 1,
      isToday: isoDate === todayIso,
      isSelected: isoDate === selectedIso,
    });
  }
  return cells;
}

function isValidCalendarDate(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }
  const utc = new Date(Date.UTC(year, month - 1, day));
  return (
    utc.getUTCFullYear() === year &&
    utc.getUTCMonth() === month - 1 &&
    utc.getUTCDate() === day
  );
}
