import numpy as np
import pandas as pd

## @package dataprep
# Moduł DataPrep zawiera funkcje i klasy służące do przygotowania danych do dalszych operacji w programie.
# Wymagane zależności: 
# Moduł 'pandas'
# Moduł 'numpy'

import db_module

##
# Klasa DataPrep odpowiedzialna za przetwarzanie danych i przygotowanie ich do dalszych operacji.
class DataPrep:
    ##
    # Konstruktor klasy DataPrep
    def __init__(self, input_date, leagues, sport_id, country):
        self.input_date = input_date #data w formacie YYYY-MM-DD rozgraniczająca co przewidujemy (upcoming) a co analizujemy (matches)
        self.leagues = leagues #przekazanie pustej tablicy oznacza chęć pobrania wszystkich lig
        self.leagues_str = ",".join(map(str, self.leagues)) #string z id lig
        self.sport_id = sport_id #id sportu używane do filtrowania danych
        self.country = country # -1 oznacza wszystkie kraje
        self.first_tier_leagues = [] #lista lig pierwszej klasy (np. Ekstraklasa)
        self.second_tier_leagues = [] #lista lig drugiej klasy (np. I liga)
        self.conn = db_module.db_connect() #połączenie z bazą danych
        self.matches_df = pd.DataFrame() # DataFrame z danymi historycznymi
        self.teams_df = pd.DataFrame() # DataFrame z danymi drużyn
        self.upcoming_df = pd.DataFrame() # DataFrame z danymi nadchodzących meczów
        self.set_data() #wywołanie funkcji do pobrania danych z bazy danych

    def set_data(self):
        self.get_historical_data()
        self.get_upcoming_data()
        self.get_teams_data()
        self.get_league_tier()

    def get_league_tier(self):
        if self.leagues == []:
            query = f"""
                SELECT id, tier 
                FROM leagues 
            """
        else:
            query = f"""
                SELECT id, tier 
                FROM leagues 
                WHERE id IN ({self.leagues_str})
            """
        self.league_tier_df = pd.read_sql(query, self.conn)
        for index, row in self.league_tier_df.iterrows():
            if row['tier'] == 1:
                self.first_tier_leagues.append(row['id'])
            elif row['tier'] == 2:
                self.second_tier_leagues.append(row['id'])

    def get_historical_data(self):
        if self.leagues == []:
            query = f"""
                SELECT * 
                FROM matches 
                WHERE game_date < '{self.input_date}'
                AND sport_id = {self.sport_id}
                AND result != '0'
            order by game_date asc
            """
        else:
            query = f"""
                SELECT * 
                FROM matches 
                WHERE game_date < '{self.input_date}'
                AND league IN ({self.leagues_str})
                AND sport_id = {self.sport_id}
                AND result != '0'
                #and (home_team_goals < 1 or away_team_goals < 1)
                order by game_date asc
            """
        try:
            self.matches_df = pd.read_sql(query, self.conn)
            self.matches_df['result'] = self.matches_df['result'].replace({'X': 0, '1' : 1, '2' : 2}).astype(int) # 0 - remis, 1 - zwyciestwo gosp. 2 - zwyciestwo goscia
        except Exception as e:
            print("Bład podczas pobierania danych historycznych: {}".format(e))

    def get_upcoming_data(self):
        if self.leagues == []:
            query = f"""
                SELECT id, home_team, game_date, away_team, league, round, season, result
                FROM matches 
                WHERE cast(game_date as date) >= '{self.input_date}'
                AND sport_id = {self.sport_id}
                order by game_date asc
        """
        else:
            query = f"""
                SELECT id, home_team, away_team, game_date, round, league, season, result
                FROM matches 
                WHERE cast(game_date as date) >= '{self.input_date}'
                AND league IN ({self.leagues_str})
                AND sport_id = {self.sport_id}
                order by game_date asc
            """
        try:
            self.upcoming_df = pd.read_sql(query, self.conn)
        except Exception as e:
            print("Bład podczas pobierania danych przyszłych: {}".format(e))
    
    
    def get_teams_data(self):
        '''
        Pobiera dane drużyn z bazy danych na podstawie sportu i kraju.
        Jeśli kraj jest równy -1, pobiera wszystkie drużyny dla danego sportu.
        Jeśli kraj jest podany, pobiera drużyny tylko dla tego kraju.
        '''
        if self.country == -1:
            query = f"""
                SELECT id, name 
                FROM teams 
                WHERE sport_id = {self.sport_id}
            """
        else:
            query = f"""
                SELECT id, name 
                FROM teams 
                WHERE country = {self.country}
                AND sport_id = {self.sport_id}
            """
        try:
            self.teams_df = pd.read_sql(query, self.conn)
        except Exception as e:
            print("Bład podczas pobierania danych drużyn: {}".format(e))
    
    def close_connection(self):
        self.conn.close()

    def get_data(self):
        return self.matches_df, self.teams_df, self.upcoming_df, self.first_tier_leagues, self.second_tier_leagues
    