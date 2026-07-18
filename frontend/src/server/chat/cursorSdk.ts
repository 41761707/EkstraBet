import { Agent, CursorAgentError } from "@cursor/sdk";
import type { ChatAnswer, ChatSportContext } from "@/types/api";
import {
  CHAT_TOOL_DESCRIPTIONS,
  runPlannedTools,
  type PlannedToolCall,
} from "@/server/chat/tools";

interface CursorPlan {
  toolCalls: PlannedToolCall[];
  refusal?: string;
}

interface CursorSummary {
  answerText?: string;
  warnings?: string[];
}

const DEFAULT_CURSOR_MODEL = "composer-2.5";

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function requireCursorApiKey(): string {
  const apiKey = process.env.CURSOR_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("Missing CURSOR_API_KEY for local Cursor SDK chat.");
  }
  return apiKey;
}

function extractText(result: unknown): string {
  if (typeof result === "string") {
    return result;
  }
  if (result && typeof result === "object" && "result" in result) {
    const value = (result as { result?: unknown }).result;
    return typeof value === "string" ? value : JSON.stringify(value);
  }
  return JSON.stringify(result);
}

function extractJsonObject<T>(text: string): T {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const jsonText = fenced?.[1] ?? text;
  const start = jsonText.indexOf("{");
  const end = jsonText.lastIndexOf("}");
  if (start < 0 || end < start) {
    throw new Error("Cursor SDK response did not contain a JSON object.");
  }
  return JSON.parse(jsonText.slice(start, end + 1)) as T;
}

async function runCursorPrompt(prompt: string): Promise<string> {
  try {
    const result = await Agent.prompt(prompt, {
      apiKey: requireCursorApiKey(),
      model: { id: process.env.CURSOR_MODEL ?? DEFAULT_CURSOR_MODEL },
      local: { cwd: process.cwd() },
    });
    return extractText(result);
  } catch (error) {
    if (error instanceof CursorAgentError) {
      throw new Error(`Cursor SDK failed to start: ${error.message}`);
    }
    throw error;
  }
}

