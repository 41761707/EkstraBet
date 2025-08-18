import streamlit as st
st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

import base_site_module
import db_module
import pandas as pd
import graphs_module
import tables_module
import statistics
from pages.nhl_funcs import nhl_schedule_package

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
        #self.ou_line = 5.5/6.5 #linia over/under dla NHL
        st.header(name)

    def get_matches(self):
        query = f'''SELECT m.id as id, cast(m.game_date as date) as game_date, m.round as round, 
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
                    join hockey_matches_add ad on m.id = ad.match_id
                    join teams t1 on m.home_team = t1.id
                    join teams t2 on m.away_team = t2.id
                    where m.league = {self.league} and m.season = {self.seasons[self.selected_season]}
                    order by m.game_date desc'''
        self.matches = pd.read_sql(query, self.conn)
    
    def generate_site(self):
        self.generate_config()
        self.generate_schedule_tab()
        self.generate_teams_tab()
        self.generate_table_tab()

    def generate_config(self):
        st.subheader("Konfiguracja strony")
        self.date_filter = st.checkbox("Filtruj po dacie", value=True, key='regular_season')
        col1, col2, col3 = st.columns(3)
        cursor = self.conn.cursor()
        with col1:
            seasons_query = "SELECT id, years from seasons where id in (select distinct(season) from matches m where m.sport_id = 2) order by years desc"
            cursor.execute(seasons_query)
            self.seasons = {years: season_id for season_id, years in cursor.fetchall()}
            seasons_list = [season for season in self.seasons.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
            self.season = self.seasons[self.selected_season]
        with col2:
            self.selected_round = int(st.selectbox("Faza sezonu", list(self.rounds_dict.keys()), format_func=lambda x: self.rounds_dict[x], key='selected_round'))
        with col3:
            if self.date_filter:
                self.date_range = st.date_input(
                                            "Wybierz zakres dat",
                                            value=(pd.to_datetime('today'), pd.to_datetime('today') + pd.Timedelta(days=7)),
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
        cursor.close()

        self.get_matches()

    def matches_buttons(self, filtered_matches):
        for _, row in filtered_matches.iterrows():
            button_label = "{} - {}, data: {}".format(row.home_team, row.away_team, row.game_date.strftime('%d.%m.%y %H:%M'))
            if row.result != '0':
                if row.OTwinner == 1:
                    button_label = button_label + ", wynik po dogrywce: {} - {}".format(row.home_goals + 1, row.away_goals)
                elif row.OTwinner == 2:
                    button_label = button_label + ", wynik po dogrywce: {} - {}".format(row.home_goals, row.away_goals + 1)
                elif row.SOwinner == 1:
                    button_label = button_label + ", wynik po rzutach karnych: {} - {}".format(row.home_goals + 1, row.away_goals)
                elif row.SOwinner == 2:
                    button_label = button_label + ", wynik po rzutach karnych: {} - {}".format(row.home_goals, row.away_goals + 1)
                else:
                    button_label = button_label + ", wynik spotkania: {} - {}".format(row.home_goals, row.away_goals)

            if st.button(button_label, use_container_width=True):
                self.match_details(row)

    def generate_schedule_tab(self):
        filtered_matches = self.matches[:]
        if self.selected_round == 100:
            filtered_matches = filtered_matches[filtered_matches['round'] == 100]
        elif self.selected_round == 200:
            filtered_matches = filtered_matches[filtered_matches['round'] != 100]            
        if len(self.date_range) == 2:
            if self.date_filter:
                filtered_matches = filtered_matches[(filtered_matches['game_date'] >= self.date_range[0]) & (filtered_matches['game_date'] <= self.date_range[1])]
        if len(filtered_matches) > 0:
            with st.expander('Mecze dla zadanej konfiguracji: '):
                self.matches_buttons(filtered_matches)
        else:
            st.write("Brak meczów dla wprowadzonej konfiguracji")
    
    def match_details(self, row):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Meczowe predykcje", "Składy", "Przebieg meczu", "Statystyki pomeczowe", "Boxscore - statystyki zawodników"])
        with tab1:
            nhl_schedule_package.match_predictions(row.id)
        with tab2:
            nhl_schedule_package.match_lineups(row.id, row.home_team, row.home_team_id, row.away_team, row.away_team_id, self.conn)
        with tab3:
            nhl_schedule_package.match_events(row.id, row.home_team, self.conn)
        with tab4:
            if row.OTwinner == 1:
                row.home_goals = row.home_goals + 1
            elif row.OTwinner == 2:
                row.away_goals = row.away_goals + 1
            nhl_schedule_package.match_stats(row)
        with tab5:
            nhl_schedule_package.match_boxscore(row.id, self.conn)

    def generate_teams_tab(self):
        self.teams_dict = nhl_schedule_package.get_teams(self.league, self.season, self.conn)
        with st.expander("Zespoły w sezonie {}".format(self.selected_season)):
            st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.selected_season))
            for key, value in self.teams_dict.items():
                button_label = value
                if st.button(button_label, use_container_width = True):
                    tab1, tab2, tab3, tab4 = st.tabs(["Statystyki drużyny", "Skład", "Statystyki zawodników", "Statystyki predykcji"])
                    self.current_team_info = nhl_schedule_package.get_team_info(key, self.lookback_games, self.matches)
                    with tab1:
                        self.current_team_stats(key, value)
                    with tab2:
                        pass
                        #nhl_schedule_package.get_team_roster(key, value, self.conn)
                    with tab3:
                        current_team_player_stats = nhl_schedule_package.get_team_players_stats(key, self.season, self.conn)
                        st.dataframe(current_team_player_stats)
                    with tab4:
                        pass
    
    def current_team_stats(self, team_id, team_name):
        df = pd.DataFrame(self.current_team_info)
        
        date = df['match_date'].tolist()
        opponent = df['opponent_shortcut'].tolist()
        home_team = df['home_team'].tolist()
        away_team = df['away_team'].tolist()
        home_team_score = df['team_goals'].tolist()
        away_team_score = df['opponent_goals'].tolist()
        home_team_sog = df['team_sog'].tolist()
        away_team_sog = df['opponent_sog'].tolist()
        goals = df.apply(lambda x: x['team_goals'] + x['opponent_goals'], axis=1).tolist()
        results = df['result'].tolist()
        col1, col2 = st.columns(2)
        with col1:
            with st.container():
                graphs_module.goals_bar_chart(date, opponent, goals, team_name, self.ou_line, "Bramki w meczach")
        with col2:
            with st.container():
                graphs_module.goals_bar_chart(date, opponent, home_team_sog, team_name, statistics.mean(home_team_sog), "Liczba oddanych strzałów przez")
        col3, col4 = st.columns(2)
        with col3:
            with st.container():
                graphs_module.winner_bar_chart_v2(results, team_name)
        with col4:
            with st.container():
                tables_module.matches_list(date, home_team, home_team_score, away_team, away_team_score, team_name)
    
    def create_table(self, matches, scope):
        team_ids = {team_id: [0] * 10 for team_id in self.teams_dict}
        nhl_schedule_package.league_table(matches, team_ids, 2, 0, 2, 1, scope)
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

        with st.expander("Tabele ligowe"):
            regular_season_matches = self.matches[self.matches['round'] == 100]  
            tab1, tab2, tab3, tab4 = st.tabs([
                "Tabela sezonu zasadniczego", 
                "Tabela domowa", 
                "Tabela wyjazdowa", 
                "Tabela OU"])
            with tab1:
                st.write("Tabela ogólna")
                st.dataframe(
                    self.create_table(regular_season_matches, 'all'),
                    use_container_width=True)
                #TO-DO: Podział na konferencje i dywizje
            with tab2:
                st.dataframe(
                    self.create_table(regular_season_matches, 'home'),
                    use_container_width=True)
            with tab3:
                st.dataframe(
                    self.create_table(regular_season_matches, 'away'),
                    use_container_width=True)
            
            st.write("Legenda: WPD - wygrane po dogrywce, PPD - przegrane po dogrywce")


if __name__ == '__main__':
    conn = db_module.db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id from leagues where name = 'NHL'")
    league_id = cursor.fetchone()[0]
    nhl = HockeySite(conn, "NHL", league_id)
    cursor.close()
    nhl.generate_site()