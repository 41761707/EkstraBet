import { describe, expect, it } from "vitest";

import {
  FIRST_LOGIN_PATH,
  isFirstLoginExemptPath,
  isFirstLoginRequiredError,
  shouldRedirectToFirstLogin,
} from "@/lib/firstLogin";

describe("isFirstLoginExemptPath", () => {
  it("allows login and the first-login form", () => {
    expect(isFirstLoginExemptPath("/login")).toBe(true);
    expect(isFirstLoginExemptPath(FIRST_LOGIN_PATH)).toBe(true);
  });

  it("does not exempt the rest of the app", () => {
    expect(isFirstLoginExemptPath("/")).toBe(false);
    expect(isFirstLoginExemptPath("/stats")).toBe(false);
    expect(isFirstLoginExemptPath("")).toBe(false);
  });
});

describe("isFirstLoginRequiredError", () => {
  it("matches the API 403 contract", () => {
    expect(isFirstLoginRequiredError(403, "first_login_required")).toBe(true);
    expect(isFirstLoginRequiredError(403, "Forbidden")).toBe(false);
    expect(isFirstLoginRequiredError(401, "first_login_required")).toBe(false);
  });
});

describe("shouldRedirectToFirstLogin", () => {
  it("redirects first-login users away from the rest of the app", () => {
    expect(shouldRedirectToFirstLogin(true, "/", true)).toBe(true);
    expect(shouldRedirectToFirstLogin(true, "/stats", true)).toBe(true);
  });

  it("keeps users on login and the completion form", () => {
    expect(shouldRedirectToFirstLogin(true, "/login", true)).toBe(false);
    expect(shouldRedirectToFirstLogin(true, FIRST_LOGIN_PATH, true)).toBe(false);
  });

  it("does not redirect completed accounts or when auth is off", () => {
    expect(shouldRedirectToFirstLogin(true, "/", false)).toBe(false);
    expect(shouldRedirectToFirstLogin(false, "/", true)).toBe(false);
  });
});
