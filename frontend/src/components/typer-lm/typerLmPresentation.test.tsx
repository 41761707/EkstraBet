import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import {
  TyperLmAdminAuditLookup,
  TyperLmAdminAuditResults,
} from "@/components/typer-lm/TyperLmAdminAuditLookup";
import { TyperLmAdminCandidateList } from "@/components/typer-lm/TyperLmAdminCandidateList";
import {
  TyperLmAdminPanel,
  TyperLmAdminSection,
} from "@/components/typer-lm/TyperLmAdminPanel";
import { TyperLmAdminRoundControls } from "@/components/typer-lm/TyperLmAdminRoundControls";
import { TyperLmDashboard } from "@/components/typer-lm/TyperLmDashboard";
import { TyperLmLeaderboard } from "@/components/typer-lm/TyperLmLeaderboard";
import { TyperLmMatchCard } from "@/components/typer-lm/TyperLmMatchCard";
import { TyperLmRoundPicker } from "@/components/typer-lm/TyperLmRoundPicker";
import { TyperLmRules } from "@/components/typer-lm/TyperLmRules";
import { TyperLmViewTabs } from "@/components/typer-lm/TyperLmViewTabs";
import { getTyperAdminPredictionHistory } from "@/lib/apiClient";
import { formatMatchDateTime } from "@/lib/format";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import { TYPER_LM_ODDS_PLACEHOLDER } from "@/lib/typerLm";
import { canPublishSelection } from "@/lib/typerLmAdmin";
import {
  TYPER_LM_RULES_SECTIONS,
  TYPER_LM_RULES_TITLE,
} from "@/lib/typerLmRules";
import type {
  TyperAdminCandidate,
  TyperDashboardResponse,
  TyperLeaderboardRow,
  TyperMatch,
} from "@/types/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: () => undefined,
    refresh: () => undefined,
  }),
}));

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return {
    ...actual,
    getTyperAdminPredictionHistory: vi.fn(async () => [
      {
        match_id: 101,
        user_uuid: "user-2",
        display_name: "Bartek",
        previous_outcome: "1",
        new_outcome: "X",
        changed_at: "2026-09-11T18:30:00",
      },
    ]),
  };
});

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

function sampleDashboard(): TyperDashboardResponse {
  return {
    season_id: 13,
    rounds: [
      {
        round_number: 1,
        round_label: "1",
        matches: [sampleMatch()],
      },
    ],
  };
}

function sampleLeaderboardRows(): TyperLeaderboardRow[] {
  return [
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
    expect(html).toContain('aria-label="Typ Bayern Monachium"');
    expect(html).toContain('aria-label="Typ Remis"');
    expect(html).toContain('aria-label="Typ Arsenal"');
    expect(html).not.toContain('aria-label="Typ 1"');
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

  it("labels 1X2 buttons with full team names from preferences", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain(">Bayern Monachium</button>");
    expect(html).toContain(">Remis</button>");
    expect(html).toContain(">Arsenal</button>");
  });

  it("labels 1X2 buttons with team shortcuts when preferred", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="shortcut"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).toContain(">BAY</button>");
    expect(html).toContain(">Remis</button>");
    expect(html).toContain(">ARS</button>");
    expect(html).toContain('aria-label="Typ BAY"');
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

function sampleCandidate(
  overrides: Partial<TyperAdminCandidate> = {},
): TyperAdminCandidate {
  return {
    match_id: 101,
    season_id: 13,
    round_number: 1,
    game_date: "2026-09-16T21:00:00",
    home_team: { id: 1, name: "Bayern Monachium", shortcut: "BAY" },
    away_team: { id: 2, name: "Arsenal", shortcut: "ARS" },
    is_published: false,
    has_complete_superbet_odds: false,
    ...overrides,
  };
}

function groupCandidates(): TyperAdminCandidate[] {
  return Array.from({ length: 9 }, (_, index) =>
    sampleCandidate({
      match_id: 101 + index,
      home_team: {
        id: index + 1,
        name: `Home ${index + 1}`,
        shortcut: `H${index + 1}`,
      },
    }),
  );
}

function silentStorage(): PreferencesStorage {
  return {
    load: () => ({ ...DEFAULT_PREFERENCES }),
    save: () => undefined,
  };
}

function silentApi(): PreferencesApi {
  return {
    get: async () => ({ status: "no-session" }),
    put: async () => ({ ...DEFAULT_PREFERENCES }),
  };
}

function renderAdminList(
  candidates: TyperAdminCandidate[],
  selectedIds: number[],
  roundNumber: number,
  pendingUnpublishId: number | null = null,
  errorMessage: string | null = null,
): string {
  return renderToStaticMarkup(
    <TyperLmAdminCandidateList
      roundNumber={roundNumber}
      candidates={candidates}
      selectedIds={selectedIds}
      isLoading={false}
      isSaving={false}
      errorMessage={errorMessage}
      canPublish={false}
      isConfirmingPublish={false}
      pendingUnpublishId={pendingUnpublishId}
      teamNameDisplay="full"
      onToggle={() => undefined}
      onRequestPublish={() => undefined}
      onConfirmPublish={() => undefined}
      onCancelPublish={() => undefined}
      onRequestUnpublish={() => undefined}
      onConfirmUnpublish={() => undefined}
      onCancelUnpublish={() => undefined}
    />,
  );
}

describe("TyperLmAdminSection", () => {
  it("hides the admin panel from a regular user", () => {
    const html = renderToStaticMarkup(
      <TyperLmAdminSection isAdmin={false} seasonId={13} />,
    );
    expect(html).toBe("");
    expect(html).not.toContain("Panel administratora");
  });

  it("renders the admin panel for an administrator", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <TyperLmAdminSection
          isAdmin={true}
          seasonId={13}
          initialCandidates={groupCandidates()}
        />
      </PreferencesProvider>,
    );
    expect(html).toContain("Panel administratora");
    expect(html).toContain("Audyt typów");
    expect(html).toContain("0/9");
  });
});

