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

# @package main


def get_matches(leagues, sport_id, country, rating_config, model_type, match_attributes):
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

    initial_rating = 1500
    second_tier_coef = 0.8
    input_date = date.today() - timedelta(days=1)
    data = dataprep_module.DataPrep(input_date, leagues, sport_id, country)
    matches_df, teams_df, upcoming_df, first_tier_leagues, second_tier_leagues = data.get_data()
    data.close_connection()
    # Tworzenie ratingu
    rating_factory = ratings_module.RatingFactory.create_rating(rating_config[model_type]['rating_type'],
                                                                matches_df=matches_df.copy(),
                                                                teams_df=teams_df,
                                                                first_tier_leagues=first_tier_leagues,
                                                                second_tier_leagues=second_tier_leagues,
                                                                initial_rating=initial_rating,
                                                                second_tier_coef=second_tier_coef,
                                                                match_attributes=match_attributes)

    # Tworzymy kopię oryginalnego DataFrame
    merged_matches_df = matches_df.copy()
    for rating in rating_factory:
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
    print(matches_df.tail())

    return matches_df, teams_df, upcoming_df


def prepare_training(model_type, leagues, sport_id, country, load_weights,
                     feature_columns, rating_config, window_size, 
                     match_attributes, training_json, model_name, model_load_name):
    """
    Główna funkcja przygotowująca dane treningowe i model predykcyjny dla wybranego typu meczu

    Args:
        model_type (str): Typ modelu do trenowania (winner/goals/btts/exact)
        leagues (list): Lista lig do uwzględnienia w analizie
        sport_id (int): ID sportu (np. 1 - piłka nożna)
        country (int): ID kraju
        load_weights (str): Flaga określająca czy ładować wagi pretrenowanego modelu ('1' - tak)
        feature_columns (list): Lista kolumn z cechami używanymi w modelu
        rating_config (dict): Konfiguracja ratingu drużyn
        window_size (int): Rozmiar okna czasowego dla danych sekwencyjnych

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
        6. Zwraca gotowy model wraz z dodatkowymi informacjami
    """

    matches_df, teams_df, _ = get_matches(
        leagues, sport_id, country, rating_config, model_type, match_attributes)
    processor = process_data.ProcessData(
        matches_df, teams_df, model_type, feature_columns, window_size)
    train_data, val_data, training_info = processor.process_train_data()

    analyze_result_distribution(train_data, model_type, "Training Data")
    analyze_result_distribution(val_data, model_type, "Validation Data")

    # Wyświetlanie informacji o danych treningowych
    print_training_data_info(train_data, val_data, training_info, 3)

    # Model i predykcje
    model = model_module.ModelModule(train_data, val_data, len(
        feature_columns), model_type, model_name, window_size)
    if load_weights == '1':
        model.load_predict_model(f'model_winner_dev/{model_load_name}.h5')
    else:
        if model_type == 'winner':
            model.create_winner_model()
        elif model_type == 'goals':
            model.create_goals_model()
        elif model_type == 'btts':
            model.create_btts_model()
        elif model_type == 'exact':
            model.create_exact_model()
    history, evaluation_results = model.train_model()
    training_json["train_accuracy"] = history.history['accuracy'][-1]
    training_json["train_loss"] = history.history['loss'][-1]
    training_json["val_accuracy"] = evaluation_results[2]
    training_json["val_loss"] = evaluation_results[3]

    # Zapisanie do pliku JSON
    with open(f'model_{model_type}_dev/{model_name}_config.json', 'w') as f:
        json.dump(training_json, f, indent=4)

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


def prepare_predictions(model_type, leagues, sport_id, country, rating_config, feature_columns, window_size, match_attributes):
    """
    Główna funkcja przygotowująca predykcje dla nadchodzących meczów

    Args:
        model_type (str): Typ modelu (winner/goals/btts/exact)
        leagues (list): Lista lig
        sport_id (int): ID sportu
        country (int): ID kraju
        rating_config (dict): Konfiguracja ratingu
        feature_columns (list): Lista kolumn z cechami
        window_size (int): Rozmiar okna dla sekwencji
    """
    matches_df, teams_df, upcoming_df = get_matches(
        leagues, sport_id, country, rating_config, model_type,  match_attributes) #pobierz mecze
    model = model_module.ModelModule([], [], [], [], [], []) #utwórz model
    predict_matches = prediction_module.PredictMatch(
        matches_df, upcoming_df, teams_df, feature_columns, model, model_type, window_size) #utwórz instancję klasy do przewidywania
    model.load_predict_model(rating_config[model_type]['model_path']) #wczytaj model
    predict_matches.predict_next_game(model, upcoming_df) #zacznij przewidywać


