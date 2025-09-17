import numpy as np
import pandas as pd

# @package dataprep
# Moduł DataPrep zawiera funkcje i klasy służące do przygotowania danych do dalszych operacji w programie.
# Wyragane zależności:
# Moduł 'pandas'
# Moduł 'numpy'

import db_module

##
# Klasa DataPrep odpowiedzialna za przetwarzanie danych i przygotowanie ich do dalszych operacji.


class DataPrep:
    # Konstruktor klasy DataPrep
    def __init__(self, input_date, leagues, sport_id, country, leagues_upcoming):
        # data w formacie YYYY-MM-DD rozgraniczająca co przewidujemy (upcoming) a co analizujemy (matches)
        self.input_date = input_date # Data graniczna miedzy meczami historycznymi a przyszlymi (>= przyszle, < historyczne)
        self.leagues = leagues  # przekazanie pustej tablicy oznacza chęć pobrania wszystkich lig do treningu
        self.leagues_str = ",".join(map(str, self.leagues))  # string z id lig do treningu
        self.leagues_upcoming = leagues_upcoming if leagues_upcoming is not None else leagues.copy() # Liga/ligi dla których generujemy predykcje (domyślnie te same co leagues)
        self.leagues_upcoming_str = ",".join(map(str, self.leagues_upcoming))  # string z id lig dla predykcji
        self.sport_id = sport_id  # id sportu używane do filtrowania danych
        self.country = country  # pusta tablica oznacza wszystkie kraje
        self.country_str = ",".join(map(str, self.country))  # string z id krajow
        self.first_tier_leagues = [] # lista lig pierwszej klasy (np. Ekstraklasa)
        self.second_tier_leagues = []  # lista lig drugiej klasy (np. I liga)
        self.conn = db_module.db_connect()  # połączenie z bazą danych
        self.matches_df = pd.DataFrame()  # DataFrame z danymi historycznymi
        self.teams_df = pd.DataFrame()  # DataFrame z danymi drużyn
        self.upcoming_df = pd.DataFrame()  # DataFrame z danymi nadchodzących meczów
        self.set_data()  # wywołanie funkcji do pobrania danych z bazy danych

    def set_data(self):
        '''
            Funkcja rozruchowa modułu Dataprep - już nie pobiera automatycznie wszystkich danych
            Dane należy pobrać ręcznie wywołując odpowiednie metody get_*
        '''
        # Usunięto automatyczne pobieranie danych - teraz każda metoda get_* zwraca swoje wyniki
        pass

    def get_league_tier(self):
        """
        Pobiera informacje o poziomach (tier) lig z bazy danych i klasyfikuje ligi

        Metoda wykonuje następujące kroki:
        1. Buduje zapytanie SQL w zależności od tego czy określono listę lig:
        - Dla pustej listy lig pobiera wszystkie ligi
        - Dla określonych lig pobiera tylko wybrane
        2. Wykonuje zapytanie i zapisuje wyniki w DataFrame league_tier_df
        3. Klasyfikuje ligi na podstawie kolumny 'tier':
        - Liga tier 1 -> dodaje do listy first_tier_leagues
        - Liga tier 2 -> dodaje do listy second_tier_leagues

        Returns:
            tuple: Krotka zawierająca (first_tier_leagues, second_tier_leagues)
                - first_tier_leagues (list): Lista id lig pierwszego poziomu
                - second_tier_leagues (list): Lista id lig drugiego poziomu

        Uwaga:
            Wymaga wcześniejszego ustawienia:
            - self.leagues (list) - lista lig do filtrowania (może być pusta)
            - self.leagues_str (str) - sformatowana lista lig jako string dla SQL
            - self.conn - aktywne połączenie do bazy danych
        """

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
        league_tier_df = pd.read_sql(query, self.conn)
        first_tier_leagues = []
        second_tier_leagues = []
        for index, row in league_tier_df.iterrows():
            if row['tier'] == 1:
                first_tier_leagues.append(row['id'])
            elif row['tier'] == 2:
                second_tier_leagues.append(row['id'])
        
        # Zachowujemy dane w atrybutach klasy dla kompatybilności
        self.first_tier_leagues = first_tier_leagues
        self.second_tier_leagues = second_tier_leagues
        
        return first_tier_leagues, second_tier_leagues

    def get_historical_data(self):
        """
        Pobiera historyczne dane meczowe z bazy danych i przygotowuje je do analizy.

        Metoda wykonuje następujące operacje:
        1. Buduje odpowiednie zapytanie SQL w zależności od tego czy określono listę lig:
        - Dla pustej listy lig pobiera wszystkie mecze dla danego sportu
        - Dla określonych lig pobiera tylko mecze z wybranych lig
        2. Filtruje mecze według kryteriów:
        - Data meczu wcześniejsza niż input_date
        - Określony sport_id
        - Wynik różny od '0' (nieważny/walkower)
        - Sortuje wyniki według daty meczu rosnąco
        3. Wykonuje zapytanie i zapisuje wyniki w DataFrame matches_df
        4. Konwertuje kolumnę 'result' na wartości liczbowe:
        - 'X' → 0 (remis)
        - '1' → 1 (zwycięstwo gospodarzy)
        - '2' → 2 (zwycięstwo gości)

        Returns:
            DataFrame: Tabela z historycznymi danymi meczowymi
                Kolumny:
                - Wszystkie kolumny z tabeli matches
                - 'result' (int): przekonwertowany wynik meczu

        Wyjątki:
            W przypadku błędu podczas pobierania danych, wyświetla komunikat o błędzie
            ale nie przerywa działania programu.

        Uwagi:
            - Wymaga wcześniejszego ustawienia:
            * self.input_date - data graniczna dla pobieranych meczów
            * self.sport_id - identyfikator sportu
            * self.leagues_str - sformatowana lista lig jako string dla SQL
            * self.conn - aktywne połączenie do bazy danych
            - Wyniki meczów są sortowane chronologicznie (najstarsze pierwsze)
            - Pomija mecze z wynikiem '0' (traktowane jako nieważne)
        """

        if self.leagues == []:
            query = f"""
                SELECT * 
                FROM matches 
                WHERE game_date < cast('{self.input_date}' as date)
                AND sport_id = {self.sport_id}
                AND result != '0'
            order by game_date asc
            """
        else:
            query = f"""
                SELECT * 
                FROM matches 
                WHERE game_date < cast('{self.input_date}' as date)
                AND league IN ({self.leagues_str})
                AND sport_id = {self.sport_id}
                AND result != '0'
                #and (home_team_goals < 1 or away_team_goals < 1)
                order by game_date asc
            """
        try:
            matches_df = pd.read_sql(query, self.conn)
            matches_df['result'] = matches_df['result'].replace({'X': 0, '1': 1, '2': 2}).astype(
                int)  # 0 - remis, 1 - zwyciestwo gosp. 2 - zwyciestwo goscia
            
            # Zachowujemy dane w atrybutach klasy dla kompatybilności
            self.matches_df = matches_df
            return matches_df
        except Exception as e:
            print("Bład podczas pobierania danych historycznych: {}".format(e))
            return pd.DataFrame()

    def get_upcoming_data(self):
        """
        Pobiera nadchodzące mecze z bazy danych na podstawie leagues_upcoming i przygotowuje je do analizy.

        Metoda wykonuje następujące operacje:
        1. Buduje zapytanie SQL w zależności od tego czy określono listę lig do predykcji:
        - Dla pustej listy lig pobiera wszystkie nadchodzące mecze dla danego sportu
        - Dla określonych lig pobiera tylko mecze z wybranych lig (leagues_upcoming)
        2. Filtruje mecze według kryteriów:
        - Data meczu równa lub późniejsza niż input_date
        - Określony sport_id
        - Sortuje wyniki według daty meczu rosnąco
        3. Wybiera tylko kluczowe kolumny:
        - id: identyfikator meczu
        - home_team: nazwa gospodarzy
        - away_team: nazwa gości  
        - game_date: data meczu
        - league: liga
        - round: runda
        - season: sezon
        - result: wynik (jeśli już rozegrany)

        Returns:
            DataFrame: Tabela z nadchodzącymi meczami zawierająca:
                - Wszystkie wybrane kolumny z tabeli matches
                - Posortowana chronologicznie (najbliższe mecze pierwsze)

        Wyjątki:
            W przypadku błędu podczas pobierania danych, wyświetla komunikat o błędzie
            ale nie przerywa działania programu.

        Uwagi:
            - Używa self.leagues_upcoming zamiast self.leagues do filtrowania nadchodzących meczów
            - Pozwala to na generowanie predykcji dla innych lig niż te używane do trenowania
        """

        if self.leagues_upcoming == []:
            query = f"""
                SELECT id, home_team, game_date, away_team, league, round, season, home_team_goals, away_team_goals, result
                FROM matches 
                WHERE cast(game_date as date) >= cast('{self.input_date}' as date)
                AND sport_id = {self.sport_id}
                order by game_date asc
        """
        else:
            query = f"""
                SELECT id, home_team, away_team, game_date, round, league, season, home_team_goals, away_team_goals, result
                FROM matches 
                WHERE cast(game_date as date) >= cast('{self.input_date}' as date)
                AND league IN ({self.leagues_upcoming_str})
                AND sport_id = {self.sport_id}
                order by game_date asc
            """
        try:
            upcoming_df = pd.read_sql(query, self.conn)
            # Zachowujemy dane w atrybutach klasy dla kompatybilności
            self.upcoming_df = upcoming_df
            return upcoming_df
        except Exception as e:
            print("Bład podczas pobierania danych przyszłych: {}".format(e))
            return pd.DataFrame()

    def get_teams_data(self):
        '''
        Pobiera dane drużyn z bazy danych na podstawie sportu i kraju.
        Jeśli kraj jest równy -1, pobiera wszystkie drużyny dla danego sportu.
        Jeśli kraj jest podany, pobiera drużyny tylko dla tego kraju.
        
        Returns:
            DataFrame: Tabela z danymi drużyn zawierająca kolumny:
                - id: identyfikator drużyny
                - name: nazwa drużyny
        '''
        if self.country == []:
            query = f"""
                SELECT id, name 
                FROM teams 
                WHERE sport_id = {self.sport_id}
            """
        else:
            query = f"""
                SELECT id, name 
                FROM teams 
                WHERE country in ({self.country_str})
                AND sport_id = {self.sport_id}
            """
        try:
            teams_df = pd.read_sql(query, self.conn)
            # Zachowujemy dane w atrybutach klasy dla kompatybilności
            self.teams_df = teams_df
            return teams_df
        except Exception as e:
            print("Bład podczas pobierania danych drużyn: {}".format(e))
            return pd.DataFrame()

    def close_connection(self):
        ''' Zamykanie połączenia'''
        self.conn.close()
