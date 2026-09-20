import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  SYSTEM_ACCOUNT_LABEL,
  TIPSTER_LEADERBOARD_EMPTY_MESSAGE,
  TIPSTER_LEADERBOARD_EMPTY_TITLE,
  TipsterLeaderboard,
} from "@/components/tipsters/TipsterLeaderboard";
import type { LeaderboardRow } from "@/types/api";

function sampleRow(overrides: Partial<LeaderboardRow> = {}): LeaderboardRow {
  return {
    user_id: 11,
    username: "alice",
    display_name: "Ala",
    is_system: false,
    currency: "PLN",
    bets_count: 4,
    won_count: 2,
    accuracy_pct: 50,
    stake_total: 40,
    profit_total: 12.5,
    avg_profit: 3.125,
    avg_odds: 1.92,
    roi_pct: 31.3,
    current_balance: 1012.5,
    ...overrides,
  };
}

describe("TipsterLeaderboard", () => {
  it("shows the empty ranking copy when there are no rows", () => {
    const html = renderToStaticMarkup(
      <TipsterLeaderboard
        rows={[]}
        total={0}
        page={1}
        pageSize={20}
        searchParams={{}}
      />,
    );

    expect(html).toContain(TIPSTER_LEADERBOARD_EMPTY_TITLE);
    expect(html).toContain(TIPSTER_LEADERBOARD_EMPTY_MESSAGE);
    expect(html).not.toContain("href=\"/profile/");
  });

  it("links each row to /profile/{username}", () => {
    const html = renderToStaticMarkup(
      <TipsterLeaderboard
        rows={[
          sampleRow(),
          sampleRow({
            user_id: 22,
            username: "system-agent",
            display_name: "Agent A",
            is_system: true,
            currency: "EUR",
            profit_total: -8,
            roi_pct: null,
            accuracy_pct: null,
            avg_odds: null,
            current_balance: 992,
          }),
        ]}
        total={2}
        page={1}
        pageSize={20}
        searchParams={{}}
      />,
    );

    expect(html).toContain('href="/profile/alice"');
    expect(html).toContain('href="/profile/system-agent"');
    expect(html).toContain("Ala");
    expect(html).toContain("Agent A");
    expect(html).toContain(SYSTEM_ACCOUNT_LABEL);
    expect(html).toContain("+12.50 PLN");
    expect(html).toContain("+3.13 PLN");
    expect(html).toContain("1012.50 PLN");
    expect(html).toContain("-8.00 EUR");
    expect(html).toContain("992.00 EUR");
  });
});
