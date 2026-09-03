import { describe, expect, it } from "vitest";

import {
  compareBetEventOptions,
  groupBetEventOptions,
  mergeEventFilterOption,
  type EventFilterOption,
} from "@/lib/betEventOptions";

function option(
  id: number,
  label: string,
  familyName: string,
): EventFilterOption {
  return { id, label, familyName };
}

describe("groupBetEventOptions", () => {
  it("puts OU, BTTS and REZULTAT above exact scores and goals", () => {
    const grouped = groupBetEventOptions([
      option(201, "0:3", "EXACT"),
      option(8, "Powyżej 2.5 gola", "OU"),
      option(6, "Obie drużyny strzelą", "BTTS"),
      option(1, "Zwycięstwo gospodarza", "REZULTAT"),
      option(174, "0 bramek w meczu", "GOALS"),
      option(12, "Poniżej 2.5 gola", "OU"),
    ]);

    expect(grouped.popular.map((event) => event.label)).toEqual([
      "Poniżej 2.5 gola",
      "Powyżej 2.5 gola",
      "Obie drużyny strzelą",
      "Zwycięstwo gospodarza",
    ]);
    expect(grouped.niche.map((event) => event.label)).toEqual([
      "0:3",
      "0 bramek w meczu",
    ]);
  });

  it("keeps original event labels", () => {
    const grouped = groupBetEventOptions([
      option(172, "Obie drużyny nie strzelą", "BTTS"),
      option(203, "0:5+", "EXACT"),
    ]);
    expect(grouped.popular[0]?.label).toBe("Obie drużyny nie strzelą");
    expect(grouped.niche[0]?.label).toBe("0:5+");
  });
});

describe("compareBetEventOptions", () => {
  it("orders families OU, BTTS, REZULTAT, EXACT, GOALS", () => {
    const events = [
      option(1, "Zwycięstwo gospodarza", "REZULTAT"),
      option(201, "0:3", "EXACT"),
      option(8, "Powyżej 2.5 gola", "OU"),
      option(6, "Obie drużyny strzelą", "BTTS"),
      option(174, "0 bramek w meczu", "GOALS"),
    ].sort(compareBetEventOptions);

    expect(events.map((event) => event.familyName)).toEqual([
      "OU",
      "BTTS",
      "REZULTAT",
      "EXACT",
      "GOALS",
    ]);
  });
});

describe("mergeEventFilterOption", () => {
  it("prefers a popular family when the same event is mapped twice", () => {
    const merged = mergeEventFilterOption(
      option(8, "Powyżej 2.5 gola", "EXACT"),
      option(8, "Powyżej 2.5 gola", "OU"),
    );
    expect(merged.familyName).toBe("OU");
    expect(merged.label).toBe("Powyżej 2.5 gola");
  });

  it("prefers GOALS over GOALS-6-CLASSES for the same event", () => {
    const merged = mergeEventFilterOption(
      option(174, "0 bramek w meczu", "GOALS-6-CLASSES"),
      option(174, "0 bramek w meczu", "GOALS"),
    );
    expect(merged.familyName).toBe("GOALS");
  });
});
