import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.utils import to_categorical
from tqdm import tqdm

class ProcessData:
    def __init__(self, matches_df, teams_df, model_type, feature_columns, sequence_length=5, output_config=None):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler()
        self.team_to_idx = None
        self.feature_columns = []
        self.model_type = model_type
        self.feature_columns = feature_columns
        self.training_info = []
        self.X_home_seq, self.X_away_seq, self.y = [], [], []
        self.output_config = output_config

    def get_sequences(self, team_id, game_date):
        # Pobiera sekwencję meczów dla danej drużyny
        team_matches = self.matches_df[
            (((self.matches_df['home_team'] == team_id) | (self.matches_df['away_team'] == team_id)) & (self.matches_df['game_date'] < game_date))
        ]
        
        if len(team_matches) >= self.sequence_length:
            return team_matches.tail(self.sequence_length)[self.feature_columns].values
        else:
            return None

    def map_result_to_class(self, row):
        """
        Mapuje wyniki meczu na klasy na podstawie typu modelu i konfiguracji output_config
        
        Args:
            row: Wiersz z danymi meczu zawierający informacje o wynikach
            
        Returns:
            int: Numer klasy odpowiadający wynikowi meczu
        """
        if self.model_type == "winner":
            return row['result']
        elif self.model_type == "goals":
            goals = int(row['home_team_goals']) + int(row['away_team_goals'])
            # Sprawdzamy maksymalną liczbę klas i ograniczamy wynik
            max_goals = self.output_config.get('classes', 7) - 1
            if goals > max_goals:
                goals = max_goals
            return goals
        elif self.model_type == "btts":
            if row['home_team_goals'] > 0 and row['away_team_goals'] > 0:
                return 1
            else:
                return 0
        elif self.model_type == "exact":
            pass #TO-DO: Implementacja mapowania dla dokładnego wyniku na podstawie configa
        else:
            raise ValueError(f"Nieobsługiwany typ modelu: {self.model_type}")

    def get_default_num_classes(self):
        """
        Zwraca domyślną liczbę klas dla danego typu modelu (dla kompatybilności wstecznej)
        
        Returns:
            int: Domyślna liczba klas
        """
        default_classes = {
            "winner": 3,
            "goals": 7,
            "btts": 2,
            "exact": 100
        }
        return default_classes.get(self.model_type, 2)

    def process_train_data(self):
        # Krok 2: Mapowanie ID drużyn na indeksy
        self.team_to_idx = {team: idx for idx, team in enumerate(self.teams_df['id'].unique())}
        
        # Krok 3: Generowanie sekwencji
        for _, row in tqdm(self.matches_df.iterrows(), total=len(self.matches_df), desc="ProcessData dla spotkań"):
            # Sekwencja dla gospodarza
            home_seq = self.get_sequences(row['home_team'], row['game_date'])
            
            # Sekwencja dla gościa
            away_seq = self.get_sequences(row['away_team'], row['game_date'])
            
            if home_seq is None or away_seq is None or len(home_seq) != self.sequence_length or len(away_seq) != self.sequence_length:
                continue
            self.X_home_seq.append(home_seq)
            self.X_away_seq.append(away_seq)
            
            # Mapowanie wyniku meczu na odpowiednią klasę
            result_class = self.map_result_to_class(row)
            self.y.append(result_class)
            self.training_info.append([row['id']])

        # Konwersja do numpy
        self.X_home_seq = np.array(self.X_home_seq)
        self.X_away_seq = np.array(self.X_away_seq)
        
        # Konwersja do categorical z dynamiczną liczbą klas z konfiguracji
        num_classes = self.output_config.get('classes') if self.output_config else self.get_default_num_classes()
        self.y = to_categorical(self.y, num_classes=num_classes)
        # Krok 4: Normalizacja cech
        n_samples, n_timesteps, n_features = self.X_home_seq.shape
        self.X_home_seq = self.scaler.fit_transform(self.X_home_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
        self.X_away_seq = self.scaler.transform(self.X_away_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)

        # Krok 5: Podział danych
        split_idx = int(0.9 * len(self.X_home_seq))
        start_idx = 0
        return (
            (self.X_home_seq[start_idx:split_idx], self.X_away_seq[start_idx:split_idx], self.y[start_idx:split_idx]),
            (self.X_home_seq[split_idx:], self.X_away_seq[split_idx:], self.y[split_idx:]),
            (self.training_info[start_idx:split_idx], self.training_info[split_idx:])
        )

    def get_data(self):
        return self.team_to_idx, self.X_home_seq, self.X_away_seq, self.y, self.training_info