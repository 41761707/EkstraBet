import { describe, expect, it } from "vitest";

import { resolvePostLoginPath, safeInternalPath } from "@/lib/authCookie";

describe("resolvePostLoginPath", () => {
  it("sends first-login accounts to the completion form", () => {
    expect(resolvePostLoginPath(true, "/stats")).toBe("/first-login");
    expect(resolvePostLoginPath(true, null)).toBe("/first-login");
  });

  it("keeps the safe next path when first login is already completed", () => {
    expect(resolvePostLoginPath(false, "/stats")).toBe("/stats");
    expect(resolvePostLoginPath(false, null)).toBe("/");
  });

  it("rejects unsafe next targets the same way as safeInternalPath", () => {
    expect(resolvePostLoginPath(false, "//evil.com")).toBe(
      safeInternalPath("//evil.com"),
    );
    expect(resolvePostLoginPath(false, "https://evil.com")).toBe("/");
  });
});
