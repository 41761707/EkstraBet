import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AdminUsersPanel,
  AdminUsersStatus,
} from "@/components/admin/AdminUsersPanel";
import {
  ADMIN_USERS_LOAD_ERROR_TITLE,
  ADMIN_USERS_TITLE,
  ADMIN_USER_CREATE_ERROR_TITLE,
  ADMIN_USER_TOGGLE_ERROR_TITLE,
  EMPTY_ADMIN_USERS_TITLE,
  SELF_ACCOUNT_HINT,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
  prependAdminUser,
  replaceAdminUser,
} from "@/components/admin/adminUsersModel";
import {
  submitCreateAdminUser,
  submitToggleUserActive,
  submitToggleUserAdmin,
} from "@/components/admin/adminUsersMutations";
import { ADD_USER_FORM_TITLE } from "@/components/admin/AddUserForm";
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

describe("AdminUsersPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the users list, create form and self-protection on the current row", () => {
    const html = renderToStaticMarkup(
      <AdminUsersPanel
        currentUserUuid={sampleUser().uuid}
        initialUsers={[
          sampleUser(),
          sampleUser({
            uuid: "22222222-2222-2222-2222-222222222222",
            username: "bob",
            is_admin: false,
            first_login: true,
          }),
        ]}
      />,
    );

    expect(html).toContain(ADMIN_USERS_TITLE);
    expect(html).toContain(ADD_USER_FORM_TITLE);
    expect(html).toContain("alice");
    expect(html).toContain("bob");
    expect(html).toContain(SELF_ACCOUNT_HINT);
    expect(html).toContain('name="temporary_password"');
    expect(html).toContain('aria-busy="false"');
    expect(html).not.toContain("password_hash");
  });

  it("renders an empty state when there are no accounts", () => {
    const html = renderToStaticMarkup(
      <AdminUsersPanel currentUserUuid={sampleUser().uuid} initialUsers={[]} />,
    );

    expect(html).toContain(EMPTY_ADMIN_USERS_TITLE);
    expect(html).toContain(ADD_USER_FORM_TITLE);
  });

  it("renders a load error through StatusMessage", () => {
    const html = renderToStaticMarkup(
      <AdminUsersPanel
        currentUserUuid={sampleUser().uuid}
        initialUsers={[]}
        usersError="Połączenie odrzucone."
      />,
    );

    expect(html).toContain(ADMIN_USERS_LOAD_ERROR_TITLE);
    expect(html).toContain("Połączenie odrzucone.");
    expect(html).not.toContain(EMPTY_ADMIN_USERS_TITLE);
  });
});

describe("AdminUsersPanel mutations", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates a user through apiClient and prepends the returned row", async () => {
    const alice = sampleUser();
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
    if (!result.ok) {
      throw new Error("expected create to succeed");
    }
    const html = renderToStaticMarkup(
      <AdminUsersPanel
        currentUserUuid={alice.uuid}
        initialUsers={prependAdminUser([alice], result.user)}
      />,
    );
    expect(html.indexOf("bob")).toBeLessThan(html.indexOf("alice"));
    expect(html).not.toContain("secret1");
    expect(html).not.toContain("password_hash");
  });

  it("shows StatusMessage after a 409 create conflict", async () => {
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
    const html = renderToStaticMarkup(
      <AdminUsersStatus title={result.errorTitle} message={result.errorMessage} />,
    );
    expect(html).toContain(ADMIN_USER_CREATE_ERROR_TITLE);
    expect(html).toContain("Nazwa użytkownika jest już zajęta");
    expect(html).toContain('role="status"');
  });

  it("toggles activity through apiClient and replaces the row", async () => {
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
    if (!result.ok) {
      throw new Error("expected toggle to succeed");
    }
    const html = renderToStaticMarkup(
      <AdminUsersPanel
        currentUserUuid={sampleUser().uuid}
        initialUsers={replaceAdminUser([sampleUser(), bob], result.user)}
      />,
    );
    expect(html).toContain("Zawieszone");
    expect(html).toContain("Wznów");
  });

  it("toggles the admin role through apiClient and replaces the row", async () => {
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
    if (!result.ok) {
      throw new Error("expected toggle to succeed");
    }
    const html = renderToStaticMarkup(
      <AdminUsersPanel
        currentUserUuid={sampleUser().uuid}
        initialUsers={replaceAdminUser([sampleUser(), bob], result.user)}
      />,
    );
    expect(html).toContain("Odbierz rolę admina");
  });

  it("shows StatusMessage after a 403 self-protection toggle", async () => {
    const alice = sampleUser();
    setAdminUserActiveMock.mockRejectedValue(
      new ApiError(403, "Cannot deactivate your own account"),
    );

    const bypassed = await submitToggleUserActive(
      "99999999-9999-9999-9999-999999999999",
      alice,
    );
    expect(setAdminUserActiveMock).toHaveBeenCalledWith(alice.uuid, false);
    expect(bypassed.ok).toBe(false);
    if (bypassed.ok) {
      throw new Error("expected toggle to fail");
    }

    const html = renderToStaticMarkup(
      <AdminUsersStatus
        title={bypassed.errorTitle}
        message={bypassed.errorMessage}
      />,
    );
    expect(html).toContain(ADMIN_USER_TOGGLE_ERROR_TITLE);
    expect(html).toContain(SELF_DEACTIVATE_HINT);
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
