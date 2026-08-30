import type { ReactNode } from "react";
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
    title: " 🏃🏻 Statystyki zawodników",
    description: "Prezentacja statystyk zawodników z poszczególnych dyscyplin objętych badaniem",
    href: "/players",
  },
  {
    title: "⚽ Baza lig",
    description: "Dostęp do szczegółowych danych oraz analiz z wielu lig.",
    href: "#ligi",
  },
  {
    title: "🤖 Chatbot",
    description: "Chatbot umożliwiający użytkownikowi interakcję z systemem poprzez chat",
    href: "/chat",
  },
  {
    title: "🏆 Wiele dyscyplin",
    description:
      "System nie ogranicza się do jednego sportu — obecnie hokej i piłka nożna, w planach koszykówka i esport.",
  },
];

const roadmapItems = [
  "Rozszerzenie o inne dyscypliny sportowe (np. koszykówka) oraz o esport (CS2, LOL)",
  "Dodanie analizy meczów w oparciu o dodatkowe dane: informacje o zawodnikach i kursach bukmacherskich",
  "Rozwinięcie profili użytkowników o personalizację filtrów",
  "Wprowadzenie generatora kuponów w oparciu o charakterstyki wybrane przez użytkownika",
  "Wizualizacja siły drużyny w oparciu o dane historyczne",
  "Informacje o osiągnięciach druzyn w każdej z połów meczu osobno (teraz pobieramy tylko dane z końca meczu)"
];

const faqItems: { question: string; answer: ReactNode }[] = [
  {
    question: "Jak działają modele predykcyjne w Ekstrabet?",
    answer: (
      <>
        Modele wykorzystują uczenie maszynowe do analizy historycznych
        danych meczowych, statystyk drużyn i zawodników. Algorytmy analizują
        wzorce w danych i na tej podstawie przewidują prawdopodobieństwa
        różnych zdarzeń meczowych. Aktualnie modele przewidują występowanie takich zdarzeń jak
        liczba bramek w spotkaniu, czy obie drużyny strzelą gola oraz jakim rezultatem zakończy się spotkanie.
        Szczegółowy opis aktualnych modeli, cech,
        ograniczeń, kluczowych pojęć oraz przykład predykcji znajdziesz na
        stronie{" "}
        <Link
          href="/o-modelach"
          className="text-accent-text transition hover:text-accent-text-hover"
        >
          O modelach
        </Link>
        .
      </>
    ),
  },
  {
    question: "Ile lig i dyscyplin sportowych obsługuje system?",
    answer:
      "Obecnie Ekstrabet obsługuje ponad 30 lig piłkarskich z całego świata oraz największą hokejową ligę świata (NHL). Pełna lista obsługiwanych lig znajduje się w sekcji „Lista obsługiwanych lig” na stronie głównej. W planach mamy dodanie koszykówki oraz esportu.",
  },
  {
    question: "Czy mogę używać prognoz do realnych zakładów bukmacherskich?",
    answer:
      "Ekstrabet ma charakter edukacyjny i badawczy. Wszystkie symulacje zakładów są hipotetyczne i służą wyłącznie do testowania modeli. Strona w żaden sposób nie zachęca do uczestnictwa w grach hazardowych, kursy bukmacherskie stosują środek weryfikacji dokładności predykcji modeli.",
  },
  {
    question: "Jaka jest dokładność prognoz systemu?",
    answer:
      "Dokładność modeli różni się w zależności od ligi i typu prognozy. Szczegółowe statystyki wydajności każdego modelu znajdziesz w „Kąciku statystycznym”. Pamiętaj, że żaden model nie jest w 100% dokładny i wszystkie prognozy są hipotetyczne.",
  },
  {
    question: "Jak zaprosić znajomego do korzystania z Ekstrabet?",
    answer: "Serwer aktualnie działa w trybie invite-only - zaproszenie do serwisu można uzyskać poprzez kontakt z autorem projektu. Więcej w sekcji 'Kontakt'"
  }
];

export function HomeStaticSections() {
  return (
    <>
      <HomeSection title="Co oferuje strona">
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted">
            Ekstrabet łączy analizę sportową z rekomendacjami opartymi na
            modelach predykcyjnych. Poniżej znajdziesz główne sekcje serwisu.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {offerCards.map((card) => (
              <div
                key={card.title}
                className="rounded-lg border border-border bg-surface-muted p-4"
              >
                <h3 className="text-sm font-semibold text-accent-text">
                  {card.href ? (
                    <Link
                      href={card.href}
                      className="transition hover:text-accent-text-hover"
                    >
                      {card.title}
                    </Link>
                  ) : (
                    card.title
                  )}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  {card.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </HomeSection>

      <HomeSection title="O projekcie">
        <div className="space-y-4">
          <h3 className="border-b border-accent/40 pb-2 text-lg font-semibold text-accent-text">
            Ekstrabet — Asystent Statystyczno-Predykcyjny
          </h3>
          <p className="text-sm leading-relaxed">
            Ekstrabet to zaawansowane narzędzie analityczne stworzone dla
            miłośników sportu. Wykorzystując uczenie maszynowe i statystykę,
            próbuje przewidywać występowanie wybranych zdarzeń na piłkarskich boiskach, 
            hokejowych lodowiskach czy też koszykarskich halach.
          </p>
          <div className="rounded-lg border-l-4 border-accent bg-surface-muted p-4">
            <p className="font-medium text-text">Główne założenia projektu:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted">
              <li>Analiza historycznych danych meczowych</li>
              <li>Predykcja wyników spotkań</li>
              <li>Identyfikacja wartościowych zakładów</li>
              <li>Wizualizacja prezentowanych danych</li>
            </ul>
          </div>
        </div>
      </HomeSection>

      <HomeSection title="Planowane rozszerzenia">
        <h3 className="mb-4 text-base font-semibold text-accent-text">
          Rozwój projektu
        </h3>
        <ol className="space-y-3">
          {roadmapItems.map((item, index) => (
            <li key={item} className="flex items-start gap-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-on-accent">
                {index + 1}
              </span>
              <span className="leading-relaxed text-muted">{item}</span>
            </li>
          ))}
        </ol>
      </HomeSection>

      <HomeSection title="FAQ — Najczęściej zadawane pytania">
        <div className="space-y-5">
          {faqItems.map((item) => (
            <div key={item.question}>
              <h3 className="text-sm font-semibold text-text">
                {item.question}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {item.answer}
              </p>
            </div>
          ))}
        </div>
      </HomeSection>

      <HomeSection title="Kontakt">
        <h3 className="text-base font-semibold text-accent-text">
          Skontaktuj się z autorem
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Masz pytania lub sugestie dotyczące projektu? Chętnie je poznam!
        </p>
        <a
          href="https://41761707.github.io/"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-block rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition hover:bg-accent-hover"
        >
          Odwiedź stronę autora
        </a>
        <p className="mt-4 text-sm text-subtle">Autor projektu: Radikey</p>
        <p className="text-sm text-subtle">
          Projekt rozwijany przez pasjonatów dla pasjonatów
        </p>
      </HomeSection>
    </>
  );
}
