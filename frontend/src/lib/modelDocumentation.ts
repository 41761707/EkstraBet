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
  "Gałąź cech statycznych: Elo, GAP atak/obrona, Czech (forma u siebie / " +
    "na wyjeździe), kontekst ligi, H2H, dni odpoczynku",
];

const SHARED_SEQUENCE_FEATURE_ENGINEERING = [
  "Okno historyczne - pobieranie danych z ostatnich 8 spotkań",
  "Ratingi Elo, GAP (atak/obrona) oraz Czech przed meczem " +
    "(patrz sekcja „Pojęcia kluczowe”)",
  "Statystyki meczowe w sekwencji: gole, xG, strzały, posiadanie, BTTS, suma goli",
  "Cechy statyczne: różnice Elo, dopasowanie atak–obrona, średnie ligowe, " +
    "H2H, dni odpoczynku, poziom ligi",
  "Skalowanie cech statycznych (StandardScaler) przed inferencją",
];

const SHARED_PREMATCH_LIMITATIONS = [
  "Predykcja edukacyjna — nie stanowi obietnicy skuteczności bukmacherskiej",
  "Jakość zależy od kompletności historii meczów i ratingów w oknie 8 spotkań",
];

/** Shared glossary of concepts shown on /o-modelach. */
export interface GlossaryEntry {
  id: "lstm" | "logit" | "softmax" | "elo" | "gap" | "czech";
  title: string;
  summary: string;
  details: string[];
}

