import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' #Nie chce warningow z TensorFlow

import numpy as np
import json

# Moduły
import dataprep_module
import ratings_module
import model_module
import process_data
import prediction_module
import config_manager
import db_module
import arg_parser

def get_matches(config):
    """
    Główna funkcja pobierająca i przetwarzająca dane meczowe, obliczająca ratingi drużyn
    Args:
        config (ConfigManager): Obiekt konfiguracyjny zawierający wszystkie parametry
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
    data = dataprep_module.DataPrep(config.threshold_date, 
                                    config.leagues,
                                    config.sport_id,
                                    config.country,
                                    config.leagues_upcoming)
    matches_df = data.get_historical_data()
    teams_df = data.get_teams_data()
    upcoming_df = data.get_upcoming_data()
    first_tier_leagues, second_tier_leagues = data.get_league_tier()
    data.close_connection()
    
    # Przygotowanie parametrów dla systemów rankingowych
    rating_params = config_manager.RatingParameters(
        model_config=config.model_config,
        matches_df=matches_df.copy(),
        teams_df=teams_df,
        first_tier_leagues=first_tier_leagues,
        second_tier_leagues=second_tier_leagues)
    rating_factory = ratings_module.RatingFactory.create_rating(
        config.model_config["ratings"],
        **rating_params.to_dict())
    merged_matches_df = matches_df.copy()
    for rating in rating_factory:
        print(f'Tworzenie rankingu dla: {type(rating).__name__}')
        rating.calculate_rating()
        rating.print_rating()
        temp_matches_df, _ = rating.get_data()
        # Znajdujemy nowe kolumny dodane przez aktualny rating
        new_columns = [col for col in temp_matches_df.columns if col not in merged_matches_df.columns]
        for col in new_columns:
            merged_matches_df[col] = temp_matches_df[col]

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
        config (ConfigManager): Obiekt zarządzający konfiguracją zawierający
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
    matches_df, teams_df, _ = get_matches(config)
    window_size = config.model_config.get("window_size", 5) # Domyślnie 5
    processor = process_data.ProcessData(
        matches_df, 
        teams_df, 
        config.model_config["model_type"], 
        config.feature_columns, 
        window_size,
        config.model_config["output_config"])
    train_data, val_data, training_info = processor.process_train_data()
    # Analiza rozkładu danych
    analyze_result_distribution(train_data, 
                                config.model_config["model_type"], 
                                config.model_config["output_config"]["label_mapping"],
                                "Training Data")
    analyze_result_distribution(val_data, 
                                config.model_config["model_type"], 
                                config.model_config["output_config"]["label_mapping"],
                                "Validation Data")
    #Testowe printy
    #print_training_data_info(train_data, val_data, training_info, 3)

    # Inicjalizacja i trenowanie modelu
    model = model_module.ModelModule(
        train_data, 
        val_data, 
        len(config.feature_columns), 
        config.model_config["model_type"], 
        config.model_config["model_name"], 
        config.model_load_name,
        window_size,
        training_info,
        config.model_config)
    if config.training_config["load_weights"] == "1":
        model.load_predict_model(config)
    else:
        model.build_model_from_config(config)
    # Trenowanie modelu i aktualizacja konfiguracji
    history, evaluation_results = model.train_model()
    config.model_config["train_accuracy"] = float(history.history['accuracy'][-1])
    config.model_config["train_loss"] = float(history.history['loss'][-1])
    config.model_config["val_accuracy"] = float(evaluation_results[1])
    config.model_config["val_loss"] = float(evaluation_results[0])

    # Zapis konfiguracji do pliku
    with open(f'model_dev/{config.model_config["model_type"]}/{config.model_config["model_name"]}_config.json', 'w') as f:
        json.dump(config.model_config, f, indent=4)

def print_training_data_info(train_data, val_data, training_info, no_prints):
    """Pomocnicza funkcja do wyświetlania informacji o danych treningowych
    Args:
        train_data: Dane treningowe w formacie (X_home_seq, X_away_seq, y)
        val_data: Dane walidacyjne w formacie (X_home_seq, X_away_seq, y)
        training_info: Informacje o danych treningowych
        no_prints: Liczba próbek do wydrukowania z każdego zbioru danych
    """
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

def analyze_result_distribution(data_tuple, model_type, label_mappings, dataset_name="Dataset"):
    """
    Analizuje i wypisuje rozkład danych w podanym zbiorze danych
    Args:
        data_tuple: Dane zawierające krotkę (X_home_seq, X_away_seq, y), gdzie y jest one-hotem
        model_type: Typ modelu ('winner', 'goals', 'btts')
        label_mappings: Mapowanie etykiet dla wyników z konfiguracji modelu (np. {"0": "Remis", "1": "Wygrana gospodarzy"})
        dataset_name: Nazwa zbioru danych, wykorzystywane głównie przy wypisywaniu informacji

    """
    _, _, y = data_tuple
    # Konwertujemy one-hot encoding do etykiet
    results = np.argmax(y, axis=1)
    unique, counts = np.unique(results, return_counts=True)
    total = len(results)
    print(f"\n=== {dataset_name} Distribution ===")
    print(f"Total samples: {total}")
    # Konwertujemy mapowanie z stringów na inty dla zgodności z wynikami np.argmax
    result_mapping = {}
    for key, value in label_mappings.items():
        result_mapping[int(key)] = value
    for result, count in zip(unique, counts):
        percentage = (count / total) * 100
        # Sprawdzamy czy klucz istnieje w mapowaniu, w przeciwnym razie używamy domyślnej etykiety
        label = result_mapping.get(result, f"Klasa {result}")
        print(f"{label}: {count} ({percentage:.2f}%)")

def prepare_predictions(config, prediction_automate: bool, conn) -> list:
    """
    Przygotowuje predykcje dla nadchodzących meczów na podstawie konfiguracji
    Args:
        config (ConfigManager): Obiekt zarządzający konfiguracją zawierający wszystkie parametry
        prediction_automate (bool): Flaga określająca, czy predykcje mają być automatycznie zapisywane do bazy danych
        conn: Połączenie z bazą danych
    Returns:
        list: Lista przewidywań meczów zawierająca:
            - match_id: ID meczu
            - event_id: ID zdarzenia
            - is_final: Czy wynik jest ostateczny
    Proces:
        1. Pobiera dane historyczne i nadchodzące mecze
        2. Inicjalizuje model predykcyjny
        3. Wczytuje wytrenowane wagi modelu
        4. Generuje predykcje dla nadchodzących meczów
    """
    matches_df, teams_df, upcoming_df = get_matches(config)
    model = model_module.ModelModule([], [], [], [], [], config.model_load_name, [], None, config.model_config)
    window_size = config.prediction_config.get("window_size", 5)  # Domyślna wartość 5
    predict_matches = prediction_module.PredictMatch(
        matches_df,
        upcoming_df,
        teams_df,
        config.feature_columns, 
        model,
        config.model_config["model_type"], 
        config.model_config["model_name"],
        window_size,
        conn,
        prediction_automate=prediction_automate,
        model_config=config.model_config)

    model.load_predict_model(config)
    predict_matches.predict_games(model, upcoming_df)
    return predict_matches.get_predictions()

def main() -> None:
    '''
        Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
    '''
    conn = db_module.db_connect()
    config = config_manager.ConfigManager()
    args_dict = arg_parser.parse_arguments()
    config.load_from_args(args_dict)
    prediction_automate = args_dict.get('prediction_automate', False)
    print(f"Tryb pracy: {args_dict['mode']}")
    print(f"Typ modelu: {config.model_config['model_type']}")
    if args_dict["mode"] == 'train':
        prepare_training(config)
    elif args_dict["mode"] == 'predict':
        matches_predictions = prepare_predictions(config, prediction_automate, conn)
        print(f"Wygenerowano {len(matches_predictions)} predykcji")
    conn.close()

if __name__ == '__main__':
    main()
