/**
 * Market parsing helpers and EV calculations for chat bet analysis.
 */

import { normalizeSearchText } from "./text";

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
