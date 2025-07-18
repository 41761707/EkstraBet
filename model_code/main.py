import numpy as np
import sys
import json

# Moduły
import dataprep_module
import ratings_module
import model_module
import process_data
import prediction_module
import config_manager
import test_module
import db_module

# @package main
def get_calculator_func(name):
    #TO-DO: Zrobić to lepiej bo teraz jest mega syf - to zwraca typy kalukatorów dla rankingu gap
    calculators = {
        'chances_home': {
            'calculator': lambda match: int(match['home_team_ck']) + int(match['home_team_sc'])
        },
        'chances_away': {
            'calculator': lambda match: int(match['away_team_ck']) + int(match['away_team_sc'])
        },
        'goals_home': {
            'calculator': lambda match: int(match['home_team_goals'])
        },
        'goals_away': {
            'calculator': lambda match: int(match['away_team_goals'])
        },
        'btts': {
            'calculator': lambda match: 1 if match['home_team_goals'] > 0 and match['away_team_goals'] > 0 else 0
        },
    }
    return calculators.get(name, None)

def get_rating_params(config):
    """
    Pobiera parametry ratingów z konfiguracji i przygotowuje je do użycia.
    
    Args:
        config (ConfigManager): Obiekt konfiguracyjny zawierający ustawienia modelu
    
    Returns:
        tuple: Krotka zawierająca:
            - initial_rating (int): Początkowa wartość rankingu ELO
            - second_tier_coef (float): Współczynnik dla drużyn z drugiej ligi
            - match_attributes (list/str): Lista atrybutów meczu lub pusty string
    """
    # Sprawdzenie czy ranking ELO jest aktywny
    elo_enabled = 'elo' in config.rating_config[config.model_type]['rating_type']
    # Pobranie początkowego rankingu ELO jeśli aktywny, w przeciwnym razie 0
    initial_rating = config.model_config["ratings"]["elo"]["initial_rating"] if elo_enabled else 0
    # Pobranie współczynnika dla drugiej ligi jeśli ELO aktywne, w przeciwnym razie 0
    second_tier_coef = config.model_config["ratings"]["elo"]["second_tier_coef"] if elo_enabled else 0

    # Sprawdzenie czy ranking GAP jest aktywny
    gap_enabled = 'gap' in config.rating_config[config.model_type]['rating_type']
    if gap_enabled:
        # Pobranie atrybutów meczu z konfiguracji (domyślnie pusty string)
        match_attributes = config.model_config["ratings"]["gap"].get("match_attributes", "")
        for attr in match_attributes:
            attr["calculator"] = get_calculator_func(attr["name"])["calculator"]
    else:
        # Dla nieaktywnego GAP zwracamy pusty string
        match_attributes = ""
    
    return initial_rating, second_tier_coef, match_attributes

def get_matches(config):
    """
    Główna funkcja pobierająca i przetwarzająca dane meczowe, obliczająca ratingi drużyn

    Args:
        leagues (list): Lista lig do analizy
        sport_id (int): ID sportu (np. 1 - piłka nożna)
        country (int): ID kraju
        rating_config (dict): Konfiguracja ratingu zawierająca parametry obliczeń
        model_type (str): Typ modelu do tworzenia ratingu

    Returns:
        tuple: Krotka zawierająca:
            - matches_df (DataFrame): Dane historycznych meczów z obliczonymi ratingami
            - teams_df (DataFrame): Informacje o drużynach
            - upcoming_df (DataFrame): Nadchodzące mecze do predykcji

    Proces:
        1. Pobiera dane meczowe i drużynowe z bazy danych
        2. Tworzy ratingi drużyn na podstawie konfiguracji
        3. Oblicza wartości ratingów dla różnych modeli
        4. Łączy wszystkie obliczone ratingi w jeden DataFrame
        5. Zwraca przetworzone dane wraz z informacjami o nadchodzących meczach
    """
    input_date = config.model_config["training_config"]["threshold_date"]
    print(input_date)
    data = dataprep_module.DataPrep(input_date, config.leagues, config.sport_id, config.country)
    matches_df, teams_df, upcoming_df, first_tier_leagues, second_tier_leagues = data.get_data()
    data.close_connection()
    initial_rating, second_tier_coef, match_attributes = get_rating_params(config)
    rating_factory = ratings_module.RatingFactory.create_rating(
        config.rating_config[config.model_type]['rating_type'],
        matches_df=matches_df.copy(),
        teams_df=teams_df,
        first_tier_leagues=first_tier_leagues,
        second_tier_leagues=second_tier_leagues,
        initial_rating=initial_rating,
        second_tier_coef=second_tier_coef,
        match_attributes=match_attributes
    )
    merged_matches_df = matches_df.copy()
    for rating in rating_factory:
        print(f'Tworzenie rankingu dla: {type(rating).__name__}')
        rating.calculate_rating()
        temp_matches_df, _ = rating.get_data()
        # Znajdujemy nowe kolumny dodane przez aktualny rating
        new_columns = [col for col in temp_matches_df.columns if col not in merged_matches_df.columns]
        for col in new_columns:
            merged_matches_df[col] = temp_matches_df[col]

    # Zastępujemy oryginalny matches_df połączonym DataFrame
    matches_df = merged_matches_df
    # Zbieramy wszystkie kolumny używane przez systemy rankingowe 
    # Nie ma co trzymac dodatkowych danych i obciazac pamiec
    rating_columns = set()
    for rating in rating_factory:
        temp_df, _ = rating.get_data()
        rating_columns.update(temp_df.columns)

    # Usuwamy kolumny, które nie są używane przez żaden system rankingowy
    columns_to_drop = [col for col in matches_df.columns if col not in rating_columns]
    matches_df = matches_df.drop(columns=columns_to_drop)
    print("Przykład reprezentacji meczów:")
    print(matches_df.tail())
    return matches_df, teams_df, upcoming_df