function buildPlanningPrompt(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): string {
  return `Jesteś lokalnym plannerem narzędzi dla czatu analitycznego EkstraBet.

Zasady:
- Odpowiadasz wyłącznie poprawnym JSON-em, bez markdown.
- Nie używaj żadnych narzędzi Cursor, terminala ani plików. Twoim zadaniem jest tylko zaplanować dozwolone narzędzia aplikacyjne.
- Czat może obsługiwać tylko pytania o dane sportowe dostępne w API EkstraBet.
- Użytkownik wybrał sport w GUI: ${sport.label} (sport_id=${sport.sport_id}). Wszystkie toolCalls muszą używać tego sport_id i nie wolno mieszać danych z innych sportów.
- Nie planuj zapisu, generowania danych, treningu modeli ani dowolnego HTTP/SQL.
- Jeżeli pytanie jest poza zakresem, zwróć pustą listę toolCalls i pole refusal.
- Najpierw rozpoznaj encję biznesową, czyli drużynę albo ligę. Dla drużyny użyj query/team_id; dla ligi nie zgaduj ID, jeżeli nie masz pewności.
- Sezon traktuj jako filtr wtórny. Nie dobieraj season_id tylko dlatego, że użytkownik go nie podał.
- Nie zatrzymuj się na samym search_teams/list_leagues, jeżeli użytkownik prosi o profil, tabelę, wykres albo analizę. W takim przypadku użyj narzędzia, które zwraca dane docelowe.
- Jeżeli użytkownik pyta o najnowsze albo ostatnie mecze drużyny, pomiń season_id. Narzędzie pobierze mecze bez filtra sezonu i posortuje je po dacie.
- Jeżeli użytkownik poda konkretny sezon lub rocznik tekstem, przekaż go jako season_years, nigdy nie zgaduj season_id.
- Akceptuj sezon zapisany przez użytkownika jako np. "2025/26", "2025/2026" albo "sezon 2025/26"; do narzędzia przekaż sam tekst sezonu w season_years.
- Jeżeli użytkownik pyta o tabelę ligi po nazwie i latach sezonu, użyj get_league_table z query i season_years. Nie używaj samego list_leagues.
- Jeżeli użytkownik pyta o profil drużyny po nazwie, użyj get_team_overview z query. Narzędzie samo dobierze najnowszy sezon z meczów drużyny, jeśli użytkownik nie podał sezonu.
- Dla profilu drużyny możesz pozwolić aplikacji pokazać tabelę i sensowny wykres domyślny. Nie musisz pytać użytkownika o każdą statystykę, jeśli prosi ogólnie o profil.
- Jeżeli użytkownik pyta o wykres ostatnich meczów drużyny i statystykę, użyj get_team_stat_series bez season_id, chyba że użytkownik wyraźnie zawęził sezon.
- Jeżeli użytkownik pyta, który zawodnik w danej drużynie ma najwięcej goli, asyst, strzałów, strzałów celnych, fauli albo żółtych kartek w ostatnich meczach drużyny, użyj get_team_player_stat_leader. To jest pytanie o statystyki indywidualne zawodników, nie o serię statystyk drużyny.
- Jeżeli użytkownik pyta o konkretnego zawodnika po nazwisku albo imieniu i nazwisku, użyj get_player_stat_summary z query, sport_id=${sport.sport_id}, stat, limitem i season_years, jeśli użytkownik podał sezon tekstem.
- Dla hokeja pytania o "minuty kar", "kary minutowe" albo "penalty minutes" mapuj na get_player_stat_summary ze stat="penalty_minutes".
- Dla hokeja pytania o strzały zawodnika mapuj na stat="sog", o czas na lodzie na stat="toi_minutes", o punkty na stat="points".
- Jeżeli użytkownik podaje dwie drużyny i prosi o przewidywanie wyniku albo dowolnej statystyki hipotetycznego meczu, użyj get_matchup_projection.
- Dla pytań o żółte kartki ustaw target="cards"; dla rożnych target="corners"; dla wyniku target="result"; dla strzałów celnych target="shots_on_target".
- Dla pytań o strzały celne zawodników ustaw stat="shots_on_target"; dla strzałów ogółem stat="shots"; dla fauli stat="fouls_conceded"; dla żółtych kartek stat="yellow_cards".
- Projekcja matchup jest statystyczna i wyjaśnialna. Nie przedstawiaj jej jako pewnego wyniku ani rekomendacji bukmacherskiej.

Dozwolone narzędzia:
${JSON.stringify(CHAT_TOOL_DESCRIPTIONS, null, 2)}

Format odpowiedzi:
{
  "toolCalls": [
    { "tool": "get_team_stat_series", "args": { "query": "Argentyna", "stat": "shots_on_target", "perspective": "team", "limit": 10 } }
  ],
  "refusal": null
}

Przykłady decyzji:
- "Pokaż tabelę ligi Ekstraklasa za sezon 2024/2025" -> get_league_table({ "query": "Ekstraklasa", "season_years": "2024/2025", "scope": "overall", "sport_id": ${sport.sport_id} })
- "Znajdź drużynę Legia Warszawa i pokaż jej profil dla najnowszego sezonu" -> get_team_overview({ "query": "Legia Warszawa", "limit": 10, "sport_id": ${sport.sport_id} })
- "Pokaż ostatnie 10 meczów Argentyny pod kątem strzałów celnych" -> get_team_stat_series({ "query": "Argentyna", "stat": "shots_on_target", "perspective": "team", "limit": 10, "sport_id": ${sport.sport_id} })
- "Który zawodnik w zespole Maroko ma najwięcej strzałów celnych na bramkę w ostatnich 5 meczach?" -> get_team_player_stat_leader({ "query": "Maroko", "stat": "shots_on_target", "limit": 5, "sport_id": ${sport.sport_id} })
- "Ile minut kar ma Connor McDavid?" -> get_player_stat_summary({ "query": "Connor McDavid", "stat": "penalty_minutes", "limit": 10, "sport_id": ${sport.sport_id} })
- "Podaj maksymalną liczbę strzałów na bramkę zawodnika McDavid w sezonie 2025/2026" -> get_player_stat_summary({ "query": "McDavid", "stat": "sog", "season_years": "2025/2026", "limit": 200, "sport_id": ${sport.sport_id} })
- "Lech Poznań vs Legia Warszawa, przewidź liczbę żółtych kartek" -> get_matchup_projection({ "team_a_query": "Lech Poznań", "team_b_query": "Legia Warszawa", "target": "cards", "limit": 10, "sport_id": ${sport.sport_id} })

Historia rozmowy:
${JSON.stringify(messages.slice(-6), null, 2)}`;
}

