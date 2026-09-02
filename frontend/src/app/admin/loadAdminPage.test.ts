import { afterEach, describe, expect, it, vi } from "vitest";

import { loadAdminPage } from "@/app/admin/loadAdminPage";
import { getCurrentUser } from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type { UserPublic } from "@/types/api";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
}));

const getCurrentUserMock = vi.mocked(getCurrentUser);

function sampleUser(overrides: Partial<UserPublic> = {}): UserPublic {
  return {
    uuid: "user-1",
    username: "alice",
    display_name: "Alicja",
    first_login: false,
    is_admin: false,
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
  });

  it("returns unauthenticated when the session is missing", async () => {
    getCurrentUserMock.mockRejectedValue(new ApiError(401, "Unauthorized"));

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "unauthenticated",
    });
  });

  it("returns ok for an administrator without fetching admin lists", async () => {
    const currentUser = sampleUser({ is_admin: true });
    getCurrentUserMock.mockResolvedValue(currentUser);

    await expect(loadAdminPage()).resolves.toEqual({
      kind: "ok",
      currentUser,
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
