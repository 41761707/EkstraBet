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

  it("pushes a new query and refreshes Server Components", () => {
    const pushState = vi.fn();
    const refresh = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/bets", search: "" },
      history: { pushState },
    });

    navigateSearch("/bets?from_now=true", refresh);

    expect(pushState).toHaveBeenCalledWith(null, "", "/bets?from_now=true");
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("refreshes without pushing when the URL is already current", () => {
    const pushState = vi.fn();
    const refresh = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/bets", search: "?from_now=true" },
      history: { pushState },
    });

    navigateSearch("/bets?from_now=true", refresh);

    expect(pushState).not.toHaveBeenCalled();
    expect(refresh).toHaveBeenCalledOnce();
  });
});
