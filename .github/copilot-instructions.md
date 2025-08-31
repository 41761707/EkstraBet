# Instrukcję Copilota dla projektu Ekstrabet

## Omówienie projektu 
- Projekt składa się z kilku kluczowym komponentów:
  - `web_code/`: Aplikacja webowa Streamlit do interakcji z użytkownikiem, nawigacji i wizualizacji przedstawionych danych (front-end).
  - `model_code/`: Moduły Pythona do przygotowania danych, obliczania ratingów, trenowania modeli, prognozowania i testowania.
  - `api_code/`: Moduły do obsługi API, umożliwiające komunikację między front-endem a backendem.
  - `graphics_code/`: Moduły do generowania wykresów i wizualizacji danych.
  - `scrapper_code/`: Moduły do scrapowania danych z zewnętrznych źródeł.
- Wszystkie dane są ładowane z bazy danych za pomocą niestandardowych zapytań przez `db_module`.

## Architektura i przepływ danych
- Aplikacja webowa (`Home.py`) zapewnia nawigację i interfejs użytkownika, dynamicznie generując linki do każdej ligi na podstawie danych z bazy.
- Pipeline modelu (`main.py` w `model_code/`) zarządza:
  - Ekstrakcją i przygotowaniem danych (`dataprep_module`)
  - Obliczaniem ratingów (`ratings_module`)
  - Trenowaniem modeli i prognozowaniem (`model_module`, `prediction_module`)
  - Zarządzaniem konfiguracją (`config_manager`)
  - Testowaniem (`test_module`)
- Przepływ danych: baza danych → przygotowanie danych → obliczanie ratingów → trenowanie/prognozowanie modeli → wyniki/testowanie.

## Przepływ pracy dewelopera
- Aby uruchomić aplikację webową: `streamlit run web_code/Home.py`.
- Aby uruchomić trening/prognozowanie/testowanie modeli:
  - `python main.py <model_type> <mode> <load_weights> <model_name>` z folderu `model_code/`.
    - Przykład: `python main.py winner train 1 alpha_0_0_result`
    - Tryby: `train`, `predict`, `test`
    - Przy uruchamianiu zapoznać się z parametrami opcjonalnymi oraz ich sposobem wykorzystywania!
- Zarządzanie konfiguracją odbywa się za pomocą argumentów wiersza poleceń i `ConfigManager`.
- Wszystkie połączenia z bazą danych muszą być zamykane po użyciu.

## Wzorce specyficzne dla projektu
- Konfiguracja modeli i typy ratingów są obsługiwane za pomocą zagnieżdżonych słowników i przekazywane przez pipeline.
- Cały interfejs użytkownika i dokumentacja są w języku polskim; zachowaj spójność językową.
- Niestandardowy HTML/CSS jest wstrzykiwany w Streamlit za pomocą `unsafe_allow_html=True`.

## Punkty integracyjne
- Wszystkie operacje na bazie danych używają `db_module`.
- Wagi modeli i konfiguracje są zapisywane/ładowane z katalogów `model_{model_type}_dev/`.
- Zewnętrzne źródła danych, które należy zacytować: `flashscore.pl`, `opta.com`, `NHL API`, `dailyfaceoff.com`.

## Konwencje
- Używaj Pandas do wszystkich wyników zapytań SQL i manipulacji danymi.
- Pliki stron w `pages/` powinny stosować wzorzec nazewnictwa `{LeagueName}.py` i być odwoływane w `Home.py`.
- Moduły pipeline modelu powinny być importowane i używane jak w `main.py`.

## Przykład: Workflow Treningu Modelu
1. Przygotuj konfigurację i bazę danych.
2. Uruchom: `python main.py winner train 0 alpha_0_0_result`
3. Pipeline wyodrębni dane, obliczy ratingi, wytrenuje model i zapisze wyniki/konfiguracje.

## Przykład: Dodawanie Nowej Ligi
1. Dodaj nową ligę do bazy danych (tabela `leagues`).
2. Utwórz nowy plik w `pages/` nazwany na cześć ligi (np. `pages/Serie A.py`).
3. Nowa liga automatycznie pojawi się w nawigacji, jeśli `active=1` w bazie danych.

