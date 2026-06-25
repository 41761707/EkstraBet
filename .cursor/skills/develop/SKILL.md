---
name: develop
description: Implement tasks based on a technical design ("projekt techniczny"). The design describes the business context (why) and the implementation approach (where and how), including classes and functions to implement. Use when the user provides a technical design, asks to implement a task from a design document, or mentions a "projekt techniczny".
---

# Develop

Ten skill realizuje implementację zadania na podstawie **projektu technicznego**.
Projekt techniczny to opis tego, jak zrealizować wskazane zadanie. Zawiera:

- **Kontekst biznesowy** — dlaczego wykonujemy daną modyfikację.
- **Sposób realizacji** — gdzie (pliki, moduły, warstwy) i w jaki sposób
  (klasy, funkcje, interfejsy do zaimplementowania).

Celem skilla jest **prawidłowa implementacja zgodna z projektem** — nie mniej
(brak elementów) i nie więcej (zbędny zakres).

## Workflow

Skopiuj i śledź tę checklistę:

```
Postęp:
- [ ] Krok 1: Wczytaj i zrozum projekt techniczny
- [ ] Krok 2: Zmapuj zakres na konkretne pliki/klasy/funkcje
- [ ] Krok 3: Zweryfikuj zgodność z istniejącym kodem
- [ ] Krok 4: Zaimplementuj zgodnie z projektem
- [ ] Krok 5: Zweryfikuj implementację (lint, testy, zgodność)
- [ ] Krok 6: Podsumuj wykonaną pracę względem projektu
```

### Krok 1: Wczytaj i zrozum projekt techniczny

- Projekt może być podany jako plik w repozytorium lub wklejony w wiadomości.
  Jeśli to plik — wczytaj go w całości.
- Wyodrębnij i wynotuj:
  - **cel biznesowy** (dlaczego),
  - **lokalizacje zmian** (które pliki/moduły/warstwy),
  - **artefakty do implementacji** (klasy, funkcje, metody, sygnatury, typy),
  - **zależności i kontrakty** (interfejsy, modele danych, API),
  - **warunki brzegowe i wymagania** (walidacje, błędy, wydajność).
- Jeśli w projekcie czegoś brakuje lub coś jest sprzeczne — zadaj pytanie
  zamiast zgadywać. Nie wymyślaj zakresu, którego nie ma w projekcie.

### Krok 2: Zmapuj zakres na konkretne pliki/klasy/funkcje

- Sporządź listę: dla każdego artefaktu z projektu wskaż docelowy plik i
  nazwę (klasa/funkcja/metoda).
- Zaznacz, co jest **nowe**, a co jest **modyfikacją** istniejącego kodu.
- Sprawdź, czy nazwy z projektu nie kolidują z istniejącymi w kodzie.

### Krok 3: Zweryfikuj zgodność z istniejącym kodem

- Przeczytaj istniejące pliki, których dotyczy projekt, zanim zaczniesz pisać.
- Dopasuj się do konwencji projektu (struktura, wzorce, nazewnictwo, warstwy).
- Nie wprowadzaj zmian wykraczających poza projekt techniczny (no scope creep).
  Jeśli widzisz potrzebę dodatkowej zmiany — zaproponuj ją osobno.

### Krok 4: Zaimplementuj zgodnie z projektem

- Implementuj dokładnie te klasy/funkcje, które opisuje projekt, z zadanymi
  sygnaturami i typami.
- Zachowaj wskazane kontrakty (nazwy, argumenty, zwracane typy, wyjątki).
- Dla kodu w Pythonie stosuj regułę
  [.cursor/rules/python-coding-style.mdc](../../rules/python-coding-style.mdc)
  (m.in. kod po angielsku, komentarze po polsku, funkcje do 100 linii,
  brak zbędnych spacji, PEP 8).
- Trzymaj się zasady: implementacja ma odpowiadać projektowi 1:1.

### Krok 5: Zweryfikuj implementację

- Uruchom linter dla zmienionych plików i napraw zgłoszone błędy.
- Uruchom istniejące testy powiązane ze zmienianym obszarem; jeśli projekt
  wymaga nowych testów — dodaj je.
- Przejdź checklistę zgodności (sekcja poniżej).

### Krok 6: Podsumuj pracę względem projektu

- Wypisz, które artefakty z projektu zostały zaimplementowane i gdzie.
- Wskaż ewentualne odstępstwa wraz z uzasadnieniem oraz otwarte pytania.

## Checklist zgodności z projektem

```
- [ ] Wszystkie klasy z projektu zaimplementowane
- [ ] Wszystkie funkcje/metody z projektu zaimplementowane
- [ ] Sygnatury (argumenty, typy, zwracane wartości) zgodne z projektem
- [ ] Kontrakty i interfejsy zachowane
- [ ] Warunki brzegowe i walidacje obsłużone
- [ ] Brak zmian wykraczających poza zakres projektu
- [ ] Lint bez błędów
- [ ] Testy przechodzą
- [ ] Cel biznesowy projektu zrealizowany
```

## Zasady

- **Wierność projektowi**: projekt techniczny jest źródłem prawdy. Realizuj go
  dokładnie — bez pomijania elementów i bez dodawania niezamówionego zakresu.
- **Pytaj przy niejasności**: braki lub sprzeczności w projekcie zgłaszaj,
  zamiast zgadywać.
- **Czytaj przed pisaniem**: zawsze poznaj istniejący kod, którego dotyczy
  zmiana, zanim go zmodyfikujesz.
- **Spójność**: dopasuj się do konwencji i wzorców obecnych w repozytorium.
