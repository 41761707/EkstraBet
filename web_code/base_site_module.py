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
        self.league = league
        self.season = -1
        self.round = -1
        self.rounds_list = []
        self.season_list = []
        self.name = ''
        self.no_events = 3 #BTTS, OU, REZULTAT
        self.EV_plus = 0
        self.teams_dict = {}
        self.date = datetime.today().strftime('%Y-%m-%d')
        self.conn = db_module.db_connect()
        self.set_config()
        self.get_teams()
        self.get_schedule()    
        self.get_league_tables()
        self.get_league_stats()          
        self.conn.close()

    def set_config(self):
        query = "select last_update, name from leagues where id = {}".format(self.league)
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        self.update = results[0][0]
        self.name = results[0][1]
        cursor.close()
        st.header(self.name)
        st.write("Ostatnia aktualizacja: {}".format(self.update))
        st.subheader("Konfiguracja prezentowanych danych")
        col1, col2, col3 = st.columns(3)
        with col1:
            self.games = st.slider("Liczba analizowanych spotkań wstecz", 5, 15, 10)
        with col2:
            self.ou_line = st.slider("Linia Over/Under", 0.5, 4.5, 2.5, 0.5)
        with col3:
            self.h2h = st.slider("Liczba prezentowanych spotkań H2H", 0, 10, 5)
        
        col4, col5, col6 = st.columns(3)
        with col4:
            season_query = f"SELECT distinct m.season, s.years from matches m join seasons s on m.season = s.id where m.league = {self.league} order by s.years desc"
            cursor = self.conn.cursor()
            cursor.execute(season_query)
            seasons_dict = {years: season_id for season_id, years in cursor.fetchall()}
            self.seasons_list = [season for season in seasons_dict.keys()]
            self.years = st.selectbox("Sezon", self.seasons_list)
            self.season = seasons_dict[self.years]
            cursor.close()
        with col5:
            rounds_query = f"select round, game_date from matches where league = {self.league} and season = {self.season} order by game_date desc"
            cursor = self.conn.cursor()
            cursor.execute(rounds_query)
            rounds_tmp = [x[0] for x in cursor.fetchall()]
            rounds_tmp.append(0)
            for item in rounds_tmp:
                if item not in self.rounds_list:
                    self.rounds_list.append(item)
            self.round = st.selectbox("Kolejka", self.rounds_list)
            cursor.close()
        with col6:
            self.date_range = st.date_input(
                            "Zakres dat (działa tylko, gdy kolejka = 0)",
                            value=(pd.to_datetime('2025-01-01'), pd.to_datetime('2025-01-31')),
                            min_value=pd.to_datetime('2000-01-01'),
                            max_value=pd.to_datetime('2030-12-31'),
                            format="YYYY-MM-DD")

    def get_teams(self):
        all_teams = "select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) where m.league = {} and m.season = {} order by t.name ".format(self.league, self.season)
        all_teams_df = pd.read_sql(all_teams, self.conn)
        self.teams_dict = all_teams_df.set_index('id')['name'].to_dict()

    def get_schedule(self):
        if self.round > 1:
            if self.round >= 100:
                round_name = self.get_special_round(self.round)
            else:
                round_name = self.round - 1
            with st.expander("Terminarz, poprzednia kolejka numer: {}".format(round_name)):
                self.generate_schedule(self.round-1, self.date_range)

        if self.round >= 100:
            round_name = self.get_special_round(self.round)
        else:
            round_name = self.round
        if self.round == 0:
            with st.expander("Terminarz, mecze dla dat: {} - {}".format(self.date_range[0], self.date_range[1])):
                self.generate_schedule(self.round, self.date_range)
        else:
            with st.expander("Terminarz, aktualna kolejka numer: {}".format(round_name)):
                self.generate_schedule(self.round, self.date_range)
        with st.expander("Zespoły w sezonie {}".format(self.years)):
            self.show_teams(self.teams_dict)

    def get_league_tables(self):
        with st.expander("Tabele ligowe" ):
            query = '''select t1.name as home_team, t2.name as away_team, home_team_goals, away_team_goals, result 
                from matches m join teams t1 on m.home_team = t1.id join teams t2 on m.away_team = t2.id 
                where league = {} and season = {} and result != '0' and round < 900 '''.format(self.league, self.season)
            results_df = pd.read_sql(query, self.conn)
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

    def get_league_stats(self):     
        with st.expander("Statystyki ligowe"):
            query = ''' select
                        count(*)
                    from matches
                    where league = {}
                        and season = {}
                        and result != '0'
            '''.format(self.league, self.season)
            cursor = self.conn.cursor()
            cursor.execute(query)
            no_games = cursor.fetchall()
            cursor.close()
            st.header("Charakterstyki ligi: {}".format(self.name))
            st.subheader("Do tej pory rozegrano {} meczów w ramach ligi: {}".format(no_games[0][0], self.name))
            if no_games[0][0] > 0:
                stats_module.league_charachteristics(self.conn, self.league, self.season, self.teams_dict, no_games[0][0])
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

    def get_special_round(self, round):
        special_round_names = {
            900 : '1/64 finału, mecz numer 1',
            901 : '1/64 finału, mecz numer 2',
            902 : '1/64 finału, mecz numer 3',
            903 : '1/64 finału, mecz numer 4',
            904 : '1/64 finału, mecz numer 5',
            905 : '1/64 finału, mecz numer 6',
            906 : '1/64 finału, mecz numer 7',
            910 : '1/32 finału, mecz numer 1',
            911 : '1/32 finału, mecz numer 2',
            912 : '1/32 finału, mecz numer 3',
            913 : '1/32 finału, mecz numer 4',
            914 : '1/32 finału, mecz numer 5',
            915 : '1/32 finału, mecz numer 6',
            916 : '1/32 finału, mecz numer 7',
            920 : '1/16 finału, mecz numer 1',
            921 : '1/16 finału, mecz numer 2',
            922 : '1/16 finału, mecz numer 3',
            923 : '1/16 finału, mecz numer 4',
            924 : '1/16 finału, mecz numer 5',
            925 : '1/16 finału, mecz numer 6',
            926 : '1/16 finału, mecz numer 7',
            930 : '1/8 finału, mecz numer 1',
            931 : '1/8 finału, mecz numer 2',
            932 : '1/8 finału, mecz numer 3',
            933 : '1/8 finału, mecz numer 4',
            934 : '1/8 finału, mecz numer 5',
            935 : '1/8 finału, mecz numer 6',
            936 : '1/8 finału, mecz numer 7',
            940 : '1/4 finału, mecz numer 1',
            941 : '1/4 finału, mecz numer 2',
            942 : '1/4 finału, mecz numer 3',
            943 : '1/4 finału, mecz numer 4',
            944 : '1/4 finału, mecz numer 5',
            945 : '1/4 finału, mecz numer 6',
            946 : '1/4 finału, mecz numer 7',
            950 : '1/2 finału, mecz numer 1',
            951 : '1/2 finału, mecz numer 2',
            952 : '1/2 finału, mecz numer 3',
            953 : '1/2 finału, mecz numer 4',
            954 : '1/2 finału, mecz numer 5',
            955 : '1/2 finału, mecz numer 6',
            956 : '1/2 finału, mecz numer 7',
            960 : 'Finał, mecz numer 1',
            961 : 'Finał, mecz numer 2',
            962 : 'Finał, mecz numer 3',
            963 : 'Finał, mecz numer 4',
            964 : 'Finał, mecz numer 5',
            965 : 'Finał, mecz numer 6',
            966 : 'Finał, mecz numer 7',
            100 : 'Brak podziału na kolejki',
            1001 : "Baraż o utrzymanie, 1/4 finału, mecz numer 1",
            1002 : "Baraż o utrzymanie, 1/4 finału, mecz numer 2",
            1003 : 'Baraż o utrzymanie, 1/2 finału, mecz numer 1',
            1004 : 'Baraż o utrzymanie, 1/2 finału, mecz numer 2',
            1005 : "Baraż o utrzymanie, finał, mecz numer 1",
            1006 : "Baraż o utrzymanie, finał, mecz numer 2",
        }
        return special_round_names[round]

    def single_team_data(self, team_id):
        query = f"SELECT name FROM teams WHERE id = {team_id}"
        team_name_df = pd.read_sql(query, self.conn)
        team_name = team_name_df.loc[0, 'name'] if not team_name_df.empty else None

        query = f'''
            SELECT 
                m.home_team AS home_id, t1.name AS home, 
                m.away_team AS guest_id, t2.name AS guest, 
                date_format(cast(m.game_date as date), '%d.%m') AS date, m.home_team_goals AS home_goals, 
                m.away_team_goals AS away_goals, m.result AS result
            FROM matches m 
            JOIN teams t1 ON t1.id = m.home_team 
            JOIN teams t2 ON t2.id = m.away_team 
            WHERE CAST(m.game_date AS date) <= '{self.date}' 
            AND (m.home_team = {team_id} OR m.away_team = {team_id}) 
            AND m.result <> '0'
            AND m.season = {self.season}
            ORDER BY m.game_date DESC 
            LIMIT {self.games}
        '''
        data = pd.read_sql(query, self.conn)

        date = [row.date for _, row in data.iterrows()]
        opponent = [row.guest if row.home_id == team_id else row.home for _, row in data.iterrows()]
        goals = [0.4 if int(row.home_goals) + int(row.away_goals) == 0 else int(row.home_goals) + int(row.away_goals) for _, row in data.iterrows()]
        btts = [1 if int(row.home_goals) > 0 and int(row.away_goals) > 0 else -1 for _, row in data.iterrows()]
        home_team = [row.home for _, row in data.iterrows()]
        home_team_score = [row.home_goals for _, row in data.iterrows()]
        away_team = [row.guest for _, row in data.iterrows()]
        away_team_score = [row.away_goals for _, row in data.iterrows()]
        results = [row.result for _, row in data.iterrows()]

        return date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score, results

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

    def show_predictions(self, home_goals, away_goals, id, result):
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 1)
        home_win = pd.read_sql(query, self.conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 2)
        draw = pd.read_sql(query, self.conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 3)
        guest_win = pd.read_sql(query, self.conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 6)
        btts_yes = pd.read_sql(query, self.conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 172)
        btts_no = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 173)
        exact_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 8)
        over_2_5 = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 12)
        under_2_5 = pd.read_sql(query, self.conn).to_numpy()

        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 174)
        zero_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 175)
        one_goal = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 176)
        two_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 177)
        three_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 178)
        four_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 179)
        five_goals = pd.read_sql(query, self.conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 180)
        six_plus_goals = pd.read_sql(query, self.conn).to_numpy()

        if len(home_win) == 0:
            st.header("Na chwilę obecną brak przewidywań dla wskazanego spotkania")
            return
        goals_no = [zero_goals[0][0], one_goal[0][0], two_goals[0][0], three_goals[0][0], four_goals[0][0], five_goals[0][0], six_plus_goals[0][0]]
        col1, col2 = st.columns(2)
        with col1:
            graphs_module.graph_winner(home_win[0][0], draw[0][0], guest_win[0][0])
        with col2:
            graphs_module.graph_btts(btts_no[0][0], btts_yes[0][0])

        col3, col4 = st.columns(2)
        with col3:
            graphs_module.graph_exact_goals(goals_no)
        with col4:
            if self.ou_line < 1:
                graphs_module.graph_ou(round(zero_goals[0][0], 2), 
                                       round(one_goal[0][0] + two_goals[0][0] + three_goals[0][0] + four_goals[0][0] + five_goals[0][0] + six_plus_goals[0][0], 2), 'OU 0.5')
            elif self.ou_line < 2:
                graphs_module.graph_ou(round(zero_goals[0][0] + one_goal[0][0], 2), 
                                       round(two_goals[0][0] + three_goals[0][0] + four_goals[0][0] + five_goals[0][0] + six_plus_goals[0][0], 2), 'OU 1.5')
            elif self.ou_line < 3:
                graphs_module.graph_ou(under_2_5[0][0], over_2_5[0][0], 'OU 2.5')
            elif self.ou_line < 4:
                graphs_module.graph_ou(round(zero_goals[0][0] + one_goal[0][0] + two_goals[0][0] + three_goals[0][0], 2), 
                                       round(four_goals[0][0] + five_goals[0][0] + six_plus_goals[0][0], 2), 'OU 3.5')
            else:
                graphs_module.graph_ou(round(zero_goals[0][0] + one_goal[0][0] + two_goals[0][0] + three_goals[0][0] + four_goals[0][0], 2), 
                                       round(five_goals[0][0] + six_plus_goals[0][0], 2), 'OU 4.5')
        
        st.header("Przewidywana liczba bramek w meczu: {}".format(exact_goals[0][0]))
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
        query = 'select b.name as bookmaker, o.event as event, o.odds as odds from odds o join bookmakers b on o.bookmaker = b.id where match_id = {}'.format(id)
        odds_details = pd.read_sql(query, self.conn)
        home_win_odds = [round(100/home_win[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        draw_odds = [round(100/draw[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        guest_win_odds = [round(100/guest_win[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        btts_no_odds = [round(100/btts_no[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        btts_yes_odds = [round(100/btts_yes[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        under_odds = [round(100/under_2_5[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        over_odds = [round(100/over_2_5[0][0], 2)] + [0] * (len(bookie_dict) - 1)
        for _, row in odds_details.iterrows():
            if row.event == 1: #GOSPO WIN
                home_win_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event == 2: #REMIS
                draw_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event == 3: #GOŚĆ WIN
                guest_win_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event == 6:
                btts_yes_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event  == 172:
                btts_no_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event == 8:
                over_odds[bookie_dict[row.bookmaker]] = row.odds
            if row.event == 12:
                under_odds[bookie_dict[row.bookmaker]] = row.odds


        col3, col4, col5 = st.columns(3)
        with col3:
            st.write("Porównanie kursów z estymacją na rezultat:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'Gospodarz' : [x for x in home_win_odds],
            'Remis' : [x for x in draw_odds],
            'Gość' : [x for x in guest_win_odds],
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        with col4:
            st.write("Porównanie kursów z estymacją na OU:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'UNDER 2.5' : [x for x in under_odds],
            'OVER 2.5' : [x for x in over_odds]
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        with col5:
            st.write("Porównanie kursów z estymacją na BTTS:")
            data = {
            'Bukmacher': [x for x in bookie_dict],
            'BTTS TAK' : [x for x in btts_yes_odds],
            'BTTS NIE' : [x for x in btts_no_odds]
            }
            df = pd.DataFrame(data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, hide_index=True)

        if self.h2h > 0:
            self.generate_h2h(id)
        st.header("Proponowane zakłady na mecz przez model: ")
        home_win_EV = round((home_win[0][0] / 100) * max(home_win_odds[1:]) - 1, 2)
        home_win_bookmaker = np.argmax(home_win_odds[1:]) + 1
        draw_EV = round((draw[0][0] / 100) * max(draw_odds[1:]) - 1, 2)
        draw_bookmaker = np.argmax(draw_odds[1:]) + 1
        guest_win_EV = round((guest_win[0][0] / 100) * max(guest_win_odds[1:]) - 1, 2)
        guest_win_bookmaker = np.argmax(guest_win_odds[1:]) + 1
        btts_no_EV = round((btts_no[0][0] / 100) * max(btts_no_odds[1:]) - 1, 2)
        btts_no_bookmaker = np.argmax(btts_no_odds[1:]) + 1
        btts_yes_EV = round((btts_yes[0][0] / 100) * max(btts_yes_odds[1:]) - 1, 2)
        btts_yes_bookmaker = np.argmax(btts_yes_odds[1:]) + 1
        under_EV = round((under_2_5[0][0] / 100) * max(under_odds[1:]) - 1, 2)
        under_bookmaker = np.argmax(under_odds[1:]) + 1
        over_EV = round((over_2_5[0][0] / 100) * max(over_odds[1:]) - 1, 2)
        over_bookmaker = np.argmax(over_odds[1:]) + 1
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
        #st.write("Zakłady o współczynniku VB (Value Bet) większym od 0 (oznaczone jasnozielonym tłem) uznawane są za WARTE ROZPATRZENIA")
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
                if row.result != '0':
                    tab1, tab2 = st.tabs(["Predykcje", "Statystyki pomeczowe"])
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
                graphs_module.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)
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
                graphs_module.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)
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
                graphs_module.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)
            #Wykresy z podziałem na typ zdarzenia
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where (home_team = {} or away_team = {}) and result != '0'".format(key, key)
            stats_module.generate_statistics(query, 0, 1, self.round, self.no_events, self.conn, self.EV_plus)



    def show_teams(self, teams_dict):
        st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.years))
        for key, value in teams_dict.items():
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
                            graphs_module.btts_bar_chart(date, opponent, btts, team_name)
                    col3, col4 = st.columns(2)
                    with col3:
                        with st.container():
                            graphs_module.winner_bar_chart(opponent, home_team ,result, team_name)
                    with col4:
                        with st.container():
                            tables_module.matches_list(date, home_team, home_team_score, away_team, away_team_score, team_name)
                with tab2:
                    self.predicts_per_team(team_name, key)
                
