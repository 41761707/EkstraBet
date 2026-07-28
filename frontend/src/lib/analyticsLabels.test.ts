import { describe, expect, it } from "vitest";

import { formatAnalyticsTypeLabel } from "@/lib/analyticsLabels";

describe("formatAnalyticsTypeLabel", () => {
  it("maps OU keys to Polish labels", () => {
    expect(formatAnalyticsTypeLabel("under_2_5")).toBe("Poniżej 2.5");
    expect(formatAnalyticsTypeLabel("over_2_5")).toBe("Powyżej 2.5");
  });

  it("maps English chart labels as fallback", () => {
    expect(formatAnalyticsTypeLabel("Under 2.5")).toBe("Poniżej 2.5");
    expect(formatAnalyticsTypeLabel("Over 2.5")).toBe("Powyżej 2.5");
  });

  it("maps BTTS and result keys", () => {
    expect(formatAnalyticsTypeLabel("yes")).toBe("BTTS tak");
    expect(formatAnalyticsTypeLabel("no")).toBe("BTTS nie");
    expect(formatAnalyticsTypeLabel("home")).toBe("Gospodarz");
    expect(formatAnalyticsTypeLabel("draw")).toBe("Remis");
    expect(formatAnalyticsTypeLabel("away")).toBe("Gość");
  });
});
