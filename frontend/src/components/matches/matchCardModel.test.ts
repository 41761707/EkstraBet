import { describe, expect, it } from "vitest";

import {
  layoutMatchCard,
  MATCH_CARD_METRICS,
  matchCardNameFontSize,
} from "@/components/matches/matchCardLayout";
import {
  buildFootballMatchCard,
  formatMatchCardDate,
  type FootballMatchCardInput,
} from "@/components/matches/matchCardModel";
import { formatMatchDateTime, formatRoundLabel } from "@/lib/format";
import {
  BASKETBALL_SPORT_ID,
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type MatchSummary,
  type PredictionPreviewResponse,
  type TeamInMatch,
  type TeamSeasonMatchPoint,
} from "@/types/api";

const homeTeam: TeamInMatch = { id: 1, name: "Cracovia", shortcut: "CRA" };
const awayTeam: TeamInMatch = { id: 2, name: "Motor Lublin", shortcut: "MOT" };

const prediction: PredictionPreviewResponse = {
  result: { p_home: 0.407, p_draw: 0.292, p_away: 0.301 },
  btts: { p_yes: 0.606, p_no: 0.394 },
  goals: {
    lambda_home: 0,
    lambda_away: 0,
    total_buckets: {},
    over_25: 0.521,
    under_25: 0.479,
    top_exact_scores: [
      { score: "1:0", probability: 0.093 },
      { score: "2:1", probability: 0.086 },
      { score: "0:1", probability: 0.04 },
      { score: "1:1", probability: 0.12 },
      { score: "0:0", probability: 0 },
    ],
  },
};

function meeting(
  id: number,
  homeGoals: number | null,
  awayGoals: number | null,
  homeId = 1,
): MatchSummary {
  const awayId = homeId === 1 ? 2 : 1;
  return {
    id,
    league_id: 1,
    season_id: 10,
    round: id,
    round_label: String(id),
    game_date: `2026-05-${String(id).padStart(2, "0")}T12:00:00`,
    home_team: {
      id: homeId,
      name: homeId === 1 ? "Cracovia" : "Motor Lublin",
      shortcut: "H",
    },
    away_team: {
      id: awayId,
      name: awayId === 2 ? "Motor Lublin" : "Cracovia",
      shortcut: "A",
    },
    home_goals: homeGoals,
    away_goals: awayGoals,
    result: "1",
    is_played: homeGoals !== null && awayGoals !== null,
    score_resolution: null,
  };
}

function historyPoint(
  id: number,
  partial: Partial<TeamSeasonMatchPoint>,
): TeamSeasonMatchPoint {
  return {
    match_id: id,
    match_date: `2026-04-${String(id).padStart(2, "0")}T12:00:00`,
    opponent_shortcut: "RAK",
    opponent_name: "Raków",
    total_goals: 3,
    btts: true,
    result: "W",
    home_team_name: "Cracovia",
    away_team_name: "Raków",
    home_goals: 2,
    away_goals: 1,
    is_home: true,
    team_cards: 0,
    opponent_cards: 0,
    total_cards: 0,
    team_offsides: 0,
    opponent_offsides: 0,
    total_offsides: 0,
    team_corners: 0,
    opponent_corners: 0,
    total_corners: 0,
    team_shots: 0,
    opponent_shots: 0,
    total_shots: 0,
    team_shots_on_target: 0,
    opponent_shots_on_target: 0,
    total_shots_on_target: 0,
    team_fouls: 0,
    opponent_fouls: 0,
    total_fouls: 0,
    ...partial,
  };
}

function cardInput(
  partial: Partial<FootballMatchCardInput> = {},
): FootballMatchCardInput {
  return {
    sportId: FOOTBALL_SPORT_ID,
    leagueName: "Ekstraklasa",
    gameDate: "2026-10-31T18:00:00",
    roundLabel: "13",
    homeTeam,
    awayTeam,
    prediction,
    headToHeadMeetings: [],
    homeHistory: [],
    awayHistory: [],
    ...partial,
  };
}

