---
name: tech-project
description: Generate a technical design ("projekt techniczny") from a business need. The output translates what needs to be added or changed into concrete implementation details such as modules, classes, database tables, functions, APIs, data parsing, tests, and rollout notes. Use when the user provides a business requirement, asks for a technical project, or mentions "projekt techniczny".
---

# Tech Project

Ten skill tworzy **projekt techniczny** na podstawie potrzeby biznesowej.
Potrzeba biznesowa opisuje, **co** trzeba dodać lub zmienić oraz **dlaczego**.
Projekt techniczny opisuje, **jak** to zaimplementować w kodzie.

Przykład:

- Input: "Dodaj nowy moduł z zawodnikami Ekstraklasy".
- Output: projekt techniczny opisujący moduł, modele danych, klasy, tabele,
  funkcje pobierające i parsujące dane z API, walidację, testy oraz miejsca
  integracji z istniejącym systemem.

## Workflow

Skopiuj i śledź tę checklistę:

```
Postęp:
- [ ] Krok 1: Zrozum potrzebę biznesową
- [ ] Krok 2: Zbadaj istniejący kod i architekturę
- [ ] Krok 3: Zdefiniuj zakres projektu technicznego
- [ ] Krok 4: Zaprojektuj implementację
- [ ] Krok 5: Opisz testy i weryfikację
- [ ] Krok 6: Wygeneruj finalny projekt techniczny
```

### Krok 1: Zrozum potrzebę biznesową

- Wyodrębnij:
  - **cel biznesowy** — po co robimy zmianę,
  - **zakres funkcjonalny** — co użytkownik/system ma móc zrobić,
  - **dane wejściowe i wyjściowe** — skąd dane pochodzą i gdzie trafiają,
  - **ograniczenia** — wydajność, bezpieczeństwo, harmonogram, zależności,
  - **kryteria akceptacji** — kiedy uznajemy zadanie za ukończone.
- Jeśli potrzeba jest zbyt ogólna, zadaj pytania doprecyzowujące przed
  tworzeniem szczegółowego projektu.

### Krok 2: Zbadaj istniejący kod i architekturę

- Przeczytaj pliki, moduły i wzorce, których może dotyczyć zmiana.
- Sprawdź istniejące:
  - modele danych,
  - warstwy dostępu do danych,
  - integracje z API,
  - serwisy biznesowe,
  - endpointy lub interfejsy użytkownika,
  - testy i konfigurację.
- Projekt techniczny musi pasować do obecnej struktury repozytorium.
  Nie projektuj abstrakcji oderwanych od istniejącego kodu.

### Krok 3: Zdefiniuj zakres projektu technicznego

- Wskaż, co jest **nowym elementem**, a co jest **modyfikacją** istniejącego
  kodu.
- Opisz zakres pozytywny (co robimy) i zakres negatywny (czego nie robimy).
- Wypisz założenia i ryzyka, jeśli wpływają na implementację.
- Jeśli istnieje kilka sensownych rozwiązań, wybierz jedno i krótko uzasadnij.

### Krok 4: Zaprojektuj implementację

Projekt powinien być wystarczająco konkretny, aby skill `develop` mógł na jego
podstawie zaimplementować zadanie bez zgadywania.

Uwzględnij:

- docelowe pliki i moduły,
- nowe lub zmieniane klasy,
- nowe lub zmieniane funkcje/metody,
- sygnatury funkcji, argumenty, typy i zwracane wartości,
- tabele, migracje lub modele danych,
- integracje z zewnętrznymi API,
- sposób parsowania i walidacji danych,
- obsługę błędów i przypadków brzegowych,
- konfigurację i zmienne środowiskowe,
- zależności między elementami,
- wpływ na istniejące funkcje.

Dla kodu w Pythonie uwzględniaj regułę
[.cursor/rules/python-coding-style.mdc](../../rules/python-coding-style.mdc)
(m.in. kod po angielsku, komentarze po polsku, funkcje do 100 linii,
brak zbędnych spacji, PEP 8).

### Krok 5: Opisz testy i weryfikację

- Wskaż testy jednostkowe, integracyjne lub end-to-end do dodania/zmiany.
- Opisz przypadki pozytywne, negatywne i brzegowe.
- Dodaj sposób ręcznej weryfikacji, jeśli jest potrzebny.
- Wskaż komendy lint/test, jeśli repozytorium ma znane narzędzia.

### Krok 6: Wygeneruj finalny projekt techniczny

Użyj poniższego formatu:

```markdown
# Projekt techniczny: [nazwa zadania]

## 1. Kontekst biznesowy
[Dlaczego robimy zmianę i jaki problem rozwiązuje.]

## 2. Cel techniczny
[Co technicznie ma powstać po zakończeniu implementacji.]

## 3. Zakres
[Co wchodzi w zakres.]

## 4. Poza zakresem
[Czego świadomie nie robimy.]

## 5. Istniejący kontekst techniczny
[Jak wygląda obecny kod, moduły, zależności i miejsca integracji.]

## 6. Proponowana implementacja

### 6.1 Pliki i moduły
- `[ścieżka]` — [co dodać lub zmienić]

### 6.2 Modele, klasy i struktury danych
- `[ClassName]` — [odpowiedzialność, pola, relacje]

### 6.3 Funkcje i metody
- `[function_name(args) -> ReturnType]` — [odpowiedzialność i kontrakt]

### 6.4 Dane, tabele i migracje
- `[table_or_model_name]` — [kolumny/pola, typy, ograniczenia]

### 6.5 Integracje i API
- `[source_or_endpoint]` — [format danych, autoryzacja, błędy]

### 6.6 Walidacja i obsługa błędów
[Warunki brzegowe, wyjątki, retry, fallbacki.]

## 7. Testy
- [Test do dodania/zmiany i oczekiwany wynik]

## 8. Kryteria akceptacji
- [Mierzalny warunek akceptacji]

## 9. Ryzyka i otwarte pytania
- [Ryzyko lub pytanie]
```

## Checklist jakości projektu technicznego

```
- [ ] Potrzeba biznesowa została jasno opisana
- [ ] Cel techniczny jest jednoznaczny
- [ ] Zakres i poza zakresem są rozdzielone
- [ ] Projekt odnosi się do istniejącego kodu
- [ ] Wskazane są konkretne pliki/moduły do zmiany
- [ ] Wskazane są klasy, funkcje lub metody do implementacji
- [ ] Sygnatury i kontrakty są wystarczająco konkretne
- [ ] Dane, tabele, modele lub migracje są opisane, jeśli potrzebne
- [ ] Integracje z API są opisane, jeśli potrzebne
- [ ] Obsługa błędów i przypadki brzegowe są opisane
- [ ] Testy i kryteria akceptacji są zdefiniowane
- [ ] Projekt jest możliwy do przekazania do skilla develop
```

## Zasady

- **Najpierw zrozum, potem projektuj**: nie twórz projektu technicznego bez
  zrozumienia celu biznesowego i istniejącej architektury.
- **Konkret zamiast ogólników**: opisuj pliki, klasy, funkcje, tabele,
  sygnatury i kontrakty tak, aby implementacja nie wymagała zgadywania.
- **Spójność z repozytorium**: projekt ma pasować do obecnych wzorców i
  konwencji kodu.
- **Brak scope creep**: nie dodawaj funkcji, których nie uzasadnia potrzeba
  biznesowa.
- **Pytaj przy niejasności**: jeśli brakuje kluczowych informacji, zadaj pytanie
  zamiast ukrywać założenie w projekcie.
