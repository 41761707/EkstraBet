import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminLeagueRow } from "@/components/admin/AdminLeagueRow";
import { ADMIN_LEAGUES_BUSY_HINT } from "@/components/admin/adminLeaguesModel";
import { formatMatchDate } from "@/lib/format";
import type { AdminLeague, AdminSeason } from "@/types/api";

function sampleLeague(overrides: Partial<AdminLeague> = {}): AdminLeague {
  return {
    id: 48,
    name: "Ekstraklasa",
    country_id: 1,
    country_name: "Polska",
    country_emoji: "🇵🇱",
    sport_id: 1,
    sport_name: "Piłka nożna",
    active: true,
    last_update: "2026-09-01",
    current_season_id: 13,
    tier: 1,
    has_player_stats: false,
    ...overrides,
  };
}

const SEASONS: AdminSeason[] = [{ id: 13, years: "2026/27" }];

describe("AdminLeagueRow", () => {
  it("renders league fields, season years and a deactivate action", () => {
    const html = renderToStaticMarkup(
      <AdminLeagueRow
        league={sampleLeague()}
        seasons={SEASONS}
        isSaving={false}
        areActionsLocked={false}
        onToggleActive={() => undefined}
      />,
    );

    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("ID 48");
    expect(html).toContain("🇵🇱 Polska");
    expect(html).toContain("Piłka nożna");
    expect(html).toContain("2026/27");
    expect(html).toContain("Aktywna");
    expect(html).toContain("Dezaktywuj");
    expect(html).toContain(formatMatchDate("2026-09-01"));
    expect(html).not.toContain("Statystyki zawodników");
  });

  it("allows activating an inactive league including a null name", () => {
    const html = renderToStaticMarkup(
      <AdminLeagueRow
        league={sampleLeague({
          name: null,
          active: false,
          has_player_stats: true,
          current_season_id: null,
          tier: null,
        })}
        seasons={SEASONS}
        isSaving={false}
        areActionsLocked={false}
        onToggleActive={() => undefined}
      />,
    );

    expect(html).toContain("—");
    expect(html).toContain("Nieaktywna");
    expect(html).toContain("Aktywuj");
    expect(html).toContain("Statystyki zawodników");
  });

  it("disables the toggle while another save is in flight", () => {
    const html = renderToStaticMarkup(
      <AdminLeagueRow
        league={sampleLeague()}
        seasons={SEASONS}
        isSaving={false}
        areActionsLocked={true}
        onToggleActive={() => undefined}
      />,
    );

    expect(html).toContain("Dezaktywuj");
    expect(html).not.toContain("Zapisywanie…");
    expect(html).toContain(ADMIN_LEAGUES_BUSY_HINT);
    expect(html).toContain("disabled");
  });
});