def main():
    '''
        Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
    '''

    model_type = sys.argv[1]  # [winner, goals, btts]
    model_mode = sys.argv[2]  # [train, predict, test]
    load_weights = sys.argv[3]  # [1, 0]
    model_name = sys.argv[4] # najlepiej żeby zawierał typ + jakiś opis użytej techniki
    model_load_name = sys.argv[5] #model z ktorego trzeba wczytac wagi (load_weights = 1)
    leagues = [1 ,21]
    sport_id = 1
    country = [1]
    window_size = 5
    feature_columns = []
    rating_types = ['elo' if model_type ==
                    'winner' or model_type == 'exact' else 'gap']

    # Definiowanie kolumn dla każdego typu ratingu
    elo_columns = ['home_team_elo', 'away_team_elo']
    gap_columns = [
        'home_home_att_power',
        'home_home_def_power',
        'away_away_att_power',
        'away_away_def_power',
        'home_goals_avg',
        'away_goals_avg'
    ]

    # Dynamiczne tworzenie feature_columns na podstawie rating_types
    feature_columns = []
    if 'elo' in rating_types:
        feature_columns.extend(elo_columns)
    if 'gap' in rating_types:
        feature_columns.extend(gap_columns)

    # Konfiguracja specyficzna dla typu predykcji
    rating_config = {
        'winner': {'rating_type': rating_types, 'model_path': f'model_winner_dev/{model_name}.h5'},
        'goals': {'rating_type': rating_types, 'model_path': f'model_goals_dev/{model_name}.h5'},
        'btts': {'rating_type': rating_types, 'model_path': f'model_btts_dev/{model_name}.h5'},
        'exact': {'rating_type': rating_types, 'model_path': f'model_exact_dev/{model_name}.h5'}
    }

    match_attributes = [
        #{
        #    'name': 'goals_home',
        #    'calculator': lambda match: int(match['home_team_goals'])
        #},
        #        {
        #    'name': 'goals_away',
        #    'calculator': lambda match: int(match['away_team_goals'])
        #},
        #{
        #    'name': 'btts',
        #    'calculator': lambda match: 1 if match['home_team_goals'] > 0 and match['away_team_goals'] > 0 else 0
        #},
        {
            'name': 'chances_home',
            'calculator': lambda match: int(match['home_team_ck']) + int(match['home_team_sc'])
        },
        {
            'name': 'chances_away',
            'calculator': lambda match: int(match['away_team_ck']) + int(match['away_team_sc'])
        },
    ]
    if model_mode == 'train':
        #Do przeniesienia wczytywanie w pliku jsona
        training_json = {
            "model_name": model_name,
            "model_type": model_type,  # [winner, goals, btts, exact]
            "window_size": window_size,
            "train_accuracy": 0,  # zostanie uzupełnione po treningu
            "train_loss": 0,     # zostanie uzupełnione po treningu
            "val_accuracy": 0,   # zostanie uzupełnione po treningu
            "val_loss": 0,       # zostanie uzupełnione po treningu
            "model_path": f'model_{model_type}_dev/{model_name}.h5',
            "feature_columns": feature_columns,  # lista używanych kolumn
            "ratings": {
                "elo": {
                    "enabled": 'elo' in rating_types,
                    "initial_rating": 1500,
                    "second_tier_coef": 0.8,
                    "columns": elo_columns if 'elo' in rating_types else []
                },
                "gap": {
                    "enabled": 'gap' in rating_types,
                    "columns": gap_columns if 'gap' in rating_types else [],
                    "match_attributes": [
                        {
                            "name": attr["name"],
                            "type": "chances"
                        } for attr in match_attributes
                    ]
                }
            },
            "model":{
                "architecture": {
                    "lstm_layers": [
                        {
                            "units": [128, 64],
                            "activation": ["tanh", "tanh"],
                            "return_sequences": [True, False]
                        },
                        {
                            "units": [128, 64],
                            "activation": ["tanh", "tanh"],
                            "return_sequences": [True, False]
                        }
                    ],
                    "dense_layers": [
                        {
                            "units": 128,
                            "activation": "relu",
                            "regularization": {
                                "l2": 0.01
                            },
                        },
                        {
                            "units": 64,
                            "activation": "relu",
                            "regularization": {
                                "l2": 0.01
                            },
                        },
                        {
                            "units": 32,
                            "activation": "relu",
                            "regularization": {
                                "l2": 0.01
                            },
                        }
                    ],
                    "output": {
                        "units": 3,
                        "activation": "softmax"
                    }
                },
                "compilation": {
                    "optimizer": {
                        "type": "Adagrad",
                        "learning_rate": 0.0001
                    },
                    "loss": "categorical_crossentropy",
                    "metrics": ["accuracy", "Precision", "Recall"]
                }
            },
            "training_config": {
                "sport_id": sport_id,
                "leagues": leagues,
                "country": country,
                "load_weights": load_weights == '1'
            }
        }
        prepare_training(model_type, leagues, sport_id,
                         country, load_weights, feature_columns, 
                         rating_config, window_size, match_attributes, 
                         training_json, model_name, model_load_name)
    elif model_mode == 'predict':
        prepare_predictions(model_type, leagues, sport_id,
                            country, rating_config, feature_columns, window_size, match_attributes)


if __name__ == '__main__':
    main()