---
W przypadku pytań lub niejasnych konwencji, zapoznaj się z `Home.py`, `main.py` i schematem bazy danych lub zapytaj autora projektu.

# Zasady Pisania Kodu w Pythonie dla Ekstrabet

## 1. Styl kodowania

- Stosuj konwencję PEP8 (wcięcia 4 spacje, czytelne nazwy zmiennych, spójność stylu).
- Nazwy zmiennych, funkcji i klas powinny być opisowe i jednoznaczne.
- Przy generowaniu kodu unikaj dodawania zbędnych pustych linii - zmniejszają czytelność kodu
- Przy generowaniu printów nie korzystaj z emotikonek
- Funkcje i klasy dokumentuj za pomocą docstringów w stylu Google lub NumPy.
- Komentarze typu docstring powinny zawierać sekcje "Args" oraz "Returns".
- Komentarze pisz wyłącznie po polsku, wyjaśniając logikę, założenia i nietypowe rozwiązania. Przy komentowaniu staraj się zachować zdrowy balans - nie każda linijka wymaga komentarza

## 2. Struktura projektu

- Moduły dziel według funkcjonalności (np. web_code, model_code).
- Każdy plik powinien mieć nagłówek z krótkim opisem przeznaczenia.
- Funkcje pomocnicze, które będą wykorzystywane w paru plikach w ramach tego samego modułu umieszczaj w osobnych plikach (np. utils.py).

## 3. Wzorce projektowe

- Stosuj wzorzec „pipeline” do przetwarzania danych (kolejne etapy: ekstrakcja, przygotowanie, obliczenia, predykcja).
- Używaj wzorca „factory” do mapowania funkcji kalkulujących ratingi (patrz: get_calculator_func).
- Konfiguracje przekazuj przez argumenty funkcji lub dedykowane klasy (np. ConfigManager).

## 4. Obsługa błędów

- W przypadku obsługi wyjątków zawsze wyświetlaj pełny stack trace (`traceback.print_exc()`).
- Komunikaty błędów pisz po polsku i dodawaj informację o kontekście.

## 5. Praca z bazą danych

- Wszystkie operacje na bazie realizuj przez moduł `db_module`.
- Wyniki zapytań SQL zawsze przetwarzaj przez Pandas (`pd.read_sql`).
- Po zakończeniu pracy z bazą zawsze zamykaj połączenie (`conn.close()`).

## 6. Testowanie i walidacja

- Twórz testy jednostkowe dla kluczowych funkcji (np. test_parse_score).
- Testy umieszczaj w osobnych plikach (np. test_module.py).
- Wyniki testów opisuj w komentarzach po polsku.

## 7. Dokumentacja i UI

- Wszystkie opisy, komentarze i komunikaty w interfejsie użytkownika pisz po polsku.
- Dokumentację techniczną umieszczaj w plikach README.md oraz docstringach. Jeżeli w danym folderze istnieje już plik README.md to go rozszerz - nigdy sam nie twórz nowego, chyba, że zostałeś o to jawnie poproszony
- W przypadku Streamlit używaj `unsafe_allow_html=True` do customizacji UI.
- Pisząc komunikację z bazą danych pamiętaj o efektywnym zarządzaniu pobranymi danymi (na przykład: korzystaj z cacheowania)

## 8. Przykłady i workflow

- Przykłady użycia kodu umieszczaj w docstringach oraz README.md.
- Opisuj typowe workflow (np. trenowanie modelu, dodawanie ligi) krok po kroku.

## 9. Integracja i rozszerzalność

- Nowe ligi dodawaj przez wpis do bazy i utworzenie pliku w `pages/`.
- Nowe typy ratingów i modeli dodawaj przez rozbudowę odpowiednich słowników i funkcji mapujących.

---

**Pamiętaj:** Kod powinien być czytelny, modularny, łatwy do testowania i zgodny z architekturą projektu Ekstrabet. Komentarze i dokumentacja zawsze po polsku!