function buildSummaryPrompt(params: {
  messages: { role: string; content: string }[];
  toolResults: unknown[];
  sport: ChatSportContext;
}): string {
  return `Jesteś asystentem analitycznym EkstraBet. Opisz po polsku wynik na podstawie danych z read-only API.

Zasady:
- Odpowiadasz wyłącznie poprawnym JSON-em, bez markdown.
- Nie dopowiadaj danych spoza toolResults.
- Nie twórz samodzielnie punktów wykresu ani tabel. One zostaną wyrenderowane przez aplikację.
- Odpowiedź dotyczy sportu wybranego w GUI: ${params.sport.label} (sport_id=${params.sport.sport_id}).
- Jeżeli użytkownik pyta o maksimum, użyj pola maximum z danych narzędzia, a nie sumy ani średniej.
- Jeżeli dane są niepełne, dodaj ostrzeżenie.

Format odpowiedzi:
{
  "answerText": "krótka odpowiedź po polsku",
  "warnings": ["opcjonalne ostrzeżenia"]
}

Historia rozmowy:
${JSON.stringify(params.messages.slice(-6), null, 2)}

Wyniki narzędzi:
${JSON.stringify(params.toolResults, null, 2)}`;
}

function normalizePlan(plan: CursorPlan): CursorPlan {
  if (!Array.isArray(plan.toolCalls)) {
    return { toolCalls: [], refusal: plan.refusal };
  }

  const seenToolCalls = new Set<string>();
  const toolCalls: PlannedToolCall[] = [];
  for (const call of plan.toolCalls) {
    if (
      !call ||
      typeof call.tool !== "string" ||
      !call.args ||
      typeof call.args !== "object"
    ) {
      continue;
    }

    const key = `${call.tool}:${stableStringify(call.args)}`;
    if (seenToolCalls.has(key)) {
      continue;
    }
    seenToolCalls.add(key);
    toolCalls.push(call);
  }

  return {
    toolCalls: toolCalls.slice(0, 4),
    refusal: typeof plan.refusal === "string" ? plan.refusal : undefined,
  };
}

function uniqueDataSources(
  sources: ChatAnswer["dataSources"],
): ChatAnswer["dataSources"] {
  const seenSources = new Set<string>();
  return sources.filter((source) => {
    const key = `${source.label}:${source.endpoint}:${stableStringify(
      source.params ?? {},
    )}`;
    if (seenSources.has(key)) {
      return false;
    }
    seenSources.add(key);
    return true;
  });
}

export async function answerWithLocalCursorSdk(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  const planText = await runCursorPrompt(buildPlanningPrompt(messages, sport));
  const plan = normalizePlan(extractJsonObject<CursorPlan>(planText));

  if (plan.toolCalls.length === 0) {
    return {
      answerText:
        plan.refusal ??
        "Nie znalazłem bezpiecznego zapytania read-only, które obsłużyłoby tę prośbę.",
      chart: null,
      table: null,
      dataSources: [],
      warnings: ["Zapytanie nie zostało wykonane na API."],
    };
  }

  const toolResults = await runPlannedTools(plan.toolCalls, sport);
  const summaryText = await runCursorPrompt(
    buildSummaryPrompt({ messages, toolResults, sport }),
  );
  const summary = extractJsonObject<CursorSummary>(summaryText);
  const firstChart = toolResults.find((result) => result.chart)?.chart ?? null;
  const firstTable = toolResults.find((result) => result.table)?.table ?? null;

  return {
    answerText:
      summary.answerText ??
      toolResults.map((result) => result.summary).join(" "),
    chart: firstChart,
    table: firstTable,
    dataSources: uniqueDataSources(
      toolResults.flatMap((result) => result.dataSources),
    ),
    warnings: [
      ...new Set([
        ...toolResults.flatMap((result) => result.warnings),
        ...(Array.isArray(summary.warnings) ? summary.warnings : []),
      ]),
    ],
  };
}
