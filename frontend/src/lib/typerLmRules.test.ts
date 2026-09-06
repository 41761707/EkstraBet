import { describe, expect, it } from "vitest";

import { TYPER_LM_RULES_SECTIONS } from "@/lib/typerLmRules";

function allRuleItems(): string[] {
  return TYPER_LM_RULES_SECTIONS.flatMap((section) => [...section.items]);
}

describe("TYPER_LM_RULES_SECTIONS", () => {
  it("makes 1X2 picks public only after that match starts", () => {
    const items = allRuleItems();
    const privacyItem = items.find((item) => item.includes("Typy 1X2"));

    expect(privacyItem).toContain("prywatne do rozpoczęcia danego meczu");
    expect(privacyItem).toContain("publiczne po jego starcie");
    expect(items.some((item) => item.startsWith("Ranking:"))).toBe(true);
    expect(
      items.some((item) => item.includes("Typy innych osób nie są publiczne")),
    ).toBe(false);
  });

  it("keeps long-term picks private", () => {
    const longTerm = TYPER_LM_RULES_SECTIONS.find((section) =>
      section.heading.includes("tabela fazy ligowej"),
    );

    expect(longTerm).toBeDefined();
    expect(
      longTerm?.items.some((item) => item.includes("stają się publiczne")),
    ).toBe(false);
  });

  it("describes ranked table tiles, 0/2/4 scoring and BOT 8", () => {
    const tableSection = TYPER_LM_RULES_SECTIONS.find((section) =>
      section.heading.includes("tabela fazy ligowej"),
    );
    const items = allRuleItems();
    const tableCopy = (tableSection?.items ?? []).join(" ");

    expect(tableSection).toBeDefined();
    expect(tableCopy).toMatch(/kafelk/i);
    expect(tableCopy).toContain("BOT 8");
    expect(tableCopy).toContain("0 pkt");
    expect(tableCopy).toContain("2 pkt");
    expect(tableCopy).toContain("4 pkt");
    expect(
      items.some((item) => item.includes("Kolejność wyboru nie ma znaczenia")),
    ).toBe(false);
  });
});
