import { describe, expect, it } from "vitest";

import {
  areBetsDateFiltersValid,
  betsDateQueryParams,
  betsFilterPath,
  createDefaultBetsFilterValues,
  parseBetsDateRange,
  parseBetsFilterValues,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";
import { todayIsoDate } from "@/lib/searchParams";
import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/types/api";

function baseFilters(
  overrides: Partial<BetsFilterValues> = {},
): BetsFilterValues {
  return createDefaultBetsFilterValues({
    dateFrom: "2026-08-15",
    dateTo: "2026-08-15",
    ...overrides,
  });
}

describe("betsFilterPath", () => {
  it("includes from_now when Tylko od teraz is selected", () => {
    expect(betsFilterPath(baseFilters({ fromNow: true }))).toContain(
      "from_now=true",
    );
  });

  it("omits from_now when the checkbox is off", () => {
    expect(betsFilterPath(baseFilters())).not.toContain("from_now");
  });

  it("keeps from_now when another field such as min odds changes", () => {
    const path = betsFilterPath(
      baseFilters({ fromNow: true, minOdds: 1.4 }),
    );
    expect(path).toContain("from_now=true");
    expect(path).toContain("min_odds=1.4");
  });

  it("serializes a date range instead of a single match_date", () => {
    const path = betsFilterPath(
      baseFilters({ dateFrom: "2026-08-01", dateTo: "2026-08-31" }),
    );
    expect(path).toContain("date_from=2026-08-01");
    expect(path).toContain("date_to=2026-08-31");
    expect(path).not.toContain("match_date");
  });

  it("marks cleared dates as all_dates so the page can load full history", () => {
    const path = betsFilterPath(baseFilters({ dateFrom: "", dateTo: "" }));
    expect(path).toContain("all_dates=true");
    expect(path).not.toContain("date_from");
    expect(path).not.toContain("date_to");
  });

  it("omits date params when from_now is on", () => {
    const path = betsFilterPath(
      baseFilters({
        fromNow: true,
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
      }),
    );
    expect(path).toContain("from_now=true");
    expect(path).not.toContain("date_from");
    expect(path).not.toContain("all_dates");
  });

  it("leaves subject and history_window off the default team URL", () => {
    const path = betsFilterPath(createDefaultBetsFilterValues());
    expect(path.startsWith("/bets")).toBe(true);
    expect(path).not.toContain("subject");
    expect(path).not.toContain("history_window");
  });

  it("writes hockey players as sport_id=2&subject=players", () => {
    const path = betsFilterPath(
      baseFilters({
        sportId: HOCKEY_SPORT_ID,
        subject: "players",
      }),
    );
    expect(path).toContain("sport_id=2&subject=players");
    expect(path).not.toContain("history_window");
  });

  it("writes history_window only for the short player window", () => {
    const shortWindow = betsFilterPath(
      baseFilters({
        sportId: HOCKEY_SPORT_ID,
        subject: "players",
        historyWindow: 5,
      }),
    );
    expect(shortWindow).toContain("history_window=5");

    const defaultWindow = betsFilterPath(
      baseFilters({
        sportId: HOCKEY_SPORT_ID,
        subject: "players",
        historyWindow: 10,
      }),
    );
    expect(defaultWindow).not.toContain("history_window");
  });

  it("omits history_window when the subject is still teams", () => {
    const path = betsFilterPath(
      baseFilters({ historyWindow: 5, subject: "teams" }),
    );
    expect(path).not.toContain("subject");
    expect(path).not.toContain("history_window");
  });
});

describe("parseBetsDateRange", () => {
  it("defaults missing dates to today", () => {
    const today = todayIsoDate();
    expect(parseBetsDateRange({})).toEqual({
      dateFrom: today,
      dateTo: today,
    });
  });

  it("maps a legacy match_date to both ends of the range", () => {
    expect(parseBetsDateRange({ match_date: "2026-07-01" })).toEqual({
      dateFrom: "2026-07-01",
      dateTo: "2026-07-01",
    });
  });

  it("keeps an open-ended range when only one bound is present", () => {
    expect(parseBetsDateRange({ date_from: "2026-08-01" })).toEqual({
      dateFrom: "2026-08-01",
      dateTo: "",
    });
  });

  it("clears both dates when all_dates is set", () => {
    expect(parseBetsDateRange({ all_dates: "true" })).toEqual({
      dateFrom: "",
      dateTo: "",
    });
  });
});

describe("parseBetsFilterValues", () => {
  it("prefers date_from/date_to over a leftover match_date", () => {
    const filters = parseBetsFilterValues({
      match_date: "2026-07-01",
      date_from: "2026-08-01",
      date_to: "2026-08-10",
    });
    expect(filters.dateFrom).toBe("2026-08-01");
    expect(filters.dateTo).toBe("2026-08-10");
  });

  it("defaults to teams and a window of 10", () => {
    const filters = parseBetsFilterValues({});
    expect(filters.subject).toBe("teams");
    expect(filters.historyWindow).toBe(10);
  });

  it("keeps players only when the sport is hockey", () => {
    const filters = parseBetsFilterValues({
      sport_id: String(HOCKEY_SPORT_ID),
      subject: "players",
      history_window: "5",
    });
    expect(filters.subject).toBe("players");
    expect(filters.historyWindow).toBe(5);
    expect(filters.sportId).toBe(HOCKEY_SPORT_ID);
  });

  it("parses subject=players on football as teams", () => {
    expect(
      parseBetsFilterValues({
        sport_id: String(FOOTBALL_SPORT_ID),
        subject: "players",
      }).subject,
    ).toBe("teams");
    expect(parseBetsFilterValues({ subject: "players" }).subject).toBe("teams");
  });

  it("treats any window other than 5 as 10", () => {
    expect(
      parseBetsFilterValues({
        sport_id: String(HOCKEY_SPORT_ID),
        history_window: "7",
      }).historyWindow,
    ).toBe(10);
    expect(
      parseBetsFilterValues({
        sport_id: String(HOCKEY_SPORT_ID),
        history_window: "10",
      }).historyWindow,
    ).toBe(10);
  });

  it("treats a subject other than players as teams", () => {
    expect(
      parseBetsFilterValues({
        sport_id: String(HOCKEY_SPORT_ID),
        subject: "teams",
      }).subject,
    ).toBe("teams");
  });
});

describe("areBetsDateFiltersValid", () => {
  it("allows empty bounds and equal dates", () => {
    expect(areBetsDateFiltersValid(baseFilters({ dateFrom: "", dateTo: "" }))).toBe(
      true,
    );
    expect(areBetsDateFiltersValid(baseFilters())).toBe(true);
  });

  it("rejects a start date later than the end date", () => {
    expect(
      areBetsDateFiltersValid(
        baseFilters({ dateFrom: "2026-08-31", dateTo: "2026-08-01" }),
      ),
    ).toBe(false);
  });
});

describe("betsDateQueryParams", () => {
  it("sends no dates when the user cleared the range", () => {
    expect(
      betsDateQueryParams(baseFilters({ dateFrom: "", dateTo: "" })),
    ).toEqual({ fromNow: false });
  });

  it("ignores the range when from_now is on", () => {
    expect(
      betsDateQueryParams(
        baseFilters({
          fromNow: true,
          dateFrom: "2026-08-01",
          dateTo: "2026-08-31",
        }),
      ),
    ).toEqual({ fromNow: true });
  });
});