describe("buildFootballMatchCard", () => {
  it("skips hockey and basketball", () => {
    expect(buildFootballMatchCard(cardInput({ sportId: HOCKEY_SPORT_ID }))).toBeNull();
    expect(
      buildFootballMatchCard(cardInput({ sportId: BASKETBALL_SPORT_ID })),
    ).toBeNull();
    expect(buildFootballMatchCard(cardInput({ sportId: null }))).toBeNull();
  });

  it("builds the header, file name and 1X2 labels without a model name", () => {
    const card = buildFootballMatchCard(cardInput());

    expect(card).not.toBeNull();
    expect(card?.leagueName).toBe("EKSTRAKLASA");
    expect(card?.metaLabel).toBe(
      `${formatMatchDateTime("2026-10-31T18:00:00")} · ${formatRoundLabel("13")}`,
    );
    expect(card?.fileName).toBe("cracovia-motor-lublin.png");
    expect(card?.result?.map((segment) => segment.label)).toEqual([
      "CRA",
      "Remis",
      "MOT",
    ]);
    expect(card?.result?.map((segment) => segment.percentLabel)).toEqual([
      "40.7%",
      "29.2%",
      "30.1%",
    ]);
    expect(card?.result?.map((segment) => segment.share)).toEqual([
      0.407,
      0.292,
      0.301,
    ]);
  });

  it("normalizes bar shares and keeps the raw percent labels", () => {
    const card = buildFootballMatchCard(cardInput({
      prediction: {
        ...prediction,
        result: { p_home: 0.2, p_draw: 0.2, p_away: 0.2 },
      },
    }));

    expect(card?.result?.map((segment) => segment.share)).toEqual([
      1 / 3,
      1 / 3,
      1 / 3,
    ]);
    expect(card?.result?.[0]?.percentLabel).toBe("20.0%");
  });

  it("drops an empty split and keeps the three most likely scores", () => {
    const card = buildFootballMatchCard(cardInput({
      prediction: {
        ...prediction,
        btts: { p_yes: 0, p_no: 0 },
      },
    }));

    expect(card?.btts).toBeNull();
    expect(card?.overUnder?.leftPercentLabel).toBe("52.1%");
    expect(card?.overUnder?.rightPercentLabel).toBe("47.9%");
    expect(card?.topScores.map((chip) => chip.score)).toEqual(["1:1", "1:0", "2:1"]);
  });

  it("summarises the five latest scored head-to-head meetings from the home side", () => {
    const card = buildFootballMatchCard(cardInput({
      headToHeadMeetings: [
        meeting(1, null, null),
        meeting(2, 2, 1),
        meeting(3, 0, 0, 2),
        meeting(4, 0, 1),
        meeting(5, 3, 2),
        meeting(6, 1, 1, 2),
        meeting(7, 4, 0),
      ],
    }));

    expect(card?.headToHead.rows).toHaveLength(5);
    expect(card?.headToHead.rows[0]?.score).toBe("2:1");
    expect(card?.headToHead.summary).toBe(
      "5 meczów · bilans gospodarza 2W 2D 1L · bramki 6:5",
    );
    expect(card?.headToHead.rates).toBe("BTTS 60.0% · Over 2.5 40.0%");
  });

  it("uses one match in the singular", () => {
    const card = buildFootballMatchCard(cardInput({
      headToHeadMeetings: [meeting(2, 1, 0)],
    }));

    expect(card?.headToHead.summary?.startsWith("1 mecz ·")).toBe(true);
  });

  it("reads recent form from the team perspective", () => {
    const card = buildFootballMatchCard(cardInput({
      homeHistory: [
        historyPoint(1, { total_goals: 2, btts: false, home_goals: 2, away_goals: 0 }),
        historyPoint(2, { is_home: false, home_goals: 1, away_goals: 4, total_goals: 5 }),
        historyPoint(3, {}),
        historyPoint(4, {}),
        historyPoint(5, {}),
        historyPoint(6, { opponent_name: "Nie powinno wejść" }),
      ],
    }));

    expect(card?.homeForm.rows).toHaveLength(5);
    expect(card?.homeForm.rows[0]).toMatchObject({
      score: "2:0",
      bothTeamsScored: false,
      overTwoAndHalf: false,
      dateLabel: "01.04.26",
    });
    expect(card?.homeForm.rows[1]).toMatchObject({
      score: "4:1",
      bothTeamsScored: true,
      overTwoAndHalf: true,
    });
    expect(card?.homeForm.rows.some((row) => row.opponent === "Nie powinno wejść")).toBe(
      false,
    );
  });

  it("keeps form when predictions are missing", () => {
    const card = buildFootballMatchCard(cardInput({
      prediction: null,
      awayHistory: [historyPoint(3, {})],
    }));

    expect(card?.result).toBeNull();
    expect(card?.btts).toBeNull();
    expect(card?.overUnder).toBeNull();
    expect(card?.topScores).toEqual([]);
    expect(card?.awayForm.rows).toHaveLength(1);
  });

  it("slugifies Polish names and truncates a long league", () => {
    const card = buildFootballMatchCard(cardInput({
      leagueName: "Bardzo długa nazwa rozgrywek ponad limit znaków",
      homeTeam: { id: 8, name: "ŁKS Łódź", shortcut: null },
      awayTeam: { id: 9, name: "Śląsk Wrocław", shortcut: null },
    }));

    expect(card?.fileName).toBe("lks-lodz-slask-wroclaw.png");
    expect(card?.leagueName.endsWith("…")).toBe(true);
    expect(card?.leagueName).toBe(card?.leagueName.toLocaleUpperCase("pl-PL"));
    expect(card?.result?.[0]?.label).toBe("ŁKS Łódź");
  });
});

