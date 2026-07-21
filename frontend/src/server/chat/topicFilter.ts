/**
 * Hard topic allowlist (Etap 5): reject obvious off-topic before tool-calling.
 * Soft prompt rules remain for borderline cases.
 */

export const OFF_TOPIC_REFUSAL_TEXT =
  "Mogę pomagać tylko w analizie danych sportowych dostępnych w EkstraBet " +
  "(ligi, drużyny, mecze, zawodnicy, statystyki, kursy i predykcje). " +
  "To pytanie jest poza zakresem.";

/** Sygnały, że pytanie dotyczy domeny sportowej / EkstraBet (stem + odmiany). */
const IN_SCOPE_PATTERN =
  /\b(lig\w*|league\w*|drużyn\w*|team\w*|mecz\w*|match\w*|zawodnik\w*|player\w*|tabel\w*|standing\w*|form\w*|gol\w*|goal\w*|strzał\w*|shot\w*|asyst\w*|assist\w*|kartk\w*|card\w*|rożn\w*|corner\w*|sezon\w*|season\w*|kurs\w*|odd(?:s)?\b|predykc\w*|prediction\w*|statystyk\w*|analit\w*|piłk\w*|hokej\w*|hockey\w*|koszyk\w*|basket\w*|ekstraklas\w*|bundesliga\w*|premier\s*league|serie\s*a|la\s*liga|match_?id|sport\w*|wynik\w*|bramk\w*|faul\w*|foul\w*|penalt\w*|kar(?:a|y|nych|ze)\b|toi\b|punkt\w*|points?\b|skład\w*|lineup\w*|trener\w*|coach\w*|transfer\w*|porówn\w*|compar\w*|projekcj\w*|projection\w*|seri\w*|series\b)/i;

/** Oczywisty off-topic — bez sygnału sportowego odmawiamy twardo. */
const OFF_TOPIC_PATTERN =
  /\b(przepis(?:y)?\s+na|recipe\b|pogod\w*|weather\s+forecast|napisz\s+(mi\s+)?kod|write\s+(me\s+)?(some\s+)?code|javascript\s+function|python\s+script|bitcoin\b|kryptowalut\w*|crypto\s+trading|inwestycj\w*\s+w\s+akcj\w*|stock\s+market|polityk\w*|wybor\w*|election\w*|diagnosz\w*|lekarstw\w*|jak\s+ugotować|how\s+to\s+cook|opowiedz\s+kawał|tell\s+me\s+a\s+joke|homework\s+essay|rozprawk\w*|horoskop\w*|astrology\b)/i;

/**
 * Returns true when the user message is clearly outside the sports analytics scope.
 * In-scope keywords win over off-topic patterns (e.g. weather at a match).
 */
export function isClearlyOffTopic(message: string): boolean {
  const text = message.trim();
  if (!text) {
    return false;
  }
  if (IN_SCOPE_PATTERN.test(text)) {
    return false;
  }
  return OFF_TOPIC_PATTERN.test(text);
}

/** Last user message content, if any. */
export function lastUserMessageContent(
  messages: { role: string; content: string }[],
): string | null {
  const lastUser = [...messages]
    .reverse()
    .find((item) => item.role === "user");
  return lastUser?.content ?? null;
}
