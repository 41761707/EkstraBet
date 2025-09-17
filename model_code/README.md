# MODEL MODULE

## Zawartość folderu

Folder `model_code` zawiera kompletny system uczenia maszynowego do predykcji wyników sportowych. Składa się z następujących głównych komponentów:

### Główne moduły
- **`main.py`** - Punkt wejścia aplikacji, zarządza całym pipelinem trenowania i predykcji
- **`dataprep_module.py`** - Przygotowanie i ładowanie danych z bazy danych
- **`ratings_module.py`** - System obliczania ratingów drużyn (ELO, GAP, PI, itp.)
- **`model_module.py`** - Implementacja modeli głębokiego uczenia (sieci neuronowe)
- **`prediction_module.py`** - Generowanie predykcji dla nadchodzących meczów
- **`config_manager.py`** - Zarządzanie konfiguracjami modeli i parametrów
- **`arg_parser.py`** - Parser argumentów wiersza poleceń

### Systemy ratingów
- **`elo_rating.py`** - Klasyczny system ELO dla rankingu drużyn
- **`gap_rating.py`** - Rating oparty na różnicach w wydajności drużyn
- **`pi_rating.py`** - ranking PI
- **`czech_rating.py`** - Czeski system rankingu
- **`rating_strategy.py`** - Strategia bazowa dla wszystkich systemów ratingów

### Definicje i konfiguracje
- **`model_definitions/`** - Pliki JSON z konfiguracjami modeli (winner, btts, goals, exact)
- **`training_configs/`** - Konfiguracje parametrów trenowania
- **`prediction_configs/`** - Konfiguracje parametrów predykcji
- **`model_*_dev/`** - Foldery z zapisanymi wagami modeli deweloperskich

### Narzędzia pomocnicze
- **`process_data.py`** - Przetwarzanie danych do formatu odpowiedniego dla modelu
- **`data_manager.py`** - Zarządzanie danymi treningowymi i walidacyjnymi
- **`recalc_*.py`** - Skrypty do przeliczania ratingów i wyników

## Uruchomienie skryptu

### Składnia
System korzysta z nowego systemu argumentów nazwanych:

```bash
python main.py --mode [tryb] --model_config [plik_konfiguracji] [opcjonalne_argumenty]
```

### Argumenty wymagane
- **`--mode`** - Tryb pracy aplikacji:
  - `train` - Trenowanie modelu
  - `predict` - Generowanie predykcji
- **`--model_config`** - Ścieżka do pliku JSON z konfiguracją modelu (np. `model_definitions/winner_model.json`)

### Argumenty opcjonalne
- **`--training_config`** - Ścieżka do pliku JSON z konfiguracją trenowania
- **`--prediction_config`** - Ścieżka do pliku JSON z konfiguracją predykcji
- **`--prediction_automate`** - Automatyczne zapisanie predykcji do bazy danych (dla trybu predict)

### Przykłady użycia

#### Trenowanie modelu wyników (winner)
```bash
python main.py --mode train --model_config model_definitions/winner_model.json --training_config training_configs/training_config.json
```

#### Trenowanie modelu BTTS (Both Teams To Score)
```bash
python main.py --mode train --model_config model_definitions/btts_model.json --training_config training_configs/training_config.json
```

#### Generowanie predykcji dla modelu bramek
```bash
python main.py --mode predict --model_config model_definitions/goals_model.json --prediction_config prediction_configs/prediction_config.json
```

#### Automatyczne zapisanie predykcji do bazy danych
```bash
python main.py --mode predict --model_config model_definitions/winner_model.json --prediction_config prediction_configs/prediction_config.json --prediction_automate
```

## Opis mechanizmu działania komponentów

### Pipeline przetwarzania danych
System działa w oparciu o metodologię pipeline, gdzie każdy etap przetwarza dane i przekazuje je do następnego:

**1. Przygotowanie danych (`dataprep_module.py`)**
- Połączenie z bazą danych i pobieranie danych historycznych
- Filtrowanie meczów według dat, lig i krajów
- Pobieranie informacji o drużynach i nadchodzących meczach
- Klasyfikacja lig według poziomów (pierwsza/druga klasa)

**2. Obliczanie ratingów (`ratings_module.py`)**
- Tworzenie factory pattern dla różnych systemów ratingów
- Iteracyjne obliczanie ratingów dla każdego meczu historycznego
- Aktualizacja ratingów drużyn na podstawie wyników meczów
- Łączenie wszystkich systemów ratingów w jeden zbiór danych

**3. Przetwarzanie danych (`process_data.py`)**
- Konwersja danych do formatu odpowiedniego dla sieci neuronowych
- Tworzenie okien czasowych (window_size) dla analizy formy drużyn
- Podział danych na zbiory treningowe i walidacyjne
- Normalizacja i przygotowanie feature'ów

**4. Trenowanie modeli (`model_module.py`)**
- Budowa architektury sieci neuronowych w oparciu o Keras/TensorFlow
- Trenowanie modeli z wykorzystaniem danych historycznych
- Walidacja modeli i ocena ich skuteczności
- Zapisywanie wytrenowanych wag do plików

**5. Generowanie predykcji (`prediction_module.py`)**
- Ładowanie wytrenowanych modeli
- Przygotowanie danych dla nadchodzących meczów
- Generowanie prawdopodobieństw dla różnych wyników
- Opcjonalne zapisywanie predykcji do bazy danych

### Zarządzanie konfiguracją (`config_manager.py`)
- Ładowanie konfiguracji z plików JSON
- Mapowanie argumentów wiersza poleceń na parametry systemu
- Walidacja parametrów konfiguracyjnych
- Zarządzanie ścieżkami do modeli i danych

### Systemy ratingów

**ELO Rating (`elo_rating.py`)**
- Klasyczny system rankingu szachowego adaptowany do sportu
- Uwzględnia różnicę bramek i poziom ligi
- Parametry: initial_rating (1500), k_factor (64), second_tier_coef (0.8)

**GAP Rating (`gap_rating.py`)**
- Rating oparty na różnicach w wydajności drużyn
- Analizuje atrybuty meczów (szanse, bramki, BTTS)
- Elastyczna konfiguracja poprzez match_attributes

**PI Rating (`pi_rating.py`)**
- System PI rating dla oceny siły drużyn
- Uwzględnia kontekst meczów i formy drużyn

**Czech Rating (`czech_rating.py`)**
- Czeski system rankingu drużyn
- Alternatywne podejście do oceny siły drużyn


### Konfiguracja modeli
Każdy model jest konfigurowany przez plik JSON zawierający:
- Definicję typu modelu i liczby klas
- Mapowanie etykiet wyników
- Konfigurację systemów ratingów
- Parametry trenowania i walidacji
- Ścieżki do folderów deweloperskich i produkcyjnych

## Obsługiwane sporty i modele

### Sporty
System aktualnie obsługuje następujące dyscypliny sportowe:
- **Piłka nożna** (sport_id: 1) - główny sport z pełnym wsparciem wszystkich modeli
- **Hokej** (sport_id: 2) - wsparcie dla modeli wyników i bramek

### Typy modeli

**1. Winner Model (`winner_model.json`)**
- **Cel:** Predykcja wyniku meczu (wygrana gospodarzy/remis/wygrana gości)
- **Klasy:** 3 (Remis, Wygrana gospodarzy, Wygrana gości)
- **Ratingi:** ELO, GAP
- **Zastosowanie:** Podstawowe zakłady na wynik meczu

**2. BTTS Model (`btts_model.json`)**
- **Cel:** Predykcja czy obie drużyny strzelą bramkę (Both Teams To Score)
- **Klasy:** 2 (Nie, Tak)
- **Ratingi:** GAP
- **Zastosowanie:** Zakłady na bramki obu drużyn