describe("TyperLmAdminCandidateList", () => {
  it("keeps publish enabled without Superbet odds when 9 matches are selected", () => {
    const candidates = groupCandidates();
    const selectedIds = candidates.map((row) => row.match_id);
    const html = renderToStaticMarkup(
      <TyperLmAdminCandidateList
        roundNumber={1}
        candidates={candidates}
        selectedIds={selectedIds}
        isLoading={false}
        isSaving={false}
        canPublish={canPublishSelection(candidates, selectedIds, 1)}
        isConfirmingPublish={false}
        pendingUnpublishId={null}
        teamNameDisplay="full"
        onToggle={() => undefined}
        onRequestPublish={() => undefined}
        onConfirmPublish={() => undefined}
        onCancelPublish={() => undefined}
        onRequestUnpublish={() => undefined}
        onConfirmUnpublish={() => undefined}
        onCancelUnpublish={() => undefined}
      />,
    );
    expect(html).toContain("nie blokuje publikacji");
    expect(html).toContain("9/9");
    expect(html).toContain("Opublikuj zestaw");
    expect(html).not.toMatch(/disabled=""[^>]*>Opublikuj zestaw/);
  });

  it("disables publish for an incomplete group-stage set", () => {
    const candidates = groupCandidates();
    const selectedIds = [101, 102, 103, 104, 105];
    const html = renderToStaticMarkup(
      <TyperLmAdminCandidateList
        roundNumber={1}
        candidates={candidates}
        selectedIds={selectedIds}
        isLoading={false}
        isSaving={false}
        canPublish={canPublishSelection(candidates, selectedIds, 1)}
        isConfirmingPublish={false}
        pendingUnpublishId={null}
        teamNameDisplay="full"
        onToggle={() => undefined}
        onRequestPublish={() => undefined}
        onConfirmPublish={() => undefined}
        onCancelPublish={() => undefined}
        onRequestUnpublish={() => undefined}
        onConfirmUnpublish={() => undefined}
        onCancelUnpublish={() => undefined}
      />,
    );
    expect(html).toContain("5/9");
    expect(html).toMatch(/disabled=""[^>]*>Opublikuj zestaw/);
  });

  it("preselects unpublished knockout matches without requiring odds", () => {
    const html = renderAdminList(
      [
        sampleCandidate({ match_id: 301, round_number: 900 }),
        sampleCandidate({ match_id: 302, round_number: 900 }),
      ],
      [301, 302],
      900,
    );
    expect(html).toContain("2/2");
    expect(html.match(/checked=""/g)?.length).toBe(2);
  });

  it("counts published matches in the group-stage completeness counter", () => {
    const candidates = [
      ...groupCandidates().slice(0, 5).map((row) => ({
        ...row,
        is_published: true,
      })),
      sampleCandidate({ match_id: 201 }),
      sampleCandidate({ match_id: 202 }),
      sampleCandidate({ match_id: 203 }),
      sampleCandidate({ match_id: 204 }),
    ];
    const html = renderAdminList(candidates, [201, 202, 203, 204], 1);
    expect(html).toContain("9/9");
  });

  it("offers a safe unpublish action for a published match", () => {
    const html = renderAdminList(
      [sampleCandidate({ is_published: true })],
      [],
      1,
    );
    expect(html).toContain("Wycofaj publikację");
    expect(html).not.toContain("Potwierdź wycofanie");
  });

  it("asks for confirmation before withdrawing a publication", () => {
    const html = renderAdminList(
      [sampleCandidate({ is_published: true })],
      [],
      1,
      101,
    );
    expect(html).toContain("Wycofać, jeśli nikt jeszcze nie typował?");
    expect(html).toContain("Potwierdź wycofanie");
  });

  it("shows an empty round only when there is no load error", () => {
    const emptyHtml = renderAdminList([], [], 1);
    expect(emptyHtml).toContain("Brak meczów w tej rundzie");
    const errorHtml = renderAdminList(
      [],
      [],
      1,
      null,
      "Brak uprawnień administratora.",
    );
    expect(errorHtml).not.toContain("Brak meczów w tej rundzie");
    expect(errorHtml).toBe("");
  });
});

