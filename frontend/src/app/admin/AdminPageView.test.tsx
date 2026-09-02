import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminPageView } from "@/app/admin/AdminPageView";
import { ADMIN_USERS_TITLE } from "@/components/admin/adminUsersModel";
import type { AdminUser } from "@/types/api";

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

describe("AdminPageView", () => {
  it("renders the admin chrome and users panel without leaking hashes", () => {
    const html = renderToStaticMarkup(
      <AdminPageView
        currentUserUuid={sampleUser().uuid}
        users={[sampleUser()]}
      />,
    );

    expect(html).toContain("Panel administratora");
    expect(html).toContain("Zarządzaj kontami użytkowników i ligami.");
    expect(html).toContain(ADMIN_USERS_TITLE);
    expect(html).toContain("alice");
    expect(html).not.toContain("password_hash");
  });
});
