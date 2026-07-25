import type { ModelDetailsResponse } from "@/types/api";

/** Names of the five models documented on the /o-modelach page. */
export type CurrentModelName =
  | "FOOTBALL_RESULT_V2"
  | "FOOTBALL_BTTS_V2"
  | "FOOTBALL_GOALS_POISSON_V1"
  | "FOOTBALL_PLAYED_BETTER_V1"
  | "FOOTBALL_PLAYED_BETTER_NOXG_V1";

export type ModelPhase = "pre_match" | "post_match";

/**
 * Offline validation metric from a release artifact.
 * Not the live analytics accuracy (outcomes may be unsettled).
 */
export interface ModelValidationMetric {
  key: string;
  label: string;
  /** Null when no published release metrics exist. */
  value: number | null;
  artifactVersion: string | null;
  note: string;
}

export interface ModelDocumentation {
  name: CurrentModelName;
  displayName: string;
  version: string;
  phase: ModelPhase;
  purpose: string;
  algorithm: string;
  inputs: string[];
  featureEngineering: string[];
  predictionSteps: string[];
  outputs: string[];
  metrics: ModelValidationMetric[];
  limitations: string[];
}

/** Documentation optionally enriched with live API metadata. */
export interface DocumentedModelView extends ModelDocumentation {
  apiDetails: ModelDetailsResponse | null;
  availabilityNote: string | null;
}

const VALIDATION_SCOPE_NOTE =
  "Metryka walidacyjna (offline) z artefaktu release — nie jest bieżącą " +
  "skutecznością produkcyjną (outcome może być nierozliczone).";

const NO_RELEASE_METRICS_NOTE =
  "Brak opublikowanego artefaktu release z metrykami — wartości nie są " +
  "szacowane na stronie.";

const SHARED_SEQUENCE_INPUTS = [
  "Sekwencja 8 wcześniejszych meczów gospodarzy (cechy meczowe i ratingi)",
  "Sekwencja 8 wcześniejszych meczów gości (cechy meczowe i ratingi)",
  "Gałąź cech statycznych: Elo, GAP atak/obrona, Czech win rate, kontekst ligi, H2H, dni odpoczynku",
];

const SHARED_SEQUENCE_FEATURE_ENGINEERING = [
  "Okno historyczne window_size=8 dla obu drużyn (FutureEventsFeatureBuilder)",
  "Ratingi Elo, GAP (atak/obrona) oraz Czech przed meczem",
  "Statystyki meczowe w sekwencji: gole, xG, strzały, posiadanie, BTTS, suma goli",
  "Cechy statyczne: różnice Elo, dopasowanie atak–obrona, średnie ligowe, H2H, rest days, league tier",
  "Skalowanie cech statycznych (StandardScaler) przed inferencją",
];

const SHARED_PREMATCH_LIMITATIONS = [
  "Predykcja edukacyjna — nie stanowi obietnicy skuteczności bukmacherskiej",
  "Jakość zależy od kompletności historii meczów i ratingów w oknie 8 spotkań",
  "Metryki na stronie pochodzą z walidacji offline; nie mylić ich z analytics 0% przy nierozliczonym outcome",
];

