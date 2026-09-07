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
    expect(tableCopy).toMatch(/kafelek/i);
    expect(tableCopy).toContain("BOT 8");
    expect(tableCopy).toContain("0 pkt");
    expect(tableCopy).toContain("2 pkt");
    expect(tableCopy).toContain("4 pkt");
    expect(
      items.some((item) => item.includes("Kolejność wyboru nie ma znaczenia")),
    ).toBe(false);
  });

  it("describes scorer and assister as typed names with a result set", () => {
    const textSection = TYPER_LM_RULES_SECTIONS.find((section) =>
      section.heading.includes("najlepszy strzelec"),
    );
    const copy = (textSection?.items ?? []).join(" ");

    expect(textSection).toBeDefined();
    expect(copy).toContain("Najlepszy strzelec");
    expect(copy).toContain("najlepszy asystent");
    expect(copy).toContain("imię i nazwisko");
    expect(copy).toContain("Wielkość liter");
    expect(copy).toContain("spacje");
    expect(copy).toContain("Haaland");
    expect(copy).toContain("Håland");
    expect(copy).toContain("2 pkt");
    expect(copy).toContain("remisie");
    expect(copy).toContain("Rozlicza administrator");
    expect(copy).toContain("startu pierwszego meczu fazy ligowej");
    expect(copy).toContain("Nie ma listy propozycji");
  });

  it("describes both yes/no league-phase questions", () => {
    const yesNoSection = TYPER_LM_RULES_SECTIONS.find((section) =>
      section.heading.includes("TAK/NIE"),
    );
    const copy = (yesNoSection?.items ?? []).join(" ");

    expect(yesNoSection).toBeDefined();
    expect(copy).toContain("Czy jakakolwiek drużyna wygra wszystkie mecze?");
    expect(copy).toContain("Czy jakakolwiek drużyna przegra wszystkie mecze?");
    expect(copy).toContain("TAK albo NIE");
    expect(copy).toContain("fazę ligową (kolejki 1–8)");
    expect(copy).toContain("2 pkt");
    expect(copy).toContain("Rozlicza administrator");
    expect(copy).toContain("startu pierwszego meczu fazy ligowej");
  });

  it("describes max and min goals with a team remis", () => {
    const goalsSection = TYPER_LM_RULES_SECTIONS.find((section) =>
      section.heading.includes("bramki drużyn"),
    );
    const copy = (goalsSection?.items ?? []).join(" ");

    expect(goalsSection).toBeDefined();
    expect(copy).toContain("strzeli najwięcej bramek");
    expect(copy).toContain("straci najwięcej bramek");
    expect(copy).toContain("jedną drużynę");
    expect(copy).toContain("36 drużyn");
    expect(copy).toContain("remisie wielu drużyn");
    expect(copy).toContain("2 pkt");
    expect(copy).toContain("Rozlicza administrator");
    expect(copy).toContain("startu pierwszego meczu fazy ligowej");
  });

  it("does not promise a player list or automatic settlement", () => {
    const items = allRuleItems();
    const copy = items.join(" ");

    expect(copy).not.toContain("Szukaj zawodnika");
    expect(copy).not.toContain("auto-boxscore");
    expect(copy).not.toMatch(/automatycznie rozlicz/i);
    expect(copy).not.toContain("player_id");
    expect(
      items.filter((item) => item.includes("Rozlicza administrator")).length,
    ).toBeGreaterThanOrEqual(3);
  });
});
