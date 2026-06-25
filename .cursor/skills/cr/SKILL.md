---
name: cr
description: Review an implementation against a technical design ("projekt techniczny") and the architecture of the whole application. Verifies whether classes, functions, contracts, tests, and code style match the architect's intent. Use when the user asks for CR, code review, implementation verification, or review against a technical design.
---

# CR

Ten skill służy do **weryfikacji poprawności implementacji danego zadania**.
Review bazuje na projekcie technicznym, istniejącym kodzie oraz zasadach
panujących w aplikacji.

Celem jest sprawdzenie, czy implementacja:

- realizuje intencję architekta opisaną w projekcie technicznym,
- zawiera wszystkie wymagane klasy, funkcje, metody, kontrakty i testy,
- jest spójna z architekturą całej aplikacji,
- nie zawiera nieuzasadnionych zmian wykraczających poza zakres,
- spełnia standardy jakości i stylu kodu, w tym reguły dla Pythona.

## Workflow

Skopiuj i śledź tę checklistę:

```
Postęp:
- [ ] Krok 1: Wczytaj projekt techniczny i zakres zmian
- [ ] Krok 2: Zrozum istniejącą aplikację i kontekst architektoniczny
- [ ] Krok 3: Przeanalizuj implementację i diff
- [ ] Krok 4: Porównaj implementację z projektem technicznym
- [ ] Krok 5: Oceń poprawność architektoniczną i jakość kodu
- [ ] Krok 6: Zweryfikuj testy, lint i przypadki brzegowe
- [ ] Krok 7: Przygotuj wynik code review
```

### Krok 1: Wczytaj projekt techniczny i zakres zmian

- Projekt techniczny jest źródłem prawdy dla intencji architekta.
- Wczytaj projekt w całości, jeśli jest dostępny jako plik.
- Wyodrębnij:
  - cel biznesowy,
  - cel techniczny,
  - wymagane pliki i moduły,
  - wymagane klasy, funkcje i metody,
  - sygnatury, typy, kontrakty i interfejsy,
  - modele danych, tabele, migracje lub konfigurację,
  - integracje z API,
  - wymagane testy i kryteria akceptacji.
- Jeśli projektu technicznego brakuje, review może być wykonane tylko względem
  intencji z opisu zadania i istniejących wzorców aplikacji. Zaznacz to w
  wyniku jako ograniczenie.

### Krok 2: Zrozum istniejącą aplikację i kontekst architektoniczny

Ten skill musi **bardzo mocno skupiać się na znajomości całej aplikacji**.
Nie oceniaj zmian wyłącznie lokalnie.

- Przeczytaj pliki zmienione w implementacji.
- Przeczytaj powiązane moduły, klasy, interfejsy, modele i testy.
- Ustal, jak dana część aplikacji jest zwykle projektowana:
  - podział na warstwy,
  - nazewnictwo,
  - przepływ danych,
  - obsługa błędów,
  - konfiguracja,
  - testowanie,
  - zależności zewnętrzne.
- Sprawdź, czy implementacja nie łamie istniejących kontraktów ani zachowań.
- Jeśli zmiana dotyka wielu obszarów, prześledź przepływ end-to-end.

### Krok 3: Przeanalizuj implementację i diff

- Przejrzyj wszystkie zmienione, dodane i usunięte pliki.
- Sprawdź, czy zmiany są potrzebne do realizacji projektu technicznego.
- Oddziel:
  - zmiany wymagane przez projekt,
  - zmiany pomocnicze uzasadnione implementacją,
  - zmiany zbędne lub ryzykowne,
  - potencjalne regresje.
- Nie oceniaj tylko tego, czy kod "działa". Oceń też, czy powinien istnieć w
  takim kształcie.

### Krok 4: Porównaj implementację z projektem technicznym

Zweryfikuj punkt po punkcie:

- czy wszystkie klasy z projektu istnieją,
- czy wszystkie funkcje i metody zostały zaimplementowane,
- czy sygnatury są zgodne z projektem,
- czy argumenty, typy i zwracane wartości są zgodne z kontraktem,
- czy tabele, modele lub migracje odpowiadają projektowi,
- czy integracje z API są zgodne z opisanym formatem i obsługą błędów,
- czy walidacje i przypadki brzegowe zostały uwzględnione,
- czy implementacja realizuje kryteria akceptacji,
- czy nie dodano zakresu, którego projekt nie przewiduje.

Jeśli implementacja świadomie odbiega od projektu, oceń:

- czy odstępstwo było potrzebne,
- czy jest technicznie poprawne,
- czy powinno zostać opisane jako aktualizacja projektu technicznego.