def prepare_training(config):
    """
    Przygotowuje i trenuje model predykcyjny na podstawie konfiguracji
    
    Args:
        config (ConfigManager): Obiekt zarządzający konfiguracją zawierający:
            - model_type: Typ modelu do trenowania (winner/goals/btts/exact)
            - leagues: Lista lig do analizy
            - sport_id: ID sportu
            - country: ID kraju
            - load_weights: Flaga określająca czy ładować wagi pretrenowanego modelu
            - feature_columns: Lista kolumn z cechami
            - rating_config: Konfiguracja ratingu drużyn
            - window_size: Rozmiar okna czasowego
            - match_attributes: Atrybuty meczu do analizy
            - model_config: Konfiguracja modelu
            - model_name: Nazwa modelu
            - model_load_name: Nazwa modelu do wczytania wag

    Returns:
        tuple: Krotka zawierająca:
            - model: Wytrenowany lub załadowany model predykcyjny
            - history: Historia trenowania modelu (None jeśli załadowano wagi)
            - training_info: Informacje o danych treningowych

    Proces:
        1. Pobiera dane meczowe z funkcji get_matches()
        2. Przetwarza dane do formatu odpowiedniego dla modelu
        3. Analizuje rozkład danych treningowych i walidacyjnych
        4. Inicjalizuje i buduje odpowiedni model w zależności od typu
        5. Trenuje model lub ładuje pretrenowane wagi
        6. Zapisuje wyniki treningu do pliku konfiguracyjnego
    """
    # Pobranie danych meczowych
    matches_df, teams_df, _ = get_matches(config)
    # Przetwarzanie danych treningowych
    processor = process_data.ProcessData(
        matches_df, 
        teams_df, 
        config.model_type, 
        config.feature_columns, 
        config.window_size
    )
    train_data, val_data, training_info = processor.process_train_data()

    # Analiza rozkładu danych
    analyze_result_distribution(train_data, config.model_type, "Training Data")
    analyze_result_distribution(val_data, config.model_type, "Validation Data")
    #Testowe printy
    #print_training_data_info(train_data, val_data, training_info, 3)

    # Inicjalizacja i trenowanie modelu
    model = model_module.ModelModule(
        train_data, 
        val_data, 
        len(config.feature_columns), 
        config.model_type, 
        config.model_name, 
        config.window_size
    )
    
    if config.load_weights == '1':
        model.load_predict_model(config)
    else:
        model.build_model_from_config(config)
    
    # Trenowanie modelu i aktualizacja konfiguracji
    history, evaluation_results = model.train_model()
    config.model_config["train_accuracy"] = float(history.history['accuracy'][-1])
    config.model_config["train_loss"] = float(history.history['loss'][-1])
    config.model_config["val_accuracy"] = float(evaluation_results[1])
    config.model_config["val_loss"] = float(evaluation_results[0])

    #TO-DO: Reprezentacja lambda funkcji jako stringa
    if "match_attributes" in config.model_config["ratings"]["gap"]:
        if config.model_config["ratings"]["gap"]["match_attributes"]:
            config.model_config["ratings"]["gap"]["match_attributes"] = ''
    # Zapis konfiguracji do pliku
    with open(f'model_{config.model_type}_dev/{config.model_name}_config.json', 'w') as f:
        json.dump(config.model_config, f, indent=4)

