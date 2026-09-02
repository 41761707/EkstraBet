import { describe, expect, it } from "vitest";

import {
  ADMIN_NAV_LINK,
  getAllNavLinks,
  getMoreNavLinks,
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

  it("appends the admin panel link only for an administrator", () => {
    expect(getAllNavLinks(true, false)).not.toContainEqual(ADMIN_NAV_LINK);
    expect(getAllNavLinks(false, true)).toContainEqual(ADMIN_NAV_LINK);
    expect(getAllNavLinks(true, true)).toEqual([
      ...PRIMARY_NAV_LINKS,
      ...MORE_NAV_LINKS,
      ADMIN_NAV_LINK,
      PROFILE_LINK,
    ]);
  });
});

describe("getMoreNavLinks", () => {
  it("keeps the admin panel out of Więcej for a regular user", () => {
    expect(getMoreNavLinks(false)).toEqual([...MORE_NAV_LINKS]);
    expect(getMoreNavLinks(false)).not.toContainEqual(ADMIN_NAV_LINK);
  });

  it("places Panel admina at the end of the overflow list", () => {
    expect(getMoreNavLinks(true)).toEqual([...MORE_NAV_LINKS, ADMIN_NAV_LINK]);
  });
});

describe("isMoreNavActive", () => {
  it("marks overflow destinations including nested simulate paths", () => {
    expect(isMoreNavActive("/chat")).toBe(true);
    expect(isMoreNavActive("/predictions/simulate")).toBe(true);
    expect(isMoreNavActive("/typer-lm")).toBe(false);
    expect(isMoreNavActive("/")).toBe(false);
  });

  it("marks the admin panel as an overflow destination when the link is shown", () => {
    expect(isMoreNavActive("/admin")).toBe(false);
    expect(isMoreNavActive("/admin", getMoreNavLinks(true))).toBe(true);
  });
});
