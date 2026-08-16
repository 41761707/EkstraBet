import { afterEach, describe, expect, it, vi } from "vitest";

import {
  navigateAfterAuth,
  navigateSearch,
} from "@/lib/clientNavigation";

describe("navigateAfterAuth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("replaces the document location so the new cookie is sent", () => {
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { replace },
    });

    navigateAfterAuth("/stats");

    expect(replace).toHaveBeenCalledWith("/stats");
  });
});

describe("navigateSearch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("pushes a new query through the App Router", () => {
    const router = { push: vi.fn(), refresh: vi.fn() };
    vi.stubGlobal("window", {
      location: { pathname: "/bets", search: "" },
    });

    navigateSearch("/bets?from_now=true", router);

    expect(router.push).toHaveBeenCalledWith("/bets?from_now=true", {
      scroll: false,
    });
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("refreshes without pushing when the URL is already current", () => {
    const router = { push: vi.fn(), refresh: vi.fn() };
    vi.stubGlobal("window", {
      location: { pathname: "/bets", search: "?from_now=true" },
    });

    navigateSearch("/bets?from_now=true", router);

    expect(router.push).not.toHaveBeenCalled();
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("treats encoded commas as the same current query", () => {
    const router = { push: vi.fn(), refresh: vi.fn() };
    vi.stubGlobal("window", {
      location: { pathname: "/stats", search: "?league_ids=1,2" },
    });

    navigateSearch("/stats?league_ids=1%2C2", router);

    expect(router.push).not.toHaveBeenCalled();
    expect(router.refresh).toHaveBeenCalledOnce();
  });
});
