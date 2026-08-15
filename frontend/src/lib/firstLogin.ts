export const FIRST_LOGIN_PATH = "/first-login";
export const FIRST_LOGIN_REQUIRED_DETAIL = "first_login_required";
export const PATHNAME_HEADER = "x-pathname";

const FIRST_LOGIN_EXEMPT_PATHS = new Set(["/login", FIRST_LOGIN_PATH]);

export function isFirstLoginExemptPath(pathname: string): boolean {
  return FIRST_LOGIN_EXEMPT_PATHS.has(pathname);
}

export function isFirstLoginRequiredError(
  status: number,
  detail: string,
): boolean {
  return status === 403 && detail === FIRST_LOGIN_REQUIRED_DETAIL;
}

/** True when a logged-in first-login user is outside the completion form. */
export function shouldRedirectToFirstLogin(
  authEnabled: boolean,
  pathname: string,
  isFirstLogin: boolean,
): boolean {
  if (!authEnabled || !isFirstLogin) {
    return false;
  }
  return !isFirstLoginExemptPath(pathname);
}
