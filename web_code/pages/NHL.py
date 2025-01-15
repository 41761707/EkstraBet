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
                                        value=(pd.to_datetime('2017-01-01'), pd.to_datetime('2017-01-31')),
                                        min_value=pd.to_datetime('2016-01-01'),
                                        max_value=pd.to_datetime('2030-12-31'),
                                        format="YYYY-MM-DD")
        cursor.close()
        self.get_matches()
    
    def get_matches(self):
        if isinstance(self.date_range, tuple) and len(self.date_range) == 2:
            start_date, end_date = self.date_range
            query = f'''SELECT m.id as id, m.game_date as game_date, m.round as round, 
                        t1.name as home_team, t2.name as away_team, m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result
                        FROM matches m 
                        join teams t1 on m.home_team = t1.id
                        join teams t2 on m.away_team = t2.id
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
        for _, row in self.matches.iterrows():
            button_label = "{} - {}, data: {}".format(row.home_team, row.away_team, row.game_date.strftime('%d.%m.%y %H:%M'))
            if row.result != '0':
                button_label = button_label + ", wynik spotkania: {} - {}".format(row.home_goals, row.away_goals)

            if st.button(button_label, use_container_width=True):
                self.match_details(row)
    
    def match_details(self, row):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Meczowe predykcje", "Składy", "Przebieg meczu", "Statystyki pomeczowe", "Boxscore - statystyki zawodników"])
        with tab1:
            self.match_predictions(row.id)
        with tab2:
            self.match_lineups(row.id)
        with tab3:
            self.match_events(row.id)
        with tab4:
            self.match_stats(row.id)
        with tab5:
            self.match_boxscore(row.id)

    def match_predictions(self, match_id):
        st.write("Tutaj będą predykcje meczowe")

    def match_lineups(self, match_id):
        pass
    
    def match_events(self, match_id):
        st.write("Tutaj będą wydarzenia meczowe")

    def match_stats(self, match_id):
        st.write("Tutaj będą statystyki meczowe")

    def match_boxscore(self, match_id):
        st.write(f"Boxscore dla meczu {match_id}")
        st.subheader("Bramkarze")
        boxscore_goaltenders = f'''select 
                t.name as Drużyna, p.common_name as Zawodnik, box.points as Punkty, box.penalty_minutes as Kary, CAST(box.toi AS char) as TOI, 
                box.shots_against as Strzały, box.shots_saved as Obronione, box.saves_acc as "Skuteczność Obron(%)"
            from hockey_match_player_stats box 
            join players p on box.player_id = p.id
            join matches m on m.id = box.match_id
            join teams t on t.id = box.team_id
            where m.id = {match_id} and p.position = 'G' ''' 
        boxscore_goaltenders_pd = pd.read_sql(boxscore_goaltenders, self.conn)
        boxscore_goaltenders_pd['TOI'] = boxscore_goaltenders_pd['TOI'].str.slice(0, -3)
        st.dataframe(boxscore_goaltenders_pd, hide_index=True)
        st.subheader("Zawodnicy pola")
        boxscore_others = f'''select 
                t.name as Drużyna, p.common_name as Zawodnik, box.goals as Bramki, box.assists as Asysty, box.points as Punkty, box.plus_minus as "+/-",
                box.penalty_minutes as Kary, box.sog as SOG, CAST(box.toi AS char) as TOI
            from hockey_match_player_stats box 
            join players p on box.player_id = p.id
            join matches m on m.id = box.match_id
            join teams t on t.id = box.team_id
            where m.id = {match_id} and p.position <> 'G' ''' 
        boxscore_pd = pd.read_sql(boxscore_others, self.conn)
        boxscore_pd['TOI'] = boxscore_pd['TOI'].str.slice(0, -3)
        players_styled = boxscore_pd.style.applymap(graphs_module.highlight_cells_plus_minus, subset = ["+/-"])
        st.dataframe(players_styled, hide_index=True)
        st.write("Tutaj będą statystyki zawodników")
    

if __name__ == '__main__':
    conn = db_module.db_connect()
    nhl = HockeySite(conn, "NHL")
    nhl.generate_site()