export const MODEL_CONCEPT_GLOSSARY: readonly GlossaryEntry[] = [
  {
    id: "lstm",
    title: "LSTM — czytanie historii meczów",
    summary:
      "LSTM (Long Short-Term Memory) to rodzaj rekurencyjnej sieci neuronowej " +
      "zaprojektowany do pracy na sekwencjach. U nas sekwencją jest historia " +
      "ostatnich 8 meczów drużyny — sieć czyta je po kolei i buduje zwięzłe " +
      "„podsumowanie formy”, zamiast traktować każdy mecz osobno i niezależnie.",
    details: [
      "Zwykła sieć gęsta widzi tylko wektor cech „tu i teraz”. LSTM ma stan " +
        "ukryty, który przechodzi z meczu na mecz w oknie — dzięki temu kolejność " +
        "i kontekst historii mają znaczenie",
      "„Pamięć długa/krótka”: wewnątrz LSTM są bramki (forget / input / output), " +
        "które uczą się, co z poprzednich spotkań zachować, a co wyciszyć " +
        "(np. stary wynik vs. niedawna seria)",
      "Dual-LSTM w EkstraBet: osobna gałąź LSTM dla sekwencji gospodarzy i " +
        "osobna dla gości; ich wyjścia łączy się z gałęzią cech statycznych " +
        "(Elo, GAP, Czech, liga…), a dopiero potem Softmax (albo Softplus w " +
        "modelu goli) zwraca predykcję",
    ],
  },
  {
    id: "logit",
    title: "Logit — surowy wynik klasy przed Softmaxem",
    summary:
      "Logit $z_i$ to nieprzetworzona liczba, którą sieć przypisuje klasie $i$ " +
      "tuż przed Softmaxem. To jeszcze nie prawdopodobieństwo: może być ujemna, " +
      "większa od 1, a logity różnych klas nie muszą się sumować do niczego. " +
      "Im wyższy $z_i$ względem pozostałych, tym większe $P(i)$ po Softmaxie.",
    details: [
      "W 1X2 sieć zwraca trzy logity $z_1$, $z_X$, $z_2$; w BTTS dwa: " +
        "$z_{\\mathrm{tak}}$, $z_{\\mathrm{nie}}$",
      "Różnica logitów ma sens porządkowy: jeśli $z_{\\mathrm{tak}} \\gg " +
        "z_{\\mathrm{nie}}$, Softmax mocno faworyzuje „tak”; gdy są blisko " +
        "siebie — prawdopodobieństwa wychodzą zrównoważone",
      "Nazwa „logit” historycznie oznacza też $\\mathrm{logit}(p) = " +
        "\\ln\\dfrac{p}{1-p}$ (odwrotność sigmoidy). W sieciach klasyfikacyjnych " +
        "„logit” potocznie oznacza właśnie surowy wektor przed Softmaxem — " +
        "tak używamy tego słowa w dokumentacji EkstraBet",
      "Model goli nie operuje na logitach klas: głowa Softplus zwraca od razu " +
        "dodatnie $\\lambda_{\\mathrm{home}}$, $\\lambda_{\\mathrm{away}}$",
    ],
  },
  {
    id: "softmax",
    title: "Softmax — z logitów na prawdopodobieństwa",
    summary:
      "Softmax to funkcja, która zamienia surowe wyniki sieci (logity $z_i$) " +
      "na rozkład prawdopodobieństwa po klasach: każda wartość jest dodatnia " +
      "i wszystkie sumują się do 1. Używamy jej w modelach 1X2 i BTTS.",
    details: [
      "Wzór ogólny dla $C$ klas: " +
        "$$P(i) = \\dfrac{e^{z_i}}{\\sum_{j=1}^{C} e^{z_j}}$$ " +
        "Exponent $e^{z_i}$ wzmacnia różnice między logitami; mianownik " +
        "normalizuje, żeby $\\sum_i P(i) = 1$",
      "Dla BTTS ($C = 2$): " +
        "$$P(\\mathrm{tak}) = \\dfrac{e^{z_{\\mathrm{tak}}}}" +
        "{e^{z_{\\mathrm{tak}}} + e^{z_{\\mathrm{nie}}}},\\quad " +
        "P(\\mathrm{nie}) = 1 - P(\\mathrm{tak})$$ " +
        "co w wyjściu modelu zapisujemy jako $p_{\\mathrm{yes}}$, " +
        "$p_{\\mathrm{no}}$",
      "Dla wyniku 1X2 ($C = 3$) Softmax daje " +
        "$p_{\\mathrm{home}}$, $p_{\\mathrm{draw}}$, $p_{\\mathrm{away}}$",
      "Predykcja dyskretna to $\\mathrm{argmax}_i\\,P(i)$ — klasa z " +
        "najwyższym prawdopodobieństwem; bliskie wartości $P$ oznaczają " +
        "niepewność modelu, nie „pewniak”",
      "Model goli nie używa Softmaxa — tam Softplus gwarantuje dodatnie " +
        "lambdy Poissona $\\lambda > 0$",
    ],
  },
  {
    id: "elo",
    title: "Elo — ogólna siła drużyny",
    summary:
      "Klasyczny ranking siły (z szachów), zaadaptowany do piłki nożnej. " +
      "Jedna liczba na drużynę: im wyższa, tym silniejsza drużyna względem " +
      "pozostałych w historii zakończonych meczów.",
    details: [
      "Start: zwykle 1500 punktów; ligi drugiego poziomu startują niżej " +
        "(współczynnik ~0,9)",
      "Przed meczem model liczy wynik oczekiwany gospodarzy na skali " +
        "logistycznej z premią własnego boiska dla gospodarza spotkania (~80 punktów): " +
        "$E_{\\mathrm{home}} = \\dfrac{1}{1 + 10^{(R_{\\mathrm{away}} - R_{\\mathrm{home}} - H)/400}}$",
      "Po meczu porównujemy wynik rzeczywisty (wygrana = 1, remis = 0,5, " +
        "porażka = 0) z oczekiwanym; różnica × współczynnik $K$ × mnożnik " +
        "różnicy bramek aktualizuje rating obu drużyn",
      "Do modelu trafia Elo sprzed kick-offu (bez przecieku wyniku meczu)",
    ],
  },
  {
    id: "gap",
    title: "GAP — atak i obrona",
    summary:
      "Dwuwymiarowy rating: osobno siła ataku $A$ i profil obrony $D$. " +
      "W przeciwieństwie do Elo nie sprowadza drużyny do jednej liczby — " +
      "lepiej opisuje, czy zespół raczej dużo strzela, czy łatwo traci bramki.",
    details: [
      "Start: $A_0 = 1$, $D_0 = 1$; współczynnik uczenia $\\alpha = 0{,}2$",
      "Przed aktualizacją liczymy oczekiwane gole (dolny próg $0{,}05$): " +
        "$$\\hat{g}_{\\mathrm{home}} = \\max\\!\\left(" +
        "\\dfrac{A_{\\mathrm{home}} + D_{\\mathrm{away}}}{2},\\,0{,}05\\right)" +
        "$$ $$\\hat{g}_{\\mathrm{away}} = \\max\\!\\left(" +
        "\\dfrac{A_{\\mathrm{away}} + D_{\\mathrm{home}}}{2},\\,0{,}05\\right)$$",
      "Po meczu z wynikiem $g_{\\mathrm{home}}{:}g_{\\mathrm{away}}$ " +
        "aktualizujemy obie drużyny (wartości nieujemne): " +
        "$$A'_{\\mathrm{home}} = \\max\\!\\bigl(" +
        "A_{\\mathrm{home}} + \\alpha\\,(g_{\\mathrm{home}} - \\hat{g}_{\\mathrm{home}})" +
        ",\\,0\\bigr)$$ " +
        "$$D'_{\\mathrm{home}} = \\max\\!\\bigl(" +
        "D_{\\mathrm{home}} + \\alpha\\,(g_{\\mathrm{away}} - \\hat{g}_{\\mathrm{away}})" +
        ",\\,0\\bigr)$$ " +
        "$$A'_{\\mathrm{away}} = \\max\\!\\bigl(" +
        "A_{\\mathrm{away}} + \\alpha\\,(g_{\\mathrm{away}} - \\hat{g}_{\\mathrm{away}})" +
        ",\\,0\\bigr)$$ " +
        "$$D'_{\\mathrm{away}} = \\max\\!\\bigl(" +
        "D_{\\mathrm{away}} + \\alpha\\,(g_{\\mathrm{home}} - \\hat{g}_{\\mathrm{home}})" +
        ",\\,0\\bigr)$$",
      "Interpretacja: strzelisz więcej niż $\\hat{g}$ → rośnie $A$; " +
        "stracisz więcej niż oczekiwano → rośnie $D$ (wyższe $D$ przeciwnika " +
        "zwiększa Twoje $\\hat{g}$ — $D$ to raczej „łatwość do strzelenia”, " +
        "nie klasyczna „twardość obrony”)",
      "W cechach modelu: `gap_attack_before`, `gap_defense_before` oraz " +
        "dopasowania typu atak gospodarzy kontra obrona gości; nazwa GAP wywodzi się bezpośrednio z pracy naukowej (TODO: Odnaleźć prace i wrzucić źródła)",
    ],
  },
  {
    id: "czech",
    title: "Czech — forma u siebie / na wyjeździe",
    summary:
      "Ostatnia forma z podziałem na boisko: osobne okno ostatnich $n \\le 8$ " +
      "meczów u siebie i na wyjeździe. Nazwa „Czech” to wewnętrzna etykieta " +
      "systemu w projekcie, ze względu na jego pochodzenie (podejście pochodzi z pracy naukowej czeskich badaczy, TODO: Odnaleźć prace i wrzucić źródła), nie oficjalny ranking zewnętrzny.",
    details: [
      "Po meczu dopisujemy wynik do okna stadionu: gospodarze -> ich seria " +
        "„u siebie”, goście -> ich seria „na wyjeździe”. Dla gospodarzy: " +
        "$$w = \\mathbf{1}[g_{\\mathrm{home}} > g_{\\mathrm{away}}],\\quad " +
        "GF = g_{\\mathrm{home}},\\quad GA = g_{\\mathrm{away}}$$ " +
        "dla gości analogicznie z ich perspektywy " +
        "($w = \\mathbf{1}[g_{\\mathrm{away}} > g_{\\mathrm{home}}]$)",
      "Z okna $n$ spotkań w danej sekcji liczymy (pusty start -> zera): " +
        "$$\\mathrm{win\\_pct} = \\dfrac{1}{n}\\sum_{i=1}^{n} w_i$$ " +
        "$$\\overline{GF} = \\dfrac{1}{n}\\sum_{i=1}^{n} GF_i,\\quad " +
        "\\overline{GA} = \\dfrac{1}{n}\\sum_{i=1}^{n} GA_i$$ " +
        "$$\\sigma_{GF} = \\sqrt{\\dfrac{1}{n}\\sum_{i=1}^{n}" +
        "(GF_i - \\overline{GF})^2},\\quad " +
        "\\sigma_{GA} = \\sqrt{\\dfrac{1}{n}\\sum_{i=1}^{n}" +
        "(GA_i - \\overline{GA})^2}$$",
      "Do modelu przedmeczowego trafia m.in. `home_czech_win_rate` / " +
        "`away_czech_win_rate` — $\\mathrm{win\\_pct}$ gospodarzy u siebie vs " +
        "gości na wyjeździe (oraz średnie/odchylenia goli z tego samego okna)",
      "Dzięki podziałowi na mecze wyjazdowe i domowe model widzi, że ta sama drużyna może być " +
        "mocna u siebie, a słaba na wyjazdach",
    ],
  },
];

