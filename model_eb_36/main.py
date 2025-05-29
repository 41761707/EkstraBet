import numpy as np
import sys
from datetime import date, timedelta
import json

# Moduły
import dataprep_module
import ratings_module
import model_module
import process_data
import prediction_module
import config_manager
# @package main


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
    input_date = date.today() - timedelta(days=7)
    data = dataprep_module.DataPrep(input_date, config.leagues, config.sport_id, config.country)
    matches_df, teams_df, upcoming_df, first_tier_leagues, second_tier_leagues = data.get_data()
    data.close_connection()
    # Tworzenie ratingu
    rating_factory = ratings_module.RatingFactory.create_rating(config.rating_config[config.model_type]['rating_type'],
                                                                matches_df=matches_df.copy(),
                                                                teams_df=teams_df,
                                                                first_tier_leagues=first_tier_leagues,
                                                                second_tier_leagues=second_tier_leagues,
                                                                initial_rating=config.model_config["ratings"]["elo"]["initial_rating"],
                                                                second_tier_coef=config.model_config["ratings"]["elo"]["second_tier_coef"],
                                                                match_attributes=config.model_config["ratings"]["gap"]["match_attributes"])

    # Tworzymy kopię oryginalnego DataFrame
    merged_matches_df = matches_df.copy()
    for rating in rating_factory:
        print(type(rating).__name__)
        rating.calculate_rating()
        rating.print_rating()
        temp_matches_df, _ = rating.get_data()

        # Znajdujemy nowe kolumny dodane przez aktualny rating
        new_columns = [
            col for col in temp_matches_df.columns if col not in merged_matches_df.columns]

        # Dodajemy nowe kolumny do głównego DataFrame
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
    print_training_data_info(train_data, val_data, training_info, 3)

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
        model.load_predict_model(f'model_{config.model_type}_dev/{config.model_load_name}.h5')
    else:
        model_creator = {
            'winner': model.build_model_from_config,
            'goals': model.build_model_from_config,
            'btts': model.build_model_from_config,
            'exact': model.build_model_from_config
        }
        model_creator[config.model_type](config)
    
    # Trenowanie modelu i aktualizacja konfiguracji
    history, evaluation_results = model.train_model()
    config.model_config["train_accuracy"] = history.history['accuracy'][-1]
    config.model_config["train_loss"] = history.history['loss'][-1]
    config.model_config["val_accuracy"] = evaluation_results[1]
    config.model_config["val_loss"] = evaluation_results[0]

    # Zapis konfiguracji do pliku
    with open(f'model_{config.model_type}_dev/{config.model_name}_config.json', 'w') as f:
        json.dump(config.model_config, f, indent=4)

def print_training_data_info(train_data, val_data, training_info, no_prints):
    """Pomocnicza funkcja do wyświetlania informacji o danych treningowych"""

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
    # Convert one-hot encoded back to labels
    results = np.argmax(y, axis=1)

    # Count occurrences
    unique, counts = np.unique(results, return_counts=True)
    total = len(results)

    print(f"\n=== {dataset_name} Distribution ===")
    print(f"Total samples: {total}")

    # Create a mapping for better readability
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


def prepare_predictions(config):
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
        config.window_size
    )

    # Wczytanie wag modelu i wykonanie predykcji
    model.load_predict_model(config.rating_config[config.model_type]['model_path'])
    predict_matches.predict_next_game(model, upcoming_df)

def main():
    '''
        Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
    '''
    config = config_manager.ConfigManager()
    config.load_from_args(sys.argv)
    if config.model_mode == 'train':
        prepare_training(config)
    elif config.model_mode == 'predict':
        prepare_predictions(config)


if __name__ == '__main__':
    main()
