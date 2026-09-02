import { describe, expect, it } from "vitest";

import {
  ADMIN_USER_CREATE_ERROR_TITLE,
  GENERIC_ADMIN_USER_ERROR,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
  buildCreateUserRequest,
  canSetUserAdmin,
  canSetUserActive,
  isSameAdminUser,
  mapAdminUserApiDetail,
  mapAdminUserError,
  prependAdminUser,
  replaceAdminUser,
  validateAddUserForm,
} from "@/components/admin/adminUsersModel";
import { ApiError } from "@/lib/apiShared";
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

describe("validateAddUserForm", () => {
  it("accepts a username, temporary password and optional display name", () => {
    expect(
      validateAddUserForm({
        username: " bob ",
        temporaryPassword: "secret1",
        displayName: " Robert ",
        isAdmin: false,
      }),
    ).toBeNull();
    expect(
      validateAddUserForm({
        username: "bob",
        temporaryPassword: "abc",
        displayName: "   ",
        isAdmin: true,
      }),
    ).toBeNull();
  });

  it("rejects an empty username after trim", () => {
    expect(
      validateAddUserForm({
        username: "   ",
        temporaryPassword: "secret1",
        displayName: "",
        isAdmin: false,
      }),
    ).toBe("Nazwa użytkownika musi mieć od 1 do 50 znaków");
  });

  it("rejects a password shorter than 3 characters", () => {
    expect(
      validateAddUserForm({
        username: "bob",
        temporaryPassword: "ab",
        displayName: "",
        isAdmin: false,
      }),
    ).toBe("Hasło musi mieć od 3 do 200 znaków");
  });
});

describe("buildCreateUserRequest", () => {
  it("trims fields and never includes a password hash", () => {
    const request = buildCreateUserRequest({
      username: " bob ",
      temporaryPassword: "secret1",
      displayName: "  ",
      isAdmin: true,
    });

    expect(request).toEqual({
      username: "bob",
      temporary_password: "secret1",
      display_name: null,
      is_admin: true,
    });
    expect(request).not.toHaveProperty("password_hash");
  });
});

describe("admin user list updates", () => {
  it("prepends a created user and replaces a toggled row", () => {
    const existing = sampleUser();
    const created = sampleUser({
      uuid: "22222222-2222-2222-2222-222222222222",
      username: "bob",
      is_admin: false,
      first_login: true,
    });
    const prepended = prependAdminUser([existing], created);
    expect(prepended.map((user) => user.username)).toEqual(["bob", "alice"]);

    const deactivated = sampleUser({ is_active: false });
    expect(replaceAdminUser(prepended, deactivated)[1]?.is_active).toBe(false);
  });
});

describe("self-protection", () => {
  it("compares uuids case-insensitively", () => {
    expect(
      isSameAdminUser(
        "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      ),
    ).toBe(true);
  });

  it("blocks deactivating or revoking admin on the current account", () => {
    const selfUuid = sampleUser().uuid;
    expect(canSetUserActive(selfUuid, selfUuid, false)).toBe(false);
    expect(canSetUserAdmin(selfUuid, selfUuid, false)).toBe(false);
    expect(canSetUserActive(selfUuid, selfUuid, true)).toBe(true);
    expect(canSetUserAdmin(selfUuid, selfUuid, true)).toBe(true);
    expect(
      canSetUserActive(selfUuid, "22222222-2222-2222-2222-222222222222", false),
    ).toBe(true);
  });
});

describe("mapAdminUserError", () => {
  it("maps create, toggle and self-protection API details", () => {
    expect(mapAdminUserApiDetail("Username already taken")).toBe(
      "Nazwa użytkownika jest już zajęta",
    );
    expect(mapAdminUserApiDetail("Cannot deactivate your own account")).toBe(
      SELF_DEACTIVATE_HINT,
    );
    expect(mapAdminUserApiDetail("Cannot revoke your own admin role")).toBe(
      SELF_REVOKE_ADMIN_HINT,
    );
    expect(
      mapAdminUserError(new ApiError(409, "Username already taken")),
    ).toBe("Nazwa użytkownika jest już zajęta");
    expect(mapAdminUserError(new ApiError(500, ""))).toBe(
      GENERIC_ADMIN_USER_ERROR,
    );
    expect(ADMIN_USER_CREATE_ERROR_TITLE).toContain("utworzyć");
  });
});
