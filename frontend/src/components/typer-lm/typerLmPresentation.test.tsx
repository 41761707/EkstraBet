import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TyperLmLeaderboard } from "@/components/typer-lm/TyperLmLeaderboard";
import { TyperLmMatchCard } from "@/components/typer-lm/TyperLmMatchCard";
import { TyperLmRoundPicker } from "@/components/typer-lm/TyperLmRoundPicker";
import { TyperLmViewTabs } from "@/components/typer-lm/TyperLmViewTabs";
import { formatMatchDateTime } from "@/lib/format";
import { TYPER_LM_ODDS_PLACEHOLDER } from "@/lib/typerLm";
import type { TyperLeaderboardRow, TyperMatch } from "@/types/api";

function sampleMatch(overrides: Partial<TyperMatch> = {}): TyperMatch {
  return {
    match_id: 101,
    season_id: 13,
    round_number: 1,
    game_date: "2026-09-16T21:00:00",
    published_at: "2026-09-10T12:00:00",
    is_locked: false,
    result: null,
    home_team: { id: 1, name: "Bayern Monachium", shortcut: "BAY" },
    away_team: { id: 2, name: "Arsenal", shortcut: "ARS" },
    odds_home: 1.85,
    odds_draw: 3.4,
    odds_away: 4.2,
    outcome: "1",
    points: null,
    changes: [
      {
        match_id: 101,
        user_uuid: "user-1",
        display_name: "Ala",
        previous_outcome: null,
        new_outcome: "1",
        changed_at: "2026-09-11T18:30:00",
      },
    ],
    ...overrides,
  };
}

describe("TyperLmMatchCard", () => {
  it("renders Superbet odds and the selected 1X2 pick", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Bayern Monachium");
    expect(html).toContain("Arsenal");
    expect(html).toContain("1.85");
    expect(html).toContain("3.40");
    expect(html).toContain("4.20");
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain(formatMatchDateTime("2026-09-16T21:00:00"));
    expect(html).toContain("Nierozstrzygnięte");
    expect(html).toContain("— na 1");
  });

  it("shows the missing-odds placeholder instead of prices", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({
          odds_home: null,
          odds_draw: null,
          odds_away: null,
        })}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain(TYPER_LM_ODDS_PLACEHOLDER);
    expect(html).not.toContain("1.85");
  });

  it("disables 1X2 buttons after kick-off from the server flag", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({ is_locked: true })}
        teamNameDisplay="full"
        isPending={false}
        nowMs={0}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Typowanie zablokowane");
    expect(html.match(/disabled=""/g)?.length).toBe(3);
  });

  it("disables 1X2 buttons after the local kick-off time without is_locked", () => {
    const kickoff = "2020-01-01T12:00:00.000Z";
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({ is_locked: false, game_date: kickoff })}
        teamNameDisplay="full"
        isPending={false}
        nowMs={Date.parse(kickoff) + 1}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Typowanie zablokowane");
    expect(html.match(/disabled=""/g)?.length).toBe(3);
  });

  it("trusts API is_locked on the first paint without a client clock", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({
          is_locked: false,
          game_date: "2020-01-01T12:00:00.000Z",
        })}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Do rozpoczęcia");
    expect(html).not.toContain("Typowanie zablokowane");
    expect(html.match(/disabled=""/g)).toBeNull();
  });

  it("shows a pending save state on the match card", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="full"
        isPending={true}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Zapisywanie typu");
    expect(html).toContain("disabled=\"\"");
  });

  it("shows the official 1X2 next to points after kick-off", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({
          is_locked: true,
          result: "X",
          outcome: "X",
          points: 3.4,
        })}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Wynik: X");
    expect(html).toContain("3.40 pkt");
  });

  it("shows waiting for a result when the locked match has none", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch({ is_locked: true, result: null })}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Oczekiwanie na wynik");
  });

  it("renders an API error on the card without exposing other picks", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="full"
        isPending={false}
        errorMessage="Mecz już się rozpoczął. Typu nie można zmienić."
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain("Mecz już się rozpoczął");
    expect(html).not.toContain("user-2");
  });
});

describe("TyperLmRoundPicker", () => {
  it("renders distinct knockout round labels", () => {
    const html = renderToStaticMarkup(
      <TyperLmRoundPicker
        rounds={[
          {
            round_number: 973,
            round_label: "1/8-FINAŁU",
            matches: [sampleMatch({ round_number: 973 })],
          },
          {
            round_number: 972,
            round_label: "ĆWIERĆFINAŁ",
            matches: [sampleMatch({ match_id: 202, round_number: 972 })],
          },
        ]}
        selectedRound={973}
        onSelect={() => undefined}
      />,
    );

    expect(html).toContain("1/8-FINAŁU");
    expect(html).toContain("ĆWIERĆFINAŁ");
    expect(html).not.toContain("Faza pucharowa");
  });
});

describe("TyperLmLeaderboard", () => {
  const rows: TyperLeaderboardRow[] = [
    {
      place: 1,
      user_uuid: "user-1",
      display_name: "Ala",
      total_points: 12.5,
      correct_predictions: 4,
      settled_predictions: 6,
    },
    {
      place: 2,
      user_uuid: "user-2",
      display_name: "Bartek",
      total_points: 8,
      correct_predictions: 2,
      settled_predictions: 6,
    },
  ];

  it("renders ranking aggregates without other users' 1X2 picks", () => {
    const html = renderToStaticMarkup(
      <TyperLmLeaderboard rows={rows} currentUserUuid="user-1" />,
    );

    expect(html).toContain("Ala");
    expect(html).toContain("Bartek");
    expect(html).toContain("12.50");
    expect(html).toContain("user-2");
    expect(html).not.toContain("aria-pressed");
    expect(html).not.toContain("outcome");
  });

  it("highlights the current user's ranking row", () => {
    const html = renderToStaticMarkup(
      <TyperLmLeaderboard rows={rows} currentUserUuid="user-1" />,
    );

    expect(html).toContain("bg-accent-soft");
  });

  it("keeps the API row order and place values", () => {
    const apiOrder: TyperLeaderboardRow[] = [
      {
        place: 1,
        user_uuid: "user-2",
        display_name: "Bartek",
        total_points: 8,
        correct_predictions: 2,
        settled_predictions: 6,
      },
      {
        place: 2,
        user_uuid: "user-1",
        display_name: "Ala",
        total_points: 12.5,
        correct_predictions: 4,
        settled_predictions: 6,
      },
    ];
    const html = renderToStaticMarkup(
      <TyperLmLeaderboard rows={apiOrder} currentUserUuid="user-1" />,
    );
    const bartekAt = html.indexOf("Bartek");
    const alaAt = html.indexOf("Ala");

    expect(bartekAt).toBeGreaterThan(-1);
    expect(alaAt).toBeGreaterThan(bartekAt);
  });
});

describe("TyperLmViewTabs", () => {
  it("renders view switchers as buttons without a tablist", () => {
    const html = renderToStaticMarkup(
      <TyperLmViewTabs activeTab="round" onChange={() => undefined} />,
    );

    expect(html).toContain("Kolejka");
    expect(html).toContain("Ranking");
    expect(html).not.toContain("role=\"tablist\"");
    expect(html).not.toContain("role=\"tab\"");
    expect(html).not.toContain("aria-selected");
  });
});
