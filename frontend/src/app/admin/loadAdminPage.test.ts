import { afterEach, describe, expect, it, vi } from "vitest";

import { loadAdminPage } from "@/app/admin/loadAdminPage";
import { getAdminUsers, getCurrentUser } from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type { AdminUser, UserPublic } from "@/types/api";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminUsers: vi.fn(),
}));

const getCurrentUserMock = vi.mocked(getCurrentUser);
const getAdminUsersMock = vi.mocked(getAdminUsers);

function sampleUser(overrides: Partial<UserPublic> = {}): UserPublic {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    first_login: false,
    is_admin: false,
    ...overrides,
  };
}

function sampleAdminUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    username: "alice",
    display_name: "Alicja",
    is_active: true,
    is_admin: true,
    first_login: false,
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

describe("loadAdminPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns forbidden for a signed-in non-admin", async () => {
    getCurrentUserMock.mockResolvedValue(sampleUser({ is_admin: false }));

    await expect(loadAdminPage()).resolves.toEqual({ kind: "forbidden" });
    expect(getAdminUsersMock).not.toHaveBeenCalled();
  });

  it("returns unauthenticated when the session is missing", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(401, "Unauthorized"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "unauthenticated",
    });
  });

  it("returns ok with bootstrapped users for an administrator", async () => {
    const currentUser = sampleUser({ is_admin: true });
    const users = [sampleAdminUser()];
    getCurrentUserMock.mockResolvedValue(currentUser);
    getAdminUsersMock.mockResolvedValue(users);

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "ok",
      currentUser,
      users,
      usersError: null,
    });
  });

  it("keeps the page available when the users list fails to load", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);
    getAdminUsersMock.mockRejectedValue(new ApiError(500, "Błąd serwera"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "ok",
      currentUser,
      users: [],
      usersError: "Błąd serwera",
    });
  });

  it("treats a 403 from /auth/me as forbidden", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(403, "Forbidden"));

    await expect(loadAdminPage()).resolves.toEqual({ kind: "forbidden" });
  });

  it("returns an error payload when the current-user lookup fails", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(500, "Błąd serwera"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "error",
      message: "Błąd serwera",
    });
  });
});
