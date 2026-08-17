"use client";

import { useState } from "react";

import {
  buildCalendarGrid,
  formatMonthTitle,
  isIsoDateInRange,
  shiftCalendarMonth,
  WEEKDAY_LABELS,
  type CalendarDate,
} from "@/components/filters/dateInputModel";

const FOOTER_BUTTON_CLASS_NAME =
  "rounded-md px-2 py-1 text-xs hover:bg-slate-800 " +
  "disabled:cursor-not-allowed disabled:text-slate-500";

interface DateInputCalendarProps {
  id: string;
  selectedIso: string;
  todayIso: string;
  initialView: CalendarDate;
  min?: string;
  max?: string;
  allowEmpty: boolean;
  onSelect: (isoDate: string) => void;
  onClear: () => void;
}

export function DateInputCalendar({
  id,
  selectedIso,
  todayIso,
  initialView,
  min,
  max,
  allowEmpty,
  onSelect,
  onClear,
}: DateInputCalendarProps) {
  const [view, setView] = useState<CalendarDate>(initialView);
  const cells = buildCalendarGrid(view.year, view.month, selectedIso, todayIso);
  const isTodayEnabled = isIsoDateInRange(todayIso, min, max);

  return (
    <div
      id={id}
      role="dialog"
      aria-label="Wybierz datę"
      className={
        "absolute z-50 mt-1 w-72 rounded-xl border border-slate-700 " +
        "bg-slate-900 p-3 shadow-xl"
      }
    >
      <CalendarHeader view={view} onViewChange={setView} />
      <div className="mt-2 grid grid-cols-7 gap-1 text-center">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label} className="text-xs font-medium text-slate-400">
            {label}
          </span>
        ))}
        {cells.map((cell) => (
          <CalendarDayButton
            key={cell.isoDate}
            isoDate={cell.isoDate}
            day={cell.day}
            inCurrentMonth={cell.inCurrentMonth}
            isToday={cell.isToday}
            isSelected={cell.isSelected}
            isDisabled={!isIsoDateInRange(cell.isoDate, min, max)}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          disabled={!isTodayEnabled}
          onClick={() => onSelect(todayIso)}
          className={`${FOOTER_BUTTON_CLASS_NAME} text-sky-300`}
        >
          Dziś
        </button>
        {allowEmpty ? (
          <button
            type="button"
            disabled={!selectedIso}
            onClick={onClear}
            className={`${FOOTER_BUTTON_CLASS_NAME} text-slate-300`}
          >
            Wyczyść
          </button>
        ) : null}
      </div>
    </div>
  );
}

interface CalendarHeaderProps {
  view: CalendarDate;
  onViewChange: (view: CalendarDate) => void;
}

function CalendarHeader({ view, onViewChange }: CalendarHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-1">
      <NavButton
        label="Poprzedni rok"
        onClick={() => onViewChange(shiftCalendarMonth(view.year, view.month, -12))}
      >
        «
      </NavButton>
      <NavButton
        label="Poprzedni miesiąc"
        onClick={() => onViewChange(shiftCalendarMonth(view.year, view.month, -1))}
      >
        ‹
      </NavButton>
      <p className="min-w-0 flex-1 text-center text-sm font-medium text-slate-100">
        {formatMonthTitle(view.year, view.month)}
      </p>
      <NavButton
        label="Następny miesiąc"
        onClick={() => onViewChange(shiftCalendarMonth(view.year, view.month, 1))}
      >
        ›
      </NavButton>
      <NavButton
        label="Następny rok"
        onClick={() => onViewChange(shiftCalendarMonth(view.year, view.month, 12))}
      >
        »
      </NavButton>
    </div>
  );
}

interface NavButtonProps {
  label: string;
  onClick: () => void;
  children: string;
}

function NavButton({ label, onClick, children }: NavButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800"
    >
      {children}
    </button>
  );
}

interface CalendarDayButtonProps {
  isoDate: string;
  day: number;
  inCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isDisabled: boolean;
  onSelect: (isoDate: string) => void;
}

function CalendarDayButton({
  isoDate,
  day,
  inCurrentMonth,
  isToday,
  isSelected,
  isDisabled,
  onSelect,
}: CalendarDayButtonProps) {
  return (
    <button
      type="button"
      disabled={isDisabled}
      aria-current={isToday ? "date" : undefined}
      aria-pressed={isSelected}
      onClick={() => onSelect(isoDate)}
      className={dayButtonClassName({
        inCurrentMonth,
        isToday,
        isSelected,
        isDisabled,
      })}
    >
      {day}
    </button>
  );
}

function dayButtonClassName(options: {
  inCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isDisabled: boolean;
}): string {
  const classes = [
    "h-8 cursor-pointer rounded-md text-sm transition",
    options.inCurrentMonth ? "text-slate-100" : "text-slate-500",
  ];
  if (options.isSelected) {
    classes.push("bg-sky-600 text-white");
  } else if (!options.isDisabled) {
    classes.push("hover:bg-slate-800");
  }
  if (options.isToday && !options.isSelected) {
    classes.push("ring-1 ring-sky-500");
  }
  if (options.isDisabled) {
    classes.push("cursor-not-allowed opacity-40");
  }
  return classes.join(" ");
}
