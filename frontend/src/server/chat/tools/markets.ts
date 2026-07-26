/**
 * Market parsing helpers, EV calculations and analyze_match_bet tool.
 */

import type {
  BetRecommendation,
  BetRecommendationsResponse,
  FootballPlayerMatchStat,
  FootballPlayerMatchStatsResponse,
  FootballPlayersListResponse,
  MatchDetails,
  MatchPredictionItem,
  MatchSummary,
  OddsItem,
  TeamProfile,
} from "@/types/api";

import { booleanArg, floatArg, numberArg, stringArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import {
  assessPlayerMarket,
  assessTeamMarket,
} from "./statisticalMarkets";
import { normalizeSearchText } from "./text";
import type { ToolResult } from "./types";
import { FOOTBALL_SPORT_ID } from "./types";

interface MatchPredictionListResponse {
  match_predictions: MatchPredictionItem[];
  total_count: number;
  match_id: number;
}

interface MatchOddsListResponse {
  odds: OddsItem[];
  total_count: number;
  match_id: number;
}

export const BETTING_TAX_RATE = 0.12;

export type MarketStat =
  | "goals"
  | "assists"
  | "shots"
  | "shots_on_target"
  | "corners"
  | "cards"
  | "fouls"
  | "offsides"
  | "fouls_conceded"
  | "yellow_cards";

export type MarketSubject = "home" | "away" | "total" | "player";

export type MarketDirection = "over" | "under";

export type MarketVerdict =
  | "positive"
  | "lean_positive"
  | "neutral"
  | "lean_negative"
  | "negative"
  | "insufficient_data";

export type EvidenceSource = "bet" | "prediction" | "statistics";

export type VerdictBasis = "value" | "probability" | "statistical_support";

export interface ParsedMarket {
  eventQuery: string;
  stat: MarketStat | null;
  /** null = subject niejednoznaczny — tool ma zwrócić insufficient_data */
  subject: MarketSubject | null;
  playerQuery: string | null;
  direction: MarketDirection | null;
  line: number | null;
}

export interface MarketOddsQuote {
  bookmaker_id: number;
  bookmaker_name: string;
  odds: number;
}

export interface MarketEvidence {
  source: EvidenceSource;
  label: string;
  value: number | string;
  interpretation: string;
}

export interface EvaluatedMarketRow {
  match_id: number;
  home_team: string;
  away_team: string;
  game_date: string;
  event_id: number | null;
  event_name: string;
  model_id: number | null;
  model_name: string | null;
  probability: number | null;
  probability_pct: number | null;
  best_odds: number | null;
  best_bookmaker: string | null;
  implied_probability: number | null;
  ev: number | null;
  ev_after_tax: number | null;
  edge_pct: number | null;
  primary_evidence_source: EvidenceSource;
  available_evidence_sources: EvidenceSource[];
  verdict_basis: VerdictBasis;
  verdict: MarketVerdict;
  supporting_evidence: MarketEvidence[];
  contradicting_evidence: MarketEvidence[];
}

export interface StatisticalMarketAssessment {
  stat: ParsedMarket["stat"];
  subject: ParsedMarket["subject"];
  direction: MarketDirection;
  line: number;
  projection: number;
  primary_sample_size: number;
  opponent_sample_size: number;
  primary_average: number;
  opponent_average: number | null;
  primary_hit_rate: number;
  opponent_hit_rate: number | null;
  combined_hit_rate: number;
  push_rate: number;
  confidence: "high" | "medium" | "low";
  verdict: MarketVerdict;
  warnings: string[];
  label: string;
}

export interface MatchedMarketEvent {
  event_id: number;
  event_name: string;
  score: number;
  isComplementary: boolean;
  askedEventId: number | null;
}

interface OddsRowLike {
  event_id: number;
  odds: number;
  bookmaker_id: number;
  bookmaker_name: string;
}

/** Known complementary event ids (Over/Under 2.5, BTTS yes/no). */
const COMPLEMENTARY_EVENT_IDS: Readonly<Record<number, number>> = {
  8: 12,
  12: 8,
  6: 172,
  172: 6,
};

const COMPLEMENTARY_QUERY_HINTS: ReadonlyArray<{
  eventId: number;
  hints: string[];
}> = [
  { eventId: 8, hints: ["powyzej 2 5", "over 2 5", "powyzej 2.5", "over 2.5"] },
  { eventId: 12, hints: ["ponizej 2 5", "under 2 5", "ponizej 2.5", "under 2.5"] },
  { eventId: 6, hints: ["btts tak", "obie strzel", "both teams to score"] },
  { eventId: 172, hints: ["btts nie", "obie nie strzel"] },
];

const STAT_PATTERNS: ReadonlyArray<{ stat: MarketStat; patterns: RegExp[] }> = [
  {
    stat: "shots_on_target",
    patterns: [
      /strzal\w*\s+celn\w*/,
      /strzal\w*\s+na\s+bramk\w*/,
      /shots?\s+on\s+target/,
    ],
  },
  {
    stat: "yellow_cards",
    patterns: [/zolte\s+kartk\w*/, /yellow\s+cards?/],
  },
  {
    stat: "fouls_conceded",
    patterns: [/faul\w*\s+popelnion\w*/, /fouls?\s+conceded/],
  },
  {
    stat: "offsides",
    patterns: [/spalon\w*/, /offsides?/],
  },
  {
    stat: "corners",
    patterns: [/rozn\w*/, /corners?/],
  },
  {
    stat: "cards",
    patterns: [/kartk\w*/, /cards?/],
  },
  {
    stat: "fouls",
    patterns: [/faul\w*/, /fouls?/],
  },
  {
    stat: "shots",
    patterns: [/strzal\w*/, /shots?/],
  },
  {
    stat: "assists",
    patterns: [/asyst\w*/, /assists?/],
  },
  {
    stat: "goals",
    patterns: [/\bgol(?:a|e|i)?\b/, /\bbramk\w*\b/, /\bgoals?\b/],
  },
];

/**
 * Compute raw expected value: probability * odds - 1.
 */
export function computeEv(probability: number, odds: number): number {
  return probability * odds - 1;
}

/**
 * Compute EV after Polish betting tax (default 12%).
 */
export function computeEvAfterTax(
  probability: number,
  odds: number,
  taxRate: number = BETTING_TAX_RATE,
): number {
  return probability * odds * (1 - taxRate) - 1;
}

const MARKET_STOPWORDS = new Set([
  "powyzej",
  "ponizej",
  "over",
  "under",
  "suma",
  "lacznie",
  "razem",
  "total",
  "gospodarz",
  "gospodarza",
  "gospodarzy",
  "home",
  "gosc",
  "goscia",
  "gosci",
  "away",
  "zawodnik",
  "player",
  "pilkarz",
  "meczu",
  "mecz",
  "gol",
  "gola",
  "gole",
  "goli",
  "bramki",
  "bramke",
  "bramek",
  "strzal",
  "strzaly",
  "strzalu",
  "strzalow",
  "celne",
  "celnego",
  "celnych",
  "asysta",
  "asysty",
  "asyst",
  "kartki",
  "kartek",
  "faule",
  "fauli",
  "spalone",
  "spalonych",
  "rozne",
  "roznych",
  "corners",
  "shots",
  "goals",
  "cards",
  "fouls",
  "offsides",
  "na",
  "bramke",
  "w",
  "ze",
  "z",
]);

/** Polskie końcówki nazwisk — odróżniają zawodnika (Lewandowski) od drużyny (Górnik Zabrze) */
const SURNAME_SUFFIX_RE =
  /(?:ski|cka|cki|dzki|dzka|owicz|ewicz|iewicz|icz|ak|ek|yk|ny|na|ly|la)$/i;

/**
 * Parse a free-text market query into structured fields.
 * Explicit structured args always win over text heuristics.
 * Ambiguous subject stays null — callers must treat it as insufficient_data.
 */
export function parseMarketQuery(
  query: string,
  structuredArgs?: Partial<ParsedMarket>,
): ParsedMarket {
  const normalized = normalizeMarketText(query);
  const fromText = parseMarketFromText(query, normalized);

  const playerQuery =
    structuredArgs?.playerQuery ?? fromText.playerQuery;
  const stat = structuredArgs?.stat ?? fromText.stat;
  const direction = structuredArgs?.direction ?? fromText.direction;
  const line = structuredArgs?.line ?? fromText.line;
  const subject = resolveSubject({
    structuredSubject: structuredArgs?.subject,
    textSubject: fromText.subject,
    playerQuery,
    stat,
    direction,
    line,
    hasLeadingEntity: fromText.hasLeadingEntity,
  });

  return {
    eventQuery: structuredArgs?.eventQuery ?? query.trim(),
    stat,
    subject,
    playerQuery,
    direction,
    line,
  };
}

/** ł nie rozkłada się przez NFD — mapujemy je przed stripem znaków. */
function normalizeMarketText(value: string): string {
  return normalizeSearchText(value.replace(/ł/gi, "l"));
}

/** Statystyki typowo drużynowe — bez „zawodnik” nie mapujemy wiodącej nazwy na player. */
const TEAM_CONTEXT_STATS = new Set<MarketStat>([
  "shots",
  "shots_on_target",
  "corners",
  "cards",
  "fouls",
  "offsides",
]);

function parseMarketFromText(
  rawQuery: string,
  normalized: string,
): {
  stat: MarketStat | null;
  subject: MarketSubject | null;
  playerQuery: string | null;
  direction: MarketDirection | null;
  line: number | null;
  hasLeadingEntity: boolean;
} {
  const direction = detectDirection(normalized);
  // linię bierzemy z surowego tekstu — normalizacja zamienia "2.5" na "2 5"
  const line = detectLine(rawQuery);
  const stat = detectStat(normalized);
  const explicitSubject = detectExplicitSubject(normalized);
  const leadingName = extractLeadingName(rawQuery);
  const hasLeadingEntity = leadingName !== null;

  let subject = explicitSubject;
  let playerQuery: string | null = null;

  if (shouldTreatLeadingNameAsPlayer(leadingName, explicitSubject, stat)) {
    playerQuery = leadingName ?? extractPlayerNameNearKeyword(rawQuery);
    if (playerQuery) {
      subject = "player";
    }
  } else if (explicitSubject === "player") {
    playerQuery = extractPlayerNameNearKeyword(rawQuery);
  }

  return {
    stat,
    subject,
    playerQuery,
    direction,
    line,
    hasLeadingEntity,
  };
}

function resolveSubject(params: {
  structuredSubject: MarketSubject | null | undefined;
  textSubject: MarketSubject | null;
  playerQuery: string | null;
  stat: MarketStat | null;
  direction: MarketDirection | null;
  line: number | null;
  hasLeadingEntity: boolean;
}): MarketSubject | null {
  // jawny subject ze structured args (w tym null) ma pierwszeństwo
  if (params.structuredSubject !== undefined) {
    return params.structuredSubject;
  }
  if (params.textSubject !== null) {
    return params.textSubject;
  }
  if (params.playerQuery) {
    return "player";
  }
  // klasyczny OU goli meczu bez wskazanej drużyny/zawodnika → total
  if (
    params.stat === "goals" &&
    params.direction !== null &&
    params.line !== null &&
    !params.hasLeadingEntity
  ) {
    return "total";
  }
  return null;
}

function detectDirection(normalized: string): MarketDirection | null {
  if (/\b(powyzej|over)\b/.test(normalized)) {
    return "over";
  }
  if (/\b(ponizej|under)\b/.test(normalized)) {
    return "under";
  }
  return null;
}

function detectLine(rawQuery: string): number | null {
  const match = rawQuery.match(/\b(\d+[.,]\d+|\d+)\b/);
  if (!match) {
    return null;
  }
  const value = Number(match[1].replace(",", "."));
  return Number.isFinite(value) ? value : null;
}

function detectStat(normalized: string): MarketStat | null {
  for (const entry of STAT_PATTERNS) {
    if (entry.patterns.some((pattern) => pattern.test(normalized))) {
      return entry.stat;
    }
  }
  return null;
}

function detectExplicitSubject(normalized: string): MarketSubject | null {
  if (/\b(zawodnik|player|pilkarz)\b/.test(normalized)) {
    return "player";
  }
  if (/\b(suma|lacznie|razem|total)\b/.test(normalized)) {
    return "total";
  }
  // "meczu" bywa w "w meczu X-Y", więc nie wymusza subject=total
  if (/\b(gospodarz(?:a|e)?|home)\b/.test(normalized)) {
    return "home";
  }
  if (/\b(gosc(?:ia|ie)?|away)\b/.test(normalized)) {
    return "away";
  }
  return null;
}

/**
 * Fragment przed kierunkiem/linią — kandydat na nazwisko lub nazwę drużyny.
 * Stopwordy (zawodnik, gola, …) są odrzucane; nie stripujemy słownika rynku regexem.
 */
function extractLeadingName(rawQuery: string): string | null {
  const directionSplit = rawQuery.split(
    /\b(?:powyżej|powyzej|poniżej|ponizej|over|under)\b/i,
  );
  const beforeDirection = (directionSplit[0] ?? "").trim();
  return extractProperNameTokens(beforeDirection);
}

/**
 * Bierzemy wyłącznie 1–2 kapitalizowane tokeny (nazwa własna).
 * Reszta zdania (statystyka, linia, słowa kluczowe) jest ignorowana.
 */
function extractProperNameTokens(fragment: string): string | null {
  const cleaned = fragment
    .replace(/\b\d+(?:[.,]\d+)?\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!cleaned) {
    return null;
  }

  const nameWords = cleaned
    .split(" ")
    .filter(Boolean)
    .filter((word) => !MARKET_STOPWORDS.has(normalizeMarketText(word)))
    .filter(
      (word) =>
        /^[\p{L}][\p{L}'’-]*$/u.test(word) &&
        word[0] === word[0].toLocaleUpperCase("pl"),
    );

  if (nameWords.length === 0 || nameWords.length > 2) {
    return null;
  }

  return nameWords.join(" ");
}

function shouldTreatLeadingNameAsPlayer(
  leadingName: string | null,
  explicitSubject: MarketSubject | null,
  stat: MarketStat | null,
): boolean {
  if (explicitSubject === "player") {
    return true;
  }
  if (!leadingNameLooksLikeSurname(leadingName)) {
    return false;
  }
  // SOT/corners/… bez słowa „zawodnik” → subject null (dopytaj home/away)
  if (stat !== null && TEAM_CONTEXT_STATS.has(stat)) {
    return false;
  }
  return true;
}

function leadingNameLooksLikeSurname(name: string | null): boolean {
  if (!name) {
    return false;
  }
  const parts = name.split(" ");
  // dwuczłonowe: tylko gdy nazwisko (ostatni token) ma typową końcówkę
  // → "Robert Lewandowski" tak, "Górnik Zabrze" / "Legia Warszawa" nie
  if (parts.length === 2) {
    const last = normalizeMarketText(parts[1] ?? "").replace(/\s/g, "");
    return SURNAME_SUFFIX_RE.test(last);
  }
  if (parts.length !== 1) {
    return false;
  }
  const single = normalizeMarketText(parts[0] ?? "").replace(/\s/g, "");
  return SURNAME_SUFFIX_RE.test(single);
}

/**
 * Fallback gdy leading name nie wyszedł: kapitalizowane tokeny tuż po „zawodnik”.
 */
function extractPlayerNameNearKeyword(rawQuery: string): string | null {
  const match = rawQuery.match(
    /\b(?:zawodnik|player|piłkarz|pilkarz)\b\s+(.+)$/iu,
  );
  if (!match?.[1]) {
    return null;
  }
  // obcinamy od kierunku — statystyka po linii nas nie interesuje
  const afterKeyword = match[1].split(
    /\b(?:powyżej|powyzej|poniżej|ponizej|over|under)\b/i,
  )[0] ?? match[1];
  return extractProperNameTokens(afterKeyword);
}

/**
 * Match events by query text; prefer fuller name matches and known complements.
 */
export function matchEventByQuery(
  events: Array<{ event_id: number; event_name: string }>,
  query: string,
): MatchedMarketEvent[] {
  const normalizedQuery = normalizeMarketText(query);
  if (!normalizedQuery || events.length === 0) {
    return [];
  }

  const scored = scoreDirectMatches(events, normalizedQuery);
  if (scored.length > 0) {
    return scored.sort((a, b) => b.score - a.score);
  }

  return findComplementaryMatches(events, normalizedQuery);
}

function scoreDirectMatches(
  events: Array<{ event_id: number; event_name: string }>,
  normalizedQuery: string,
): MatchedMarketEvent[] {
  const results: MatchedMarketEvent[] = [];

  for (const event of events) {
    const normalizedName = normalizeMarketText(event.event_name);
    if (!normalizedName) {
      continue;
    }

    let score = 0;
    if (normalizedName === normalizedQuery) {
      score = 100;
    } else if (
      normalizedName.includes(normalizedQuery) ||
      normalizedQuery.includes(normalizedName)
    ) {
      // dłuższe dopasowanie wygrywa (np. "powyzej 2 5" vs samo "2 5")
      const overlap = Math.min(normalizedName.length, normalizedQuery.length);
      score = 50 + overlap;
    }

    if (score > 0) {
      results.push({
        event_id: event.event_id,
        event_name: event.event_name,
        score,
        isComplementary: false,
        askedEventId: null,
      });
    }
  }

  return results;
}

function findComplementaryMatches(
  events: Array<{ event_id: number; event_name: string }>,
  normalizedQuery: string,
): MatchedMarketEvent[] {
  const byId = new Map(events.map((event) => [event.event_id, event]));
  const askedEventId = resolveAskedComplementaryEventId(
    events,
    normalizedQuery,
  );
  if (askedEventId === null) {
    return [];
  }

  const complementId = COMPLEMENTARY_EVENT_IDS[askedEventId];
  if (complementId === undefined) {
    return [];
  }

  // brak bezpośredniego eventu — używamy komplementu, jeśli jest w liście
  if (byId.has(askedEventId)) {
    return [];
  }

  const complement = byId.get(complementId);
  if (!complement) {
    return [];
  }

  return [
    {
      event_id: complement.event_id,
      event_name: complement.event_name,
      score: 40,
      isComplementary: true,
      askedEventId,
    },
  ];
}

function resolveAskedComplementaryEventId(
  events: Array<{ event_id: number; event_name: string }>,
  normalizedQuery: string,
): number | null {
  for (const hint of COMPLEMENTARY_QUERY_HINTS) {
    const hintMatched = hint.hints.some((entry) => {
      const normalizedHint = normalizeMarketText(entry);
      return (
        normalizedQuery.includes(normalizedHint) ||
        normalizedHint.includes(normalizedQuery)
      );
    });
    if (hintMatched) {
      return hint.eventId;
    }
  }

  for (const event of events) {
    const normalizedName = normalizeMarketText(event.event_name);
    const complementId = COMPLEMENTARY_EVENT_IDS[event.event_id];
    if (complementId === undefined) {
      continue;
    }
    // zapytanie brzmi jak brakująca strona pary komplementarnej
    const askedHints = COMPLEMENTARY_QUERY_HINTS.find(
      (entry) => entry.eventId === complementId,
    );
    if (!askedHints) {
      continue;
    }
    const matchesAsked = askedHints.hints.some((entry) =>
      normalizedQuery.includes(normalizeMarketText(entry)),
    );
    if (matchesAsked && !normalizedQuery.includes(normalizedName)) {
      return complementId;
    }
  }

  return null;
}

/**
 * Pick the highest decimal odds quote for a given event.
 */
export function pickBestOdds(
  oddsRows: OddsRowLike[],
  eventId: number,
): MarketOddsQuote | null {
  let best: MarketOddsQuote | null = null;

  for (const row of oddsRows) {
    if (row.event_id !== eventId) {
      continue;
    }
    if (!Number.isFinite(row.odds) || row.odds <= 1) {
      continue;
    }
    if (!best || row.odds > best.odds) {
      best = {
        bookmaker_id: row.bookmaker_id,
        bookmaker_name: row.bookmaker_name,
        odds: row.odds,
      };
    }
  }

  return best;
}

// --- analyze_match_bet -----------------------------------------------------

const MARKET_STAT_ENUM = [
  "goals",
  "assists",
  "shots",
  "shots_on_target",
  "corners",
  "cards",
  "fouls",
  "offsides",
  "fouls_conceded",
  "yellow_cards",
] as const satisfies readonly MarketStat[];

const MARKET_SUBJECT_ENUM = [
  "home",
  "away",
  "total",
  "player",
] as const satisfies readonly MarketSubject[];

const MARKET_DIRECTION_ENUM = [
  "over",
  "under",
] as const satisfies readonly MarketDirection[];

interface MatchSearchResponseLike {
  matches: MatchSummary[];
  total_count: number;
  filters_applied?: { warnings?: string[] };
}

interface AnalyzeMatchContext {
  match: MatchSummary;
  sportId: number;
  warnings: string[];
  dataSources: ToolResult["dataSources"];
}

interface AnalyzeEvidenceBundle {
  bets: BetRecommendation[];
  predictions: MatchPredictionItem[];
  odds: OddsItem[];
  profileA: TeamProfile | null;
  profileB: TeamProfile | null;
  playerMatches: FootballPlayerMatchStat[];
  warnings: string[];
  dataSources: ToolResult["dataSources"];
}

interface AnalyzeVerdictPayload {
  evaluation: EvaluatedMarketRow;
  statistical: StatisticalMarketAssessment | null;
  risks: string[];
  odds_available: boolean;
  market: ParsedMarket;
}

/**
 * Critique a user-specified market for one match (bets -> prediction -> statistics).
 */
export async function analyzeMatchBet(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const eventQuery = stringArg(args, "event_query", {
    required: true,
    maxLength: 160,
  })!;
  const applyTax = booleanArg(args, "apply_tax") ?? true;
  const fromNow = booleanArg(args, "from_now") ?? true;
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const market = parseAnalyzeMarketArgs(args, eventQuery);

  const context = await resolveAnalyzeMatchContext({
    matchId: numberArg(args, "match_id", { min: 1 }),
    teamAQuery: stringArg(args, "team_a_query", { maxLength: 80 }),
    teamBQuery: stringArg(args, "team_b_query", { maxLength: 80 }),
    fromNow,
    sportId,
  });
  if (!context) {
    return emptyAnalyzeResult(
      "Nie znaleziono meczu do analizy rynku.",
      [
        "Podaj match_id albo obie nazwy drużyn (team_a_query i team_b_query).",
      ],
    );
  }

  const resolvedMarket = resolveSubjectAgainstMatch(
    market,
    context.match.home_team.name,
    context.match.away_team.name,
  );
  const missing = missingMarketFields(resolvedMarket);

  const evidence = await fetchAnalyzeEvidence({
    match: context.match,
    market: resolvedMarket,
    applyTax,
    sportId: sportId ?? context.sportId,
  });

  const verdict = buildAnalyzeVerdict({
    match: context.match,
    market: resolvedMarket,
    evidence,
    applyTax,
    missingFields: missing,
  });

  const warnings = [
    ...context.warnings,
    ...evidence.warnings,
    ...verdict.risks,
  ];

  return {
    name: "analyze_match_bet",
    summary: buildAnalyzeSummary(context.match, verdict),
    data: {
      ...verdict.evaluation,
      market: verdict.market,
      statistical: verdict.statistical,
      risks: verdict.risks,
      odds_available: verdict.odds_available,
    },
    table: buildAnalyzeTable(verdict),
    dataSources: [...context.dataSources, ...evidence.dataSources],
    warnings,
  };
}

function parseAnalyzeMarketArgs(
  args: Record<string, unknown>,
  eventQuery: string,
): ParsedMarket {
  const structuredStat = stringArg(args, "stat", { maxLength: 40 });
  const structuredSubject = stringArg(args, "subject", { maxLength: 20 });
  const structuredDirection = stringArg(args, "direction", { maxLength: 20 });
  const structured: Partial<ParsedMarket> = {
    eventQuery,
    playerQuery: stringArg(args, "player_query", { maxLength: 80 }) ?? null,
    line: floatArg(args, "line", { min: 0, max: 100 }) ?? null,
  };
  if (
    structuredStat &&
    (MARKET_STAT_ENUM as readonly string[]).includes(structuredStat)
  ) {
    structured.stat = structuredStat as MarketStat;
  }
  if (
    structuredSubject &&
    (MARKET_SUBJECT_ENUM as readonly string[]).includes(structuredSubject)
  ) {
    structured.subject = structuredSubject as MarketSubject;
  }
  if (
    structuredDirection &&
    (MARKET_DIRECTION_ENUM as readonly string[]).includes(structuredDirection)
  ) {
    structured.direction = structuredDirection as MarketDirection;
  }
  return parseMarketQuery(eventQuery, structured);
}

async function resolveAnalyzeMatchContext(params: {
  matchId?: number;
  teamAQuery?: string;
  teamBQuery?: string;
  fromNow: boolean;
  sportId?: number;
}): Promise<AnalyzeMatchContext | null> {
  if (params.matchId) {
    try {
      const details = await fetchReadOnly<MatchDetails>(
        `/matches/${params.matchId}/details`,
      );
      return {
        match: matchSummaryFromDetails(details),
        sportId: details.sport_id ?? params.sportId ?? FOOTBALL_SPORT_ID,
        warnings: [],
        dataSources: [
          {
            label: "Szczegóły meczu",
            endpoint: getEndpoint(`/matches/${params.matchId}/details`),
            params: { match_id: params.matchId },
          },
        ],
      };
    } catch {
      return null;
    }
  }

  if (!params.teamAQuery || !params.teamBQuery) {
    return null;
  }

  return searchAnalyzeMatch({
    teamAQuery: params.teamAQuery,
    teamBQuery: params.teamBQuery,
    fromNow: params.fromNow,
    sportId: params.sportId,
  });
}

async function searchAnalyzeMatch(params: {
  teamAQuery: string;
  teamBQuery: string;
  fromNow: boolean;
  sportId?: number;
}): Promise<AnalyzeMatchContext | null> {
  const warnings: string[] = [];
  const dataSources: ToolResult["dataSources"] = [];

  const first = await fetchReadOnly<MatchSearchResponseLike>("/matches/search", {
    team_a_query: params.teamAQuery,
    team_b_query: params.teamBQuery,
    sport_id: params.sportId,
    from_now: params.fromNow,
    played: false,
    page_size: 10,
  });
  dataSources.push({
    label: "Wyszukiwanie meczów",
    endpoint: getEndpoint("/matches/search"),
    params: {
      team_a_query: params.teamAQuery,
      team_b_query: params.teamBQuery,
      sport_id: params.sportId ?? null,
      from_now: params.fromNow,
      played: false,
      page_size: 10,
    },
  });
  if (first.filters_applied?.warnings?.length) {
    warnings.push(...first.filters_applied.warnings);
  }

  let matches = first.matches;
  if (matches.length === 0) {
    const fallback = await fetchReadOnly<MatchSearchResponseLike>(
      "/matches/search",
      {
        team_a_query: params.teamAQuery,
        team_b_query: params.teamBQuery,
        sport_id: params.sportId,
        from_now: false,
        page_size: 10,
      },
    );
    dataSources.push({
      label: "Wyszukiwanie meczów (fallback)",
      endpoint: getEndpoint("/matches/search"),
      params: {
        team_a_query: params.teamAQuery,
        team_b_query: params.teamBQuery,
        sport_id: params.sportId ?? null,
        from_now: false,
        page_size: 10,
      },
    });
    matches = fallback.matches;
    if (matches.length > 0) {
      warnings.push(
        "Brak nadchodzącego meczu nierozegnanego — użyłem najbliższego dopasowania historycznego/bez filtra played.",
      );
    }
  }

  if (matches.length === 0) {
    return null;
  }

  const sorted = [...matches].sort(
    (a, b) =>
      new Date(a.game_date).getTime() - new Date(b.game_date).getTime(),
  );
  const match = pickNearestMatch(sorted);
  if (matches.length > 1) {
    warnings.push(
      `Znaleziono ${matches.length} meczów — użyłem najbliższego: ${match.home_team.name} vs ${match.away_team.name} (${String(match.game_date).slice(0, 10)}).`,
    );
  }

  return {
    match,
    sportId: params.sportId ?? FOOTBALL_SPORT_ID,
    warnings,
    dataSources,
  };
}

function pickNearestMatch(matchesAsc: MatchSummary[]): MatchSummary {
  const now = Date.now();
  const upcoming = matchesAsc.filter(
    (match) => new Date(match.game_date).getTime() >= now,
  );
  if (upcoming.length > 0) {
    return upcoming[0]!;
  }
  return matchesAsc[matchesAsc.length - 1]!;
}

function matchSummaryFromDetails(details: MatchDetails): MatchSummary {
  return {
    id: details.id,
    league_id: details.league_id,
    season_id: details.season_id,
    round: details.round,
    round_label: details.round_label,
    game_date: details.game_date,
    home_team: details.home_team,
    away_team: details.away_team,
    home_goals: details.home_goals,
    away_goals: details.away_goals,
    result: details.result,
    is_played: details.is_played,
    score_resolution: details.score_resolution,
  };
}

function resolveSubjectAgainstMatch(
  market: ParsedMarket,
  homeName: string,
  awayName: string,
): ParsedMarket {
  if (market.subject !== null) {
    return market;
  }

  const query = normalizeMarketText(market.eventQuery);
  const home = normalizeMarketText(homeName);
  const away = normalizeMarketText(awayName);
  const homeHit = home.length > 0 && query.includes(home.split(" ")[0] ?? home);
  const awayHit = away.length > 0 && query.includes(away.split(" ")[0] ?? away);

  // dopasowanie po pierwszym tokenie nazwy (Górnik / Śląsk) gdy subject null
  if (homeHit && !awayHit) {
    return { ...market, subject: "home" };
  }
  if (awayHit && !homeHit) {
    return { ...market, subject: "away" };
  }
  return market;
}

function missingMarketFields(market: ParsedMarket): string[] {
  const missing: string[] = [];
  if (!market.stat) {
    missing.push("stat");
  }
  if (market.subject === null) {
    missing.push("subject");
  }
  if (!market.direction) {
    missing.push("direction");
  }
  if (market.line === null) {
    missing.push("line");
  }
  if (market.subject === "player" && !market.playerQuery) {
    missing.push("player_query");
  }
  return missing;
}

async function fetchAnalyzeEvidence(params: {
  match: MatchSummary;
  market: ParsedMarket;
  applyTax: boolean;
  sportId: number;
}): Promise<AnalyzeEvidenceBundle> {
  const warnings: string[] = [];
  const dataSources: ToolResult["dataSources"] = [];
  const matchId = params.match.id;

  const settled = await Promise.allSettled([
    fetchReadOnly<BetRecommendationsResponse>("/bets/recommendations", {
      match_id: matchId,
      apply_tax: params.applyTax,
      page_size: 50,
    }),
    fetchReadOnly<MatchPredictionListResponse>(
      `/predictions/match/${matchId}`,
    ),
    fetchReadOnly<MatchOddsListResponse>(`/odds/match/${matchId}`),
    fetchReadOnly<TeamProfile>(`/teams/${params.match.home_team.id}/profile`, {
      limit: 10,
    }),
    fetchReadOnly<TeamProfile>(`/teams/${params.match.away_team.id}/profile`, {
      limit: 10,
    }),
  ]);

  const betsResponse = takeSettled(
    settled[0],
    warnings,
    "Nie udało się pobrać rekomendacji bets.",
  );
  const predictionsResponse = takeSettled(
    settled[1],
    warnings,
    "Nie udało się pobrać predykcji modelu.",
  );
  const oddsResponse = takeSettled(
    settled[2],
    warnings,
    "Nie udało się pobrać kursów.",
  );
  const profileA = takeSettled(
    settled[3],
    warnings,
    "Nie udało się pobrać profilu gospodarza.",
  );
  const profileB = takeSettled(
    settled[4],
    warnings,
    "Nie udało się pobrać profilu gościa.",
  );

  dataSources.push(
    ...buildEvidenceDataSources({
      match: params.match,
      applyTax: params.applyTax,
      bets: Boolean(betsResponse),
      predictions: Boolean(predictionsResponse),
      odds: Boolean(oddsResponse),
      profileA: Boolean(profileA),
      profileB: Boolean(profileB),
    }),
  );

  let playerMatches: FootballPlayerMatchStat[] = [];
  if (params.market.subject === "player" && params.market.playerQuery) {
    const playerBundle = await fetchPlayerEvidence({
      sportId: params.sportId,
      seasonId: params.match.season_id,
      playerQuery: params.market.playerQuery,
    });
    playerMatches = playerBundle.matches;
    warnings.push(...playerBundle.warnings);
    dataSources.push(...playerBundle.dataSources);
  }

  return {
    bets: betsResponse?.recommendations ?? [],
    predictions: predictionsResponse?.match_predictions ?? [],
    odds: oddsResponse?.odds ?? [],
    profileA: profileA ?? null,
    profileB: profileB ?? null,
    playerMatches,
    warnings,
    dataSources,
  };
}

function buildEvidenceDataSources(params: {
  match: MatchSummary;
  applyTax: boolean;
  bets: boolean;
  predictions: boolean;
  odds: boolean;
  profileA: boolean;
  profileB: boolean;
}): ToolResult["dataSources"] {
  const matchId = params.match.id;
  const sources: ToolResult["dataSources"] = [];
  if (params.bets) {
    sources.push({
      label: "Rekomendacje zakładów",
      endpoint: getEndpoint("/bets/recommendations"),
      params: { match_id: matchId, apply_tax: params.applyTax },
    });
  }
  if (params.predictions) {
    sources.push({
      label: "Predykcje meczu",
      endpoint: getEndpoint(`/predictions/match/${matchId}`),
      params: { match_id: matchId },
    });
  }
  if (params.odds) {
    sources.push({
      label: "Kursy meczu",
      endpoint: getEndpoint(`/odds/match/${matchId}`),
      params: { match_id: matchId },
    });
  }
  if (params.profileA) {
    sources.push({
      label: "Profil gospodarza",
      endpoint: getEndpoint(`/teams/${params.match.home_team.id}/profile`),
      params: { team_id: params.match.home_team.id, limit: 10 },
    });
  }
  if (params.profileB) {
    sources.push({
      label: "Profil gościa",
      endpoint: getEndpoint(`/teams/${params.match.away_team.id}/profile`),
      params: { team_id: params.match.away_team.id, limit: 10 },
    });
  }
  return sources;
}

function takeSettled<T>(
  result: PromiseSettledResult<T>,
  warnings: string[],
  message: string,
): T | null {
  if (result.status === "fulfilled") {
    return result.value;
  }
  warnings.push(message);
  return null;
}

async function fetchPlayerEvidence(params: {
  sportId: number;
  seasonId: number;
  playerQuery: string;
}): Promise<{
  matches: FootballPlayerMatchStat[];
  warnings: string[];
  dataSources: ToolResult["dataSources"];
}> {
  const warnings: string[] = [];
  const dataSources: ToolResult["dataSources"] = [];
  try {
    const players = await fetchReadOnly<FootballPlayersListResponse>(
      `/players/${params.sportId}`,
      {
        season_id: params.seasonId,
        search: params.playerQuery,
      },
    );
    dataSources.push({
      label: "Wyszukiwanie zawodnika",
      endpoint: getEndpoint(`/players/${params.sportId}`),
      params: {
        sport_id: params.sportId,
        season_id: params.seasonId,
        search: params.playerQuery,
      },
    });
    const player = players.players[0];
    if (!player) {
      warnings.push(`Nie znaleziono zawodnika dla "${params.playerQuery}".`);
      return { matches: [], warnings, dataSources };
    }
    if (players.players.length > 1) {
      warnings.push(
        `Znaleziono kilku zawodników dla "${params.playerQuery}". Użyłem: ${player.common_name}.`,
      );
    }
    const stats = await fetchReadOnly<FootballPlayerMatchStatsResponse>(
      `/players/${params.sportId}/${player.id}/match-stats`,
      { season_id: params.seasonId, limit: 10 },
    );
    dataSources.push({
      label: "Log meczowy zawodnika",
      endpoint: getEndpoint(
        `/players/${params.sportId}/${player.id}/match-stats`,
      ),
      params: {
        sport_id: params.sportId,
        player_id: player.id,
        season_id: params.seasonId,
        limit: 10,
      },
    });
    return { matches: stats.matches, warnings, dataSources };
  } catch {
    warnings.push("Nie udało się pobrać statystyk zawodnika.");
    return { matches: [], warnings, dataSources };
  }
}

function buildAnalyzeVerdict(params: {
  match: MatchSummary;
  market: ParsedMarket;
  evidence: AnalyzeEvidenceBundle;
  applyTax: boolean;
  missingFields: string[];
}): AnalyzeVerdictPayload {
  const { match, market, evidence, applyTax } = params;
  const supporting: MarketEvidence[] = [];
  const contradicting: MarketEvidence[] = [];
  const risks: string[] = [];
  const available: EvidenceSource[] = [];

  const modelLayer = collectModelEvidence({
    market,
    evidence,
    supporting,
    contradicting,
    available,
    risks,
    applyTax,
  });

  const oddsLayer = collectOddsMetrics({
    probability: modelLayer.probability,
    eventId: modelLayer.eventId,
    predictionEventId: modelLayer.predictionEventId,
    betOdds: modelLayer.betOdds,
    betBookmaker: modelLayer.betBookmaker,
    primary: modelLayer.primary,
    oddsRows: evidence.odds,
    applyTax,
    supporting,
    contradicting,
    risks,
  });

  const statistical = assessStatisticalLayer({ market, evidence });
  appendStatisticalEvidence({
    statistical,
    available,
    primaryRef: modelLayer,
    supporting,
    contradicting,
    risks,
  });

  if (available.length === 0) {
    const reason =
      params.missingFields.length > 0
        ? `Brak źródeł i niejednoznaczny rynek (brakuje: ${params.missingFields.join(", ")}).`
        : "Brak bets, predykcji i wystarczających statystyk dla tego rynku.";
    return {
      evaluation: buildEmptyEvaluation(
        match,
        market,
        modelLayer.eventName,
        reason,
      ),
      statistical,
      risks: [...risks, reason],
      odds_available: oddsLayer.oddsAvailable,
      market,
    };
  }

  const { verdict, verdictBasis } = settleAnalyzeVerdict({
    oddsAvailable: oddsLayer.oddsAvailable,
    ev: oddsLayer.ev,
    evAfterTax: applyTax ? oddsLayer.evAfterTax : oddsLayer.ev,
    probability: modelLayer.probability,
    statistical,
  });
  const softened = softenContradictoryVerdict(
    verdict,
    oddsLayer.oddsAvailable,
    oddsLayer.evAfterTax ?? oddsLayer.ev,
    statistical,
  );

  return {
    evaluation: toEvaluatedMarketRow({
      match,
      modelLayer,
      oddsLayer,
      applyTax,
      available,
      verdictBasis,
      verdict: softened,
      supporting,
      contradicting,
    }),
    statistical,
    risks,
    odds_available: oddsLayer.oddsAvailable,
    market,
  };
}

function toEvaluatedMarketRow(params: {
  match: MatchSummary;
  modelLayer: ModelEvidenceState;
  oddsLayer: {
    oddsValue: number | null;
    bookmaker: string | null;
    implied: number | null;
    ev: number | null;
    evAfterTax: number | null;
    edgePct: number | null;
  };
  applyTax: boolean;
  available: EvidenceSource[];
  verdictBasis: VerdictBasis;
  verdict: MarketVerdict;
  supporting: MarketEvidence[];
  contradicting: MarketEvidence[];
}): EvaluatedMarketRow {
  const { match, modelLayer, oddsLayer } = params;
  return {
    match_id: match.id,
    home_team: match.home_team.name,
    away_team: match.away_team.name,
    game_date: String(match.game_date),
    event_id: modelLayer.eventId,
    event_name: modelLayer.eventName,
    model_id: modelLayer.modelId,
    model_name: modelLayer.modelName,
    probability: modelLayer.probability,
    probability_pct: modelLayer.probabilityPct,
    best_odds: oddsLayer.oddsValue,
    best_bookmaker: oddsLayer.bookmaker,
    implied_probability: oddsLayer.implied,
    ev: oddsLayer.ev,
    ev_after_tax: params.applyTax ? oddsLayer.evAfterTax : null,
    edge_pct: oddsLayer.edgePct,
    primary_evidence_source: modelLayer.primary ?? "statistics",
    available_evidence_sources: params.available,
    verdict_basis: params.verdictBasis,
    verdict: params.verdict,
    supporting_evidence: params.supporting,
    contradicting_evidence: params.contradicting,
  };
}

interface ModelEvidenceState {
  probability: number | null;
  probabilityPct: number | null;
  eventId: number | null;
  eventName: string;
  modelId: number | null;
  modelName: string | null;
  primary: EvidenceSource | null;
  predictionEventId: number | null;
  betOdds: number | null;
  betBookmaker: string | null;
}

function collectModelEvidence(params: {
  market: ParsedMarket;
  evidence: AnalyzeEvidenceBundle;
  supporting: MarketEvidence[];
  contradicting: MarketEvidence[];
  available: EvidenceSource[];
  risks: string[];
  applyTax: boolean;
}): ModelEvidenceState {
  const betHit = findMatchingBet(params.evidence.bets, params.market.eventQuery);
  const predictionHit = findMatchingPrediction(
    params.evidence.predictions,
    params.market.eventQuery,
  );
  if (predictionHit?.warning) {
    params.risks.push(`Uwaga: ${predictionHit.warning}`);
  }

  const state: ModelEvidenceState = {
    probability: null,
    probabilityPct: null,
    eventId: null,
    eventName: params.market.eventQuery,
    modelId: null,
    modelName: null,
    primary: null,
    predictionEventId: predictionHit?.event_id ?? null,
    betOdds: betHit?.odds ?? null,
    betBookmaker: betHit?.bookmaker_name ?? null,
  };

  if (betHit) {
    params.available.push("bet");
    state.primary = "bet";
    state.probability = betHit.probability;
    state.probabilityPct = betHit.probability_pct;
    state.eventId = betHit.event_id;
    state.eventName = betHit.event_name;
    state.modelId = betHit.model_id;
    state.modelName = betHit.model_name;
    pushBetEvidenceByEv(betHit, params.applyTax, params.supporting, params.contradicting);
  }

  if (!predictionHit) {
    return state;
  }

  params.available.push("prediction");
  if (!state.primary) {
    state.primary = "prediction";
  }
  if (state.probability === null) {
    state.probability = predictionHit.probability;
    state.probabilityPct =
      predictionHit.probability !== null
        ? predictionHit.probability * 100
        : null;
    state.eventId = predictionHit.event_id;
    state.eventName = predictionHit.event_name;
    state.modelId = predictionHit.model_id;
    state.modelName = predictionHit.model_name;
  }
  if (predictionHit.probability === null) {
    return state;
  }

  const predEvidence: MarketEvidence = {
    source: "prediction",
    label: predictionHit.isComplementary
      ? "Predykcja komplementarna (1-p)"
      : "Predykcja modelu",
    value: formatPct(predictionHit.probability),
    interpretation: `Model ${predictionHit.model_name ?? predictionHit.model_id} ocenia ${predictionHit.event_name} na ${formatPct(predictionHit.probability)}.`,
  };
  // zgodność z betem: różnica > 10 pp idzie w przeciw
  if (
    betHit &&
    Math.abs(betHit.probability - predictionHit.probability) > 0.1
  ) {
    params.contradicting.push(predEvidence);
  } else {
    params.supporting.push(predEvidence);
  }
  return state;
}

/** Klasyfikuje rekord bets wg znaku EV — nie wrzuca zawsze do supporting. */
function pushBetEvidenceByEv(
  betHit: BetRecommendation,
  applyTax: boolean,
  supporting: MarketEvidence[],
  contradicting: MarketEvidence[],
): void {
  const betEvSignal =
    applyTax && betHit.ev_after_tax != null ? betHit.ev_after_tax : betHit.ev;
  const betEvidence: MarketEvidence = {
    source: "bet",
    label:
      betEvSignal > 0
        ? "Gotowa rekomendacja bets (dodatni EV)"
        : "Gotowa rekomendacja bets (ujemny/zerowy EV)",
    value: `${formatPct(betHit.probability)} @ ${betHit.odds}`,
    interpretation: `Automat zapisał rynek ${betHit.event_name}; EV rekordu = ${formatPct(betEvSignal)}.`,
  };
  if (betEvSignal > 0) {
    supporting.push(betEvidence);
  } else {
    contradicting.push(betEvidence);
  }
}

function collectOddsMetrics(params: {
  probability: number | null;
  eventId: number | null;
  predictionEventId: number | null;
  betOdds: number | null;
  betBookmaker: string | null;
  primary: EvidenceSource | null;
  oddsRows: OddsItem[];
  applyTax: boolean;
  supporting: MarketEvidence[];
  contradicting: MarketEvidence[];
  risks: string[];
}): {
  oddsValue: number | null;
  bookmaker: string | null;
  oddsAvailable: boolean;
  ev: number | null;
  evAfterTax: number | null;
  implied: number | null;
  edgePct: number | null;
} {
  const oddsEventId = params.eventId ?? params.predictionEventId;
  const bestOdds =
    oddsEventId != null ? pickBestOdds(params.oddsRows, oddsEventId) : null;
  const oddsValue = bestOdds?.odds ?? params.betOdds ?? null;
  const bookmaker = bestOdds?.bookmaker_name ?? params.betBookmaker ?? null;
  const oddsAvailable = oddsValue !== null && oddsValue > 1;

  let ev: number | null = null;
  let evAfterTax: number | null = null;
  let implied: number | null = null;
  let edgePct: number | null = null;

  if (params.probability !== null && oddsAvailable && oddsValue !== null) {
    ev = computeEv(params.probability, oddsValue);
    evAfterTax = params.applyTax
      ? computeEvAfterTax(params.probability, oddsValue)
      : null;
    implied = 1 / oddsValue;
    edgePct = (params.probability - implied) * 100;
    const evLabel = params.applyTax && evAfterTax !== null ? evAfterTax : ev;
    const evEvidence: MarketEvidence = {
      source: params.primary === "bet" ? "bet" : "prediction",
      label: params.applyTax ? "EV po podatku 12%" : "EV",
      value: formatPct(evLabel),
      interpretation:
        evLabel > 0
          ? "Dodatni EV wspiera grę względem kursu."
          : "Ujemny lub zerowy EV przemawia przeciw grze względem kursu.",
    };
    if (evLabel > 0) {
      params.supporting.push(evEvidence);
    } else {
      params.contradicting.push(evEvidence);
    }
  } else if (params.probability !== null && !oddsAvailable) {
    params.risks.push(
      "Brak kursu — nie wolno nazywać typu value bet; ocena opiera się na prawdopodobieństwie/statystykach.",
    );
  }

  return {
    oddsValue,
    bookmaker,
    oddsAvailable,
    ev,
    evAfterTax,
    implied,
    edgePct,
  };
}

function appendStatisticalEvidence(params: {
  statistical: StatisticalMarketAssessment | null;
  available: EvidenceSource[];
  primaryRef: ModelEvidenceState;
  supporting: MarketEvidence[];
  contradicting: MarketEvidence[];
  risks: string[];
}): void {
  const { statistical } = params;
  if (!statistical) {
    return;
  }
  if (statistical.verdict === "insufficient_data") {
    params.risks.push(...statistical.warnings.map((w) => `Uwaga: ${w}`));
    return;
  }

  params.available.push("statistics");
  if (!params.primaryRef.primary) {
    params.primaryRef.primary = "statistics";
  }
  const statsEvidence: MarketEvidence = {
    source: "statistics",
    label: "Wsparcie historyczne (hit rate)",
    value: formatPct(statistical.combined_hit_rate),
    interpretation: `Linia ${statistical.direction} ${statistical.line}: combined hit rate ${formatPct(statistical.combined_hit_rate)} (n=${statistical.primary_sample_size}+${statistical.opponent_sample_size}, confidence=${statistical.confidence}). Hit rate nie jest kalibrowanym prawdopodobieństwem modelu.`,
  };
  if (
    statistical.verdict === "positive" ||
    statistical.verdict === "lean_positive"
  ) {
    params.supporting.push(statsEvidence);
  } else if (
    statistical.verdict === "negative" ||
    statistical.verdict === "lean_negative"
  ) {
    params.contradicting.push(statsEvidence);
  } else {
    params.supporting.push(statsEvidence);
  }
  params.risks.push(...statistical.warnings.map((w) => `Uwaga: ${w}`));
}

function findMatchingBet(
  bets: BetRecommendation[],
  eventQuery: string,
): BetRecommendation | null {
  if (bets.length === 0) {
    return null;
  }
  const matched = matchEventByQuery(
    bets.map((bet) => ({
      event_id: bet.event_id,
      event_name: bet.event_name,
    })),
    eventQuery,
  );
  const top = matched[0];
  // komplement w bets pomijamy — wolimy bezpośredni event lub predykcję
  if (!top || top.isComplementary) {
    return null;
  }
  return bets.find((bet) => bet.event_id === top.event_id) ?? null;
}

function findMatchingPrediction(
  predictions: MatchPredictionItem[],
  eventQuery: string,
): {
  event_id: number;
  event_name: string;
  model_id: number;
  model_name: string | null;
  probability: number | null;
  isComplementary: boolean;
  warning?: string;
} | null {
  if (predictions.length === 0) {
    return null;
  }
  const matched = matchEventByQuery(
    predictions.map((row) => ({
      event_id: row.event_id,
      event_name: row.event_name,
    })),
    eventQuery,
  );
  const top = matched[0];
  if (!top) {
    return null;
  }
  const row = predictions.find((item) => item.event_id === top.event_id);
  if (!row || row.value === null) {
    return null;
  }
  if (top.isComplementary) {
    return {
      event_id: top.askedEventId ?? row.event_id,
      event_name: eventQuery,
      model_id: row.model_id,
      model_name: row.model_name,
      probability: 1 - row.value,
      isComplementary: true,
      warning:
        "Użyto komplementarnej predykcji (1-p), bo brak bezpośredniej strony rynku w final_predictions.",
    };
  }
  return {
    event_id: row.event_id,
    event_name: row.event_name,
    model_id: row.model_id,
    model_name: row.model_name,
    probability: row.value,
    isComplementary: false,
  };
}

function assessStatisticalLayer(params: {
  market: ParsedMarket;
  evidence: AnalyzeEvidenceBundle;
}): StatisticalMarketAssessment | null {
  const { market, evidence } = params;
  if (market.subject === "player") {
    if (!market.stat || !market.direction || market.line === null) {
      return null;
    }
    return assessPlayerMarket(evidence.playerMatches, market, 10);
  }
  if (
    !market.stat ||
    market.subject === null ||
    !market.direction ||
    market.line === null
  ) {
    return null;
  }
  if (!evidence.profileA || !evidence.profileB) {
    return null;
  }
  return assessTeamMarket(evidence.profileA, evidence.profileB, market, 10);
}

function settleAnalyzeVerdict(params: {
  oddsAvailable: boolean;
  ev: number | null;
  evAfterTax: number | null;
  probability: number | null;
  statistical: StatisticalMarketAssessment | null;
}): { verdict: MarketVerdict; verdictBasis: VerdictBasis } {
  const valueMetric = params.evAfterTax ?? params.ev;
  if (params.oddsAvailable && params.probability !== null && valueMetric !== null) {
    return {
      verdict: verdictFromEv(valueMetric),
      verdictBasis: "value",
    };
  }
  if (params.probability !== null) {
    return {
      verdict: verdictFromRate(params.probability),
      verdictBasis: "probability",
    };
  }
  if (
    params.statistical &&
    params.statistical.verdict !== "insufficient_data"
  ) {
    return {
      verdict: params.statistical.verdict,
      verdictBasis: "statistical_support",
    };
  }
  return { verdict: "insufficient_data", verdictBasis: "statistical_support" };
}

function softenContradictoryVerdict(
  verdict: MarketVerdict,
  oddsAvailable: boolean,
  valueMetric: number | null,
  statistical: StatisticalMarketAssessment | null,
): MarketVerdict {
  if (
    !statistical ||
    statistical.verdict === "insufficient_data" ||
    !oddsAvailable ||
    valueMetric === null
  ) {
    return verdict;
  }
  const valuePositive = valueMetric > 0;
  const statsNegative =
    statistical.verdict === "negative" ||
    statistical.verdict === "lean_negative";
  const valueNegative = valueMetric <= 0;
  const statsPositive =
    statistical.verdict === "positive" ||
    statistical.verdict === "lean_positive";

  if (valuePositive && statsNegative) {
    return valueMetric > 0.08 ? "lean_positive" : "neutral";
  }
  if (valueNegative && statsPositive) {
    return valueMetric < -0.08 ? "lean_negative" : "neutral";
  }
  return verdict;
}

function verdictFromEv(ev: number): MarketVerdict {
  if (ev >= 0.08) {
    return "positive";
  }
  if (ev > 0) {
    return "lean_positive";
  }
  if (ev > -0.05) {
    return "neutral";
  }
  if (ev > -0.1) {
    return "lean_negative";
  }
  return "negative";
}

function verdictFromRate(rate: number): MarketVerdict {
  if (rate >= 0.65) {
    return "positive";
  }
  if (rate >= 0.55) {
    return "lean_positive";
  }
  if (rate >= 0.45) {
    return "neutral";
  }
  if (rate >= 0.35) {
    return "lean_negative";
  }
  return "negative";
}

function buildEmptyEvaluation(
  match: MatchSummary,
  market: ParsedMarket,
  eventName: string,
  reason: string,
): EvaluatedMarketRow {
  return {
    match_id: match.id,
    home_team: match.home_team.name,
    away_team: match.away_team.name,
    game_date: String(match.game_date),
    event_id: null,
    event_name: eventName,
    model_id: null,
    model_name: null,
    probability: null,
    probability_pct: null,
    best_odds: null,
    best_bookmaker: null,
    implied_probability: null,
    ev: null,
    ev_after_tax: null,
    edge_pct: null,
    primary_evidence_source: "statistics",
    available_evidence_sources: [],
    verdict_basis: "statistical_support",
    verdict: "insufficient_data",
    supporting_evidence: [],
    contradicting_evidence: [
      {
        source: "statistics",
        label: "Brak danych",
        value: reason,
        interpretation: reason,
      },
    ],
  };
}

function buildAnalyzeSummary(
  match: MatchSummary,
  verdict: AnalyzeVerdictPayload,
): string {
  const date = String(match.game_date).slice(0, 10);
  const label = verdictLabelPl(verdict.evaluation.verdict);
  return `${match.home_team.name} vs ${match.away_team.name} (${date}): ${verdict.evaluation.event_name} — ${label} [${verdict.evaluation.verdict_basis}].`;
}

function verdictLabelPl(verdict: MarketVerdict): string {
  switch (verdict) {
    case "positive":
      return "wsparcie pozytywne";
    case "lean_positive":
      return "lekko na tak";
    case "neutral":
      return "neutralnie";
    case "lean_negative":
      return "lekko na nie";
    case "negative":
      return "słabe wsparcie";
    default:
      return "niewystarczające dane";
  }
}

function buildAnalyzeTable(verdict: AnalyzeVerdictPayload): ToolResult["table"] {
  const row = verdict.evaluation;
  return {
    title: "Krytyka rynku",
    columns: ["Pole", "Wartość"],
    rows: [
      ["Werdykt", verdictLabelPl(row.verdict)],
      ["Podstawa", row.verdict_basis],
      ["Źródło główne", row.primary_evidence_source],
      [
        "Prawdopodobieństwo",
        row.probability_pct != null
          ? `${row.probability_pct.toFixed(1)}%`
          : "—",
      ],
      ["Kurs", row.best_odds != null ? row.best_odds.toFixed(2) : "—"],
      [
        "EV",
        row.ev != null ? `${(row.ev * 100).toFixed(1)}%` : "—",
      ],
      [
        "EV po podatku",
        row.ev_after_tax != null
          ? `${(row.ev_after_tax * 100).toFixed(1)}%`
          : "—",
      ],
      [
        "Hit rate (stat)",
        verdict.statistical &&
        verdict.statistical.verdict !== "insufficient_data"
          ? `${(verdict.statistical.combined_hit_rate * 100).toFixed(1)}%`
          : "—",
      ],
    ],
  };
}

function emptyAnalyzeResult(
  summary: string,
  warnings: string[],
): ToolResult {
  return {
    name: "analyze_match_bet",
    summary,
    data: null,
    dataSources: [],
    warnings,
  };
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
