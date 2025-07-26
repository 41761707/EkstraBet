# Copilot Instructions for Ekstrabet

## Project Overview
- Ekstrabet consists of two main components:
  - `web_code/`: Streamlit web application for user interaction, navigation, and visualization.
  - `model_code/`: Python modules for data preparation, rating calculation, model training, prediction, and testing.
- All data is loaded from a database using custom queries via `db_module`.

## Architecture & Data Flow
- The web app (`Home.py`) provides navigation and UI, dynamically generating links for each league using database data.
- The model pipeline (`main.py` in `model_code/`) orchestrates:
  - Data extraction and preparation (`dataprep_module`)
  - Rating calculation (`ratings_module`)
  - Model training and prediction (`model_module`, `prediction_module`)
  - Configuration management (`config_manager`)
  - Testing (`test_module`)
- Data flows from database → data prep → rating calculation → model training/prediction → results/testing.

## Developer Workflows
- To run the web app: `streamlit run Home.py` from `web_code/`.
- To run model training/prediction/testing:
  - `python main.py <model_type> <mode> <load_weights> <model_name>` from `model_code/`.
    - Example: `python main.py winner train 1 alpha_0_0_result`
    - Modes: `train`, `predict`, `test`
- Configuration is managed via command-line arguments and `ConfigManager`.
- All database connections must be closed after use.

## Project-Specific Patterns
- Calculator functions for rating attributes are mapped in `get_calculator_func` (see `main.py`).
- Model configuration and rating types are handled via nested dictionaries and passed through the pipeline.
- All UI and documentation is in Polish; maintain language consistency.
- Custom HTML/CSS is injected in Streamlit with `unsafe_allow_html=True`.

## Integration Points
- All database operations use `db_module`.
- Model weights and configs are saved/loaded from `model_{model_type}_dev/` directories.
- External data sources referenced for attribution: `flashscore.pl`, `opta.com`, `NHL API`, `dailyfaceoff.com`.

## Conventions
- Use Pandas for all SQL query results and data manipulation.
- Page files in `pages/` should follow the naming pattern `{LeagueName}.py` and be referenced in `Home.py`.
- Model pipeline modules should be imported and used as in `main.py`.

## Example: Model Training Workflow
1. Prepare configuration and database.
2. Run: `python main.py winner train 0 alpha_0_0_result`
3. The pipeline will extract data, calculate ratings, train the model, and save results/configs.

## Example: Adding a New League
1. Add a new league to the database (`leagues` table).
2. Create a new file in `pages/` named after the league (e.g., `pages/Serie A.py`).
3. The new league will automatically appear in the navigation if `active=1` in the database.

---
For questions or unclear conventions, review `Home.py`, `main.py`, and the database schema, or ask the project author (see contact info in the UI).

# Zasady Pisania Kodu w Pythonie dla Ekstrabet

## 1. Styl kodowania

- Stosuj konwencję PEP8 (wcięcia 4 spacje, czytelne nazwy zmiennych, spójność stylu).
- Nazwy zmiennych, funkcji i klas powinny być opisowe i jednoznaczne.
- Funkcje i klasy dokumentuj za pomocą docstringów w stylu Google lub NumPy.
- Komentarze pisz wyłącznie po polsku, wyjaśniając logikę, założenia i nietypowe rozwiązania.

## 2. Struktura projektu

- Moduły dziel według funkcjonalności (np. web_code, model_code).
- Każdy plik powinien mieć nagłówek z krótkim opisem przeznaczenia.
- Funkcje pomocnicze umieszczaj w osobnych plikach (np. utils.py).

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
- Dokumentację techniczną umieszczaj w plikach README.md oraz docstringach.
- W przypadku Streamlit używaj `unsafe_allow_html=True` do customizacji UI.

## 8. Przykłady i workflow

- Przykłady użycia kodu umieszczaj w docstringach oraz README.md.
- Opisuj typowe workflow (np. trenowanie modelu, dodawanie ligi) krok po kroku.

## 9. Integracja i rozszerzalność

- Nowe ligi dodawaj przez wpis do bazy i utworzenie pliku w `pages/`.
- Nowe typy ratingów i modeli dodawaj przez rozbudowę odpowiednich słowników i funkcji mapujących.

---

**Pamiętaj:** Kod powinien być czytelny, modularny, łatwy do testowania i zgodny z architekturą projektu Ekstrabet. Komentarze i dokumentacja zawsze po polsku!
