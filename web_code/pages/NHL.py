import streamlit as st
st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

import base_site_module
import db_module
import pandas as pd
import graphs_module
import tables_module
import hockey_rink

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
                            t1.name as home_team, t1.id as home_team_id, t2.name as away_team, t2.id as away_team_id, m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result,
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
    
    def match_details(self, row):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Meczowe predykcje", "Składy", "Przebieg meczu", "Statystyki pomeczowe", "Boxscore - statystyki zawodników"])
        with tab1:
            self.match_predictions(row.id)
        with tab2:
            self.match_lineups(row.id, row.home_team, row.home_team_id, row.away_team, row.away_team_id)
        with tab3:
            self.match_events(row.id)
        with tab4:
            self.match_stats(row, row.home_team_id, row.away_team_id)
        with tab5:
            self.match_boxscore(row.id)

    def match_predictions(self, match_id):
        st.write("Tutaj będą predykcje meczowe")

    def match_lineups(self, match_id, home_team, home_team_id, away_team, away_team_id):
        lineup_query = f'''SELECT 
            t.id AS Drużyna, 
            p.common_name AS Zawodnik, 
            line.position AS Pozycja, 
            line.number AS Numer, 
            line.line AS Linia
        FROM hockey_match_rosters line
        JOIN players p ON line.player_id = p.id
        JOIN matches m ON m.id = line.match_id
        JOIN teams t ON t.id = line.team_id
        WHERE m.id = {match_id}'''
        
        lineup_pd = pd.read_sql(lineup_query, self.conn)
        
        def display_lineup(team_name, team_id, column):
            with column:
                tabs = st.tabs([f"{i} linia" for i in ["Pierwsza", "Druga", "Trzecia", "Czwarta"]])
                for i, tab in enumerate(tabs, start=1):
                    with tab:
                        st.subheader(team_name)
                        lineup = lineup_pd[
                            (lineup_pd['Drużyna'] == team_id) & (lineup_pd['Linia'] == i)
                        ].drop(columns=['Linia', 'Drużyna'])
                        st.dataframe(lineup, hide_index=True)
                st.plotly_chart(hockey_rink.draw_hockey_rink())
        
        col1, col2 = st.columns(2)
        display_lineup(home_team, home_team_id, col1)
        display_lineup(away_team, away_team_id, col2)


    
    def match_events(self, match_id):
        events_query = f'''select 
            t.name as Druzyna, p.common_name as Zawodnik, e.name as Zdarzenie, hme.period as Tercja, hme.event_time as Czas, hme.description as Opis
                from hockey_match_events hme 
                join players p on hme.player_id = p.id
                join events e on e.id = hme.event_id
                join matches m on m.id = hme.match_id
                join teams t on t.id = hme.team_id
                where m.id = {match_id}
                order by m.id, hme.period, hme.event_time
        '''
        events_pd = pd.read_sql(events_query, self.conn)
        st.subheader("Tercja 1")
        events_pd_1 = events_pd[events_pd['Tercja'] == 1].drop(columns=['Tercja'])
        st.dataframe(events_pd_1, hide_index=True)
        st.subheader("Tercja 2")
        events_pd_2 = events_pd[events_pd['Tercja'] == 2].drop(columns=['Tercja'])
        st.dataframe(events_pd_2, hide_index=True)
        st.subheader("Tercja 3")
        events_pd_3 = events_pd[events_pd['Tercja'] == 3].drop(columns=['Tercja'])
        st.dataframe(events_pd_3, hide_index=True)
        events_pd_ot = events_pd[events_pd['Tercja'] == 4].drop(columns=['Tercja'])
        if len(events_pd_ot) > 0:
            st.subheader("Dogrywka")
            st.dataframe(events_pd_ot, hide_index=True)
        events_pd_so = events_pd[events_pd['Tercja'] == 5].drop(columns=['Tercja'])
        if len(events_pd_so) > 0:
            st.subheader("Rzuty karne")
            st.dataframe(events_pd_so, hide_index=True)

    def generate_event_entry(self, event_row):
        pass

    def match_stats(self, match_row, home_team_id, away_team_id):
        col1, col2, col3 = st.columns(3)
        match_row_dict = match_row.to_dict()
        centered_style = """
        <div style="text-align: center; margin:5px;">{}</div>
        """
        stat_name = {
            'team' : 'Nazwa drużyny',
            'goals': 'Bramki',
            'team_sog' : 'Strzały na bramkę',
            'team_fk' : 'Minuty kar', 
            'team_fouls' : 'Liczba kar',
            'team_pp_goals' : 'Liczba bramek w przewadze (PP)',
            'team_sh_goals' : "Liczba bramek w osłabieniu (SH)",
            'team_shots_acc' : "Skuteczność strzałów (%)",
            'team_saves' : "Liczba obron",
            'team_saves_acc' : 'Skuteczność obron (%)',
            'team_pp_acc' : 'Skuteczność gier w przewadze (%)',
            'team_pk_acc' : 'Skuteczność gier w osłabieniu (%)',
            'team_faceoffs' : 'Liczba wygranych wznowień',
            'team_faceoffs_acc' : 'Skuteczność wznowień (%)',
            'team_hits' : 'Liczba uderzeń',
            'team_to' : 'Liczba strat',
            'team_en' : 'Liczba bramek strzelonych na pustą bramkę'

        }
        for key, value in match_row_dict.items():
            if key in ('home_team_id', 'away_team_id'):
                continue
            if 'home' in key:
                col1.markdown(centered_style.format(value), unsafe_allow_html=True)
                col2.markdown(centered_style.format(stat_name[key.replace('home_', '')]), unsafe_allow_html=True)
            elif 'away' in key:
                col3.markdown(centered_style.format(value), unsafe_allow_html=True)

    def match_boxscore(self, match_id):
        st.write(f"Boxscore dla meczu {match_id}")
        st.subheader("Bramkarze")
        boxscore_goaltenders = f'''select 
                t.name as Drużyna, p.common_name as Zawodnik, box.points as Punkty, box.penalty_minutes as "Kary(MIN)", box.toi as TOI, 
                box.shots_against as Strzały, box.shots_saved as Obronione, box.saves_acc as "Skuteczność Obron(%)"
            from hockey_match_player_stats box 
            join players p on box.player_id = p.id
            join matches m on m.id = box.match_id
            join teams t on t.id = box.team_id
            where m.id = {match_id} and p.position = 'G' ''' 
        boxscore_goaltenders_pd = pd.read_sql(boxscore_goaltenders, self.conn)
        boxscore_goaltenders_pd['TOI'] = boxscore_goaltenders_pd['TOI'].str.slice(0, -3)
        boxscore_goaltenders_pd.index = range(1, len(boxscore_goaltenders_pd) + 1)
        boxscore_goaltenders_pd['Skuteczność Obron(%)'] = boxscore_goaltenders_pd['Skuteczność Obron(%)'].apply(lambda x: f"{x:.2f}")
        st.table(boxscore_goaltenders_pd)
        st.subheader("Zawodnicy pola")
        boxscore_others = f'''select 
                t.name as Drużyna, p.common_name as Zawodnik, box.goals as Bramki, box.assists as Asysty, box.points as Punkty, box.plus_minus as "+/-",
                box.penalty_minutes as "Kary(MIN)", box.sog as SOG, box.toi as TOI
            from hockey_match_player_stats box 
            join players p on box.player_id = p.id
            join matches m on m.id = box.match_id
            join teams t on t.id = box.team_id
            where m.id = {match_id} and p.position <> 'G' ''' 
        boxscore_pd = pd.read_sql(boxscore_others, self.conn)
        boxscore_pd['TOI'] = boxscore_pd['TOI'].str.slice(0, -3)
        boxscore_pd.index = range(1, len(boxscore_pd) + 1)
        players_styled = boxscore_pd.style.applymap(graphs_module.highlight_cells_plus_minus, subset = ["+/-"])
        st.table(players_styled)
        st.write("Tutaj będą statystyki zawodników")
    

if __name__ == '__main__':
    conn = db_module.db_connect()
    nhl = HockeySite(conn, "NHL")
    nhl.generate_site()