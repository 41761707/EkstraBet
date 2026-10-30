import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ADMIN_USER_CREATE_ERROR_TITLE,
  ADMIN_USER_TOGGLE_ERROR_TITLE,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
} from "@/components/admin/adminUsersModel";
import {
  submitCreateAdminUser,
  submitToggleUserActive,
  submitToggleUserAdmin,
} from "@/components/admin/adminUsersMutations";
import {
  createAdminUser,
  setAdminUserActive,
  setAdminUserAdmin,
} from "@/lib/apiClient";
import { ApiError } from "@/lib/apiShared";
import type { AdminUser, CreateUserRequest } from "@/types/api";

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return {
    ...actual,
    createAdminUser: vi.fn(),
    setAdminUserActive: vi.fn(),
    setAdminUserAdmin: vi.fn(),
  };
});

const createAdminUserMock = vi.mocked(createAdminUser);
const setAdminUserActiveMock = vi.mocked(setAdminUserActive);
const setAdminUserAdminMock = vi.mocked(setAdminUserAdmin);

function sampleUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    is_active: true,
    is_admin: true,
    is_system: false,
    first_login: false,
    created_at: "2026-09-01T10:00:00",
    updated_at: "2026-09-01T10:00:00",
    ...overrides,
  };
}

const CREATE_REQUEST: CreateUserRequest = {
  username: "bob",
  temporary_password: "secret1",
  display_name: "Robert",
  is_admin: false,
};

describe("admin user mutations", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates a user through apiClient", async () => {
    const created = sampleUser({
      uuid: "22222222-2222-2222-2222-222222222222",
      username: "bob",
      display_name: "Robert",
      is_admin: false,
      first_login: true,
    });
    createAdminUserMock.mockResolvedValue(created);

    const result = await submitCreateAdminUser(CREATE_REQUEST);

    expect(createAdminUserMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result).toEqual({ ok: true, user: created });
  });

  it("returns the create error title when the API rejects the username", async () => {
    createAdminUserMock.mockRejectedValue(
      new ApiError(409, "Username already taken"),
    );

    const result = await submitCreateAdminUser(CREATE_REQUEST);

    expect(createAdminUserMock).toHaveBeenCalledWith(CREATE_REQUEST);
    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected create to fail");
    }
    expect(result.errorTitle).toBe(ADMIN_USER_CREATE_ERROR_TITLE);
  });

  it("toggles activity through apiClient", async () => {
    const bob = sampleUser({
      uuid: "22222222-2222-2222-2222-222222222222",
      username: "bob",
      is_admin: false,
    });
    const deactivated = { ...bob, is_active: false };
    setAdminUserActiveMock.mockResolvedValue(deactivated);

    const result = await submitToggleUserActive(sampleUser().uuid, bob);

    expect(setAdminUserActiveMock).toHaveBeenCalledWith(bob.uuid, false);
    expect(result).toEqual({ ok: true, user: deactivated });
  });

  it("toggles the admin role through apiClient", async () => {
    const bob = sampleUser({
      uuid: "22222222-2222-2222-2222-222222222222",
      username: "bob",
      is_admin: false,
    });
    const promoted = { ...bob, is_admin: true };
    setAdminUserAdminMock.mockResolvedValue(promoted);

    const result = await submitToggleUserAdmin(sampleUser().uuid, bob);

    expect(setAdminUserAdminMock).toHaveBeenCalledWith(bob.uuid, true);
    expect(result).toEqual({ ok: true, user: promoted });
  });

  it("maps an API self-protection failure onto the toggle error", async () => {
    const alice = sampleUser();
    setAdminUserActiveMock.mockRejectedValue(
      new ApiError(403, "Cannot deactivate your own account"),
    );

    const result = await submitToggleUserActive(
      "99999999-9999-9999-9999-999999999999",
      alice,
    );

    expect(setAdminUserActiveMock).toHaveBeenCalledWith(alice.uuid, false);
    expect(result).toEqual({
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: SELF_DEACTIVATE_HINT,
    });
  });

  it("blocks self-protection toggles without calling apiClient", async () => {
    const alice = sampleUser();

    const activeResult = await submitToggleUserActive(alice.uuid, alice);
    const adminResult = await submitToggleUserAdmin(alice.uuid, alice);

    expect(setAdminUserActiveMock).not.toHaveBeenCalled();
    expect(setAdminUserAdminMock).not.toHaveBeenCalled();
    expect(activeResult).toEqual({
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: SELF_DEACTIVATE_HINT,
    });
    expect(adminResult).toEqual({
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: SELF_REVOKE_ADMIN_HINT,
    });
  });
});
