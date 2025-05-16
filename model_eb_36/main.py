import numpy as np
import sys
from datetime import date, timedelta

#Moduły
import dataprep_module
import ratings_module
import model_module
import process_data
import prediction_module
## @package main
# Moduł main zawiera funkcje i procedury odpowiedzialne za interakcję z użytkownikiem 
# oraz inicjalizację jak i poprawny przepływ działania programu.


def generate_schedule(df):
    schedule = []
    for _, row in df.iterrows():
        schedule.append([row['home_team'], row['away_team']])
    return schedule

def get_matches(leagues, sport_id, country, rating_config, model_type):
    initial_rating = 1500
    second_tier_coef = 0.8
    input_date = date.today() - timedelta(days=7)
    data = dataprep_module.DataPrep(input_date, leagues, sport_id, country)
    matches_df, teams_df, upcoming_df, first_tier_leagues, second_tier_leagues = data.get_data()
    data.close_connection()
    # Tworzenie ratingu
    rating_factory = ratings_module.RatingFactory.create_rating(model_type,
                                                        rating_config[model_type]['rating_type'],  
                                                        matches_df=matches_df.copy(), 
                                                        teams_df=teams_df,
                                                        first_tier_leagues=first_tier_leagues,
                                                        second_tier_leagues=second_tier_leagues,
                                                        initial_rating=initial_rating,
                                                        second_tier_coef=second_tier_coef)

    # Tworzymy kopię oryginalnego DataFrame
    merged_matches_df = matches_df.copy()
    for rating in rating_factory:
        rating.calculate_rating()
        temp_matches_df, _ = rating.get_data()
        
        # Znajdujemy nowe kolumny dodane przez aktualny rating
        new_columns = [col for col in temp_matches_df.columns if col not in merged_matches_df.columns]
        
        # Dodajemy nowe kolumny do głównego DataFrame
        for col in new_columns:
            merged_matches_df[col] = temp_matches_df[col]

    # Zastępujemy oryginalny matches_df połączonym DataFrame
    matches_df = merged_matches_df
    print(matches_df.tail())

    return matches_df, teams_df, upcoming_df

def prepare_predictions(model_type, leagues, sport_id, country, load_weights, 
                      feature_columns, rating_config, window_size):
    """
    Główna funkcja przygotowująca predykcje dla wybranego typu (winner/goals)
    """
    matches_df, teams_df, _ = get_matches(leagues, sport_id, country, rating_config, model_type)
    processor = process_data.ProcessData(matches_df, teams_df, model_type, feature_columns, window_size)
    train_data, val_data, training_info = processor.process_train_data()
    
    analyze_result_distribution(train_data, model_type, "Training Data")
    analyze_result_distribution(val_data, model_type, "Validation Data")
    
    # Wyświetlanie informacji o danych treningowych
    print_training_data_info(train_data, val_data, training_info, 3)
    
    # Model i predykcje
    model = model_module.ModelModule(train_data, val_data, len(feature_columns), model_type, window_size)
    if load_weights == '1':
        model.load_predict_model(rating_config[model_type]['model_path'])
    else:
        if model_type == 'winner':
            model.create_winner_model()
        elif model_type == 'goals':
            model.create_goals_model()
        elif model_type == 'btts':
            model.create_btts_model()
        elif model_type == 'exact':
            model.create_exact_model()
    history = model.train_model()

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
    Analyzes and prints the distribution of results in the dataset
    
    Args:
        data_tuple: Tuple containing (X_home_seq, X_away_seq, y) where y contains one-hot encoded results
        dataset_name: Name of the dataset for printing purposes
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


##
# Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
def main():
    model_type = sys.argv[1] #[winner, goals]
    model_mode = sys.argv[2] #[train, predict]
    load_weights = sys.argv[3] #[1, 0]
    leagues = []
    sport_id = 1
    country = -1
    window_size = 5
    feature_columns = []
    rating_types = ['elo' if model_type == 'winner' or model_type == 'exact' else 'gap']
    
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
        'winner': {'rating_type': rating_types, 'model_path': 'model_winner_dev/best_model.h5'},
        'goals': {'rating_type': rating_types, 'model_path': 'model_goals_dev/best_model.h5'},
        'btts': {'rating_type': rating_types, 'model_path': 'model_btts_dev/best_model.h5'},
        'exact': {'rating_type': rating_types, 'model_path': 'model_exact_dev/best_model.h5'}
    }
    if model_mode == 'train':
        prepare_predictions(model_type, leagues, sport_id, 
                                    country, load_weights, feature_columns, rating_config, window_size)
    elif model_mode == 'predict':
        #Zaimplementowac moduł z przewidywaniem
        matches_df, teams_df, upcoming_df = get_matches(leagues, sport_id, country, rating_config, model_type)
        print(matches_df)
        print(teams_df)
        print(upcoming_df)
        processor = process_data.ProcessData(matches_df, teams_df, model_type, feature_columns, window_size)
        model = model_module.ModelModule([], [], [], [], [])
        model.load_predict_model(rating_config[model_type]['model_path'])
        processor.predict_games(model, upcoming_df)
if __name__ == '__main__':
    main()