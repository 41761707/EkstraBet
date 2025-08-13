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
        """Wyświetla statystyki ligowe w rozwijanym panelu.
        
        Funkcja pokazuje liczbę rozegranych meczów w danej lidze i sezonie,
        a jeśli mecze zostały rozegrane, wywołuje moduł statystyk ligowych.
        """
        with st.expander("Statystyki ligowe"):
            query = '''
                SELECT COUNT(*) 
                FROM matches 
                WHERE league = %s AND season = %s AND result != '0'
            '''
            cursor = self.conn.cursor()
            try:
                cursor.execute(query, (self.league, self.season))
                no_games = cursor.fetchone()
                
                st.header(f"Charakterystyki ligi: {self.name}")
                st.subheader(f"Do tej pory rozegrano {no_games[0]} meczów w ramach ligi: {self.name}")
                
                if no_games[0] > 0:
                    # Wywołanie modułu statystyk ligowych
                    stats_module.league_charachteristics(
                        self.conn, self.league, self.season, 
                        self.teams_dict, no_games[0]
                    )
            finally:
                cursor.close()

    def prediction_stats(self):
        """
        Wyświetla statystyki predykcji dla wybranej ligi i sezonu.
        Pozwala użytkownikowi wybrać zakres rund oraz opcję podatku.
        """
        with st.expander(f"Statystyki predykcji"):
            st.header(f"Podsumowanie predykcji wykonanych dla ligi {self.name} w sezonie {self.years}")
            # Wybór zakresu rund do analizy
            if self.round > 1:
                rundy_dostepne = [x + 1 for x in range(self.round)]
                first_round, last_round = st.select_slider("Zakres analizowanych rund",
                    options=rundy_dostepne,
                    value=(self.round, self.round)
                )
            else:
                first_round, last_round = 1, 1
            tax_flag = st.checkbox("Uwzględnij podatek 12%")
            rounds = list(range(first_round, last_round + 1))
            if not rounds:
                st.warning("Brak dostępnych rund do analizy.")
                return
            rounds_str = ','.join(map(str, rounds))
            query = f""" league = {self.league}
                    AND season = {self.season}
                    AND round IN ({rounds_str}) 
                    AND result != '0' """
            # Wywołanie funkcji generującej statystyki
            stats_module.generate_statistics(query, 
                                             tax_flag, 
                                             self.conn, 
                                             self.EV_plus,
                                             'all')
        # Statystyki porównawcze między drużynami
        with st.expander(f"Statystyki predykcji w sezonie {self.years} - porównania między drużynami"):
            stats_module.aggregate_team_acc(self.teams_dict, 
                                            self.league, self.season, 
                                            self.conn)

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
        team_name = self.get_team_name(team_id)
        if not team_name:
            raise ValueError(f"Nie znaleziono drużyny o ID: {team_id}")
        match_data = self.get_team_matches(team_id)
        processed_data = self.process_match_data(match_data, team_id, team_name)
        return processed_data

    def match_pred_summary(self, id, result, home_goals, away_goals):
        """Generuje podsumowanie predykcji i zakładów dla pojedynczego meczu.
        
        Args:
            id (int): ID meczu w bazie danych
            result (str): Wynik meczu (1, X, 2)
            home_goals (int): Liczba goli gospodarzy
            away_goals (int): Liczba goli gości
            
        Wyświetla tabelę porównującą przewidywania z rzeczywistymi wynikami
        dla typów zakładów: OU (over/under), BTTS (both teams to score) i rezultatu.
        """
        # Stałe dla identyfikatorów zdarzeń
        #To sa wartosci z bazy, przepisałem, żeby nie musieć tego każdorazowo wyciągać z bazy danych
        #Czy to dobre podejście? Pewnie nie, ale potem się tym zajmę
        EVENT_IDS = {
            'HOME_WIN': 1,
            'DRAW': 2,
            'AWAY_WIN': 3,
            'OVER_2_5': 8,
            'UNDER_2_5': 12,
            'BTTS_YES': 6,
            'BTTS_NO': 172
        }
        st.header("Pomeczowe statystyki predykcji i zakładów")  
        # Pobieranie predykcji z bazy danych
        query = """SELECT p.event_id as event_id, e.name as name 
                   FROM predictions p 
                   JOIN final_predictions fp ON p.id = fp.predictions_id
                   JOIN events e ON p.event_id = e.id 
                   WHERE match_id = %s"""
        final_predictions_df = pd.read_sql(query, self.conn, params=(id,))
        
        # Inicjalizacja struktury na wyniki
        results = {
            'OU': {'prediction': '', 'outcome': '', 'correct': 'NIE'},
            'BTTS': {'prediction': '', 'outcome': '', 'correct': 'NIE'},
            'RESULT': {'prediction': '', 'outcome': '', 'correct': 'NIE'}
        }
        # Obliczenie rzeczywistych wyników
        total_goals = home_goals + away_goals
        ou_result = total_goals > 2.5
        btts_result = home_goals > 0 and away_goals > 0
        
        # Ustalenie tekstowych opisów rzeczywistych wyników
        results['OU']['outcome'] = 'Powyżej 2.5 gola' if ou_result else 'Poniżej 2.5 gola'
        results['BTTS']['outcome'] = 'Obie drużyny strzelą' if btts_result else 'Obie drużyny nie strzelą'
        
        # Ustalenie wyniku meczu
        if result == '1':
            results['RESULT']['outcome'] = 'Zwycięstwo gospodarza'
        elif result == 'X': 
            results['RESULT']['outcome'] = 'Remis'
        else:
            results['RESULT']['outcome'] = 'Zwycięstwo gościa'
        
        # Mapowanie predykcji na rzeczywiste wyniki
        for _, row in final_predictions_df.iterrows():
            event_id = row['event_id']
            
            # Sprawdzenie predykcji wyniku meczu (1X2)
            if event_id in (EVENT_IDS['HOME_WIN'], EVENT_IDS['DRAW'], EVENT_IDS['AWAY_WIN']):
                results['RESULT']['prediction'] = row['name']
                if ((result == '1' and event_id == EVENT_IDS['HOME_WIN']) or 
                    (result == 'X' and event_id == EVENT_IDS['DRAW']) or 
                    (result == '2' and event_id == EVENT_IDS['AWAY_WIN'])):
                    results['RESULT']['correct'] = 'TAK'
                    
            # Sprawdzenie predykcji over/under
            elif event_id in (EVENT_IDS['OVER_2_5'], EVENT_IDS['UNDER_2_5']):
                results['OU']['prediction'] = row['name']
                if ((not ou_result and event_id == EVENT_IDS['UNDER_2_5']) or 
                    (ou_result and event_id == EVENT_IDS['OVER_2_5'])):
                    results['OU']['correct'] = 'TAK'
                    
            # Sprawdzenie predykcji BTTS
            elif event_id in (EVENT_IDS['BTTS_YES'], EVENT_IDS['BTTS_NO']):
                results['BTTS']['prediction'] = row['name']
                if ((not btts_result and event_id == EVENT_IDS['BTTS_NO']) or 
                    (btts_result and event_id == EVENT_IDS['BTTS_YES'])):
                    results['BTTS']['correct'] = 'TAK'
        
        # Przygotowanie danych do wyświetlenia w tabeli
        data = {
            'Zdarzenie': list(results.keys()),
            'Predykcja': [v['prediction'] for v in results.values()],
            'Obserwacja': [v['outcome'] for v in results.values()],
            'Czy przewidywanie poprawne?': [v['correct'] for v in results.values()]
        }
        
        # Tworzenie i wyświetlenie DataFrame
        df = pd.DataFrame(data)
        df.index = range(1, len(df) + 1)  # Indeksowanie od 1
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def generate_h2h(self, match_id):
        """Generuje historię bezpośrednich spotkań (head-to-head) dla danego meczu.
        
        Args:
            match_id (int): ID meczu, dla którego generujemy statystyki h2h
            
        Wyświetla listę ostatnich spotkań między drużynami w formacie:
        data | gospodarz | wynik | gość
        """
        team_query = "SELECT home_team, away_team FROM matches WHERE id = %s"
        teams = pd.read_sql(team_query, self.conn, params=(match_id,))
        if teams.empty:
            st.warning("Nie znaleziono meczu o podanym ID")
            return
        home_id, away_id = teams.iloc[0]['home_team'], teams.iloc[0]['away_team']
        h2h_query = f"""
            SELECT 
                m.game_date AS date, 
                t1.name AS home_team, 
                m.home_team_goals AS home_goals, 
                t2.name AS away_team, 
                m.away_team_goals AS away_goals
            FROM matches m
            JOIN teams t1 ON m.home_team = t1.id
            JOIN teams t2 ON m.away_team = t2.id
            WHERE ((m.home_team = {home_id} AND m.away_team = {away_id})
               OR (m.home_team = {away_id} AND m.away_team = {home_id}))
            AND m.result != '0'
            ORDER BY m.game_date DESC
            LIMIT {self.h2h}
        """
        h2h_df = pd.read_sql(h2h_query, self.conn)
        # Przygotowanie i wyświetlenie wyników
        if not h2h_df.empty:
            st.header(f"Ostatnie {min(self.h2h, len(h2h_df))} bezpośrednie spotkania")
            matches_data = {
                'dates': h2h_df['date'].dt.strftime('%d.%m.%y').tolist(),
                'home_teams': h2h_df['home_team'].tolist(),
                'home_scores': h2h_df['home_goals'].tolist(),
                'away_teams': h2h_df['away_team'].tolist(),
                'away_scores': h2h_df['away_goals'].tolist()
            }
            tables_module.matches_list_h2h(matches_data['dates'],
                                           matches_data['home_teams'],
                                           matches_data['home_scores'],
                                           matches_data['away_teams'],
                                           matches_data['away_scores'])
        else:
            st.header("Brak bezpośrednich spotkań między drużynami w bazie danych")

    def get_match_predictions(self, match_id: int) -> dict:
        """Pobiera predykcje dla meczu z bazy danych.
        Args:
            match_id: ID meczu
            
        Returns:
            Słownik z predykcjami lub None jeśli brak danych
        """
        # Definicja identyfikatorów zdarzeń predykcji
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
            return (sum(goals_no[:1]), sum(goals_no[1:]), 'OU 0.5')
        elif self.ou_line < 2:
            return (sum(goals_no[:2]), sum(goals_no[2:]), 'OU 1.5')
        elif self.ou_line < 3:
            return (sum(goals_no[:3]), sum(goals_no[3:]),'OU 2.5')
        elif self.ou_line < 4:
            return (sum(goals_no[:4]), sum(goals_no[4:]), 'OU 3.5')
        else: 
            return (sum(goals_no[:5]), sum(goals_no[5:]), 'OU 4.5')
        
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
    
    def display_odds_comparison(self, odds_dict: dict, bookie_dict : dict) -> None:
        """Wyświetla porównanie kursów bukmacherskich w formie wykresu słupkowego.
        
        Args:
            odds_dict: Słownik z kursami dla różnych zdarzeń
            bookie_dict: Słownik mapujący nazwy bukmacherów na ID
        """
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

    def display_recommended_bets(self, predictions, odds_dict, bookie_dict_reversed) -> None:
        """Wyświetla rekomendowane zakłady na podstawie predykcji i kursów.
        
        Args:
            predictions (dict): Słownik z predykcjami
            odds_dict (dict): Słownik z kursami bukmacherskimi
            bookie_dict_reversed (dict): Odwrócony słownik bukmacherów
        """   
        st.header("Proponowane zakłady na mecz przez model:")
        # Przygotowanie danych o zdarzeniach
        events_data = [
            ('Zwycięstwo gospodarza', 'home_win', 'home'),
            ('Remis', 'draw', 'draw'),
            ('Zwycięstwo gościa', 'guest_win', 'away'),
            ('BTTS NIE', 'btts_no', 'btts_no'),
            ('BTTS TAK', 'btts_yes', 'btts_yes'),
            ('Under 2.5', 'under_2_5', 'under'),
            ('Over 2.5', 'over_2_5', 'over')
        ]
        # Obliczanie wartości oczekiwanej (EV) i najlepszego bukmachera
        results = []
        for event_name, pred_key, odds_key in events_data:
            if pred_key in predictions and odds_key in odds_dict:
                max_odds = max(odds_dict[odds_key][1:])
                bookie_idx = np.argmax(odds_dict[odds_key][1:]) + 1
                ev = round(predictions[pred_key] * max_odds - 1, 2)
                bookie_name = bookie_dict_reversed.get(bookie_idx, 'Nieznany')
                results.append((event_name, ev, bookie_name))
        # Tworzenie i formatowanie DataFrame
        df = pd.DataFrame(results, columns=['Zdarzenie', 'VB', 'Bukmacher'])
        df.index = range(1, len(df) + 1)
        df['VB'] = df['VB'].apply(lambda x: f"{x:.2f}")
        
        # Podświetlenie komórek i wyświetlenie tabeli
        styled_df = df.style.applymap(graphs_module.highlight_cells_EV, subset=['VB'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    def show_predictions(self, home_goals, away_goals, id, result) -> None:
        """Wyświetla predykcje i kursy dla danego meczu.
        Args:
            home_goals (int): Liczba goli gospodarzy
            away_goals (int): Liczba goli gości
            id (int): ID meczu
            result (str): Wynik meczu (1, X, 2)
            """
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
        bookie_dict_reversed = {v: k for k, v in bookie_dict.items()}
        odds_dict = self.get_bookmaker_odds(id, bookie_dict, predictions)
        #Pokaż porównanie kursów bukmacherskich
        self.display_odds_comparison(odds_dict, bookie_dict)
        if predictions is not None:
            # Wyświetl rekomendowane zakłady
            self.display_recommended_bets(predictions, odds_dict, bookie_dict_reversed)
            if result != '0':
                self.match_pred_summary(id, result, home_goals, away_goals)



    def generate_schedule(self, round, date_range):
        """Generuje harmonogram meczów dla wybranej rundy lub zakresu dat.
        
        Args:
            round (int): Numer rundy (0 dla wyboru według daty)
            date_range (tuple): Krotka (start_date, end_date) używana gdy round=0
            
        Wyświetla listę meczów z przyciskami do szczegółów każdego spotkania.
        """
        query = """
            SELECT 
                m.id as id, 
                m.home_team as home_id, 
                t1.name as home, 
                m.away_team as guest_id, 
                t2.name as guest, 
                m.game_date as date, 
                m.result as result, 
                m.home_team_goals as h_g, 
                m.away_team_goals as a_g
            FROM matches m 
            JOIN teams t1 ON t1.id = m.home_team 
            JOIN teams t2 ON t2.id = m.away_team 
            WHERE m.league = %s AND m.season = %s
        """
        params = [self.league, self.season]
        
        # Dodanie warunków w zależności od trybu (wybór rundy lub daty)
        if round == 0:
            start_date, end_date = date_range
            query += " AND m.game_date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        else:
            query += " AND m.round = %s"
            params.append(round)
            
        query += " ORDER BY m.game_date"
        
        # Wykonanie zapytania
        schedule_df = pd.read_sql(query, self.conn, params=params)
        
        # Generowanie interfejsu dla każdego meczu
        for _, row in schedule_df.iterrows():
            self.generate_match_button(row)
    
    def generate_match_button(self, row):
        """Generuje przycisk i szczegóły dla pojedynczego meczu.
        
        Args:
            row (pd.Series): Wiersz DataFrame z danymi meczu
        """
        # Budowanie etykiety przycisku
        button_label = f"{row.home} - {row.guest}, data: {row.date.strftime('%d.%m.%y %H:%M')}"
        
        # Dodanie wyniku jeśli mecz się zakończył
        if row.result != '0':
            button_label += f", wynik spotkania: {row.h_g} - {row.a_g}"
        
        # Wyświetlenie przycisku i paneli szczegółów
        if st.button(button_label, use_container_width=True, key=f"match_{row.id}"):
            tab1, tab2, tab3 = st.tabs(["Predykcje i kursy", "Statystyki pomeczowe", "Dla developerów"])
            with tab1:
                self.show_predictions(row.h_g, row.a_g, row.id, row.result)     
            with tab2:
                status_msg = "Statystyki pomeczowe" if row.result != '0' else "Statystyki pomeczowe dostępne po zakończeniu spotkania"
                st.header(status_msg)
                if row.result != '0':
                    self.display_match_statistics()      
            with tab3:
                self.display_dev_data(row)

    def display_match_statistics(self):
        """Wyświetla statystyki pomeczowe dla aktualnie wybranego meczu.
        """
        pass
        #TO-DO implementacja

    def display_dev_data(self, row):
        """Wyświetla szczegółowe dane techniczne meczu dla developerów.
        
        Args:
            row (pd.Series): Wiersz DataFrame z danymi meczu
        """
        st.header("Dane dla developerów")
        dev_data = {
            "ID meczu": row.id,
            "ID Ligi": self.league,
            "ID sezonu": self.season,
            "Wynik meczu (1/X/2)": row.result,
            "Gole gospodarzy": row.h_g,
            "Gole gości": row.a_g,
            "Data meczu": row.date.strftime('%d.%m.%y %H:%M'),
            "Drużyna gospodarzy": f"{row.home_id} - {row.home}",
            "Drużyna gości": f"{row.guest_id} - {row.guest}"
        }
        for key, value in dev_data.items():
            st.write(f"{key}: {value}")

    def prediction_accuracy(self, outcomes, event_name) -> None:
        """Oblicza i wyświetla skuteczność predykcji dla danego zdarzenia.
        Args:
            outcomes (list): Lista wyników predykcji (1 - poprawna, 0 - niepoprawna)
            event_name (str): Nazwa zdarzenia, dla którego obliczana jest skuteczność
        """
        suma = sum(outcomes)
        liczba = len(outcomes)
        st.write(f"Skuteczność predykcji dla zdarzenia {event_name}")
        data = {
            'Zdarzenie': [event_name],
            'Wszystkie': [liczba],
            'Poprawne': [suma],
            'Skuteczność' : [str(round((suma * 100 / liczba), 2)) + "%"]
            }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        graphs_module.generate_pie_chart(['Niepoprawne', 'Poprawne'], [liczba - suma, suma])

    def predicts_per_team(self, team_name: str, key: int) -> None:
        """Wyświetla statystyki skuteczności predykcji dla wybranej drużyny.
        
        Generuje wykresy kołowe przedstawiające skuteczność predykcji:
        - Over/Under (OU)
        - Both Teams To Score (BTTS)
        - Wynik meczu (Rezultat)
        dla ostatnich N meczów wybranej drużyny.

        Args:
            team_name (str): Nazwa drużyny do wyświetlenia w nagłówku
            key (int): ID drużyny w bazie danych

        Returns:
            None: Funkcja wyświetla wyniki bez zwracania wartości
        """
        # Zapytanie SQL pobierające predykcje dla drużyny
        query = f"""
            SELECT event_id, outcome 
            FROM predictions p 
            JOIN final_predictions f ON p.id = f.predictions_id 
            JOIN matches m ON m.id = p.match_id 
            WHERE (m.home_team = {key} OR m.away_team = {key}) and m.season = {self.season}
            AND m.result != '0' 
            ORDER BY m.game_date DESC
        """
        predicts_df = pd.read_sql(query, self.conn)
        # Inicjalizacja list na wyniki
        result_outcomes = []
        btts_outcomes = []
        ou_outcomes = []
        counter = 0
        # Przetwarzanie predykcji - wykresy kołowe
        if len(predicts_df) > 0:
            for _, row in predicts_df.iterrows():
                counter += 1
                if counter == self.games * 3 + 1:
                    break
                # Kategoryzacja wyników według typu zdarzenia
                if row['event_id'] in (1, 2, 3):  # Wynik meczu
                    result_outcomes.append(1 if row['outcome'] == 1 else 0)
                elif row['event_id'] in (8, 12):  # Over/Under
                    ou_outcomes.append(1 if row['outcome'] == 1 else 0)
                elif row['event_id'] in (6, 172):  # BTTS
                    btts_outcomes.append(1 if row['outcome'] == 1 else 0)
            matches_count = min(self.games, len(predicts_df) // 3)
            st.header(f"Skuteczność predykcji ostatnich {matches_count} meczów z udziałem drużyny {team_name}")
            # Wyświetlenie wykresów w trzech kolumnach
            col1, col2, col3 = st.columns(3)
            with col1:
                self.prediction_accuracy(ou_outcomes, "OU")
            with col2:
                self.prediction_accuracy(btts_outcomes, "BTTS")
            with col3:
                self.prediction_accuracy(result_outcomes, "Rezultat meczu")
            
            # Generowanie dodatkowych statystyk
            stats_query = f"""(home_team = {key} OR away_team = {key}) AND result != '0' """
            stats_module.generate_statistics(stats_query, 
                                             0, 
                                             self.conn, 
                                             self.EV_plus,
                                             'all')

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
                            graphs_module.vertical_bar_chart(team_data['date'],
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
                
