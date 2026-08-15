export const MIN_PASSWORD_LENGTH = 3;
export const MAX_PASSWORD_LENGTH = 200;
export const MIN_USERNAME_LENGTH = 1;
export const MAX_USERNAME_LENGTH = 50;
export const MIN_DISPLAY_NAME_LENGTH = 1;
export const MAX_DISPLAY_NAME_LENGTH = 50;

const COMPLETE_FIRST_LOGIN_ERRORS: Record<string, string> = {
  "Passwords do not match": "Hasła nie są identyczne",
  "Username already taken": "Nazwa użytkownika jest już zajęta",
  "First login already completed": "Konto zostało już uzupełnione",
};

interface FirstLoginFormValues {
  username: string;
  displayName: string;
  newPassword: string;
  newPasswordConfirm: string;
}

export function validateFirstLoginForm(
  input: FirstLoginFormValues,
): string | null {
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
    displayName.length < MIN_DISPLAY_NAME_LENGTH ||
    displayName.length > MAX_DISPLAY_NAME_LENGTH
  ) {
    return (
      `Wyświetlana nazwa musi mieć od ${MIN_DISPLAY_NAME_LENGTH} ` +
      `do ${MAX_DISPLAY_NAME_LENGTH} znaków`
    );
  }
  if (input.newPassword !== input.newPasswordConfirm) {
    return "Hasła nie są identyczne";
  }
  if (
    input.newPassword.length < MIN_PASSWORD_LENGTH ||
    input.newPassword.length > MAX_PASSWORD_LENGTH
  ) {
    return (
      `Hasło musi mieć od ${MIN_PASSWORD_LENGTH} ` +
      `do ${MAX_PASSWORD_LENGTH} znaków`
    );
  }
  return null;
}

export function mapCompleteFirstLoginError(detail: string | undefined): string {
  if (!detail) {
    return "Nie udało się zapisać danych konta";
  }
  const mapped = COMPLETE_FIRST_LOGIN_ERRORS[detail];
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
