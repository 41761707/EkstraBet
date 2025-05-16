import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.utils import to_categorical

class ProcessData:
    def __init__(self, matches_df, teams_df, model_type, feature_columns, sequence_length=5):
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

    def get_sequences(self, team_id, game_date):
        # Pobiera sekwencję meczów dla danej drużyny
        team_matches = self.matches_df[
            (((self.matches_df['home_team'] == team_id) | (self.matches_df['away_team'] == team_id)) & (self.matches_df['game_date'] < game_date))
        ]
        
        if len(team_matches) >= self.sequence_length:
            return team_matches.tail(self.sequence_length)[self.feature_columns].values
        else:
            return None

    def process_train_data(self):
        # Krok 2: Mapowanie ID drużyn na indeksy
        self.team_to_idx = {team: idx for idx, team in enumerate(self.teams_df['id'].unique())}
        
        # Krok 3: Generowanie sekwencji
        for _, row in self.matches_df.iterrows():
            # Sekwencja dla gospodarza
            home_seq = self.get_sequences(row['home_team'], row['game_date'])
            
            # Sekwencja dla gościa
            away_seq = self.get_sequences(row['away_team'], row['game_date'])
            
            if home_seq is None or away_seq is None or len(home_seq) != self.sequence_length or len(away_seq) != self.sequence_length:
                continue
            self.X_home_seq.append(home_seq)
            self.X_away_seq.append(away_seq)
            
            # Cel
            if self.model_type == "winner":
                self.y.append(row['result'])
            elif self.model_type == "goals":
                goals = int(row['home_team_goals']) + int(row['away_team_goals'])
                if goals > 6:
                    goals = 6
                self.y.append(goals)
            elif self.model_type == "btts":
                if row['home_team_goals'] > 0 and row['away_team_goals'] > 0:
                    self.y.append(1)
                else:
                    self.y.append(0)
            elif self.model_type == "exact":
                home_team_goals = int(row['home_team_goals']) 
                away_team_goals = int(row['away_team_goals'])
                if home_team_goals > 9:
                    home_team_goals = 9
                if away_team_goals > 9:
                    away_team_goals = 9
                exact_score = home_team_goals * 10 + away_team_goals
                self.y.append(exact_score)
            self.training_info.append([row['id']])

        # Konwersja do numpy
        self.X_home_seq = np.array(self.X_home_seq)
        self.X_away_seq = np.array(self.X_away_seq)
        if self.model_type == "winner":
            self.y = to_categorical(self.y, num_classes=3)
        elif self.model_type == "goals":
            self.y = to_categorical(self.y, num_classes=7)
        elif self.model_type == "btts":
            self.y = to_categorical(self.y, num_classes=2)
        elif self.model_type == "exact":
            self.y = to_categorical(self.y, num_classes=100)
        # Krok 4: Normalizacja cech
        n_samples, n_timesteps, n_features = self.X_home_seq.shape
        self.X_home_seq = self.scaler.fit_transform(self.X_home_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
        self.X_away_seq = self.scaler.transform(self.X_away_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)

        # Krok 5: Podział danych
        split_idx = int(0.9 * len(self.X_home_seq))
        start_idx = int(0.1 * len(self.X_home_seq))
        return (
            (self.X_home_seq[start_idx:split_idx], self.X_away_seq[start_idx:split_idx], self.y[start_idx:split_idx]),
            (self.X_home_seq[split_idx:], self.X_away_seq[split_idx:], self.y[split_idx:]),
            (self.training_info[start_idx:split_idx], self.training_info[split_idx:])
        )
    
    def predict_games(self, model, upcoming_df):
        predictions_list = []
        for _, row in upcoming_df.iterrows():
            print(self.matches_df.tail(20))
            # Sekwencja dla gospodarza
            home_seq = self.get_sequences(row['home_team'], row['game_date'])
            
            # Sekwencja dla gościa
            away_seq = self.get_sequences(row['away_team'], row['game_date'])
            
            if home_seq is None or away_seq is None or len(home_seq) != self.sequence_length or len(away_seq) != self.sequence_length:
                continue
                
            # Przekształcenie sekwencji do odpowiedniego formatu
            home_seq = np.array([home_seq])  # Dodaj wymiar batch
            away_seq = np.array([away_seq])  # Dodaj wymiar batch
            
            # Normalizacja danych
            n_samples, n_timesteps, n_features = home_seq.shape
            home_seq_normalized = self.scaler.fit_transform(home_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
            away_seq_normalized = self.scaler.transform(away_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
            
            # Predykcja
            prediction = model.predict([home_seq_normalized, away_seq_normalized])
            
            # Formatowanie wyniku w zależności od typu modelu
            if self.model_type == "winner":
                result = ["Remis", "Wygrana gospodarzy", "Wygrana gości"][np.argmax(prediction[0])]
                probabilities = prediction[0]
            elif self.model_type == "goals":
                result = f"{np.argmax(prediction[0])} goli"
                probabilities = prediction[0]
            elif self.model_type == "btts":
                result = "Obie strzelą" if np.argmax(prediction[0]) == 1 else "Jedna lub żadna nie strzeli"
                probabilities = prediction[0]
            elif self.model_type == "exact":
                home_team_goals = np.argmax(prediction[0]) // 10 
                away_team_goals = np.argmax(prediction[0]) % 10
                result = f"Wynik {home_team_goals}:{away_team_goals}"
                probabilities = prediction[0]
                
            # Dodanie wyniku do listy
            predictions_list.append({
                'home_team': self.teams_df.loc[self.teams_df['id'] == row['home_team'], 'name'].iloc[0],
                'away_team': self.teams_df.loc[self.teams_df['id'] == row['away_team'], 'name'].iloc[0],
                'game_date': row['game_date'],
                'predicted_result': result,
                'probabilities': probabilities
            })
            
        print(pd.DataFrame(predictions_list))
        return pd.DataFrame(predictions_list)

    def get_data(self):
        return self.team_to_idx, self.X_home_seq, self.X_away_seq, self.y, self.training_info