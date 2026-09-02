import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminUserRow } from "@/components/admin/AdminUserRow";
import {
  ADMIN_USERS_BUSY_HINT,
  SELF_ACCOUNT_HINT,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
} from "@/components/admin/adminUsersModel";
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

describe("AdminUserRow", () => {
  it("renders account fields without secrets and disables self-protection actions", () => {
    const html = renderToStaticMarkup(
      <AdminUserRow
        user={sampleUser()}
        currentUserUuid={sampleUser().uuid}
        isSaving={false}
        areActionsLocked={false}
        onToggleActive={() => undefined}
        onToggleAdmin={() => undefined}
      />,
    );

    expect(html).toContain("alice");
    expect(html).toContain("UUID 11111111-1111-1111-1111-111111111111");
    expect(html).toContain("Alicja");
    expect(html).toContain(SELF_ACCOUNT_HINT);
    expect(html).toContain(SELF_DEACTIVATE_HINT);
    expect(html).toContain(SELF_REVOKE_ADMIN_HINT);
    expect(html).toContain("Zawieś");
    expect(html).toContain("Odbierz rolę admina");
    expect(html).not.toContain("password_hash");
    expect(html).not.toContain("temporary_password");
  });

  it("allows toggling another account including a first-login user", () => {
    const html = renderToStaticMarkup(
      <AdminUserRow
        user={sampleUser({
          uuid: "22222222-2222-2222-2222-222222222222",
          username: "bob",
          is_admin: false,
          is_active: false,
          first_login: true,
        })}
        currentUserUuid={sampleUser().uuid}
        isSaving={false}
        areActionsLocked={false}
        onToggleActive={() => undefined}
        onToggleAdmin={() => undefined}
      />,
    );

    expect(html).toContain("bob");
    expect(html).toContain("UUID 22222222-2222-2222-2222-222222222222");
    expect(html).toContain("Wznów");
    expect(html).toContain("Nadaj rolę admina");
    expect(html).toContain("Pierwsze logowanie");
    expect(html).toContain("Zawieszone");
    expect(html).not.toContain(SELF_DEACTIVATE_HINT);
  });

  it("disables all actions on every row while another save is in flight", () => {
    const html = renderToStaticMarkup(
      <AdminUserRow
        user={sampleUser({
          uuid: "22222222-2222-2222-2222-222222222222",
          username: "bob",
          is_admin: false,
        })}
        currentUserUuid={sampleUser().uuid}
        isSaving={false}
        areActionsLocked={true}
        onToggleActive={() => undefined}
        onToggleAdmin={() => undefined}
      />,
    );

    expect(html).toContain("Zawieś");
    expect(html).toContain("Nadaj rolę admina");
    expect(html).not.toContain("Zapisywanie…");
    expect(html).toContain(ADMIN_USERS_BUSY_HINT);
    expect(html).toContain("disabled");
  });
});
