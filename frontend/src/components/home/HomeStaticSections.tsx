import Link from "next/link";
import { HomeSection } from "@/components/home/HomeSection";

const offerCards = [
  {
    title: "📊 Kącik statystyczny",
    description:
      "Szczegółowe analizy osiągnięć modeli oraz charakterystyk ligowych.",
    href: "/stats",
  },
  {
    title: "💸 Kącik bukmacherski",
    description: "Rekomendacje zakładów oparte na modelach predykcyjnych.",
    href: "/bets",
  },
  {
    title: "⚽ Baza lig",
    description: "Dostęp do szczegółowych danych oraz analiz z wielu lig.",
    href: "#ligy",
  },
  {
    title: "🏆 Wiele dyscyplin",
    description:
      "System nie ogranicza się do jednego sportu — obecnie hokej i piłka nożna, w planach koszykówka i esport.",
  },
];

const roadmapItems = [
  "Rozszerzenie o inne dyscypliny sportowe (np. koszykówka) oraz o esport (CS2, LOL)",
  "Dodanie analizy w czasie rzeczywistym w oparciu o dane użytkownika",
  "Utworzenie API do łatwiejszej integracji z systemem dla developerów",
  "Utworzenie profili użytkownika do personalizacji filtrów",
];

const faqItems = [
  {
    question: "Jak działają modele predykcyjne w Ekstrabet?",
    answer:
      "Nasze modele wykorzystują uczenie maszynowe do analizy historycznych danych meczowych, statystyk drużyn i zawodników. Algorytmy analizują wzorce w danych i na tej podstawie przewidują prawdopodobieństwa różnych wyników meczów. Więcej informacji zostanie opublikowanych w specjalnej sekcji „Działanie modeli”.",
  },
  {
    question: "Ile lig i dyscyplin sportowych obsługuje system?",
    answer:
      "Obecnie Ekstrabet obsługuje ponad 30 lig piłkarskich z całego świata oraz hokej na lodzie (NHL). Pełna lista obsługiwanych lig znajduje się w sekcji „Lista obsługiwanych lig” na stronie głównej. W planach mamy dodanie koszykówki oraz esportu.",
  },
  {
    question: "Czy mogę używać prognoz do realnych zakładów bukmacherskich?",
    answer:
      "Ekstrabet ma charakter edukacyjny i badawczy. Wszystkie symulacje zakładów są hipotetyczne i służą wyłącznie do testowania modeli. Nie zachęcamy do uczestnictwa w grach hazardowych.",
  },
  {
    question: "Skąd pochodzą dane używane w analizach?",
    answer:
      "Wszystkie dane pochodzą z publicznych źródeł: statystyki piłkarskie z flashscore.pl i opta.com, dane hokejowe z oficjalnego NHL API.",
  },
  {
    question: "Jaka jest dokładność prognoz systemu?",
    answer:
      "Dokładność modeli różni się w zależności od ligi i typu prognozy. Szczegółowe statystyki wydajności każdego modelu znajdziesz w „Kąciku statystycznym”. Pamiętaj, że żaden model nie jest w 100% dokładny.",
  },
];

export function HomeStaticSections() {
  return (
    <>
      <HomeSection title="Co oferuje strona" defaultOpen>
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-slate-300">
            Ekstrabet łączy analizę sportową z rekomendacjami opartymi na
            modelach predykcyjnych. Poniżej znajdziesz główne sekcje serwisu.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {offerCards.map((card) => (
              <div
                key={card.title}
                className="rounded-lg border border-slate-700/80 bg-slate-800/50 p-4"
              >
                <h3 className="text-sm font-semibold text-sky-300">
                  {card.href ? (
                    <Link
                      href={card.href}
                      className="transition hover:text-sky-200"
                    >
                      {card.title}
                    </Link>
                  ) : (
                    card.title
                  )}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  {card.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </HomeSection>

      <HomeSection title="Statystyki zawodników">
        <p className="mb-4 text-sm leading-relaxed text-slate-300">
          Sprawdź szczegółowe statystyki i analizy zawodników z różnych
          dyscyplin sportowych:
        </p>
        <ul className="space-y-2 text-sm text-slate-400">
          <li>
            <Link
              href="/players"
              className="text-sky-300 transition hover:text-sky-200"
            >
              ⚽ Piłka nożna — Zawodnicy
            </Link>
          </li>
          <li>🏒 NHL — Zawodnicy (wkrótce w nowej wersji)</li>
          <li>🏀 NBA — Zawodnicy (wkrótce w nowej wersji)</li>
        </ul>
      </HomeSection>

      <HomeSection title="O projekcie">
        <div className="space-y-4">
          <h3 className="border-b border-sky-500/40 pb-2 text-lg font-semibold text-sky-300">
            Ekstrabet — Inteligentny Asystent Bukmacherski
          </h3>
          <p className="text-sm leading-relaxed">
            Ekstrabet to zaawansowane narzędzie analityczne stworzone dla
            miłośników sportu i zakładów bukmacherskich. Wykorzystując uczenie
            maszynowe i statystykę, pomaga w podejmowaniu świadomych decyzji przy
            obstawianiu meczów piłkarskich.
          </p>
          <div className="rounded-lg border-l-4 border-sky-400 bg-slate-800/60 p-4">
            <p className="font-medium text-white">Główne założenia projektu:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-300">
              <li>Analiza historycznych danych meczowych</li>
              <li>Predykcja wyników spotkań</li>
              <li>Identyfikacja wartościowych zakładów</li>
              <li>Wizualizacja prezentowanych danych</li>
            </ul>
          </div>
        </div>
      </HomeSection>

      <HomeSection title="Planowane rozszerzenia">
        <h3 className="mb-4 text-base font-semibold text-sky-300">
          Rozwój projektu
        </h3>
        <ol className="space-y-3">
          {roadmapItems.map((item, index) => (
            <li key={item} className="flex items-start gap-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-400 text-xs font-bold text-slate-950">
                {index + 1}
              </span>
              <span className="leading-relaxed text-slate-300">{item}</span>
            </li>
          ))}
        </ol>
      </HomeSection>

      <HomeSection title="FAQ — Najczęściej zadawane pytania">
        <div className="space-y-5">
          {faqItems.map((item) => (
            <div key={item.question}>
              <h3 className="text-sm font-semibold text-white">
                {item.question}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                {item.answer}
              </p>
            </div>
          ))}
        </div>
      </HomeSection>

      <HomeSection title="Kontakt">
        <h3 className="text-base font-semibold text-sky-300">
          Skontaktuj się z autorem
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">
          Masz pytania lub sugestie dotyczące projektu? Chętnie je poznam!
        </p>
        <a
          href="https://41761707.github.io/"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-block rounded-md bg-sky-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-300"
        >
          Odwiedź stronę autora
        </a>
        <p className="mt-4 text-sm text-slate-500">Autor projektu: Radikey</p>
        <p className="text-sm text-slate-500">
          Projekt rozwijany przez pasjonatów dla pasjonatów
        </p>
      </HomeSection>
    </>
  );
}