**3. Goals Model (`goals_model.json`)**
- **Cel:** Predykcja łącznej liczby bramek w meczu
- **Klasy:** 7 (0, 1, 2, 3, 4, 5, 6+ bramek)
- **Ratingi:** GAP, Goals
- **Zastosowanie:** Zakłady Over/Under, dokładna liczba bramek

**4. Goals 6-Classes Model (`goals_model_6_classes.json`)**
- **Cel:** Uproszczona wersja modelu bramek
- **Klasy:** 6 kategorii bramkowych
- **Ratingi:** GAP, Goals
- **Zastosowanie:** Alternatywna klasyfikacja bramek

**5. Exact Model**
- **Cel:** Predykcja dokładnego wyniku meczu
- **Status:** W rozwoju
- **Zastosowanie:** Zakłady na dokładny wynik

## Opis mechanizmu trenowania modelu

### Proces trenowania
1. **Przygotowanie danych:**
   - Pobieranie danych historycznych z bazy danych
   - Filtrowanie według dat, lig i krajów
   - Obliczanie ratingów dla wszystkich meczów historycznych

2. **Przetwarzanie danych:**
   - Tworzenie okien czasowych (window_size) dla analizy formy
   - Normalizacja feature'ów
   - Podział na zbiory treningowe i walidacyjne

3. **Budowa modelu:**
   - Wczytanie architektury z pliku konfiguracyjnego
   - Inicjalizacja sieci neuronowej (Keras/TensorFlow)
   - Konfiguracja optimizera i funkcji straty

4. **Trenowanie:**
   - Trenowanie na danych historycznych
   - Walidacja na oddzielnym zbiorze danych
   - Monitorowanie metryk (accuracy, loss)

5. **Zapisywanie wyników:**
   - Zapis wag modelu do pliku .h5
   - Aktualizacja pliku konfiguracyjnego o wyniki trenowania
   - Logowanie procesu w folderze logs/

### Struktura folderów modeli
- `model_{type}_dev/` - Modele deweloperskie z wagami i konfiguracjami
- `model_{type}_release/` - Modele produkcyjne gotowe do wdrożenia
- `logs/train/` - Logi procesów trenowania
- `logs/validation/` - Logi walidacji modeli

### Parametry konfiguracyjne
- **window_size** - Liczba poprzednich meczów uwzględnianych w analizie
- **feature_columns** - Kolumny danych używane jako cechy modelu
- **rating_types** - Lista systemów ratingów do wykorzystania
- **threshold_date** - Data graniczna między danymi historycznymi a predykcjami

### Monitoring i ewaluacja
System automatycznie zapisuje metryki trenowania:
- **train_accuracy** - Dokładność na zbiorze treningowym
- **train_loss** - Strata na zbiorze treningowym  
- **val_accuracy** - Dokładność na zbiorze walidacyjnym
- **val_loss** - Strata na zbiorze walidacyjnym

## Uwagi i wymagania

### Zależności
- Python 3.8+
- TensorFlow/Keras
- Pandas, NumPy
- Moduł db_module do połączenia z bazą danych

### Struktura bazy danych
System wymaga dostępu do tabel:
- `matches` - Dane historycznych meczów
- `teams` - Informacje o drużynach  
- `leagues` - Definicje lig
- `sports` - Rodzaje sportów
- `predictions` - Tabela do zapisywania predykcji

### Wydajność
- Trenowanie modelu może zająć od kilku minut do kilku godzin w zależności od ilości danych
- Zalecane jest użycie GPU dla większych zbiorów danych
- System automatycznie zarządza pamięcią poprzez usuwanie nieużywanych kolumn

### Rozszerzanie systemu
Aby dodać nowy typ modelu:
1. Utwórz odpowiednie pliki konfiguracjyne w `model_definitions/`, `training_configs/` i `prediction_configs/`
2. Zaimplementuj logikę przetwarzania w `process_data.py`
3. Dodaj odpowiedni folder `model_{type}_dev/`
4. Zaktualizuj parser argumentów w `arg_parser.py`