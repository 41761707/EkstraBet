import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminPageView } from "@/app/admin/AdminPageView";
import { ADMIN_LEAGUES_TITLE } from "@/components/admin/adminLeaguesModel";
import { ADMIN_USERS_TITLE } from "@/components/admin/adminUsersModel";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  AdminUser,
} from "@/types/api";

function sampleUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    is_active: true,
    is_admin: true,
    first_login: false,
    created_at: "2026-09-01T10:00:00",
    updated_at: "2026-09-01T10:00:00",
    ...overrides,
  };
}

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

const COUNTRIES: AdminCountry[] = [
  { id: 1, name: "Polska", short_name: "POL", emoji: "🇵🇱" },
];
const SPORTS: AdminSport[] = [{ id: 1, name: "Piłka nożna" }];
const SEASONS: AdminSeason[] = [{ id: 13, years: "2026/27" }];

describe("AdminPageView", () => {
  it("renders both admin panels without leaking hashes", () => {
    const html = renderToStaticMarkup(
      <AdminPageView
        currentUserUuid={sampleUser().uuid}
        users={[sampleUser()]}
        leagues={[sampleLeague()]}
        countries={COUNTRIES}
        sports={SPORTS}
        seasons={SEASONS}
      />,
    );

    expect(html).toContain("Panel administratora");
    expect(html).toContain("Zarządzaj kontami użytkowników i ligami.");
    expect(html).toContain(ADMIN_USERS_TITLE);
    expect(html).toContain(ADMIN_LEAGUES_TITLE);
    expect(html).toContain("alice");
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("Polska");
    expect(html).toContain("2026/27");
    expect(html).not.toContain("password_hash");
  });
});