### Krok 5: Oceń poprawność architektoniczną i jakość kodu

- Sprawdź zgodność z architekturą aplikacji i lokalnymi wzorcami.
- Sprawdź, czy odpowiedzialności są umieszczone we właściwych warstwach.
- Szukaj duplikacji, niepotrzebnych abstrakcji i zbyt dużych funkcji.
- Oceń czytelność, prostotę, spójność nazewnictwa i obsługę błędów.
- Dla kodu w Pythonie stosuj regułę
  [.cursor/rules/python-coding-style.mdc](../../rules/python-coding-style.mdc)
  (m.in. kod po angielsku, komentarze po polsku, funkcje do 100 linii,
  brak zbędnych spacji, PEP 8).
- Zwracaj uwagę na błędy składniowe, typy, importy, formatowanie i martwy kod.

### Krok 6: Zweryfikuj testy, lint i przypadki brzegowe

- Sprawdź, czy testy pokrywają wymagania z projektu technicznego.
- Sprawdź przypadki pozytywne, negatywne i brzegowe.
- Jeśli możesz, uruchom powiązane testy i lint.
- Jeśli nie możesz uruchomić testów, zaznacz to w wyniku review.
- Brak testu dla istotnej logiki traktuj jako realne ryzyko, nie detal.

### Krok 7: Przygotuj wynik code review

Wynik review powinien zaczynać się od najważniejszych problemów.
Nie zaczynaj od podsumowania, jeśli są błędy.

Użyj tego formatu:

```markdown
## Findings

- **[Severity] [Obszar]** Krótki opis problemu.
  `ścieżka/do/pliku`
  Dlaczego to problem względem projektu technicznego, architektury lub zasad
  kodowania.
  Sugerowana poprawka.

## Zgodność z projektem technicznym

- [ ] Wszystkie klasy zgodne z projektem
- [ ] Wszystkie funkcje/metody zgodne z projektem
- [ ] Sygnatury i kontrakty zgodne z projektem
- [ ] Kryteria akceptacji spełnione
- [ ] Brak nieuzasadnionego scope creep

## Weryfikacja

- Lint: [uruchomiono / nie uruchomiono / wynik]
- Testy: [uruchomiono / nie uruchomiono / wynik]
- Ograniczenia review: [jeśli istnieją]

## Podsumowanie

[Krótka ocena końcowa, dopiero po findings.]
```

Severity:

- **Critical** - błąd blokujący poprawne działanie, bezpieczeństwo, dane lub
  zgodność z kluczowym kontraktem.
- **High** - istotna niezgodność z projektem, architekturą lub przypadkiem
  brzegowym.
- **Medium** - problem jakościowy, testowy lub utrzymaniowy, który warto
  naprawić przed zakończeniem zadania.
- **Low** - drobna niespójność, czytelność, nazewnictwo lub styl.

Jeśli nie ma istotnych problemów, napisz jasno: `No blocking issues found`.
Następnie wskaż pozostałe ryzyka, ograniczenia review i brakujące testy, jeśli
istnieją.

## Checklist review

```
- [ ] Projekt techniczny został wczytany i zrozumiany
- [ ] Zmienione pliki zostały przeanalizowane
- [ ] Powiązane części aplikacji zostały sprawdzone
- [ ] Wszystkie wymagane klasy zostały zweryfikowane
- [ ] Wszystkie wymagane funkcje/metody zostały zweryfikowane
- [ ] Sygnatury, typy i kontrakty są zgodne z projektem
- [ ] Architektura i podział odpowiedzialności są poprawne
- [ ] Zmiany są potrzebne i mieszczą się w zakresie zadania
- [ ] Kod spełnia lokalne zasady stylu
- [ ] Kod Python spełnia .cursor/rules/python-coding-style.mdc
- [ ] Testy pokrywają kluczowe ścieżki i przypadki brzegowe
- [ ] Lint/testy zostały uruchomione albo ograniczenie zostało opisane
```

## Zasady

- **Najpierw kontekst aplikacji**: nie rób review bez zrozumienia powiązanych
  modułów i istniejących wzorców.
- **Projekt techniczny jako źródło prawdy**: oceniaj implementację względem
  intencji architekta, nie tylko względem lokalnego kodu.
- **Zero domysłów przy brakach**: jeśli projekt lub implementacja są niejasne,
  nazwij niejasność i wskaż, co trzeba doprecyzować.
- **Findings przed podsumowaniem**: najpierw pokaż ryzyka i błędy, potem
  dopiero ogólną ocenę.
- **Nie naprawiaj w trakcie review**, chyba że użytkownik wyraźnie poprosi o
  poprawienie znalezionych problemów.
