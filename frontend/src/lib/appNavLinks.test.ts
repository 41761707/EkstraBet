import { describe, expect, it } from "vitest";

import {
  getAllNavLinks,
  isMoreNavActive,
  MORE_NAV_LINKS,
  PRIMARY_NAV_LINKS,
  PROFILE_LINK,
} from "@/lib/appNavLinks";

describe("getAllNavLinks", () => {
  it("keeps primary destinations before overflow items", () => {
    const hrefs = getAllNavLinks(false).map((link) => link.href);
    expect(hrefs.slice(0, PRIMARY_NAV_LINKS.length)).toEqual(
      PRIMARY_NAV_LINKS.map((link) => link.href),
    );
    expect(hrefs.slice(PRIMARY_NAV_LINKS.length)).toEqual(
      MORE_NAV_LINKS.map((link) => link.href),
    );
  });

  it("appends the profile link only when requested", () => {
    expect(getAllNavLinks(false)).not.toContainEqual(PROFILE_LINK);
    expect(getAllNavLinks(true).at(-1)).toEqual(PROFILE_LINK);
  });
});

describe("isMoreNavActive", () => {
  it("marks overflow destinations including nested simulate paths", () => {
    expect(isMoreNavActive("/chat")).toBe(true);
    expect(isMoreNavActive("/predictions/simulate")).toBe(true);
    expect(isMoreNavActive("/typer-lm")).toBe(false);
    expect(isMoreNavActive("/")).toBe(false);
  });
});
