import { describe, expect, it } from "vitest";

import {
  computeEv,
  computeEvAfterTax,
  matchEventByQuery,
  parseMarketQuery,
  pickBestOdds,
} from "@/server/chat/tools/markets";

describe("computeEv / computeEvAfterTax", () => {
  it("computes known EV values", () => {
    expect(computeEv(0.55, 2.0)).toBeCloseTo(0.1, 8);
    expect(computeEvAfterTax(0.55, 2.0, 0.12)).toBeCloseTo(-0.032, 8);
  });
});

describe("parseMarketQuery", () => {
  it("parses Polish over goals total market", () => {
    const parsed = parseMarketQuery("Powyżej 2.5 gola");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(2.5);
    expect(parsed.stat).toBe("goals");
    expect(parsed.subject).toBe("total");
  });

  it("parses under shots on target for home", () => {
    const parsed = parseMarketQuery(
      "Poniżej 3.5 strzału celnego gospodarza",
    );
    expect(parsed.direction).toBe("under");
    expect(parsed.line).toBe(3.5);
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.subject).toBe("home");
  });

  it("maps strzały na bramkę to shots_on_target", () => {
    const parsed = parseMarketQuery("Over 4.5 strzałów na bramkę gościa");
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.subject).toBe("away");
    expect(parsed.direction).toBe("over");
  });

  it("does not guess subject for team name without home/away/total", () => {
    const parsed = parseMarketQuery(
      "Górnik powyżej 3.5 strzału celnego",
    );
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("does not treat two-word club name as player", () => {
    const parsed = parseMarketQuery(
      "Górnik Zabrze powyżej 3.5 strzału celnego",
    );
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("does not treat Legia Warszawa as player for team market", () => {
    const parsed = parseMarketQuery(
      "Legia Warszawa powyżej 9.5 rożnych",
    );
    expect(parsed.stat).toBe("corners");
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("detects player prop from surname before direction", () => {
    const parsed = parseMarketQuery("Lewandowski powyżej 0.5 gola");
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("goals");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(0.5);
  });

  it("detects full player name before direction", () => {
    const parsed = parseMarketQuery("Robert Lewandowski over 0.5 goals");
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Robert Lewandowski");
  });

  it("keeps clean playerQuery with explicit zawodnik and SOT market", () => {
    const parsed = parseMarketQuery(
      "zawodnik Lewandowski powyżej 3.5 strzału celnego",
    );
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
  });

  it("parses player prop from structured args with text fallback", () => {
    const parsed = parseMarketQuery("Lewandowski powyżej 0.5 gola", {
      subject: "player",
      playerQuery: "Lewandowski",
      stat: "goals",
      direction: "over",
      line: 0.5,
    });
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("goals");
    expect(parsed.line).toBe(0.5);
  });

  it("lets structured args override ambiguous text", () => {
    const parsed = parseMarketQuery("coś niejasnego", {
      stat: "corners",
      subject: "total",
      direction: "under",
      line: 9.5,
    });
    expect(parsed.stat).toBe("corners");
    expect(parsed.direction).toBe("under");
    expect(parsed.line).toBe(9.5);
    expect(parsed.subject).toBe("total");
  });

  it("leaves ambiguous fields null instead of guessing", () => {
    const parsed = parseMarketQuery("ciekawy rynek");
    expect(parsed.stat).toBeNull();
    expect(parsed.direction).toBeNull();
    expect(parsed.line).toBeNull();
    expect(parsed.subject).toBeNull();
  });
});

describe("matchEventByQuery", () => {
  const events = [
    { event_id: 8, event_name: "Powyżej 2.5 gola" },
    { event_id: 12, event_name: "Poniżej 2.5 gola" },
    { event_id: 6, event_name: "Obie strzelą" },
  ];

  it("prefers exact and fuller matches", () => {
    const matched = matchEventByQuery(events, "Powyżej 2.5 gola");
    expect(matched[0]?.event_id).toBe(8);
    expect(matched[0]?.isComplementary).toBe(false);
  });

  it("matches partial query preferring longer overlap", () => {
    const matched = matchEventByQuery(events, "powyżej 2.5");
    expect(matched[0]?.event_id).toBe(8);
  });

  it("returns complementary Over when only Under side is missing", () => {
    const onlyOver = [{ event_id: 8, event_name: "Powyżej 2.5 gola" }];
    const matched = matchEventByQuery(onlyOver, "Poniżej 2.5 gola");
    expect(matched).toHaveLength(1);
    expect(matched[0]?.event_id).toBe(8);
    expect(matched[0]?.isComplementary).toBe(true);
    expect(matched[0]?.askedEventId).toBe(12);
  });
});

describe("pickBestOdds", () => {
  it("returns max odds for event", () => {
    const best = pickBestOdds(
      [
        {
          event_id: 8,
          odds: 1.9,
          bookmaker_id: 1,
          bookmaker_name: "A",
        },
        {
          event_id: 8,
          odds: 2.15,
          bookmaker_id: 2,
          bookmaker_name: "B",
        },
        {
          event_id: 12,
          odds: 3.0,
          bookmaker_id: 2,
          bookmaker_name: "B",
        },
      ],
      8,
    );
    expect(best).toEqual({
      bookmaker_id: 2,
      bookmaker_name: "B",
      odds: 2.15,
    });
  });
});