describe("TyperLmAdminRoundControls", () => {
  it("renders knockout rounds with dictionary labels instead of numeric codes", () => {
    const html = renderToStaticMarkup(
      <TyperLmAdminRoundControls
        selectedRound={973}
        knockoutRounds={[
          {
            round_number: 973,
            round_label: "1/8-FINAŁU",
            game_date: "2027-03-10",
          },
          {
            round_number: 972,
            round_label: "ĆWIERĆFINAŁ",
            game_date: "2027-04-14",
          },
        ]}
        onSelectRound={() => undefined}
      />,
    );
    expect(html).toContain("1/8-FINAŁU");
    expect(html).toContain("ĆWIERĆFINAŁ");
    expect(html).toContain("Kolejka 1");
    expect(html).toContain("Numer rundy pucharowej");
    expect(html).toContain("Wczytaj rundę");
  });

  it("shows a knockout load error and keeps the manual round field", () => {
    const html = renderToStaticMarkup(
      <TyperLmAdminRoundControls
        selectedRound={1}
        knockoutRounds={[]}
        knockoutRoundsError="Failed to fetch rounds"
        onSelectRound={() => undefined}
      />,
    );
    expect(html).toContain("Nie udało się wczytać rund pucharowych");
    expect(html).toContain("Failed to fetch rounds");
    expect(html).toContain("Numer rundy pucharowej");
    expect(html).not.toContain("Brak zaimportowanych rund pucharowych");
  });

  it("disables round selection while a publication is saving", () => {
    const html = renderToStaticMarkup(
      <TyperLmAdminRoundControls
        selectedRound={1}
        knockoutRounds={[
          {
            round_number: 973,
            round_label: "1/8-FINAŁU",
            game_date: "2027-03-10",
          },
        ]}
        isSaving={true}
        onSelectRound={() => undefined}
      />,
    );
    expect(html).toMatch(/disabled=""[^>]*>Kolejka 1/);
    expect(html).toMatch(/disabled=""[^>]*>1\/8-FINAŁU/);
    expect(html).toMatch(/disabled=""[^>]*>Wczytaj rundę/);
  });
});

describe("TyperLmAdminPanel knockout defaults", () => {
  it("selects every unpublished knockout match on first paint", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <TyperLmAdminPanel
          seasonId={13}
          initialRoundNumber={900}
          knockoutRounds={[
            {
              round_number: 900,
              round_label: "Baraże",
              game_date: "2027-02-17",
            },
          ]}
          initialCandidates={[
            sampleCandidate({ match_id: 401, round_number: 900 }),
            sampleCandidate({
              match_id: 402,
              round_number: 900,
              is_published: true,
            }),
          ]}
        />
      </PreferencesProvider>,
    );
    expect(html).toContain("1/1");
    expect(html).toContain("Opublikowany");
    expect(html).toContain("Baraże");
  });
});