describe("formatMatchCardDate", () => {
  it("prints a compact day.month.year", () => {
    expect(formatMatchCardDate("2026-05-16T12:00:00")).toBe("16.05.26");
  });
});

describe("layoutMatchCard", () => {
  it("grows by one row slot for each listed meeting", () => {
    const empty = buildFootballMatchCard(cardInput({ prediction: null }));
    const filled = buildFootballMatchCard(cardInput({
      prediction: null,
      headToHeadMeetings: [1, 2, 3, 4, 5].map((id) => meeting(id, 1, 0)),
      homeHistory: [1, 2, 3, 4, 5].map((id) => historyPoint(id, {})),
      awayHistory: [1, 2, 3, 4, 5].map((id) => historyPoint(id, {})),
    }));
    expect(empty).not.toBeNull();
    expect(filled).not.toBeNull();
    if (!empty || !filled) {
      return;
    }
    const rowDelta = (
      5 * MATCH_CARD_METRICS.row
      + MATCH_CARD_METRICS.h2hHead
      + MATCH_CARD_METRICS.sectionTail
      - MATCH_CARD_METRICS.h2hEmpty
    ) + 2 * (
      5 * MATCH_CARD_METRICS.row
      + MATCH_CARD_METRICS.formHead
      + MATCH_CARD_METRICS.sectionTail
      - MATCH_CARD_METRICS.formEmpty
    );
    expect(layoutMatchCard(filled).height - layoutMatchCard(empty).height).toBe(rowDelta);
  });

  it("shrinks the name when it would overflow one line", () => {
    expect(matchCardNameFontSize("Cracovia")).toBe(64);
    expect(matchCardNameFontSize("Raków Częstochowa")).toBe(52);
    expect(matchCardNameFontSize("A".repeat(26))).toBe(44);
    expect(matchCardNameFontSize("A".repeat(34))).toBe(36);
  });
});
