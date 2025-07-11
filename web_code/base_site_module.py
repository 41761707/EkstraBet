import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

import db_module
import graphs_module
import tables_module
import stats_module

class Base:
    def __init__(self, league, season, name):
        """ Inicjalizacja klasy bazowej dla analizy lig piłkarskich."""
        self.league = league #ID ligi
        self.season = -1 #ID sezonu
        self.round = -1 #Numer kolejki
        self.rounds_list = [] #Lista kolejki
        self.season_list = [] #Lista sezonów
        self.name = '' #Nazwa ligi
        self.no_events = 3 #BTTS, OU, REZULTAT
        self.EV_plus = 0 #EV dla zakładów
        self.teams_dict = {} #Słownik z drużynami
        self.special_rounds = {} #Słownik z nazwami specjalnych kolejek
        self.date = datetime.today().strftime('%Y-%m-%d') # Data w formacie YYYY-MM-DD
        self.conn = db_module.db_connect() # Połączenie z bazą danych
        self.set_config() # Ustawienie konfiguracji na podstawie wybranej ligi
        self.get_teams() # Pobranie drużyn z bazy danych dla danej ligi i sezonu
        self.get_schedule()  # Pobranie terminarza meczów dla danej ligi i sezonu
        self.get_league_tables() # Pobranie tabeli ligowej dla danej ligi i sezonu
        self.get_league_stats() # Pobranie statystyk ligowych dla danej ligi i sezonu
        self.conn.close() # Zamknięcie połączenia z bazą danych

    def get_available_seasons(self) -> dict:
        """
        Pobiera dostępne sezony z bazy danych dla obecnej ligi.
        
        Returns:
            dict: Słownik w formacie {lata: id_sezonu}, np. {'2022/2023': 1}
        """
        season_query = f"""
            SELECT distinct m.season, s.years 
            FROM matches m 
            JOIN seasons s ON m.season = s.id 
            WHERE m.league = {self.league} 
            ORDER BY s.years DESC
        """
        cursor = self.conn.cursor()
        cursor.execute(season_query)
        seasons = {years: season_id for season_id, years in cursor.fetchall()}
        cursor.close()
        return seasons

    def set_season(self) -> None:
        """
        Umożliwia użytkownikowi wybór sezonu przez UI i zapisuje wybór w obiekcie.
        """
        seasons_dict = self.get_available_seasons()
        selected_year = st.selectbox("Sezon", list(seasons_dict.keys()))
        self.season = seasons_dict[selected_year]  # Tylko tutaj modyfikujemy stan!
        self.years = selected_year

    def get_available_rounds(self) -> list:
        """
        Pobiera listę dostępnych kolejek dla bieżącej ligi i sezonu z bazy danych.
        Przetwarza specjalne kolejki (o ID > 100) na czytelne nazwy.

        Returns:
            list: Lista kolejek w formacie [int | str], np. [1, 2, 3, 'Finał']
        """
        rounds = []
        rounds_query = f"""
            SELECT round, game_date 
            FROM matches 
            WHERE league = {self.league} AND season = {self.season} 
            ORDER BY game_date DESC
        """
        cursor = self.conn.cursor()
        cursor.execute(rounds_query)
        rounds_tmp = [
            self.special_rounds[round_id] if round_id > 100 else round_id
            for round_id, _ in cursor.fetchall()
        ]
        rounds_tmp.append(0)  # Dodajemy 0 jako domyślną kolejkę dla dat
        for item in rounds_tmp:
            if item not in rounds:
                rounds.append(item)
        cursor.close()
        return rounds

    def set_round(self) -> None:
        """
        Umożliwia interaktywny wybór kolejki przez użytkownika i aktualizuje stan obiektu.
        Przetwarza wybór użytkownika (w tym specjalne kolejki) na odpowiadające ID.

        Args:
            None (korzysta z atrybutów klasy: self.league, self.season, self.special_rounds)

        Ustawia atrybuty:
            self.rounds_list: lista wszystkich dostępnych kolejek
            self.round: ID wybranej kolejki (int)
        """
        available_rounds = self.get_available_rounds()
        # Interaktywny wybór
        selected_round = st.selectbox("Kolejka", available_rounds)
        # Konwersja nazwy specjalnej kolejki na ID
        if isinstance(selected_round, str):
            selected_round = next(
                round_id 
                for round_id, round_name in self.special_rounds.items()
                if round_name == selected_round
            )
        # Aktualizacja stanu
        self.rounds_list = available_rounds 
        self.round = selected_round

    def set_db_queries(self) -> None:
        """
        Pobiera i ustawia specjalne kolejki oraz informacje o lidze z bazy danych.    
        Wykonuje dwa główne zadania:
        1. Ładuje słownik specjalnych kolejek (id: nazwa) do self.special_rounds
        2. Ustawia datę ostatniej aktualizacji (self.update) i nazwę ligi (self.name)

        Sets:
            self.special_rounds: dict - słownik specjalnych kolejek {id: nazwa}
            self.update: datetime - data ostatniej aktualizacji ligi
            self.name: str - nazwa wybranej ligi

        Raises:
            implicit DatabaseError: jeśli wystąpi błąd podczas wykonywania zapytań SQL
        """
        # Pobranie specjalnych kolejek
        with self.conn.cursor() as cursor:  # Context manager dla automatycznego zamknięcia kursora
            cursor.execute("SELECT id, name FROM special_rounds")
            self.special_rounds = dict(cursor.fetchall())  # Bezpośrednia konwersja na słownik

        # Pobranie informacji o lidze
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT last_update, name FROM leagues WHERE id = %s", 
                (self.league,)
            )
            result = cursor.fetchone()
            
            if result:  # Zabezpieczenie przed brakiem wyników
                self.update, self.name = result
            else:
                raise ValueError(f"Nie znaleziono ligi o ID: {self.league}")

    def set_date_range(self) -> tuple:
        """
        Tworzy interfejs wyboru zakresu dat w Streamlit i zwraca wybrany okres.
        Funkcja działa tylko gdy kolejka nie jest wybrana (wartość 0). Generuje domyślny zakres
        7-dniowy od bieżącej daty i umożliwia jego modyfikację przez użytkownika.

        Returns:
            tuple: Krotka zawierająca:
                - date: Obiekt daty początkowej (datetime.date)
                - date: Obiekt daty końcowej (datetime.date)
                Przykład: (datetime.date(2023, 5, 1), datetime.date(2023, 5, 7))
        """
        # Ustalenie domyślnego zakresu: dzisiaj -> dzisiaj + 7 dni
        today = datetime.today()
        end_date = today + timedelta(days=7)

        # Utworzenie interaktywnego komponentu wyboru dat w Streamlit
        date_range = st.date_input(
            label="Zakres dat (działa tylko, gdy kolejka = 0)",
            value=(today.date(), end_date.date()),  # Domyślny zakres
            min_value=pd.to_datetime('2015-01-01'),  # Ograniczenie dolne
            max_value=pd.to_datetime('2030-12-31'),  # Ograniczenie górne
            format="YYYY-MM-DD"  # Format wyświetlania
        )

        return date_range

    def set_config(self) -> None:
        """
        Konfiguruje główne ustawienia aplikacji poprzez interfejs użytkownika Streamlit.
        
        Wykonuje następujące operacje:
        1. Inicjalizuje połączenie z bazą danych i pobiera podstawowe dane
        2. Wyświetla nagłówek z nazwą ligi i datą aktualizacji
        3. Udostępnia interfejs do konfiguracji parametrów analizy
        4. Umożliwia wybór sezonu, kolejki i zakresu dat

        Sets:
            self.games: int - liczba analizowanych spotkań wstecz
            self.ou_line: float - linia over/under
            self.h2h: int - liczba spotkań head-to-head
            self.date_range: tuple - wybrany zakres dat
            oraz atrybuty ustawiane przez wywoływane metody
        """
        # 1. Inicjalizacja danych z bazy
        self.set_db_queries()
        
        # 2. Wyświetlenie nagłówka sekcji
        st.header(self.name)
        st.write(f"Ostatnia aktualizacja: {self.update}")
        st.subheader("Konfiguracja prezentowanych danych")

        # 3. Konfiguracja głównych parametrów w układzie kolumnowym
        col1, col2, col3 = st.columns(3)
        with col1:
            self.games = st.slider(
                "Liczba analizowanych spotkań wstecz",
                min_value=5,
                max_value=15,
                value=10,
                help="Określa ile ostatnich meczów będzie analizowanych dla każdego zespołu"
            )
        with col2:
            self.ou_line = st.slider(
                "Linia Over/Under",
                min_value=0.5,
                max_value=4.5,
                value=2.5,
                step=0.5,
                help="Próg dla analizy zakładów over/under"
            )
        with col3:
            self.h2h = st.slider(
                "Liczba prezentowanych spotkań H2H",
                min_value=0,
                max_value=10,
                value=5,
                help="Ilość historycznych bezpośrednich spotkań do wyświetlenia"
            )
        # 4. Wybór zakresu danych (sezon/kolejka/daty)
        col4, col5, col6 = st.columns(3)
        with col4:
            self.set_season()  # Ustawia self.season i self.years  
        with col5:
            self.set_round()  # Ustawia self.round i self.rounds_list      
        with col6:
            self.date_range = self.set_date_range()  # Ustawia zakres dat

    def get_teams(self) -> None:
        """
        Pobiera listę drużyn dla wybranej ligi i sezonu z bazy danych.
        Tworzy słownik mapujący ID drużyn na ich nazwy.
        
        Metoda wykonuje następujące operacje:
        1. Wykonuje zapytanie SQL pobierające wszystkie drużyny (zarówno gospodarzy jak i gości)
        dla aktualnie wybranej ligi (self.league) i sezonu (self.season)
        2. Konwertuje wynik na DataFrame pandas
        3. Tworzy słownik {id_druzyny: nazwa_druzyny} i zapisuje go w self.teams_dict

        Sets:
            self.teams_dict: Dict[int, str] - słownik mapujący ID drużyn na ich nazwy
        """
        # Bezpieczne zapytanie SQL z parametryzacją
        query = """
            SELECT DISTINCT t.id, t.name 
            FROM matches m 
            JOIN teams t ON (m.home_team = t.id OR m.away_team = t.id)
            WHERE m.league = %s AND m.season = %s 
            ORDER BY t.name
        """
        # Wykonanie zapytania z parametrami
        all_teams_df = pd.read_sql(
            query, 
            self.conn, 
            params=(self.league, self.season)  # Bezpieczne wstawienie parametrów
        )
        # Konwersja DataFrame do słownika
        self.teams_dict = all_teams_df.set_index('id')['name'].to_dict()

    def get_schedule(self) -> None:
        """
        Wyświetla terminarz meczów w rozwijanych sekcjach w zależności od wybranej kolejki/dat.
        
        Logika prezentacji:
        1. Dla wybranej kolejki > 1 pokazuje dodatkowo terminarz poprzedniej kolejki
        2. Dla specjalnych kolejek (ID >= 100) używa nazw zamiast numerów
        3. Dla kolejki = 0 (wybór po dacie) pokazuje mecze w wybranym zakresie dat
        4. Dodatkowo wyświetla panel z listą wszystkich drużyn w sezonie

        Args:
            None (wykorzystuje atrybuty klasy):
                - self.round: numer bieżącej kolejki (0 dla wyboru po dacie)
                - self.special_rounds: słownik specjalnych kolejek {id: nazwa}
                - self.date_range: krotka (start_date, end_date)
                - self.years: opis sezonu
                - self.teams_dict: słownik drużyn {id: nazwa}
        """
        # 1. Wyświetlenie poprzedniej kolejki (jeśli aktualna > 1)
        if self.round > 1:
            prev_round = self.round - 1
            round_title = (
                self.special_rounds.get(prev_round, prev_round) 
                if prev_round >= 100 
                else prev_round
            ) 
            with st.expander(f"Terminarz, poprzednia kolejka: {round_title}"):
                self.generate_schedule(prev_round, self.date_range)

        # 2. Wyświetlenie aktualnego terminarza
        current_round_title = (
            self.special_rounds.get(self.round, self.round) 
            if self.round >= 100 
            else self.round
        )
        expander_title = (
            f"Terminarz, mecze dla dat: {self.date_range[0]} - {self.date_range[1]}" 
            if self.round == 0 
            else f"Terminarz, aktualna kolejka: {current_round_title}"
        )
        with st.expander(expander_title):
            self.generate_schedule(self.round, self.date_range)

        # 3. Panel z listą drużyn
        with st.expander(f"Zespoły w sezonie {self.years}"):
            self.show_teams(self.teams_dict)

    def get_league_tables(self):
        """
        Generuje interaktywne tabele ligowe w rozwijanej sekcji Streamlit.
        
        Pobiera wyniki meczów z bazy danych i prezentuje je w czterech różnych formatach:
        1. Tradycyjna tabela ligowa (punkty, kolejność)
        2. Tabela wyników domowych
        3. Tabela wyników wyjazdowych
        4. Statystyki Over/Under i BTTS (Both Teams To Score
        """
        with st.expander("Tabele ligowe" ):
            query = """
                SELECT 
                    t1.name AS home_team, 
                    t2.name AS away_team, 
                    home_team_goals, 
                    away_team_goals, 
                    result 
                FROM matches m 
                JOIN teams t1 ON m.home_team = t1.id 
                JOIN teams t2 ON m.away_team = t2.id 
                WHERE league = %s 
                AND season = %s 
                AND result != '0' 
                AND round < 900
            """
            results_df = pd.read_sql(query, self.conn, params=(self.league, self.season))

            tab1, tab2, tab3, tab4 = st.tabs(["Tradycyjna tabela ligowa", "Tabela domowa", "Tabela wyjazdowa", "Tabela OU / BTTS"])
            with tab1:
                st.header("Tradycyjna tabela ligowa")
                tables_module.generate_traditional_table(self.teams_dict, results_df, 'traditional')
            with tab2:
                st.header("Tabela domowa")
                tables_module.generate_traditional_table(self.teams_dict, results_df, 'home')
            with tab3:
                st.header("Tabela wyjazdowa")
                tables_module.generate_traditional_table(self.teams_dict, results_df, 'away')
            with tab4:
                st.header("Tabela OU / BTTS")
                tables_module.generate_ou_btts_table(self.teams_dict, results_df)
                st.write("Drużyny prezentowane są w kolejności alfabetycznej")

    def league_stats(self):
        with st.expander("Statystyki ligowe"):
            query = ''' select count(*) from matches where league = {} and season = {} and result != '0' '''.format(self.league, self.season)
            cursor = self.conn.cursor()
            cursor.execute(query)
            no_games = cursor.fetchall()
            cursor.close()
            st.header("Charakterstyki ligi: {}".format(self.name))
            st.subheader("Do tej pory rozegrano {} meczów w ramach ligi: {}".format(no_games[0][0], self.name))
            if no_games[0][0] > 0:
                stats_module.league_charachteristics(self.conn, self.league, self.season, self.teams_dict, no_games[0][0])

    def prediction_stats(self):
        with st.expander("Statystyki predykcji"):
            st.header("Podsumowanie predykcji wykonanych dla ligi {} w sezonie {}".format(self.name, self.years))
            if self.round > 1:
                first_round, last_round = st.select_slider(
                "Zakres analizowanych rund",
                options=[x+1 for x in range(self.round)],
                value=(self.round,self.round))
            else:
                first_round, last_round = 1, 1
            tax_flag = st.checkbox("Uwzględnij podatek 12%")
            rounds = list(range(first_round, last_round + 1))
            rounds_str =','.join(map(str, rounds))
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where league = {} and season = {} and round in ({}) and result != '0'".format(self.league, self.season, rounds_str)
            stats_module.generate_statistics(query, tax_flag, first_round, last_round, self.no_events, self.conn, self.EV_plus)
        with st.expander("Statystyki predykcji w sezonie {} - porównania między drużynami".format(self.years)):
            stats_module.aggregate_team_acc(self.teams_dict, self.league, self.season, self.conn) 

    def get_league_stats(self): 
        """Pobiera i wyświetla statystyki ligowe oraz predykcje dla wybranej ligi i sezonu."""    
        self.league_stats() # Pobranie i wyświetlenie statystyk ligowych
        self.prediction_stats() # Pobranie i wyświetlenie statystyk predykcji

    def get_team_name(self, team_id: int) -> str:
        """Pobiera nazwę drużyny z bazy danych"""
        query = "SELECT name FROM teams WHERE id = %s"
        team_df = pd.read_sql(query, self.conn, params=(team_id,))
        return team_df.loc[0, 'name'] if not team_df.empty else None
    
    def process_match_data(self, data: pd.DataFrame, team_id: int, team_name: str) -> dict:
        """Przetwarza surowe dane meczowe na gotowy słownik"""
        if data.empty:
            return {
                'date': [],
                'opponent': [],
                'opponent_shortcut': [],
                'team_name': team_name,
                'goals': [],
                'btts': [],
                'home_teams': [],
                'home_goals': [],
                'away_teams': [],
                'away_goals': [],
                'results': []
            }

        return {
            'date': data['date'].tolist(),
            'opponent': [row['guest'] if row['home_id'] == team_id else row['home'] 
                for _, row in data.iterrows()],
            'opponent_shortcut': [row['guest_shortcut'] if row['home_id'] == team_id else row['home_shortcut'] 
                for _, row in data.iterrows()],
            'team_name': team_name,
            'goals': [0.4 if int(row['home_goals']) + int(row['away_goals']) == 0 
                else int(row['home_goals']) + int(row['away_goals']) 
                for _, row in data.iterrows()],
            'btts': [ 1 if int(row['home_goals']) > 0 and int(row['away_goals']) > 0 
                else -1 
                for _, row in data.iterrows()],
            'home_teams': data['home'].tolist(),
            'home_goals': data['home_goals'].tolist(),
            'away_teams': data['guest'].tolist(),
            'away_goals': data['away_goals'].tolist(),
            'results': data['result'].tolist()
        }
    
    def get_team_matches(self, team_id: int) -> pd.DataFrame:
        """Pobiera ostatnie mecze drużyny z bazy danych"""
        query = """
            SELECT 
                m.home_team AS home_id, 
                t1.name AS home, 
                t1.shortcut AS home_shortcut, 
                m.away_team AS guest_id, 
                t2.name AS guest, 
                t2.shortcut AS guest_shortcut, 
                DATE_FORMAT(CAST(m.game_date AS date), '%d.%m') AS date, 
                m.home_team_goals AS home_goals, 
                m.away_team_goals AS away_goals, 
                m.result AS result
            FROM matches m 
            JOIN teams t1 ON t1.id = m.home_team 
            JOIN teams t2 ON t2.id = m.away_team 
            WHERE CAST(m.game_date AS date) <= %s
            AND (m.home_team = %s OR m.away_team = %s) 
            AND m.result <> '0'
            AND m.season = %s
            ORDER BY m.game_date DESC 
            LIMIT %s
        """
        return pd.read_sql(
            query, 
            self.conn, 
            params=(self.date, team_id, team_id, self.season, self.games))

    def single_team_data(self, team_id: int) -> dict:
        """
        Pobiera i przetwarza dane historyczne dla pojedynczej drużyny.
        
        Args:
            team_id (int): ID drużyny, dla której pobierane są dane

        Returns:
            dict: Słownik zawierający przetworzone dane meczowe:
                - dates (list): Lista dat meczów w formacie DD.MM
                - opponents (list): Lista nazw drużyn przeciwnych
                - opponent_shortcuts (list): Lista skrótów nazw przeciwników
                - goals (list): Lista sum bramek w meczu (min. 0.4 dla meczu 0:0)
                - btts (list): Lista flag czy padły bramki obu drużyn (1: tak, -1: nie)
                - team_name (str): Nazwa drużyny
                - home_teams (list): Lista nazw drużyn gospodarzy
                - home_scores (list): Lista bramek gospodarzy
                - away_teams (list): Lista nazw drużyn gości
                - away_scores (list): Lista bramek gości
                - results (list): Lista wyników meczów
        """
        # 1. Pobranie nazwy drużyny
        team_name = self.get_team_name(team_id)
        if not team_name:
            raise ValueError(f"Nie znaleziono drużyny o ID: {team_id}")
        # 2. Pobranie danych meczowych
        match_data = self.get_team_matches(team_id)
        # 3. Przetworzenie danych
        processed_data = self.process_match_data(match_data, team_id, team_name)
        return processed_data

    def match_pred_summary(self, id, result, home_goals, away_goals):
        st.header("Pomeczowe statystyki predykcji i zakładów")
        query = "select f.event_id as event_id, e.name as name from final_predictions f join events e on f.event_id = e.id where match_id = {}".format(id)
        final_predictions_df = pd.read_sql(query, self.conn)
        predicts = [""] * 3
        outcomes = [""] * 3
        correct = ["NIE"] * 3
        ou = 1 if home_goals + away_goals > 2.5 else 0
        btts = 1 if home_goals > 0 and away_goals > 0 else 0
        outcomes[0] = 'Poniżej 2.5 gola' if ou == 0 else 'Powyżej 2.5 gola'
        outcomes[1] = 'Obie drużyny strzelą' if btts == 1 else 'Obie drużyny nie strzelą'
        if result == '1':
            outcomes[2] = 'Zwycięstwo gospodarza'
        elif result == 'X': 
            outcomes[2] = 'Remis'
        else:
            outcomes[2] = 'Zwycięstwo gościa'
        for _, row in final_predictions_df.iterrows():
            if row['event_id'] in (1,2,3):
                predicts[2] = row['name']
                if (result == '1' and row['event_id'] == 1) or (result == 'X' and row['event_id'] == 2) or (result == '2' and row['event_id'] == 3):
                    correct[2] = 'TAK'
            if row['event_id'] in (8,12):
                predicts[0] = row['name']
                if (ou == 0 and row['event_id'] == 12) or (ou == 1 and row['event_id'] == 8):
                    correct[0] = 'TAK'
            if row['event_id'] in (6, 172):
                predicts[1] = row['name']
                if (btts == 0 and row['event_id'] == 172) or (btts == 1 and row['event_id'] == 6):
                    correct[1] = 'TAK'
        final_predictions_df = pd.read_sql(query, self.conn)
        data = {
        'Zdarzenie': ["OU", "BTTS", "REZULTAT"],
        'Predykcja' : [x for x in predicts],
        'Obserwacja' : [x for x in outcomes],
        'Czy przewidywanie poprawne?' : [x for x in correct]
        }
        df = pd.DataFrame(data)
        df.index = range(1, len(df) + 1)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def generate_h2h(self, match_id):
        # Get teams in the match
        query = f"SELECT home_team, away_team FROM matches WHERE id = {match_id}"
        teams_in_match = pd.read_sql(query, self.conn).to_numpy()
        query = f"""
            SELECT m.game_date AS date, t1.name AS home_team, m.home_team_goals AS home_team_goals, 
                t2.name AS away_team, m.away_team_goals AS away_team_goals
            FROM matches m
            JOIN teams t1 ON m.home_team = t1.id
            JOIN teams t2 ON m.away_team = t2.id
            WHERE m.home_team IN ({teams_in_match[0][0]}, {teams_in_match[0][1]})
            AND m.away_team IN ({teams_in_match[0][0]}, {teams_in_match[0][1]})
            AND m.result != '0'
            ORDER BY m.game_date DESC
            LIMIT {self.h2h}
        """
        h2h_df = pd.read_sql(query, self.conn)
        if len(h2h_df) > 0:
            dates = h2h_df['date'].dt.strftime('%d.%m.%y').tolist()
            home_team = h2h_df['home_team'].tolist()
            home_team_score = h2h_df['home_team_goals'].tolist()
            away_team = h2h_df['away_team'].tolist()
            away_team_score = h2h_df['away_team_goals'].tolist()
            st.header(f"Ostatnie {min(self.h2h, len(h2h_df))} bezpośrednie spotkania")
            tables_module.matches_list_h2h(dates, home_team, home_team_score, away_team, away_team_score)
        else:
            st.header("Brak bezpośrednich spotkań między drużynami w bazie danych")

    def get_match_predictions(self, match_id: int) -> dict:
        """Pobiera predykcje dla meczu z bazy danych.
        
        Args:
            match_id: ID meczu
            
        Returns:
            Słownik z predykcjami lub None jeśli brak danych
        """
        prediction_events = {
            'home_win': 1,
            'draw': 2,
            'guest_win': 3,
            'btts_yes': 6,
            'btts_no': 172,
            'exact_goals': 173,
            'over_2_5': 8,
            'under_2_5': 12,
            'zero_goals': 174,
            'one_goal': 175,
            'two_goals': 176,
            'three_goals': 177,
            'four_goals': 178,
            'five_goals': 179,
            'six_plus_goals': 180
        }
        
        predictions = {}
        for name, event_id in prediction_events.items():
            query = f"""
                SELECT value 
                FROM predictions 
                WHERE match_id = {match_id} 
                AND event_id = {event_id}
            """
            result = pd.read_sql(query, self.conn).to_numpy()
            if len(result) > 0:
                predictions[name] = result[0][0]
        
        return predictions if predictions else None
    
    def display_prediction_charts(self, predictions: dict) -> None:
        """Wyświetla wykresy predykcji dla meczu.
            Args:   
                predictions: Słownik z predykcjami meczu
        """
        if predictions is not None:
            goals_no = [predictions['zero_goals'], 
                        predictions['one_goal'], 
                        predictions['two_goals'], 
                        predictions['three_goals'], 
                        predictions['four_goals'], 
                        predictions['five_goals'], 
                        predictions['six_plus_goals']]
            col1, col2 = st.columns(2)
            with col1:
                graphs_module.graph_winner(predictions['home_win'], predictions['draw'], predictions['guest_win'])
            with col2:
                graphs_module.graph_btts(predictions['btts_no'], predictions['btts_yes'])

            col3, col4 = st.columns(2)
            with col3:
                graphs_module.graph_exact_goals(goals_no)
            with col4:
                under_prob, over_prob, label = self.calculate_ou_probabilities(goals_no)
                graphs_module.graph_ou(under_prob, over_prob, label)
    
    def calculate_ou_probabilities(self, goals_no : list) -> tuple:
        """Oblicza prawdopodobieństwa under/over dla różnych linii.
        Args:
            goals_no: Lista z prawdopodobieństwami dla 0, 1, 2, 3, 4, 5 i 6+ goli
        Returns:
            Tuple z sumą prawdopodobieństw dla under i over oraz etykietą linii"""
        if self.ou_line < 1:
            return (
                sum(goals_no[:1]),
                sum(goals_no[1:]),
                'OU 0.5'
            )
        elif self.ou_line < 2:
            return (
                sum(goals_no[:2]),
                sum(goals_no[2:]),
                'OU 1.5'
            )
        elif self.ou_line < 3:
            return (
                sum(goals_no[:3]),
                sum(goals_no[3:]),
                'OU 2.5'
            )
        elif self.ou_line < 4:
            return (
                sum(goals_no[:4]),
                sum(goals_no[4:]),
                'OU 3.5'
            )
        else:
            return (
                sum(goals_no[:5]),
                sum(goals_no[5:]),
                'OU 4.5'
            )
        
    def get_bookmaker_odds(self, match_id: int, bookie_dict: dict, predictions : dict) -> dict:
        """Pobiera kursy bukmacherskie z bazy danych.
        
        Args:
            match_id: ID meczu
            bookie_dict: Słownik mapujący nazwy bukmacherów na ID
            predictions: Słownik z predykcjami
            
        Returns:
            Słownik z kursami
        """
        query = f"""
            SELECT b.name as bookmaker, o.event as event, o.odds as odds 
            FROM odds o 
            JOIN bookmakers b ON o.bookmaker = b.id 
            WHERE match_id = {match_id}
        """
        odds_details = pd.read_sql(query, self.conn)
        bookmakers_no = len(bookie_dict)
        # Inicjalizacja słownika z kursami
        odds = {
            'home': [round(1 / predictions['home_win'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'draw': [round(1 / predictions['draw'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'away': [round(1 / predictions['guest_win'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'btts_yes': [round(1 / predictions['btts_yes'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'btts_no': [round(1 / predictions['btts_no'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'under': [round(1 / predictions['under_2_5'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
            'over': [round(1 / predictions['over_2_5'], 2)] + [0] * (bookmakers_no - 1) if predictions is not None else [0] * bookmakers_no,
        }
        
        # Mapowanie eventów
        event_mapping = {
            1: 'home',
            2: 'draw',
            3: 'away',
            6: 'btts_yes',
            172: 'btts_no',
            8: 'over',
            12: 'under'
        }
        
        # Wypełnienie danych
        for _, row in odds_details.iterrows():
            event_type = event_mapping.get(row.event)
            if event_type:
                bookie_idx = bookie_dict[row.bookmaker]
                odds[event_type][bookie_idx] = row.odds
        
        return odds

    def show_predictions(self, home_goals, away_goals, id, result):
        #Pobierz predykcje dla meczu
        predictions = self.get_match_predictions(id)
        #Jeżeli nie ma predykcji - poinformuj o tym użytkownika
        if predictions is None:
            st.header("Na chwilę obecną brak przewidywań dla wskazanego spotkania")
        # Jeżeli są predykcje - wyświetl je w formie graficznej
        self.display_prediction_charts(predictions)
        if self.h2h > 0:
            self.generate_h2h(id)
        bookie_dict = {
            'USTALONE' : 0,
            'Superbet' : 1,
            'Betclic' : 2,
            'Fortuna': 3,
            'STS' : 4,
            'LvBet': 5,
            'Betfan' : 6,
            'Etoto' : 7,
            'Fuksiarz' : 8,
        }
        bookie_dict_reversed_keys = {
            0: 'USTALONE',
            1: 'Superbet',
            2: 'Betclic',
            3: 'Fortuna',
            4: 'STS',
            5: 'LvBet',
            6: 'Betfan',
            7: 'Etoto',
            8: 'Fuksiarz'
        }
        odds_dict = self.get_bookmaker_odds(id, bookie_dict, predictions)
        col3, col4, col5 = st.columns(3)
        with col3:
            st.write("Porównanie kursów z estymacją na rezultat:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'Gospodarz' : [x for x in odds_dict['home']],
            'Remis' : [x for x in odds_dict['draw']],
            'Gość' : [x for x in odds_dict['away']],
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        with col4:
            st.write("Porównanie kursów z estymacją na OU:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'UNDER 2.5' : [x for x in odds_dict['under']],
            'OVER 2.5' : [x for x in odds_dict['over']]
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        with col5:
            st.write("Porównanie kursów z estymacją na BTTS:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'BTTS TAK' : [x for x in odds_dict['btts_yes']],
            'BTTS NIE' : [x for x in odds_dict['btts_no']]
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        #TO-DO: Przenieść do osobnej funkcji i zredagować
        if predictions is not None:
            st.header("Proponowane zakłady na mecz przez model: ")
            home_win_EV = round((predictions['home_win']) * max(odds_dict['home'][1:]) - 1, 2)
            home_win_bookmaker = np.argmax(odds_dict['home'][1:]) + 1
            draw_EV = round((predictions['draw']) * max(odds_dict['draw'][1:]) - 1, 2)
            draw_bookmaker = np.argmax(odds_dict['draw'][1:]) + 1
            guest_win_EV = round((predictions['guest_win']) * max(odds_dict['away'][1:]) - 1, 2)
            guest_win_bookmaker = np.argmax(odds_dict['away'][1:]) + 1
            btts_no_EV = round((predictions['btts_no']) * max(odds_dict['btts_no'][1:]) - 1, 2)
            btts_no_bookmaker = np.argmax(odds_dict['btts_no'][1:]) + 1
            btts_yes_EV = round((predictions['btts_yes']) * max(odds_dict['btts_yes'][1:]) - 1, 2)
            btts_yes_bookmaker = np.argmax(odds_dict['btts_yes'][1:]) + 1
            under_EV = round((predictions['under_2_5']) * max(odds_dict['under'][1:]) - 1, 2)
            under_bookmaker = np.argmax(odds_dict['under'][1:]) + 1
            over_EV = round((predictions['over_2_5']) * max(odds_dict['over'][1:]) - 1, 2)
            over_bookmaker = np.argmax(odds_dict['over'][1:]) + 1
            events = ['Zwycięstwo gospodarza', 
                    'Remis',
                    'Zwycięstwo gościa',
                    'BTTS NIE',
                    'BTTS TAK',
                    'Under 2.5',
                    'Over 2.5']
            EVs = [home_win_EV, draw_EV, guest_win_EV, btts_no_EV, btts_yes_EV, under_EV, over_EV]
            EV_bookmakers = [bookie_dict_reversed_keys[home_win_bookmaker], 
                            bookie_dict_reversed_keys[draw_bookmaker], 
                            bookie_dict_reversed_keys[guest_win_bookmaker], 
                            bookie_dict_reversed_keys[btts_no_bookmaker], 
                            bookie_dict_reversed_keys[btts_yes_bookmaker], 
                            bookie_dict_reversed_keys[under_bookmaker], 
                            bookie_dict_reversed_keys[over_bookmaker]]
            data = {
            'Zdarzenie': [x for x in events],
            'VB' : ["{:.2f}".format(x) for x in EVs],
            'Bukmacher' : [x for x in EV_bookmakers]
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            styled_df = df.style.applymap(graphs_module.highlight_cells_EV, subset = ['VB'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        if result != '0':
            self.match_pred_summary(id, result, home_goals, away_goals)



    def generate_schedule(self, round, date_range):
        print(round)
        query = f'''select m.id as id, m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.result as result, m.home_team_goals as h_g, m.away_team_goals as a_g
                        from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                        where m.league = {self.league} and m.season = {self.season}'''
        if round == 0:
            start_date, end_date = date_range
            query = query + f" and m.game_date between '{start_date}' and '{end_date}'"
        else:
            query = query + f" and m.round = {round}"
        query = query + ' order by m.game_date'

        schedule_df = pd.read_sql(query,self.conn)
        for index, row in schedule_df.iterrows():
            button_label = "{} - {}, data: {}".format(row.home, row.guest,row.date.strftime('%d.%m.%y %H:%M'))
            if row.result != '0':
                button_label = button_label + ", wynik spotkania: {} - {}".format(row.h_g, row.a_g)
            if st.button(button_label, use_container_width=True):
                tab1, tab2, tab3 = st.tabs(["Predykcje i kursy", "Statystyki pomeczowe", "Dla developerów"])
                if row.result != '0':
                    with tab1:
                        self.show_predictions(row.h_g, row.a_g, row.id, row.result)
                    with tab2:
                        st.write("Statystyki pomeczowe")
                else:
                    self.show_predictions(row.h_g, row.a_g, row.id, row.result)

    def predicts_per_team(self, team_name, key):
        query = "select event_id, outcome from final_predictions f join matches m on m.id = f.match_id where (m.home_team = {} or m.away_team = {}) and m.result != '0' order by m.game_date desc".format(key, key)
        predicts_df = pd.read_sql(query, self.conn)
        result_outcomes = []
        btts_outcomes = []
        ou_outcomes = []
        counter = 0
        #Predykcje - wykresy kołowe
        if len(predicts_df) > 0:
            for _, row in predicts_df.iterrows():
                counter = counter + 1
                if counter == self.games * 3 + 1:
                    break
                if row['event_id'] in (1,2,3):
                    if row['outcome'] == 1:
                        result_outcomes.append(1)
                    else:
                        result_outcomes.append(0)
                if row['event_id'] in (8,12):
                    if row['outcome'] == 1:
                        ou_outcomes.append(1)
                    else:
                        ou_outcomes.append(0)
                if row['event_id'] in (6, 172):
                    if row['outcome'] == 1:
                        btts_outcomes.append(1)
                    else:
                        btts_outcomes.append(0)        
            st.header("Skuteczność predykcji ostatnich {} meczów z udziałem drużyny {}".format(min(self.games, len(predicts_df) // 3), team_name))
            col1, col2, col3 = st.columns(3)
            suma = sum(ou_outcomes)
            liczba = len(ou_outcomes)
            with col1:
                st.write("Skuteczność predykcji dla zdarzenia OU")
                data = {
                    'Zdarzenie': ['OU'],
                    'Wszystkie': [liczba],
                    'Poprawne': [suma],
                    'Skuteczność' : [str(round((suma * 100 / liczba), 2)) + "%"]
                    }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                graphs_module.generate_pie_chart(['Niepoprawne', 'Poprawne'], [liczba - suma, suma])
            suma = sum(btts_outcomes)
            liczba = len(btts_outcomes)
            with col2:
                st.write("Skuteczność predykcji dla zdarzenia BTTS")
                data = {
                    'Zdarzenie': ['BTTS'],
                    'Wszystkie': [liczba],
                    'Poprawne': [suma],
                    'Skuteczność' : [str(round((suma * 100 / liczba), 2)) + "%"]
                    }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                graphs_module.generate_pie_chart(['Niepoprawne', 'Poprawne'], [liczba - suma, suma])
            suma = sum(result_outcomes)
            liczba = len(result_outcomes)
            with col3:
                st.write("Skuteczność predykcji dla REZULTAT")
                data = {
                    'Zdarzenie': ['REZULTAT'],
                    'Wszystkie': [liczba],
                    'Poprawne': [suma],
                    'Skuteczność' : [str(round((suma * 100 / liczba), 2)) + "%"]
                    }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                graphs_module.generate_pie_chart(['Niepoprawne', 'Poprawne'], [liczba - suma, suma])
            #Wykresy z podziałem na typ zdarzenia
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where (home_team = {} or away_team = {}) and result != '0'".format(key, key)
            stats_module.generate_statistics(query, 0, 1, self.round, self.no_events, self.conn, self.EV_plus)

    def show_teams(self, teams_dict: dict) -> None:
        """
        Wyświetla interfejs wyboru drużyn i prezentuje ich statystyki w formie zakładek.
        
        Dla każdej drużyny z przekazanego słownika generuje przycisk, który po kliknięciu
        pokazuje szczegółowe statystyki w dwóch zakładkach:
        1. Statystyki historyczne drużyny
        2. Statystyki predykcji

        Args:
            teams_dict (dict): Słownik drużyn w formacie {id_druzyny: nazwa_druzyny}
        """
        st.header(f"Drużyny grające w {self.name} w sezonie {self.years}:")

        for team_id, team_name in teams_dict.items():
            # Przycisk wyboru drużyny
            if st.button(team_name, use_container_width=True, key=f"team_{team_id}"):
                # Pobranie danych w nowym formacie słownikowym
                team_data = self.single_team_data(team_id)
                # Utworzenie zakładek
                tab1, tab2 = st.tabs(["Statystyki drużyny", "Statystyki predykcji"])
                # Zakładka 1: Statystyki historyczne
                with tab1:
                    # Układ dwukolumnowy dla wykresów
                    col1, col2 = st.columns(2)
                    with col1:
                        with st.container():
                            graphs_module.goals_bar_chart(team_data['date'],
                                team_data['opponent_shortcut'],
                                team_data['goals'],
                                team_data['team_name'],
                                self.ou_line,
                                "Bramki w meczach")        
                    with col2:
                        with st.container():
                            graphs_module.btts_bar_chart(team_data['date'],
                                team_data['opponent_shortcut'],
                                team_data['btts'],
                                team_data['team_name'])
                    # Drugi rząd kolumn
                    col3, col4 = st.columns(2)
                    with col3:
                        with st.container():
                            graphs_module.winner_bar_chart(team_data['opponent'],
                                team_data['home_teams'],
                                team_data['results'],
                                team_data['team_name'])
                    with col4:
                        with st.container():
                            tables_module.matches_list(team_data['date'],
                                team_data['home_teams'],
                                team_data['home_goals'],
                                team_data['away_teams'],
                                team_data['away_goals'],
                                team_data['team_name'])
                
                # Zakładka 2: Statystyki predykcji
                with tab2:
                    self.predicts_per_team(team_data['team_name'], team_id)
                
