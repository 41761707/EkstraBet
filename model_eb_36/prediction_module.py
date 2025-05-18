import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class PredictMatch:
    def __init__(self, matches_df, upcoming_df, teams_df, feature_columns, model, model_type, window_size):
        self.matches_df = matches_df
        self.upcoming_df = upcoming_df
        self.teams_df = teams_df
        self.feature_columns = feature_columns
        self.model = model
        self.model_type = model_type 
        self.sequence_length = window_size
        self.scaler = MinMaxScaler()

    def get_sequences(self, team_id, game_date):
        # Pobiera sekwencję meczów dla danej drużyny 
        #TO-DO: usunać redundancję między tą klasą a process_data.py
        team_matches = self.matches_df[
            (((self.matches_df['home_team'] == team_id) | (self.matches_df['away_team'] == team_id)) & (self.matches_df['game_date'] < game_date))
        ]
        
        if len(team_matches) >= self.sequence_length:
            return team_matches.tail(self.sequence_length)[self.feature_columns].values
        else:
            return None

    def predict_next_game(self, model, upcoming_df):
        predictions_list = []
        print("JESTEM W PREDICT NEXT GAME")
        for _, row in upcoming_df.iterrows():
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
                'probabilities': [round(x, 2) for x in probabilities],
                'max_probability': np.max(probabilities)  # Add max probability for sorting
            })
            
        # Sort predictions by max probability in descending order before creating DataFrame
        predictions_list.sort(key=lambda x: x['max_probability'], reverse=True)
        # Remove the helper field before creating DataFrame
        for pred in predictions_list:
            del pred['max_probability']
            
        print(pd.DataFrame(predictions_list))
        return pd.DataFrame(predictions_list)
    
    def predict_match_period(self):
        #TO-DO: Tu chodzi o to, że jak wyżej możemy tylko jeden mecz przewidzieć
        #To tutaj chcielibysmy móc przewidzieć więcej
        #Docelowo nawet cały sezon do przodu
        pass