/** Rating subset — Elo / GAP / Czech (without architecture concepts). */
export const RATING_GLOSSARY: readonly GlossaryEntry[] =
  MODEL_CONCEPT_GLOSSARY.filter(
    (entry) =>
      entry.id !== "lstm" &&
      entry.id !== "logit" &&
      entry.id !== "softmax",
  );

export const MODEL_DOCUMENTATION: readonly ModelDocumentation[] = [
  {
    name: "FOOTBALL_RESULT_V2",
    displayName: "Wynik meczu (1X2) v2",
    version: "2.0.0",
    phase: "pre_match",
    purpose:
      "Klasyfikuje przed meczem wynik końcowy na trzy wykluczające się " +
      "klasy rynku 1X2: wygrana gospodarzy (1), remis (X) albo wygrana gości (2).",
    algorithm:
      "Dual-LSTM: osobne LSTM czytają sekwencje 8 meczów gospodarzy i gości, " +
      "gęsta gałąź przetwarza cechy statyczne (Elo, GAP, kontekst ligi…). " +
      "Połączenie gałęzi daje trzy logity $z_1$, $z_X$, $z_2$; Softmax " +
      "zamienia je na prawdopodobieństwa " +
      "$$P(i) = \\dfrac{e^{z_i}}{\\sum_j e^{z_j}}$$ " +
      "tak że $p_{\\mathrm{home}} + p_{\\mathrm{draw}} + p_{\\mathrm{away}} = 1$.",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych dla pary drużyn",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja dual-LSTM — trzy logity (siła każdej klasy 1 / X / 2)",
      "Softmax zamienia logity na prawdopodobieństwa: " +
        "$$P(i) = \\dfrac{e^{z_i}}{\\sum_j e^{z_j}}$$ " +
        "co daje $p_{\\mathrm{home}}$, $p_{\\mathrm{draw}}$, " +
        "$p_{\\mathrm{away}}$ (suma = 1)",
      "Wybór klasy $\\mathrm{argmax}_i\\,P(i)$ → zdarzenia " +
        "result_home / result_draw / result_away",
    ],
    outputs: [
      "$p_{\\mathrm{home}}$ — prawdopodobieństwo wygranej gospodarzy (klasa 1)",
      "$p_{\\mathrm{draw}}$ — prawdopodobieństwo remisu (klasa X)",
      "$p_{\\mathrm{away}}$ — prawdopodobieństwo wygranej gości (klasa 2)",
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
      "Klasyfikacja 1X2 — model nie przewiduje dokładnego wyniku bramkowego " +
        "ani wysokości wygranej",
      "Softmax rozdziela 100% masy między trzy klasy; bliskie prawdopodobieństwa " +
        "oznaczają dużą niepewność, nie „pewny typ”",
    ],
  },
  {
    name: "FOOTBALL_BTTS_V2",
    displayName: "Obie drużyny strzelą (BTTS) v2",
    version: "2.0.0",
    phase: "pre_match",
    purpose:
      "Klasyfikuje przed meczem rynek BTTS (obie drużyny strzelą): czy " +
      "gospodarze i goście zdobędą po co najmniej jednym golu (tak / nie).",
    algorithm:
      "Ten sam szkielet dual-LSTM co wynik 1X2, ale Softmax na 2 klasy. " +
      "Etykieta treningowa: 1 gdy home_goals $> 0$ i away_goals $> 0$, " +
      "inaczej 0. Logity $z_{\\mathrm{tak}}$, $z_{\\mathrm{nie}}$ przechodzą " +
      "przez Softmax: " +
      "$$P(\\mathrm{tak}) = \\dfrac{e^{z_{\\mathrm{tak}}}}" +
      "{e^{z_{\\mathrm{tak}}} + e^{z_{\\mathrm{nie}}}}$$ " +
      "analogicznie $P(\\mathrm{nie})$; oba sumują się do 1.",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja dual-LSTM — dwa logity (siła klas tak / nie)",
      "Softmax zamienia logity na prawdopodobieństwa: " +
        "$$P(\\mathrm{tak}) = \\dfrac{e^{z_{\\mathrm{tak}}}}" +
        "{e^{z_{\\mathrm{tak}}} + e^{z_{\\mathrm{nie}}}}$$ " +
        "$$P(\\mathrm{nie}) = \\dfrac{e^{z_{\\mathrm{nie}}}}" +
        "{e^{z_{\\mathrm{tak}}} + e^{z_{\\mathrm{nie}}}}$$ " +
        "w wyjściu: $p_{\\mathrm{yes}} = P(\\mathrm{tak})$, " +
        "$p_{\\mathrm{no}} = P(\\mathrm{nie})$",
      "Wybór klasy $\\mathrm{argmax}\\,P$ → zdarzenia btts_yes / btts_no",
    ],
    outputs: [
      "$p_{\\mathrm{yes}}$ — prawdopodobieństwo, że obie drużyny strzelą " +
        "co najmniej jednego gola",
      "$p_{\\mathrm{no}}$ — prawdopodobieństwo, że przynajmniej jedna " +
        "drużyna nie strzeli",
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
      "BTTS to tylko fakt gola po obu stronach — bez wysokości wyniku " +
        "(1:0 i 4:3 to ta sama klasa „nie” / „tak”)",
      "Model nie modeluje liczby goli; do sumy i dokładnego wyniku służy " +
        "osobny model Poissona",
    ],
  },
  {
    name: "FOOTBALL_GOALS_POISSON_V1",
    displayName: "Gole (Poisson) v1",
    version: "1.0.0",
    phase: "pre_match",
    purpose:
      "Szacuje przed meczem średnią liczbę goli gospodarzy i gości " +
      "(intensywności Poissona λ_home i λ_away), a z rozkładu wyprowadza " +
      "przedziały sumy goli (0…6+), rynek powyżej/poniżej 2.5 oraz " +
      "najbardziej prawdopodobne dokładne wyniki.",
    algorithm:
      "Ten sam szkielet dual-LSTM co modele 1X2 i BTTS (osobne LSTM dla " +
      "sekwencji gospodarzy i gości + gałąź cech statycznych), ale zamiast " +
      "Softmaxa głowa Softplus zwraca dwie dodatnie lambdy. Każda drużyna " +
      "ma własny rozkład Poissona: " +
      "$$P(K = k) = \\dfrac{e^{-\\lambda}\\,\\lambda^{k}}{k!}$$ " +
      "gdzie $\\lambda$ to oczekiwana liczba goli, a $k$ to konkretna liczba " +
      "bramek. Przy założeniu niezależności prawdopodobieństwo wyniku $h{:}a$ " +
      "to iloczyn $P_{\\mathrm{home}}(h)\\cdot P_{\\mathrm{away}}(a)$ — " +
      "z tego powstaje macierz wyników, z której składamy rynki.",
    inputs: [...SHARED_SEQUENCE_INPUTS],
    featureEngineering: [...SHARED_SEQUENCE_FEATURE_ENGINEERING],
    predictionSteps: [
      "Zbudowanie sekwencji home/away i wektora cech statycznych",
      "Skalowanie cech statycznych scalerem z artefaktu release",
      "Inferencja sieci — Softplus zwraca $\\lambda_{\\mathrm{home}}$ i " +
        "$\\lambda_{\\mathrm{away}}$ (oczekiwane gole)",
      "Dla każdej drużyny: rozkład Poissona $P(k\\mid\\lambda)$ dla " +
        "$k = 0\\ldots 4$ oraz ogon $5+$ (reszta masy prawdopodobieństwa, " +
        "max_goals=5)",
      "Macierz wyników: iloczyn zewnętrzny rozkładów home × away " +
        "(niezależne Poissony), potem normalizacja do sumy 1",
      "Z macierzy: przedziały sumy goli $0\\ldots 5$ i $6+$, " +
        "powyżej/poniżej 2.5 oraz ranking najpewniejszych dokładnych " +
        "wyników (np. 1:1, 2:1)",
    ],
    outputs: [
      "$\\lambda_{\\mathrm{home}}$ / $\\lambda_{\\mathrm{away}}$ — oczekiwana " +
        "liczba goli gospodarzy i gości",
      "total_buckets — $P(\\mathrm{suma} = 0\\ldots 5)$ oraz " +
        "$P(\\mathrm{suma} \\ge 6)$",
      "over_25 / under_25 — $P(\\mathrm{suma} \\ge 3)$ / " +
        "$P(\\mathrm{suma} \\le 2)$ (powyżej/poniżej 2.5)",
      "top_exact_scores — ranking najpewniejszych dokładnych wyników $h{:}a$",
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
      "Niezależność Poissona: gole gospodarzy i gości liczone osobno — " +
        "w rzeczywistości bywają skorelowane (np. otwarta gra po stracie gola)",
      "Ogon 5+ / 6+ składa rzadkie wysokie wyniki w jedną klasę — to " +
        "aproksymacja, nie pełny rozkład nieskończonego ogona",
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