export const MODEL_DOCUMENTATION: readonly ModelDocumentation[] = [
  {
    name: "FOOTBALL_RESULT_V2",
    displayName: "Wynik meczu (1X2) v2",
    version: "2.0.0",
    phase: "pre_match",
    purpose:
      "Szacuje prawdopodobieństwa wyniku końcowego przed meczem: wygrana " +
      "gospodarzy, remis lub wygrana gości (rynek 1X2).",
    algorithm:
      "Dual-LSTM: osobne LSTM dla sekwencji gospodarzy i gości oraz gęsta " +
      "gałąź cech statycznych, połączone Softmaxem na 3 klasy.",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych dla pary drużyn",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja dual-LSTM (FOOTBALL_RESULT_V2)",
      "Normalizacja wyjścia Softmax do p_home, p_draw, p_away",
      "Mapowanie argmax na zdarzenia result_home / result_draw / result_away",
    ],
    outputs: [
      "p_home — prawdopodobieństwo wygranej gospodarzy",
      "p_draw — prawdopodobieństwo remisu",
      "p_away — prawdopodobieństwo wygranej gości",
    ],
    metrics: [
      {
        key: "accuracy",
        label: "Accuracy (walidacja)",
        value: 0.481,
        artifactVersion: "2.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
      {
        key: "log_loss",
        label: "Log loss (walidacja)",
        value: 1.029,
        artifactVersion: "2.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
    ],
    limitations: [
      ...SHARED_PREMATCH_LIMITATIONS,
      "Model klasyfikuje wynik, nie przewiduje dokładnego wyniku bramkowego",
    ],
  },
  {
    name: "FOOTBALL_BTTS_V2",
    displayName: "Obie drużyny strzelą (BTTS) v2",
    version: "2.0.0",
    phase: "pre_match",
    purpose:
      "Szacuje przed meczem, czy obie drużyny strzelą co najmniej jednego gola " +
      "(Both Teams To Score — tak/nie).",
    algorithm:
      "Ten sam szkielet dual-LSTM co wynik 1X2, z Softmaxem na 2 klasy " +
      "(BTTS nie / BTTS tak).",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja dual-LSTM (FOOTBALL_BTTS_V2)",
      "Normalizacja wyjścia do p_no i p_yes",
      "Mapowanie argmax na zdarzenia btts_no / btts_yes",
    ],
    outputs: [
      "p_yes — prawdopodobieństwo, że obie drużyny strzelą",
      "p_no — prawdopodobieństwo, że przynajmniej jedna nie strzeli",
    ],
    metrics: [
      {
        key: "accuracy",
        label: "Accuracy (walidacja)",
        value: 0.542,
        artifactVersion: "2.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
      {
        key: "log_loss",
        label: "Log loss (walidacja)",
        value: 0.687,
        artifactVersion: "2.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
    ],
    limitations: [
      ...SHARED_PREMATCH_LIMITATIONS,
      "BTTS nie rozróżnia wysokości wyniku — tylko fakt gola po obu stronach",
    ],
  },
  {
    name: "FOOTBALL_GOALS_POISSON_V1",
    displayName: "Gole (Poisson) v1",
    version: "1.0.0",
    phase: "pre_match",
    purpose:
      "Modeluje oczekiwane gole gospodarzy i gości (λ) i wyprowadza z nich " +
      "bucket sumy goli, Over/Under 2.5 oraz exact score.",
    algorithm:
      "Dual-LSTM ze wspólnym backbone’em, wyjście Softplus na dwie dodatnie " +
      "intensywności Poissona (λ_home, λ_away); rynki z macierzy wyników.",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja modelu Poissona — dwie lambdy (λ_home, λ_away)",
      "Złożenie macierzy wyników (niezależne Poissony, fold przy max_goals=5)",
      "Wyprowadzenie bucketów 0…6+, Over/Under 2.5 oraz top exact scores",
    ],
    outputs: [
      "lambda_home / lambda_away — oczekiwane gole",
      "total_buckets — prawdopodobieństwa sumy goli 0…5 i 6+",
      "over_25 / under_25 — rynki Over/Under 2.5",
      "top_exact_scores — najprawdopodobniejsze dokładne wyniki",
    ],
    metrics: [
      {
        key: "poisson_nll",
        label: "Poisson NLL (walidacja)",
        value: 2.901,
        artifactVersion: "1.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
      {
        key: "home_goals_mae",
        label: "MAE goli gospodarzy",
        value: 0.943,
        artifactVersion: "1.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
      {
        key: "away_goals_mae",
        label: "MAE goli gości",
        value: 0.851,
        artifactVersion: "1.0.0",
        note: VALIDATION_SCOPE_NOTE,
      },
    ],
    limitations: [
      ...SHARED_PREMATCH_LIMITATIONS,
      "Założenie niezależności Poissona upraszcza zależność goli obu drużyn",
      "Ogon 5+ / 6+ jest złożony — rzadkie wysokie wyniki są aproksymowane",
    ],
  },
  {
    name: "FOOTBALL_PLAYED_BETTER_V1",
    displayName: "Ocena jakości gry (z xG) v1",
    version: "1.0.0",
    phase: "post_match",
    purpose:
      "Po meczu ocenia, która drużyna zagrała lepiej na podstawie statystyk " +
      "pomeczowych (w tym xG), niezależnie od samego rezultatu bramkowego.",
    algorithm:
      "HistGradientBoostingClassifier z kalibracją isotoniczną " +
      "(CalibratedClassifierCV); wejściem są różnice i udziały statystyk.",
    inputs: [
      "Statystyki pomeczowe z tabeli matches (wymagane dodatnie xG obu drużyn)",
      "Strzały, strzały celne, posiadanie, rzuty rożne (wymagane)",
      "Opcjonalnie: wolne, spalone, faule, kartki (imputowane medianą)",
    ],
    featureEngineering: [
      "FootballMatchStatsFeatureBuilder: różnice (diff) i udziały (share)",
      "Cechy xG: xg_diff, total_xg, home_xg_share, xg_per_shot_*",
      "Cechy bez goli jako wejścia modelu (include_goals_as_features=false)",
      "Polityka braków: reject wymaganych, impute opcjonalnych; require_positive_xg=true",
      "Pipeline: SimpleImputer → StandardScaler → kalibrowany HGB",
    ],
    predictionSteps: [
      "Filtrowanie meczów z kompletnymi wymaganymi statystykami i dodatnim xG",
      "Zbudowanie wektora cech tabularnych (diff/share)",
      "Inferencja kalibrowanego HistGradientBoosting",
      "Trzy prawdopodobieństwa: home / draw / away played better",
      "Zapis oceny jakości gry (nie zakładu przedmeczowego)",
    ],
    outputs: [
      "home_played_better_probability",
      "draw_probability",
      "away_played_better_probability",
    ],
    metrics: [
      {
        key: "unavailable",
        label: "Metryki release",
        value: null,
        artifactVersion: null,
        note: NO_RELEASE_METRICS_NOTE,
      },
    ],
    limitations: [
      "Wymaga dodatniego xG — mecze bez xG są odrzucane (patrz wariant NOXG)",
      "Ocena post-match nie zmienia historycznych predykcji przedmeczowych",
      "Etykiety treningowe są słabe (weighted formula), nie eksperckie",
      "Brak commitowanych metryk release — nie prezentujemy szacunków",
      "Charakter edukacyjny — nie jest sygnałem bukmacherskim",
    ],
  },
  {
    name: "FOOTBALL_PLAYED_BETTER_NOXG_V1",
    displayName: "Ocena jakości gry (bez xG) v1",
    version: "1.0.0",
    phase: "post_match",
    purpose:
      "Wariant post-match bez xG: ocenia jakość gry na podstawie pozostałych " +
      "statystyk, gdy xG jest niedostępne lub celowo wykluczone.",
    algorithm:
      "Ten sam HistGradientBoosting z kalibracją isotoniczną, bez cech xG " +
      "(exclude_positive_xg / brak xG w feature_config).",
    inputs: [
      "Statystyki pomeczowe bez xG: strzały, strzały celne, posiadanie, rożne",
      "Opcjonalnie: wolne, spalone, faule, kartki (imputowane)",
      "Celowo pomija xG — działa przy braku expected goals",
    ],
    featureEngineering: [
      "FootballMatchStatsFeatureBuilder bez kolumn xG",
      "Różnice i udziały: possession, shots, SOG, corners, cards, fouls…",
      "exclude_positive_xg=true, require_positive_xg=false",
      "Pipeline: SimpleImputer → StandardScaler → kalibrowany HGB",
    ],
    predictionSteps: [
      "Filtrowanie meczów z wymaganymi statystykami (bez wymogu xG)",
      "Zbudowanie cech tabularnych bez xG",
      "Inferencja kalibrowanego HistGradientBoosting (wariant NOXG)",
      "Trzy prawdopodobieństwa oceny jakości gry",
    ],
    outputs: [
      "home_played_better_probability",
      "draw_probability",
      "away_played_better_probability",
    ],
    metrics: [
      {
        key: "unavailable",
        label: "Metryki release",
        value: null,
        artifactVersion: null,
        note: NO_RELEASE_METRICS_NOTE,
      },
    ],
    limitations: [
      "Bez xG ocena opiera się na proxy jakości (strzały, posiadanie itd.)",
      "Ocena post-match nie przelicza predykcji przedmeczowych",
      "Brak commitowanych metryk release — nie prezentujemy szacunków",
      "Charakter edukacyjny — nie jest sygnałem bukmacherskim",
    ],
  },
];

const DOCUMENTATION_BY_NAME: ReadonlyMap<CurrentModelName, ModelDocumentation> =
  new Map(MODEL_DOCUMENTATION.map((entry) => [entry.name, entry]));

const REQUIRED_DOCUMENTATION_KEYS: readonly (keyof ModelDocumentation)[] = [
  "name",
  "displayName",
  "version",
  "phase",
  "purpose",
  "algorithm",
  "inputs",
  "featureEngineering",
  "predictionSteps",
  "outputs",
  "metrics",
  "limitations",
] as const;

/** Ordered list of documented current model names. */
export const CURRENT_MODEL_NAMES: readonly CurrentModelName[] =
  MODEL_DOCUMENTATION.map((entry) => entry.name);

export function getModelDocumentation(
  name: CurrentModelName,
): ModelDocumentation {
  const documentation = DOCUMENTATION_BY_NAME.get(name);
  if (!documentation) {
    throw new Error(`Missing documentation for model ${name}`);
  }
  return documentation;
}

export function getModelsByPhase(phase: ModelPhase): ModelDocumentation[] {
  return MODEL_DOCUMENTATION.filter((entry) => entry.phase === phase);
}

export function hasCompleteDocumentation(
  documentation: ModelDocumentation,
): boolean {
  for (const key of REQUIRED_DOCUMENTATION_KEYS) {
    const value = documentation[key];
    if (value === undefined || value === null) {
      return false;
    }
    if (typeof value === "string" && value.trim().length === 0) {
      return false;
    }
    if (Array.isArray(value) && value.length === 0) {
      return false;
    }
  }
  return true;
}

/**
 * Merge static docs with optional API details.
 * Missing API never hides documentation content.
 */
export function toDocumentedModelView(
  documentation: ModelDocumentation,
  apiDetails: ModelDetailsResponse | null,
): DocumentedModelView {
  if (!apiDetails) {
    return {
      ...documentation,
      apiDetails: null,
      availabilityNote: "Status dostępności nie został pobrany",
    };
  }

  const isActive = apiDetails.active === 1;
  return {
    ...documentation,
    apiDetails,
    availabilityNote: isActive ? null : "Model nieaktywny w API",
  };
}