def print_training_data_info(train_data, val_data, training_info, no_prints):
    """Pomocnicza funkcja do wyświetlania informacji o danych treningowych"""
    # Nieładnie, ale tak ma być - nie chce mi się tego poprawiać jak to tylko pomocnicza funkcja
    print("\n=== TRAINING DATA ===")
    print(f"Shape of sequences: {train_data[0].shape}")
    print(f"Number of samples: {len(train_data[0])}")
    print("\nTrain sequences:")
    for i in range(no_prints):
        print(f"\nSequence {i+1}:")
        print("Home team sequence:")
        print(train_data[0][i])
        print("\nAway team sequence:")
        print(train_data[1][i])
        print("\nTarget:")
        print(train_data[2][i])
        print("\n MATCH_ID")
        print(training_info[0][i])

    print("\n=== VALIDATION DATA ===")
    print(f"Shape of sequences: {val_data[0].shape}")
    print(f"Number of samples: {len(val_data[0])}")
    print("\nVal sequences:")
    for i in range(no_prints):
        print(f"\nSequence {i+1}:")
        print("Home team sequence:")
        print(val_data[0][i])
        print("\nAway team sequence:")
        print(val_data[1][i])
        print("\nTarget:")
        print(val_data[2][i])
        print("\n MATCH_ID")
        print(training_info[1][i])


def analyze_result_distribution(data_tuple, model_type, dataset_name="Dataset"):
    """
    Analizuje i wypisuje rozkład danych w podanym zbiorze danych

    Args:
        data_tuple: Dane zawierające krotkę (X_home_seq, X_away_seq, y), gdzie y jest one-hotem
        dataset_name: Nazwa zbioru danych, wykorzystywane głównie przy wypisywaniu informacji
    """
    _, _, y = data_tuple
    # Konwertujemy one-hot encoding do etykiet
    results = np.argmax(y, axis=1)

    unique, counts = np.unique(results, return_counts=True)
    total = len(results)

    print(f"\n=== {dataset_name} Distribution ===")
    print(f"Total samples: {total}")

    # Ułatwienie czytelności - mapowanie wyników na czytelne etykiety
    if model_type == 'winner':
        result_mapping = {0: "Draw", 1: "Home Win", 2: "Away Win"}
    elif model_type == 'goals':
        result_mapping = {i: f"{i} Goals" for i in range(7)}
    elif model_type == 'btts':
        result_mapping = {0: "No BTTS", 1: "BTTS"}
    else:
        return

    for result, count in zip(unique, counts):
        percentage = (count / total) * 100
        print(f"{result_mapping[result]}: {count} ({percentage:.2f}%)")


def prepare_predictions(config, conn):
    """
    Przygotowuje predykcje dla nadchodzących meczów na podstawie konfiguracji

    Args:
        config (ConfigManager): Obiekt zarządzający konfiguracją zawierający:
            - model_type: Typ modelu (winner/goals/btts/exact)
            - leagues: Lista lig do analizy
            - sport_id: ID sportu
            - country: ID kraju
            - rating_config: Konfiguracja ratingu
            - feature_columns: Lista kolumn z cechami
            - window_size: Rozmiar okna czasowego
            - match_attributes: Atrybuty meczu do analizy

    Proces:
        1. Pobiera dane historyczne i nadchodzące mecze
        2. Inicjalizuje model predykcyjny
        3. Wczytuje wytrenowane wagi modelu
        4. Generuje predykcje dla nadchodzących meczów
    """
    # Pobranie danych meczowych
    matches_df, teams_df, upcoming_df = get_matches(config)

    # Inicjalizacja modelu
    model = model_module.ModelModule([], [], [], [], [], [])
    # Utworzenie instancji klasy do przewidywania
    predict_matches = prediction_module.PredictMatch(
        matches_df,
        upcoming_df,
        teams_df,
        config.feature_columns,
        model,
        config.model_type,
        config.model_name,
        config.window_size,
        conn
    )

    # Wczytanie wag modelu i wykonanie predykcji
    model.load_predict_model(config)
    predict_matches.predict_games(model, upcoming_df)
    return predict_matches.get_predictions()

def run_tests(matches_predictions, analized_event, conn):
    '''
    Uruchamia testy na podstawie przewidywań meczów
    Args:
        matches_predictions (list): Lista przewidywań meczów zawierająca:
            - match_id: ID meczu
            - event_id: ID zdarzenia
            - is_final: Czy wynik jest ostateczny
        analized_event (str): Typ analizowanego zdarzenia (winner/goals/btts/exact)
        conn: Połączenie z bazą danych
    '''
    tests = test_module.TestModule(matches_predictions, analized_event, conn)
    tests.calculate_predictions_profit()

def main():
    '''
        Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
        Przykłady wywołania:
        python .\main.py winner predict 1 alpha_0_0_result - przewidywanie meczów dla zdarzenia typu winner
        python .\main.py goals train 1 alpha_0_0_result - trenowanie modelu dla zdarzenia typu goals
    '''
    conn = db_module.db_connect()
    config = config_manager.ConfigManager()
    config.load_from_args(sys.argv)
    if config.model_mode == 'train':
        prepare_training(config)
    elif config.model_mode == 'predict':
        matches_predictions = prepare_predictions(config, conn)
        for element in matches_predictions:
            print(element)
    elif config.model_mode == 'test':
        run_tests(matches_predictions, config.model_type, conn)
    conn.close()


if __name__ == '__main__':
    main()
