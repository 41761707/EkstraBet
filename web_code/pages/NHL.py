import streamlit as st
st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

import db_module
import pandas as pd
import graphs_module
import tables_module
import statistics
from pages.nhl_funcs import nhl_schedule_package, nhl_table_package, nhl_stats_package

class HockeySite:
    def __init__(self, conn, name, league):
        self.conn = conn #połączenie z bazą danych
        self.name = name #nazwa ligi
        self.league = league #id ligi
        self.seasons = {} #wszystkie sezony, z których posiadamy mecze w bazie w ramach danej ligi
        self.selected_season = 0 #sezon wybrany przez użytkownika (w formie 2019/20)
        self.season = 0 #id sezonu wybranego przez użytkownika
        self.matches = "" #info o wszystkich meczach w danym sezonie (pobierane jednorazowo aby później usprawnić filtrowanie - nie trzeba za każdym razem pobierać z bazy danych)
        self.date_range = "" #zakres dat do filtrowania meczów
        self.teams_dict = {} #słownik drużyn w danym sezonie
        self.current_team_info = [] #statystyki aktualnie wybranej drużyny
        self.current_team_player_stats = [] #statystyki zawodników aktualnie wybranej drużyny
        self.h2h = 0 #liczba meczów H2H do wyświetlenia
        self.rounds_dict = {'100' : 'Sezon zasadniczy', '200': 'Playoffy'}
        self.selected_round = 100 #Faza sezonu (100 - sezon zasadniczy, 200 - playoffy)
        self.lookback_games = 10  # liczba ostatnich meczów branych pod uwagę w analizie
        self.date_filter = True #czy filtrujemy po dacie
        self.ou_line = 5.5 #linia over/under dla wykresów
        st.header(name)

    @st.cache_data(ttl=300)
    def get_matches(_self, league_id, season_id, round_id):
        """
        Pobiera mecze dla danej ligi i sezonu z cachowaniem.
        
        Args:
            league_id (int): ID ligi
            season_id (int): ID sezonu
            round_id (int): ID rundy (100 dla sezonu zasadniczego, inne dla playoffów)
            
        Returns:
            pd.DataFrame: DataFrame z danymi meczów
        """
        # Warunek filtrowania rundy na podstawie round_id
        if round_id == 100:
            round_condition = "m.round = 100"
        else:
            round_condition = "m.round != 100"
            
        query = f'''SELECT m.id as id, m.game_date as game_date, m.round as round, 
                        t1.name as home_team, t1.id as home_team_id, t1.shortcut as home_team_shortcut, 
                        t2.name as away_team, t2.id as away_team_id, t2.shortcut as away_team_shortcut,
                        m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result,
                        ad.OT as OT, ad.SO as SO, ad.OTwinner as OTwinner, ad.SOwinner as SOwinner,
                        m.home_team_sog, m.away_team_sog, m.home_team_fk, m.away_team_fk, 
                        m.home_team_fouls, m.away_team_fouls, 
                        ad.home_team_pp_goals, ad.away_team_pp_goals,
                        ad.home_team_sh_goals, ad.away_team_sh_goals,
                        ad.home_team_shots_acc, ad.away_team_shots_acc,
                        ad.home_team_saves, ad.away_team_saves,
                        ad.home_team_saves_acc, ad.away_team_saves_acc,
                        ad.home_team_pp_acc, ad.away_team_pp_acc,
                        ad.home_team_pk_acc, ad.away_team_pk_acc,
                        ad.home_team_faceoffs, ad.away_team_faceoffs,
                        ad.home_team_faceoffs_acc, ad.away_team_faceoffs_acc,
                        ad.home_team_hits, ad.away_team_hits,
                        ad.home_team_to, ad.away_team_to,
                        ad.home_team_en, ad.away_team_en
                    FROM matches m 
                    left join hockey_matches_add ad on m.id = ad.match_id
                    join teams t1 on m.home_team = t1.id
                    join teams t2 on m.away_team = t2.id
                    where m.league = {league_id} and m.season = {season_id} and {round_condition}
                    order by m.game_date desc'''
        return pd.read_sql(query, _self.conn)
    
    @st.cache_data(ttl=600)
    def get_seasons(_self):
        """
        Pobiera listę sezonów dla hokeja z cachowaniem.
            
        Returns:
            dict: Słownik {nazwa_sezonu: id_sezonu}
        """
        seasons_query = "SELECT id, years from seasons where id in (select distinct(season) from matches m where m.sport_id = 2) order by years desc"
        cursor = _self.conn.cursor()
        cursor.execute(seasons_query)
        seasons = {years: season_id for season_id, years in cursor.fetchall()}
        cursor.close()
        return seasons
    
    @st.cache_data(ttl=900)
    def get_divisions_cached(_self, league_id):
        """
        Pobiera listę dywizji dla danej ligi z cachowaniem.
        Args:
            league_id (int): ID ligi
        Returns:
            dict: Słownik {id_dywizji: nazwa_dywizji}
        """
        return nhl_table_package.get_divisions(league_id, _self.conn)
    
    @st.cache_data(ttl=900)
    def get_conferences_cached(_self, league_id):
        """
        Pobiera listę konferencji dla danej ligi z cachowaniem.
        Args:
            league_id (int): ID ligi  
        Returns:
            dict: Słownik {id_konferencji: nazwa_konferencji}
        """
        return nhl_table_package.get_conferences(league_id, _self.conn)

    @st.cache_data(ttl=900)
    def get_teams_cached(_self, league_id, season_id):
        """
        Pobiera listę drużyn dla danej ligi i sezonu z cachowaniem.
        
        Args:
            league_id (int): ID ligi
            season_id (int): ID sezonu  
            
        Returns:
            dict: Słownik {id_drużyny: nazwa_drużyny}
        """
        return nhl_table_package.get_teams(league_id, season_id, _self.conn)

    @st.cache_data(ttl=600)
    def get_team_players_stats_cached(_self, team_id, season_id):
        """
        Pobiera statystyki zawodników drużyny z cachowaniem.
        
        Args:
            team_id (int): ID drużyny
            season_id (int): ID sezonu
            
        Returns:
            tuple: (bramkarze_df, zawodnicy_df)
        """
        return nhl_schedule_package.get_team_players_stats(team_id, season_id, _self.conn)

    def generate_site(self):
        self.generate_config()
        self.generate_schedule_tab()
        self.generate_teams_tab()
        self.generate_table_tab()
        self.generate_league_stats_tab()

    def generate_config(self):
        st.subheader("Konfiguracja strony")
        self.date_filter = st.checkbox("Filtruj po dacie", value=True, key='regular_season')
        col1, col2, col3 = st.columns(3)
        with col1:
            self.seasons = self.get_seasons()
            seasons_list = [season for season in self.seasons.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
            self.season = self.seasons[self.selected_season]
        with col2:
            self.selected_round = int(st.selectbox("Faza sezonu", list(self.rounds_dict.keys()), format_func=lambda x: self.rounds_dict[x], key='selected_round'))
        with col3:
            if self.date_filter:
                self.date_range = st.date_input(
                                            "Wybierz zakres dat",
                                            value=(pd.to_datetime('today') - pd.Timedelta(days=1), 
                                                   pd.to_datetime('today') + pd.Timedelta(days=7)),
                                            min_value=pd.to_datetime('2016-01-01'),
                                            max_value=pd.to_datetime('2030-12-31'),
                                            format="YYYY-MM-DD")
            else:
                self.date_range = []
        col4, col5, col6 = st.columns(3)
        with col4:
            self.lookback_games = st.slider("Liczba analizowanych spotkań wstecz", 5, 15, 10)  # liczba ostatnich meczów branych pod uwagę w analizie = st.slider("Liczba analizowanych spotkań wstecz", 5, 15, 10)
        with col5:
            self.ou_line = st.slider("Linia Over/Under", 4.0, 8.0, 5.5, 0.5)
        with col6:
            self.h2h = st.slider("Liczba prezentowanych spotkań H2H", 0, 10, 5)

        # Wybór statystyk do wyświetlania
        st.subheader("Statystyki do wyświetlania")
        self.selected_stats = st.multiselect(
            "Wybierz statystyki, które chcesz wyświetlać:",
            options=["Bramki", "Bramki w pierwszej tercji", "Bramki drużyny/przeciwników", "Strzały celne", "Rezultaty"],
            default=["Bramki", "Bramki w pierwszej tercji", "Bramki drużyny/przeciwników", "Strzały celne", "Rezultaty"],
            help="Możesz wybrać kilka opcji jednocześnie"
        )

        self.matches = self.get_matches(self.league, self.seasons[self.selected_season], self.selected_round)

    def matches_buttons(self, filtered_matches):
        for _, row in filtered_matches.iterrows():
            # Inicjalizacja session_state dla meczu
            state_key = f"nhl_match_state_{row.id}"
            button_key = f"nhl_match_button_{row.id}"
            
            if state_key not in st.session_state:
                st.session_state[state_key] = False
            
            button_label = "{} - {}, data: {}".format(row.home_team, row.away_team, row.game_date.strftime('%d.%m.%y %H:%M'))
            if row.result != '0':
                if row.OTwinner == 1:
                    button_label = button_label + ", wynik po dogrywce: {} - {}".format(int(row.home_goals + 1), int(row.away_goals))
                elif row.OTwinner == 2:
                    button_label = button_label + ", wynik po dogrywce: {} - {}".format(int(row.home_goals), int(row.away_goals + 1))
                elif row.SOwinner == 1:
                    button_label = button_label + ", wynik po rzutach karnych: {} - {}".format(int(row.home_goals + 1), int(row.away_goals))
                elif row.SOwinner == 2:
                    button_label = button_label + ", wynik po rzutach karnych: {} - {}".format(int(row.home_goals), int(row.away_goals + 1))
                else:
                    button_label = button_label + ", wynik spotkania: {} - {}".format(int(row.home_goals), int(row.away_goals))

            if st.button(button_label, use_container_width=True, key=button_key):
                st.session_state[state_key] = not st.session_state[state_key]
            
            if st.session_state[state_key]:
                self.match_details(row)

    def generate_schedule_tab(self):
        filtered_matches = self.matches[:]
        if len(self.date_range) == 2:
            if self.date_filter:
                # Konwersja dat z st.date_input (date objects) na pd.Timestamp dla porównania z datetime64[ns]
                start_date = pd.Timestamp(self.date_range[0])
                end_date = pd.Timestamp(self.date_range[1])
                filtered_matches = filtered_matches[(filtered_matches['game_date'] >= start_date) & (filtered_matches['game_date'] <= end_date)]
        if len(filtered_matches) > 0:
            with st.expander('Mecze dla zadanej konfiguracji: '):
                self.matches_buttons(filtered_matches)
        else:
            st.write("Brak meczów dla wprowadzonej konfiguracji")
    
    def match_details(self, row):
        tabs = st.tabs(["Meczowe predykcje", 
                       "Składy", 
                       "Przebieg meczu", 
                       "Statystyki pomeczowe", 
                       "Boxscore - statystyki zawodników", 
                       "Dla developerów"])
        with tabs[0]:
            nhl_schedule_package.match_predictions(row.id)
        with tabs[1]:
            nhl_schedule_package.match_lineups(row.id, row.home_team, row.home_team_id, row.away_team, row.away_team_id, self.conn)
        with tabs[2]:
            nhl_schedule_package.match_events(row.id, row.home_team, self.conn)
        with tabs[3]:
            if row.OTwinner == 1:
                row.home_goals = row.home_goals + 1
            elif row.OTwinner == 2:
                row.away_goals = row.away_goals + 1
            nhl_schedule_package.match_stats(row)
        with tabs[4]:
            nhl_schedule_package.match_boxscore(row.id, self.conn)
        with tabs[5]:
            nhl_schedule_package.match_dev_info(row, self.league, self.season)

    def generate_teams_tab(self):
        self.teams_dict = self.get_teams_cached(self.league, self.season)
        with st.expander("Zespoły w sezonie {}".format(self.selected_season)):
            st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.selected_season))
            for key, value in self.teams_dict.items():
                # Inicjalizacja session_state dla drużyny
                state_key = f"nhl_team_state_{key}"
                button_key = f"nhl_team_button_{key}"
                
                if state_key not in st.session_state:
                    st.session_state[state_key] = False
                
                button_label = value
                if st.button(button_label, use_container_width=True, key=button_key):
                    st.session_state[state_key] = not st.session_state[state_key]
                
                if st.session_state[state_key]:
                    tabs = st.tabs(["Statystyki drużyny", 
                                   "Skład", 
                                   "Statystyki zawodników", 
                                   "Statystyki predykcji"])
                    self.current_team_info = nhl_schedule_package.get_team_info(key, self.lookback_games, self.matches)
                    if self.current_team_info == []:
                        st.warning("Brak meczów w wybranym sezonie i fazie sezonu.")
                    else:
                        with tabs[0]:
                            self.current_team_stats(value)
                        with tabs[1]:
                            pass
                            #nhl_schedule_package.get_team_roster(key, value, self.conn)
                        with tabs[2]:
                            goalie_df, player_df = self.get_team_players_stats_cached(key, self.season)
                            st.header("Statystyki bramkarzy")
                            st.dataframe(goalie_df)
                            st.header("Statystyki zawodników")
                            st.dataframe(player_df)
                        with tabs[3]:
                            pass
    
    def current_team_stats(self, team_name):
        df = pd.DataFrame(self.current_team_info)
        
        match_ids = df['match_id'].tolist()
        date = df['match_date'].tolist()
        opponent = df['opponent_shortcut'].tolist()
        home_team_names = df['home_team'].tolist()
        away_team_names = df['away_team'].tolist()
        home_team_goals = df['home_team_goals'].tolist()
        away_team_goals = df['away_team_goals'].tolist()
        team_goals = df['team_goals'].tolist()
        opponent_goals = df['opponent_goals'].tolist()
        team_sog = df['team_sog'].tolist()
        opponent_sog = df['opponent_sog'].tolist()
        goals = df.apply(lambda x: x['team_goals'] + x['opponent_goals'], axis=1).tolist()
        results = df['result'].tolist()

        if "Bramki" in self.selected_stats or "Bramki w pierwszej tercji" in self.selected_stats:
            col1, col2 = st.columns(2)
            if "Bramki" in self.selected_stats:
                with col1:
                    with st.container():
                        graphs_module.vertical_bar_chart(date, opponent, goals, team_name, self.ou_line, "Bramki w meczach")
            if "Bramki w pierwszej tercji" in self.selected_stats:
                with col2:
                    with st.container():
                        first_period_goals_dict = nhl_schedule_package.first_period_goals_analysis(match_ids, self.conn)
                        first_period_goals = [first_period_goals_dict.get(match_id, 0) for match_id in match_ids]
                        graphs_module.vertical_bar_chart(date, opponent, first_period_goals, team_name, 1.5, "Bramki w pierwszej tercji")

        if "Bramki drużyny/przeciwników" in self.selected_stats:
            col3, col4 = st.columns(2)
            with col3:
                with st.container():
                    graphs_module.vertical_bar_chart(date, opponent, team_goals, team_name, statistics.mean(team_goals), "Liczba bramek drużyny")
            with col4:
                with st.container():
                    graphs_module.vertical_bar_chart(date, opponent, opponent_goals, team_name, statistics.mean(opponent_goals), "Liczba bramek przeciwników")
        
        if "Strzały celne" in self.selected_stats:
            col5, col6 = st.columns(2)
            with col5:
                with st.container():
                    graphs_module.vertical_bar_chart(date, opponent, team_sog, team_name, statistics.mean(team_sog), "Liczba strzałów celnych drużyny")
            with col6:
                with st.container():
                    graphs_module.vertical_bar_chart(date, opponent, opponent_sog, team_name, statistics.mean(opponent_sog), "Liczba strzałów przeciwników")
        
        if "Rezultaty" in self.selected_stats:
            col7, col8 = st.columns(2)
            with col7:
                with st.container():
                    graphs_module.winner_bar_chart_with_ot(results, team_name)
            with col8:
                with st.container():
                    tables_module.matches_list_with_ot(date, home_team_names, home_team_goals, away_team_names, away_team_goals, results)
    
    def create_table(self, matches, scope):
        team_ids = {team_id: [0] * 10 for team_id in self.teams_dict}
        nhl_table_package.league_table(matches, team_ids, 2, 0, 2, 1, scope)
        table_data = {
            "Drużyna": [self.teams_dict[team_id] for team_id in team_ids.keys()],
            "Mecze": [team_stats[0] for team_stats in team_ids.values()],
            "Wygrane": [team_stats[1] for team_stats in team_ids.values()],
            "Przegrane": [team_stats[3] for team_stats in team_ids.values()],
            "WPD": [team_stats[8] for team_stats in team_ids.values()],
            "PPD": [team_stats[9] for team_stats in team_ids.values()],
            "Bramki": [f"{team_stats[4]}:{team_stats[5]}" for team_stats in team_ids.values()],
            "Różnica bramek": [team_stats[6] for team_stats in team_ids.values()],
            "Punkty": [team_stats[7] for team_stats in team_ids.values()],
        }
        table_df = pd.DataFrame(table_data)
        table_df = table_df.sort_values(by='Punkty', ascending=False)
        table_df = table_df.reset_index(drop=True)
        table_df.index += 1
        table_df.index.name = "Miejsce"
        return table_df

    def generate_table_tab(self):
        '''Generowanie tabeli ligowej dla wybranego sezonu i fazy rozgrywek'''
        with st.expander("Tabele ligowe"):
            regular_season_matches = self.matches[(self.matches['round'] == 100) & (self.matches['result'] != '0')]
            standing = self.create_table(regular_season_matches, 'all')
            tabs = st.tabs([
                "Tabela sezonu zasadniczego", 
                "Tabela - konferencje",
                "Tabela - dywizje",
                "Tabela domowa", 
                "Tabela wyjazdowa"])
            with tabs[0]:
                st.header("Tabela ogólna")
                st.dataframe(
                    standing,
                    use_container_width=True)
            with tabs[1]:
                st.header("Tabela z podziałem na konferencje")
            with tabs[2]:
                st.header("Tabela z podziałem na dywizje")
            with tabs[3]:
                st.dataframe(
                    self.create_table(regular_season_matches, 'home'),
                    use_container_width=True)
            with tabs[4]:
                st.dataframe(
                    self.create_table(regular_season_matches, 'away'),
                    use_container_width=True)

            st.write("Legenda: WPD - wygrane po dogrywce, PPD - przegrane po dogrywce")
            
    def generate_league_stats_tab(self):
        '''Generowanie statystyk ligowych dla wybranego sezonu'''
        with st.expander("Statystyki ligowe"):
            tabs = st.tabs(["Strzały", "Bramki", "Over/Under"])
            with tabs[0]:
                nhl_stats_package.display_shots_stats(self.league, self.season, self.conn, self.selected_round)
            with tabs[1]:
                nhl_stats_package.display_goals_stats(self.league, self.season, self.conn, self.selected_round)
            with tabs[2]:
                nhl_stats_package.display_over_under_stats(self.league, self.season, self.conn, self.selected_round)

if __name__ == '__main__':
    conn = db_module.db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id from leagues where name = 'NHL'")
    league_id = cursor.fetchone()[0]
    nhl = HockeySite(conn, "NHL", league_id)
    cursor.close()
    nhl.generate_site()