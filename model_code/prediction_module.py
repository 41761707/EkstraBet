import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import Any

class PredictMatch:
    def __init__(self, matches_df, upcoming_df, teams_df, feature_columns, model, model_type, model_name, window_size, conn, prediction_automate: bool = False, model_config=None) -> None:
        self.predictions_list = []
        self.conn = conn
        self.matches_df = matches_df
        self.upcoming_df = upcoming_df
        self.teams_df = teams_df
        self.feature_columns = feature_columns
        self.model = model
        self.model_type = model_type 
        self.model_name = model_name
        self.sequence_length = window_size
        self.scaler = MinMaxScaler()
        self.prediction_automate = prediction_automate
        self.model_config = model_config
        self.events, self.model_id = self.get_additional_prediction_info()

    def get_additional_prediction_info(self):
        print(f'MODEL NAME: {self.model_name}')
        query_model_id = f"SELECT id FROM models WHERE lower(name) = '{self.model_name}'"
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(query_model_id)
            result = cursor.fetchone()
            model_id = result[0] if result else None
            
            # Pobieranie events z konfiguracji modelu jeśli dostępna
            events = []
            if self.model_config and 'prediction_config' in self.model_config and 'events' in self.model_config['prediction_config']:
                events = self.model_config['prediction_config']['events']
            else:
                print("[ERROR] Brak konfiguracji prediction_config/events w model_config.")
            
            print(f"MODEL ID: {model_id}")
            return events, model_id
            
        except Exception as e:
            print(f"Error fetching model ID: {str(e)}")
            return events, None
        finally:
            cursor.close()

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

    def predict_games(self, model, upcoming_df):
        for _, row in upcoming_df.iterrows():
            # Sekwencja dla gospodarza
            home_seq = self.get_sequences(row['home_team'], row['game_date'])
            # Sekwencja dla gościa
            away_seq = self.get_sequences(row['away_team'], row['game_date'])
            if home_seq is None or away_seq is None or len(home_seq) != self.sequence_length or len(away_seq) != self.sequence_length:
                continue
            # Przekształcenie sekwencji do odpowiedniego formatu
            home_seq = np.array([home_seq]) 
            away_seq = np.array([away_seq])
            # Normalizacja danych
            n_samples, n_timesteps, n_features = home_seq.shape
            home_seq_normalized = self.scaler.fit_transform(home_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
            away_seq_normalized = self.scaler.transform(away_seq.reshape(-1, n_features)).reshape(n_samples, n_timesteps, n_features)
            # Predykcja
            prediction = model.predict([home_seq_normalized, away_seq_normalized])
            self.predictions_list.append(self.create_probability_list_entry(row, prediction))
        if self.prediction_automate:
            self.insert_predictions_into_db()
        else:
            self.print_predictions()

    def predict_match_period(self) -> None:
        #TO-DO: Tu chodzi o to, że jak wyżej możemy tylko jeden mecz przewidzieć
        #To tutaj chcielibysmy móc przewidzieć więcej
        #Docelowo nawet cały sezon do przodu
        #Chodzi o to że po każdym przewidywaniu trzeba jakoś sprytnie wygenerować wynik meczu
        #I na jego podstawie dodać nowy wpis do matches_df
        pass
    
    def create_probability_list_entry(self, row, prediction) -> dict[str, Any]:
        entry = {}
        # Formatowanie wyniku w zależności od typu modelu
        probabilities = prediction[0]
        result = ""
        if self.model_type == "winner":
            # Użycie mapowania z konfiguracji modelu zamiast hardkodowanych wartości
            if self.model_config and 'output_config' in self.model_config and 'label_mapping' in self.model_config['output_config']:
                predicted_class_index = np.argmax(prediction[0])
                result = self.model_config['output_config']['label_mapping'][str(predicted_class_index)]
            else:
                # Fallback na stare hardkodowane wartości
                result = ["Remis", "Wygrana gospodarzy", "Wygrana gości"][np.argmax(prediction[0])]
        elif self.model_type == "goals":
            # Użycie mapowania z konfiguracji modelu zamiast hardkodowanych wartości
            if self.model_config and 'output_config' in self.model_config and 'label_mapping' in self.model_config['output_config']:
                predicted_class_index = np.argmax(prediction[0])
                result = self.model_config['output_config']['label_mapping'][str(predicted_class_index)]
            else:
                # Fallback na stare hardkodowane wartości
                result = f"{np.argmax(prediction[0])} goli"
            #dodajemy OU
            under_2_5 = sum(prediction[0][:3])  # Sum of probabilities for 0, 1, 2 goals
            over_2_5 = sum(prediction[0][3:])   # Sum of probabilities for 3+ goals
            probabilities = np.append(probabilities, [under_2_5, over_2_5, np.argmax(prediction[0])])  # Add U/O to probabilities array
        elif self.model_type == "btts":
            # Użycie mapowania z konfiguracji modelu zamiast hardkodowanych wartości
            if self.model_config and 'output_config' in self.model_config and 'label_mapping' in self.model_config['output_config']:
                predicted_class_index = np.argmax(prediction[0])
                result = self.model_config['output_config']['label_mapping'][str(predicted_class_index)]
            else:
                # Fallback na stare hardkodowane wartości
                result = "Obie strzelą" if np.argmax(prediction[0]) == 1 else "Obie nie strzelą"
        elif self.model_type == "exact":
            # Użycie mapowania z konfiguracji modelu zamiast hardkodowanych wartości
            if self.model_config and 'output_config' in self.model_config and 'label_mapping' in self.model_config['output_config']:
                predicted_class_index = np.argmax(prediction[0])
                result = self.model_config['output_config']['label_mapping'][str(predicted_class_index)]
            else:
                # Fallback na stare hardkodowane wartości
                home_team_goals = np.argmax(prediction[0]) // 10 
                away_team_goals = np.argmax(prediction[0]) % 10
                result = f"Wynik {home_team_goals}:{away_team_goals}"
        # Dodanie wyniku do listy - wersja czytelna dla człowieka
        if not self.prediction_automate:
            entry =  {
            'home_team': self.teams_df.loc[self.teams_df['id'] == row['home_team'], 'name'].iloc[0],
            'away_team': self.teams_df.loc[self.teams_df['id'] == row['away_team'], 'name'].iloc[0],
            'game_date': row['game_date'],
            'predicted_result': result,
            'probabilities': [float(f"{x:.4f}") for x in probabilities],
            'wynik' : f"{row['home_team_goals']}:{row['away_team_goals']}",
            }
        #Dodanie wyniku do listy - wersja do automatyzacji procesu
        else:
            # Indeks wartości z największym prawdopodobieństwem
            if self.model_type == "goals":
                # W przypadku modelu 'goals' na końcu jest przewidywana liczba bramek, więc nie bierzemy jej pod uwagę przy określaniu indeksu
                max_prob_index = np.argmax(probabilities[:-1])
            else:
                max_prob_index = np.argmax(probabilities)
            # Tworzenie listy is_final, gdzie tylko najwyższy indeks ma wartość 1
            # Reszta ma wartość 0
            is_final = [0] * len(probabilities)
            # Ustawienie wartości 1 dla indeksu z najwyższym prawdopodobieństwem
            is_final[max_prob_index] = 1
            entry = {
            'match_id' : row['id'],
            'model_id' : self.model_id,
            'event_id' : self.events,
            'probabilities': [float(f"{x:.6f}") for x in probabilities],
            'is_final' : is_final
            }
        return entry

    def insert_predictions_into_db(self):
        cursor = self.conn.cursor()
        try:
            for element in self.predictions_list:
                for i in range(len(element['probabilities'])):
                    if element['model_id'] is None:
                        #Jeżeli nie znalazł modelu to znaczy, że jedynie testuję!
                        sql_prediction = f"""
                        INSERT INTO predictions(match_id, event_id, model_id, value)
                        VALUES ({element['match_id']}, {element['event_id'][i]}, {element['model_id']}, {element['probabilities'][i]})
                        """
                        print(sql_prediction)
                        if element['is_final'][i] == 1:
                            sql_final = f"""
                                INSERT INTO final_predictions(predictions_id, created_at)
                                VALUES ({prediction_id}, NOW())
                            """
                            print(sql_final)
                    else:
                        sql_prediction = """
                            INSERT INTO predictions(match_id, event_id, model_id, value)
                            VALUES (%s, %s, %s, %s)
                        """
                        values = (
                            element['match_id'],
                            element['event_id'][i],
                            element['model_id'],
                            element['probabilities'][i]
                        )
                        cursor.execute(sql_prediction, values)
                        prediction_id = cursor.lastrowid
                        # Jeśli jest to faktyczna predykcja (is_final == 1), dodajemy do final_predictions
                        if element['is_final'][i] == 1:
                            sql_final = """
                                INSERT INTO final_predictions(predictions_id, created_at)
                                VALUES (%s, NOW())
                            """
                            cursor.execute(sql_final, (prediction_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error inserting predictions: {str(e)}")
        finally:
            cursor.close()

    def print_predictions(self):
        if not self.predictions_list:
            print("No predictions available.")
            return
        print("\n=== Match Predictions ===")
        print("-" * 80)
        for pred in self.predictions_list:
            print(f"Match: {pred['home_team']} vs {pred['away_team']}")
            print(f"Date: {pred['game_date']}")
            print(f"Predicted Result: {pred['predicted_result']}")
            print(f"Probabilities: {pred['probabilities']}")
            if pred['wynik'] != -1:
                print(f"Actual Goals: {pred['wynik']}")
            print("-" * 80)

    def get_predictions(self):
        return self.predictions_list