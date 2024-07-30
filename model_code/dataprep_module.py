import numpy as np
import pandas as pd

## @package dataprep
# Moduł DataPrep zawiera funkcje i klasy służące do przygotowania danych do dalszych operacji w programie.
# Wymagane zależności: 
# Moduł 'pandas'
# Moduł 'numpy'

##
# Klasa Data odpowiedzialna za przetwarzanie danych i przygotowanie ich do dalszych operacji.
class DataPrep:
    ##
    # Konstruktor klasy DataPrep
    # @param matches_df Lista rozegranych meczów
    # @param teams_df Lista wszystkich drużyn w bazie danych
    # @param upcoming_df Lista przyszłych meczów do rozpatrzenia
    def __init__(self, matches_df, teams_df, upcoming_df):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.upcoming_df = upcoming_df
        self.model_columns = []
        self.model_columns_df = []
    
    def prepare_predict_goals(self):
        for index, _ in self.matches_df.iterrows():
            self.model_columns.append({'id' : index, 
                                       'home_team' : self.matches_df.loc[index, 'home_team'],
                                       'away_team' : self.matches_df.loc[index, 'away_team'],
                                       'game_date' : self.matches_df.loc[index, 'game_date'],
                                       'home_home_att_power' : self.matches_df.at[index, 'home_home_att_power'],
                                       'home_home_def_power' : self.matches_df.at[index, 'home_home_def_power'],
                                       'away_away_att_power' : self.matches_df.at[index, 'away_away_att_power'],
                                       'away_away_def_power' : self.matches_df.at[index, 'away_away_def_power'],
                                       'home_goals_avg' : self.matches_df.at[index, 'home_goals_avg'],
                                       'away_goals_avg' : self.matches_df.at[index, 'away_goals_avg'],
                                       'goals' : self.matches_df.loc[index, 'home_team_goals'] + self.matches_df.loc[index, 'away_team_goals']})
        self.model_columns_df = pd.DataFrame(self.model_columns)

    def prepare_predict_goals_ppb(self):
        for index, _ in self.matches_df.iterrows():
            total_goals = int(self.matches_df.loc[index, 'home_team_goals']) + int(self.matches_df.loc[index, 'away_team_goals'])
            results = [0] * 7
            results[min(total_goals, 6)] = 1
            self.model_columns.append({'id' : index,
                                       'home_team' : self.matches_df.loc[index, 'home_team'],
                                       'away_team' : self.matches_df.loc[index, 'away_team'],
                                       'game_date' : self.matches_df.loc[index, 'game_date'], 
                                       'home_home_att_power' : self.matches_df.at[index, 'home_home_att_power'],
                                       'home_home_def_power' : self.matches_df.at[index, 'home_home_def_power'],
                                       'away_away_att_power' : self.matches_df.at[index, 'away_away_att_power'],
                                       'away_away_def_power' : self.matches_df.at[index, 'away_away_def_power'],
                                       'home_goals_avg' : self.matches_df.at[index, 'home_goals_avg'],
                                       'away_goals_avg' : self.matches_df.at[index, 'away_goals_avg'],
                                       '0_goals' : results[0],
                                       '1_goals' : results[1],
                                       '2_goals' : results[2],
                                       '3_goals' : results[3],
                                       '4_goals' : results[4],
                                       '5_goals' : results[5],
                                       '6_goals' : results[5]})
        self.model_columns_df = pd.DataFrame(self.model_columns)

    def prepare_predict_btts(self):
        for index, _ in self.matches_df.iterrows():
            home_goals = int(self.matches_df.loc[index, 'home_team_goals'])
            away_goals = int(self.matches_df.loc[index, 'away_team_goals'])
            results = [1, 0] if home_goals > 0 and away_goals > 0 else [0, 1]
            self.model_columns.append({'id' : index, 
                                       'home_team' : self.matches_df.loc[index, 'home_team'],
                                       'away_team' : self.matches_df.loc[index, 'away_team'],
                                       'game_date' : self.matches_df.loc[index, 'game_date'],
                                       'home_home_att_power' : self.matches_df.at[index, 'home_home_att_power'],
                                       'home_home_def_power' : self.matches_df.at[index, 'home_home_def_power'],
                                       'home_away_att_power' : self.matches_df.at[index, 'home_away_att_power'],
                                       'home_away_def_power' : self.matches_df.at[index, 'home_away_def_power'],
                                       'home_goals_avg' : self.matches_df.at[index, 'home_goals_avg'],
                                       'away_goals_avg' : self.matches_df.at[index, 'away_goals_avg'],
                                       'btts_yes' : results[0],
                                       'btts_no' : results[1]})
        self.model_columns_df = pd.DataFrame(self.model_columns)

    def prepare_predict_ou(self):
        for index, _ in self.matches_df.iterrows():
            total_goals = int(self.matches_df.loc[index, 'home_team_goals']) + int(self.matches_df.loc[index, 'away_team_goals'])
            results = [0, 1] if total_goals > 2.5 else [1, 0]
            self.model_columns.append({'id' : index, 
                                       'home_team' : self.matches_df.loc[index, 'home_team'],
                                       'away_team' : self.matches_df.loc[index, 'away_team'],
                                       'game_date' : self.matches_df.loc[index, 'game_date'],
                                       'home_home_att_power' : self.matches_df.at[index, 'home_home_att_power'],
                                       'home_home_def_power' : self.matches_df.at[index, 'home_home_def_power'],
                                       'home_away_att_power' : self.matches_df.at[index, 'home_away_att_power'],
                                       'home_away_def_power' : self.matches_df.at[index, 'home_away_def_power'],
                                       'home_goals_avg' : self.matches_df.at[index, 'home_goals_avg'],
                                       'away_goals_avg' : self.matches_df.at[index, 'away_goals_avg'],
                                       'under_2_5' : results[0],
                                       'over_2_5' : results[1]})
        self.model_columns_df = pd.DataFrame(self.model_columns)

    def prepare_predict_winner(self):
        for index, _ in self.matches_df.iterrows():
            result = self.matches_df.loc[index, 'result']
            results = [1, 0, 0] if result == 1 else [0, 1, 0] if result == 0 else [0, 0, 1]
            self.model_columns.append({'id' : index, 
                                       'home_team' : self.matches_df.loc[index, 'home_team'],
                                       'away_team' : self.matches_df.loc[index, 'away_team'],
                                       'game_date' : self.matches_df.loc[index, 'game_date'],
                                       'home_rating' : self.matches_df.loc[index, 'home_rating'],
                                       'away_rating' : self.matches_df.loc[index, 'away_rating'],
                                       'results_home' : results[0],
                                       'results_draw' : results[1],
                                       'results_away' : results[2]})
        self.model_columns_df = pd.DataFrame(self.model_columns)
    
    def turn_match_into_numpy_goals(self, match):
        return [match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg'],
                ]
    
    def turn_match_into_numpy_winner(self, match):
        return [match['home_rating'], 
                match['away_rating'], 
                ]
    
    def turn_match_into_numpy_btts(self, match):
        return [
                match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg']
                ]
    
    def return_last_matches(self, amount, team_id):
        filtered_rows = self.matches_df[(self.matches_df['home_team'] == int(team_id)) | (self.matches_df['away_team'] == int(team_id))].tail(int(amount))
        return filtered_rows
    
    def return_last_matches_one(self, amount, team_id, matches_df):
        filtered_rows = matches_df[(matches_df['home_team'] == int(team_id)) | (matches_df['away_team'] == int(team_id))].tail(int(amount))
        return filtered_rows
    
    def generate_goals_test(self, schedule, ratings, powers, last_five_matches):
        external_test = []
        for pair in schedule:
            match_schedule = []
            home_team_df = self.return_last_matches(4, pair[0])
            away_team_df = self.return_last_matches(4, pair[1])
            home_team_schedule = []
            away_team_schedule = []
            for _, match in home_team_df.iterrows():
                home_team_schedule.append(self.turn_match_into_numpy_goals(match))
            for _, match in away_team_df.iterrows():
                away_team_schedule.append(self.turn_match_into_numpy_goals(match))
            for i in range(len(home_team_schedule)):
                match_schedule.append(home_team_schedule[i])
                match_schedule.append(away_team_schedule[i])
                #print(pair[0], pair[1])
            match_schedule.append( [powers["{}h_att".format(pair[0])], 
                                       powers["{}h_def".format(pair[0])], 
                                       powers["{}a_att".format(pair[1])], 
                                       powers["{}a_def".format(pair[1])],
                                       sum(last_five_matches[pair[0]]) / 5,
                                       sum(last_five_matches[pair[1]]) / 5])
            external_test.append(match_schedule)
        return external_test

    def generate_winner_test(self, schedule, ratings):
        external_test = []
        for pair in schedule:
            match_schedule = []
            home_team_df = self.return_last_matches(4, pair[0])
            away_team_df = self.return_last_matches(4, pair[1])
            home_team_schedule = []
            away_team_schedule = []
            for _, match in home_team_df.iterrows():
                home_team_schedule.append(self.turn_match_into_numpy_winner(match))
            for _, match in away_team_df.iterrows():
                away_team_schedule.append(self.turn_match_into_numpy_winner(match))
            for i in range(len(home_team_schedule)):
                match_schedule.append(home_team_schedule[i])
                match_schedule.append(away_team_schedule[i])
            match_schedule.append([ratings[pair[0]],ratings[pair[1]]])
            #match_schedule.append([self.get_last_elo(pair[0]), self.get_last_elo(pair[1])])
            external_test.append(match_schedule)
        return external_test
    
    def generate_btts_test(self, schedule, ratings, powers, last_five_matches):
        external_test = []
        for pair in schedule:
            match_schedule = []
            home_team_df = self.return_last_matches(4, pair[0])
            away_team_df = self.return_last_matches(4, pair[1])
            home_team_schedule = []
            away_team_schedule = []
            for _, match in home_team_df.iterrows():
                home_team_schedule.append(self.turn_match_into_numpy_btts(match))
            for _, match in away_team_df.iterrows():
                away_team_schedule.append(self.turn_match_into_numpy_btts(match))
            for i in range(len(home_team_schedule)):
                match_schedule.append(home_team_schedule[i])
                match_schedule.append(away_team_schedule[i])
                #print(pair[0], pair[1])
            match_schedule.append( [
                                    powers["{}h_att".format(pair[0])], 
                                    powers["{}h_def".format(pair[0])], 
                                    powers["{}a_att".format(pair[1])], 
                                    powers["{}a_def".format(pair[1])],
                                    sum(last_five_matches[pair[0]]) / 5,
                                    sum(last_five_matches[pair[1]]) / 5])
            external_test.append(match_schedule)
        return external_test
    
    def generate_winner_test_one(self, pair, ratings, matches_df):
        external_test = []
        match_schedule = []
        home_team_df = self.return_last_matches_one(4, pair[0], matches_df)
        away_team_df = self.return_last_matches_one(4, pair[1], matches_df)
        home_team_schedule = []
        away_team_schedule = []
        for _, match in home_team_df.iterrows():
            home_team_schedule.append(self.turn_match_into_numpy_winner(match))
        for _, match in away_team_df.iterrows():
            away_team_schedule.append(self.turn_match_into_numpy_winner(match))
        for i in range(len(home_team_schedule)):
            match_schedule.append(home_team_schedule[i])
            match_schedule.append(away_team_schedule[i])
        match_schedule.append([ratings[pair[0]],ratings[pair[1]]])
        # match_schedule.append([self.get_last_elo(pair[0]), self.get_last_elo(pair[1])])
        external_test.append(match_schedule)
        return external_test
    ##
    # Funkcja odpowiadająca za zwrócenie przygotowanych danych do dalszych operacji
    # @return matches_df Lista rozegranych meczów
    # @return teams_df Lista wszystkich drużyn w bazie danych
    # @return upcoming_df Lista przyszłych meczów do rozpatrzenia
    def get_data(self):
        return self.matches_df, self.teams_df, self.upcoming_df, self.model_columns_df