describe("TyperLmAdminAuditLookup", () => {
  it("renders an audit row from the mocked history client", async () => {
    const rows = await getTyperAdminPredictionHistory({
      userUuid: "user-2",
    });
    const html = renderToStaticMarkup(
      <>
        <TyperLmAdminAuditLookup seasonId={13} />
        <TyperLmAdminAuditResults rows={rows} isLoading={false} />
      </>,
    );
    expect(html).toContain("Audyt typów");
    expect(html).toContain("Bartek");
    expect(html).toContain("user-2");
    expect(html).toContain("mecz 101");
    expect(html).toContain("1 na X");
    expect(html).toContain(formatMatchDateTime("2026-09-11T18:30:00"));
  });
});

describe("TyperLmRules", () => {
  function detailsOpenAttribute(html: string): string | undefined {
    return html.match(/<details([^>]*)>/)?.[1];
  }

  it("renders a collapsed expander with contest, typing and scoring rules", () => {
    const html = renderToStaticMarkup(<TyperLmRules />);
    const detailsAttributes = detailsOpenAttribute(html) ?? "";

    expect(html).toContain(TYPER_LM_RULES_TITLE);
    expect(detailsAttributes).not.toMatch(/\sopen(?:="[^"]*")?(?=[\s>]|$)/);

    for (const section of TYPER_LM_RULES_SECTIONS) {
      expect(html).toContain(section.heading);
      for (const item of section.items) {
        expect(html).toContain(item);
      }
    }
  });

  it("keeps the full rules out of match cards", () => {
    const html = renderToStaticMarkup(
      <TyperLmMatchCard
        match={sampleMatch()}
        teamNameDisplay="full"
        isPending={false}
        onSelectOutcome={() => undefined}
      />,
    );

    expect(html).not.toContain(TYPER_LM_RULES_TITLE);
    expect(html).not.toContain("Regulamin rozgrywek");
    expect(html).not.toContain("Zasady punktacji");
  });
});

describe("Typer LM page smoke", () => {
  it("places collapsed rules above the participant round and hides admin", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <div>
          <TyperLmRules />
          <TyperLmAdminSection isAdmin={false} seasonId={13} />
          <TyperLmDashboard
            dashboard={sampleDashboard()}
            leaderboard={sampleLeaderboardRows()}
            currentUserUuid="user-1"
            currentUserDisplayName="Ala"
          />
        </div>
      </PreferencesProvider>,
    );
    const rulesAt = html.indexOf(TYPER_LM_RULES_TITLE);
    const roundAt = html.indexOf("Kolejka");
    const historyAt = html.indexOf("— na 1");

    expect(rulesAt).toBeGreaterThan(-1);
    expect(roundAt).toBeGreaterThan(rulesAt);
    expect(historyAt).toBeGreaterThan(roundAt);
    expect(html.match(/<details([^>]*)>/)?.[1] ?? "").not.toMatch(
      /\sopen(?:="[^"]*")?(?=[\s>]|$)/,
    );
    expect(html).not.toContain("Panel administratora");
    expect(html).toContain("Bayern Monachium");
    expect(html).toContain("1.85");
  });

  it("shows the admin panel after the rules for an administrator", () => {
    const html = renderToStaticMarkup(
      <PreferencesProvider
        hasSession={false}
        storage={silentStorage()}
        api={silentApi()}
      >
        <div>
          <TyperLmRules />
          <TyperLmAdminSection
            isAdmin={true}
            seasonId={13}
            initialCandidates={groupCandidates()}
          />
          <TyperLmDashboard
            dashboard={sampleDashboard()}
            leaderboard={sampleLeaderboardRows()}
            currentUserUuid="user-1"
            currentUserDisplayName="Ala"
          />
        </div>
      </PreferencesProvider>,
    );
    const rulesAt = html.indexOf(TYPER_LM_RULES_TITLE);
    const adminAt = html.indexOf("Panel administratora");
    const roundAt = html.indexOf("Kolejka");

    expect(adminAt).toBeGreaterThan(rulesAt);
    expect(roundAt).toBeGreaterThan(adminAt);
    expect(html).toContain("Audyt typów");
    expect(html).toContain("0/9");
  });
});
