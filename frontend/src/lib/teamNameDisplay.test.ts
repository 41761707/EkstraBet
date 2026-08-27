import { describe, expect, it } from "vitest";

import { formatTeamName } from "@/lib/teamNameDisplay";

describe("formatTeamName", () => {
  it("returns the full name in full mode even when a shortcut exists", () => {
    expect(formatTeamName("Lech Poznań", "LPO", "full")).toBe("Lech Poznań");
    expect(formatTeamName("Śląsk Wrocław", "SLA", "full")).toBe("Śląsk Wrocław");
  });

  it("returns the trimmed shortcut in shortcut mode", () => {
    expect(formatTeamName("Lech Poznań", "LPO", "shortcut")).toBe("LPO");
    expect(formatTeamName("Lech Poznań", "  LPO  ", "shortcut")).toBe("LPO");
  });

  it("falls back to the full name when the shortcut is missing or blank", () => {
    expect(formatTeamName("Lech Poznań", null, "shortcut")).toBe("Lech Poznań");
    expect(formatTeamName("Górnik Zabrze", undefined, "shortcut")).toBe(
      "Górnik Zabrze",
    );
    expect(formatTeamName("Lech Poznań", "", "shortcut")).toBe("Lech Poznań");
    expect(formatTeamName("Lech Poznań", "   ", "shortcut")).toBe("Lech Poznań");
  });

  it("keeps Polish characters in full names", () => {
    expect(formatTeamName("Zagłębie Lubin", "ZAG", "full")).toBe(
      "Zagłębie Lubin",
    );
    expect(formatTeamName("Zagłębie Lubin", null, "shortcut")).toBe(
      "Zagłębie Lubin",
    );
  });
});
