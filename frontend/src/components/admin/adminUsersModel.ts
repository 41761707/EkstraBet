import {
  MAX_DISPLAY_NAME_LENGTH,
  MAX_PASSWORD_LENGTH,
  MAX_USERNAME_LENGTH,
  MIN_DISPLAY_NAME_LENGTH,
  MIN_PASSWORD_LENGTH,
  MIN_USERNAME_LENGTH,
} from "@/components/auth/firstLoginFormModel";
import { ApiError } from "@/lib/apiShared";
import type { AdminUser, CreateUserRequest } from "@/types/api";

export const ADMIN_USERS_TITLE = "Użytkownicy";
export const ADMIN_USERS_DESCRIPTION =
  "Twórz konta i zarządzaj aktywnością oraz rolą administratora. " +
  "Hasło tymczasowe przekaż użytkownikowi poza aplikacją.";

export const EMPTY_ADMIN_USERS_TITLE = "Brak kont";
export const EMPTY_ADMIN_USERS_MESSAGE =
  "Dodaj pierwsze konto, aby użytkownik mógł przejść pierwsze logowanie.";

export const ADMIN_USERS_LOAD_ERROR_TITLE =
  "Nie udało się wczytać listy użytkowników";
export const ADMIN_USER_CREATE_ERROR_TITLE = "Nie udało się utworzyć konta";
export const ADMIN_USER_TOGGLE_ERROR_TITLE = "Nie udało się zapisać zmiany";

export const SELF_ACCOUNT_HINT = "To Twoje konto";
export const SELF_DEACTIVATE_HINT = "Nie możesz zawiesić własnego konta";
export const SELF_REVOKE_ADMIN_HINT =
  "Nie możesz odebrać sobie roli administratora";

export const GENERIC_ADMIN_USER_ERROR =
  "Nie udało się wykonać operacji. Spróbuj ponownie.";

export const ADMIN_USERS_BUSY_HINT =
  "Trwa zapisywanie. Poczekaj na zakończenie operacji.";

const ADMIN_USER_API_ERRORS: Record<string, string> = {
  "Username already taken": "Nazwa użytkownika jest już zajęta",
  "Cannot deactivate your own account": SELF_DEACTIVATE_HINT,
  "Cannot revoke your own admin role": SELF_REVOKE_ADMIN_HINT,
  "User not found": "Nie znaleziono użytkownika",
  "Invalid user uuid": "Nieprawidłowy identyfikator użytkownika",
};

export interface AddUserFormValues {
  username: string;
  temporaryPassword: string;
  displayName: string;
  isAdmin: boolean;
}

export function validateAddUserForm(input: AddUserFormValues): string | null {
  const username = input.username.trim();
  if (
    username.length < MIN_USERNAME_LENGTH ||
    username.length > MAX_USERNAME_LENGTH
  ) {
    return (
      `Nazwa użytkownika musi mieć od ${MIN_USERNAME_LENGTH} ` +
      `do ${MAX_USERNAME_LENGTH} znaków`
    );
  }
  const displayName = input.displayName.trim();
  if (
    displayName.length > 0 &&
    (displayName.length < MIN_DISPLAY_NAME_LENGTH ||
      displayName.length > MAX_DISPLAY_NAME_LENGTH)
  ) {
    return (
      `Wyświetlana nazwa musi mieć od ${MIN_DISPLAY_NAME_LENGTH} ` +
      `do ${MAX_DISPLAY_NAME_LENGTH} znaków`
    );
  }
  if (
    input.temporaryPassword.length < MIN_PASSWORD_LENGTH ||
    input.temporaryPassword.length > MAX_PASSWORD_LENGTH
  ) {
    return (
      `Hasło musi mieć od ${MIN_PASSWORD_LENGTH} ` +
      `do ${MAX_PASSWORD_LENGTH} znaków`
    );
  }
  return null;
}

export function buildCreateUserRequest(
  input: AddUserFormValues,
): CreateUserRequest {
  const displayName = input.displayName.trim();
  return {
    username: input.username.trim(),
    temporary_password: input.temporaryPassword,
    display_name: displayName === "" ? null : displayName,
    is_admin: input.isAdmin,
  };
}

export function mapAdminUserError(error: unknown): string {
  if (error instanceof ApiError) {
    return mapAdminUserApiDetail(error.message);
  }
  return GENERIC_ADMIN_USER_ERROR;
}

export function mapAdminUserApiDetail(detail: string | undefined): string {
  if (!detail) {
    return GENERIC_ADMIN_USER_ERROR;
  }
  const mapped = ADMIN_USER_API_ERRORS[detail];
  if (mapped) {
    return mapped;
  }
  if (detail.startsWith("Username must be between")) {
    return (
      `Nazwa użytkownika musi mieć od ${MIN_USERNAME_LENGTH} ` +
      `do ${MAX_USERNAME_LENGTH} znaków`
    );
  }
  if (detail.startsWith("Display name must be between")) {
    return (
      `Wyświetlana nazwa musi mieć od ${MIN_DISPLAY_NAME_LENGTH} ` +
      `do ${MAX_DISPLAY_NAME_LENGTH} znaków`
    );
  }
  if (detail.startsWith("Password must be between")) {
    return (
      `Hasło musi mieć od ${MIN_PASSWORD_LENGTH} ` +
      `do ${MAX_PASSWORD_LENGTH} znaków`
    );
  }
  return detail;
}

export function isSameAdminUser(
  currentUserUuid: string,
  userUuid: string,
): boolean {
  return currentUserUuid.toLowerCase() === userUuid.toLowerCase();
}

export function canSetUserActive(
  currentUserUuid: string,
  userUuid: string,
  nextActive: boolean,
): boolean {
  if (nextActive) {
    return true;
  }
  return !isSameAdminUser(currentUserUuid, userUuid);
}

export function canSetUserAdmin(
  currentUserUuid: string,
  userUuid: string,
  nextAdmin: boolean,
): boolean {
  if (nextAdmin) {
    return true;
  }
  return !isSameAdminUser(currentUserUuid, userUuid);
}

export function replaceAdminUser(
  users: readonly AdminUser[],
  updated: AdminUser,
): AdminUser[] {
  return users.map((user) => (user.uuid === updated.uuid ? updated : user));
}

export function prependAdminUser(
  users: readonly AdminUser[],
  created: AdminUser,
): AdminUser[] {
  if (users.some((user) => user.uuid === created.uuid)) {
    return replaceAdminUser(users, created);
  }
  return [created, ...users];
}
