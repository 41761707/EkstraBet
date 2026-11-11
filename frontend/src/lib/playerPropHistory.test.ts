import { describe, expect, it } from "vitest";

import { formatPropHistoryCount } from "@/lib/playerPropHistory";

describe("formatPropHistoryCount", () => {
  it("counts hits against the matches that had a stat", () => {
    expect(formatPropHistoryCount(6, 10)).toBe("6 na 10");
  });

  it("uses a dash when the player has no prior matches", () => {
    expect(formatPropHistoryCount(0, 0)).toBe("—");
  });
});
