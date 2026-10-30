import { describe, expect, it } from "vitest";

import { overlayPositionForDrag } from "@/components/typer-lm/TyperLmLongTermRankedTable";

describe("overlayPositionForDrag", () => {
  const teamIds = [1, 36];

  it("returns a 1-based slot for the team under the pointer", () => {
    expect(overlayPositionForDrag(1, teamIds)).toBe(1);
    expect(overlayPositionForDrag(36, teamIds)).toBe(2);
    expect(overlayPositionForDrag(null, teamIds)).toBeNull();
  });
});
