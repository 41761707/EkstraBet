import streamlit as st
st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

import base_site_module
import db_module
import pandas as pd
import graphs_module
import tables_module

class HockeySite:
    def __init__(self, conn, name):
        self.conn = conn
        self.name = name
        self.league = 45 #NHL
        self.seasons = {}
        self.selected_season = 0
        self.matches = ""
        self.date_range = ""
        self.teams_dict = {}
        self.ou_line = 5.5
        st.header(name)
    
    def generate_site(self):
        cursor = self.conn.cursor() 
        seasons_query = "SELECT id, years from SEASONS order by years desc"
        self.generate_config()
        self.show_teams()

    #To są stare funkcje - zobaczyć, czy warto poprawić
    def single_team_data(self, team_id):
        query = "select name from teams where id = {}".format(team_id)
        team_name_df = pd.read_sql(query, self.conn)
        if not team_name_df.empty:
            team_name = team_name_df.loc[0, 'name']
        query = '''select m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result
                    from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                    where cast(m.game_date as date) <= current_date and (m.home_team = {} or m.away_team = {}) and m.result <> '0'
                    order by m.game_date desc'''.format(team_id, team_id)
        data = pd.read_sql(query, self.conn)
        date = []
        opponent = []
        goals = []
        btts = []
        home_team = []
        home_team_score = []
        away_team = []
        away_team_score = []
        results = []
        for _, row in data.iterrows():
            #O/U
            if int(row.home_goals) + int(row.away_goals) == 0:
                goals.append(0.4)
            else:
                goals.append(int(row.home_goals) + int(row.away_goals))
            #BTTS
            if int(row.home_goals) > 0 and int(row.away_goals) > 0:
                btts.append(1)
            else:
                btts.append(-1)
            #DATE
            date.append(row.date.strftime('%d.%m.%y'))
            #HOME AND AWAY
            home_team.append(row.home)
            home_team_score.append(row.home_goals)
            away_team.append(row.guest)
            away_team_score.append(row.away_goals)
            #OPPONENT
            if row.home_id == team_id:
                opponent.append(row.guest)
            else:
                opponent.append(row.home)
            #RESULTS
            results.append(row.result)
        return date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score, results
    
    def show_teams(self):
        with st.expander("Zespoły w sezonie {}".format(self.selected_season)):
            all_teams = '''select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) 
                            where m.league = {} and m.season = {} order by t.name'''.format(self.league, self.seasons[self.selected_season])
            all_teams_df = pd.read_sql(all_teams, self.conn)
            self.teams_dict = all_teams_df.set_index('id')['name'].to_dict()
            st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.selected_season))
            for key, value in self.teams_dict.items():
                button_label = value
                if st.button(button_label, use_container_width = True):
                    tab1, tab2 = st.tabs(["Statystyki drużyny", "Statystyki predykcji"])
                    with tab1:
                        date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score, result = self.single_team_data(key)
                        col1, col2 = st.columns(2)
                        with col1:
                            with st.container():
                                graphs_module.goals_bar_chart(date, opponent, goals, team_name, self.ou_line)
                        with col2:
                            with st.container():
                                graphs_module.winner_bar_chart(opponent, home_team ,result, team_name)
                        with st.container():
                            tables_module.matches_list(date, home_team, home_team_score, away_team, away_team_score, team_name)
                    with tab2:
                        st.write("Tu na razie pusto")
    #Koniec starych funkcji

    def init_config(self):
        self.get_matches()

    def generate_config(self):
        st.subheader("Konfiguracja strony")
        col1, col2, col3 = st.columns(3)
        cursor = self.conn.cursor()
        with col1:
            seasons_query = "SELECT id, years from SEASONS where id in (select distinct(season) from matches m where m.sport_id = 2) order by years desc"
            cursor.execute(seasons_query)
            self.seasons = {years: season_id for season_id, years in cursor.fetchall()}
            seasons_list = [season for season in self.seasons.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
        with col2:
            st.write("TU RUNDY")
        with col3:
            self.date_range = st.date_input(
                                        "Wybierz zakres dat",
                                        value=(pd.to_datetime('2024-01-01'), pd.to_datetime('2024-01-31')),
                                        min_value=pd.to_datetime('2000-01-01'),
                                        max_value=pd.to_datetime('2030-12-31'),
                                        format="YYYY-MM-DD")
        cursor.close()
        self.get_matches()
    
    def get_matches(self):
        if isinstance(self.date_range, tuple) and len(self.date_range) == 2:
            start_date, end_date = self.date_range
            query = f'''SELECT m.game_date as game_date, m.round as round, 
                        t1.name as home_team, t2.name as away_team, m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result
                        FROM matches m 
                        join teams t1 on m.home_team = t1.id
                        join teams t2 on m.away_team = t2.id
                        #where m.id = 85832
                        where m.league = {self.league} and m.season = {self.seasons[self.selected_season]} and cast(m.game_date as date) between '{start_date}' and '{end_date}'
                        order by m.game_date desc'''
            print(query)
            self.matches = pd.read_sql(query, self.conn)
            if len(self.matches) > 0:
                with st.expander('Mecze dla zadanej konfiguracji: '):
                    self.generate_schedule()
            else:
                st.write("Brak meczów dla wprowadzonej konfiguracji")

    def generate_schedule(self):
        for index, row in self.matches.iterrows():
            button_label = "{} - {}, data: {}".format(row.home_team, row.away_team, row.game_date.strftime('%d.%m.%y %H:%M'))
            if row.result != '0':
                button_label = button_label + ", wynik spotkania: {} - {}".format(row.home_goals, row.away_goals)

            if st.button(button_label, use_container_width=True):
                st.write("Tu dane o meczu")

if __name__ == '__main__':
    conn = db_module.db_connect()
    nhl = HockeySite(conn, "NHL")
    nhl.generate_site()
    #conn.close()