import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

import db_module
import graphs_module
import tables_module

class Base:
    def __init__(self, league, season, current_round, name, date):
        self.league = league
        self.season = season
        self.date = date
        self.round = current_round
        self.conn = db_module.db_connect()
        query = "select years from seasons where id = {}".format(self.season)
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        self.years = results[0][0]
        self.no_events = 3 #OU, BTTS, REZULTAT
        query = "select last_update from leagues where id = {}".format(self.league)
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        self.update = results[0][0]
        self.name = name
        st.header(name)
        st.write("Aktualny sezon: {}. Aktulana kolejka: {}. Ostatnia aktualizacja: {}".format(self.years, self.round, self.update))
        all_teams = "select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) where m.league = {} and m.season = {} order by t.name ".format(self.league, self.season)
        all_teams_df = pd.read_sql(all_teams, self.conn)
        teams_dict = all_teams_df.set_index('id')['name'].to_dict()
        #TO-DO: Przedstawianie historycznych predykcji
        st.subheader("Konfiguracja prezentowanych danych")
        self.EV_plus = st.checkbox("Uwzględnij tylko wartościowe zakłady (VB > 0)")
        self.games = st.slider("Liczba analizowanych spotkań wstecz", 5, 15, 10)
        self.ou_line = st.slider("Linia Over/Under", 0.5, 4.5, 2.5, 0.5)
        self.h2h = st.slider("Liczba prezentowanych spotkań H2H", 0, 10, 5)
        if self.round > 1 and self.league != 25 : #durne MLS
            with st.expander("Terminarz, poprzednia kolejka numer: {}".format(self.round-1)):
                self.generate_schedule(league, self.round-1, season)
        with st.expander("Terminarz, aktualna kolejka numer: {}".format(self.round)):
            self.generate_schedule(league, self.round, season)
        with st.expander("Zespoły w sezonie {}".format(self.years)):
            self.show_teams(teams_dict)
        with st.expander("Tabela ligowa w sezonie {}".format(self.years)):
            st.write("Tabela ligowa")
        with st.expander("Statystyki ligowe"):
            st.header("Charakterstyki ligi {}".format(self.name))
        with st.expander("Statystyki predykcji"):
            st.header("Podsumowanie predykcji wykonanych dla ligi {} w sezonie {}".format(self.name, self.years))
            self.generate_statistics(self.league, self.season, self.round)
                    
        self.conn.close()

    def show_statistics(self, ou_predictions, btts_predictions, result_predictions,
                        first_round, last_round, ou_bets, btts_bets, result_bets, predictions):
        col1, col2 = st.columns(2)
        with col1:
            ou_accuracy_pred = 0
            btts_accuracy_pred = 0
            result_accuracy_pred = 0
            if predictions != 0:
                predictions = predictions / self.no_events
                ou_accuracy_pred = round(100 * ou_predictions['correct_ou_pred'] / predictions, 2)
                btts_accuracy_pred = round(100 * btts_predictions['correct_btts_pred'] / predictions, 2)
                result_accuracy_pred = round(100 * result_predictions['correct_result_pred'] / predictions, 2)    
            st.header("Wszystkie przewidywnia \n Kolejki: {} - {}".format(first_round, last_round))
            data = {
            'Label': ["OU", "BTTS", "REZULTAT"],
            'Wszystkie': [predictions] * 3,
            'Poprawne': [ou_predictions['correct_ou_pred'], btts_predictions['correct_btts_pred'], result_predictions['correct_result_pred']],
            'Skuteczność' : [str(ou_accuracy_pred) + "%", str(btts_accuracy_pred) + "%", str(result_accuracy_pred) + "%"]
            }
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        with col2:
            ou_accuracy = 0
            btts_accuracy = 0
            result_accuracy = 0
            if ou_bets['ou_bets'] != 0:
                ou_accuracy = round(100 * ou_bets['correct_ou_bets'] / ou_bets['ou_bets'], 2)
            if btts_bets['btts_bets'] != 0:
                btts_accuracy = round(100 * btts_bets['correct_btts_bets'] / btts_bets['btts_bets'], 2)
            if result_bets['result_bets'] != 0:
                result_accuracy = round(100 * result_bets['correct_result_bets'] / result_bets['result_bets'], 2)
            st.header("Wszystkie zakłady \n Kolejki: {} - {}".format(first_round, last_round))
            data = {
            'Label': ["OU", "BTTS", "REZULTAT"],
            'Wszystkie': [ou_bets['ou_bets'], btts_bets['btts_bets'], result_bets['result_bets']],
            'Poprawne': [ou_bets['correct_ou_bets'], btts_bets['correct_btts_bets'], result_bets['correct_result_bets']],
            'Profit (unit)' : [str(round(ou_bets['ou_profit_bets'],2)), str(round(btts_bets['btts_profit_bets'],2)), str(round(result_bets['result_profit_bets'],2))],
            'Skuteczność' : [str(ou_accuracy)+"%", str(btts_accuracy)+"%", str(result_accuracy)+"%"]
            }
            df = pd.DataFrame(data)
            styled_df = df.style.applymap(graphs_module.highlight_cells_profit, subset = ['Profit (unit)'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        col3, col4 = st.columns(2)
        with col3:
            if predictions != 0:
                st.write("Obrazowe porównanie liczby poprawnych i niepoprawnych predykcji")
                graphs_module.generate_comparision(['OU', 'BTTS', 'REZULTAT'], 
                                        [ou_predictions['correct_ou_pred'], btts_predictions['correct_btts_pred'], result_predictions['correct_result_pred']], 
                                        [predictions - ou_predictions['correct_ou_pred'], predictions - btts_predictions['correct_btts_pred'], predictions - result_predictions['correct_result_pred']])
        with col4:
            if ou_bets['ou_bets'] != 0 or btts_bets['btts_bets'] != 0 or result_bets['result_bets'] != 0:
                st.write("Obrazowe porównanie liczby poprawnych i niepoprawnych zakładów")
                graphs_module.generate_comparision(['OU', 'BTTS', 'REZULTAT'], 
                                        [ou_bets['correct_ou_bets'], btts_bets['correct_btts_bets'], result_bets['correct_result_bets']], 
                                        [ou_bets['ou_bets'] - ou_bets['correct_ou_bets'], btts_bets['btts_bets'] - btts_bets['correct_btts_bets'], result_bets['result_bets'] - result_bets['correct_result_bets']])
        col5, col6 = st.columns(2)
        with col5:
            #st.write(round(ou_predictions['under_pred'] * 100 / predictions, 2), round(ou_predictions['over_pred'] * 100 / predictions, 2))
            if predictions > 0:
                st.header("Under vs Over - porównanie liczby predykcji oraz ich skuteczności")
                data = {
                'Label': ["Under 2.5", "Over 2.5"],
                'Wszystkie': [ou_predictions['under_pred'], ou_predictions['over_pred']],
                'Poprawne': [ou_predictions['under_correct'], ou_predictions['over_correct']],
                'Procent przewidywań' : [str(round(ou_predictions['under_pred'] * 100 / predictions, 2)) + "%", 
                                         str(round(ou_predictions['over_pred'] * 100 / predictions, 2)) + "%"],
                'Skuteczność' : [str(round(100 * ou_predictions['under_correct'] / max(ou_predictions['under_pred'], 1), 2)) + "%", 
                                 str(round( 100 * ou_predictions['over_correct'] / max(ou_predictions['over_pred'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                #st.write(ou_predictions)
                st.write('Rozkład wykonanych przewidywań na zdarzenie OU')
                graphs_module.generate_pie_chart_binary(['Under 2.5', 'Over 2.5'], 
                                               round(ou_predictions['under_pred'] * 100 / predictions, 2), 
                                               round(ou_predictions['over_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['Under 2.5', 'Over 2.5'], 
                                          [ou_predictions['under_correct'], ou_predictions['over_correct']],
                                          [ou_predictions['under_pred'] - ou_predictions['under_correct'], ou_predictions['over_pred'] - ou_predictions['over_correct']])
        with col6:
            if ou_bets['ou_bets'] > 0:
                st.header("Under vs Over - porównanie liczby zakładów oraz ich skuteczności")
                data = {
                'Label': ["Under 2.5", "Over 2.5"],
                'Wszystkie': [ou_bets['under_bets'], ou_bets['over_bets']],
                'Poprawne': [ou_bets['under_correct'], ou_bets['over_correct']],
                'Procent przewidywań' : [str(round(ou_bets['under_bets'] * 100 / ou_bets['ou_bets'], 2)) + "%", 
                                         str(round(ou_bets['over_bets'] * 100 / ou_bets['ou_bets'], 2)) + "%"],
                'Skuteczność' : [str(round(100 * ou_bets['under_correct'] / max(ou_bets['under_bets'], 1), 2)) + "%", 
                                 str(round( 100 * ou_bets['over_correct'] / max(ou_bets['over_bets'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                #st.write(ou_bets)
                st.write('Rozkład wykonanych zakładów na zdarzenie OU')
                graphs_module.generate_pie_chart_binary(['Under 2.5', 'Over 2.5'], 
                                               round(ou_bets['under_bets'] * 100 / ou_bets['ou_bets'], 2), 
                                               round(ou_bets['over_bets'] * 100 / ou_bets['ou_bets'], 2))
                st.write('Wynik zakładów w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['Under 2.5', 'Over 2.5'], 
                                          [ou_bets['under_correct'], ou_bets['over_correct']],
                                          [ou_bets['under_bets'] - ou_bets['under_correct'], ou_bets['over_bets'] - ou_bets['over_correct']])
        col7, col8 = st.columns(2)
        with col7:
            if predictions > 0:
                st.header("NO BTTS vs BTTS - porównanie liczby predykcji oraz ich skuteczności")
                data = {
                'Label': ["NO BTTS", "BTTS"],
                'Wszystkie': [btts_predictions['btts_no_pred'], btts_predictions['btts_yes_pred']],
                'Poprawne': [btts_predictions['btts_no_correct'], btts_predictions['btts_yes_correct']],
                'Procent przewidywań' : [str(round(btts_predictions['btts_no_pred'] * 100 / predictions, 2)) + "%", 
                                         str(round(btts_predictions['btts_yes_pred'] * 100 / predictions, 2)) + "%"],
                'Skuteczność' : [str(round(100 * btts_predictions['btts_no_correct'] / max(btts_predictions['btts_no_pred'], 1), 2)) + "%", 
                                 str(round( 100 * btts_predictions['btts_yes_correct'] / max(btts_predictions['btts_yes_pred'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                #st.write(ou_predictions)
                st.write('Rozkład wykonanych przewidywań na zdarzenie BTTS')
                graphs_module.generate_pie_chart_binary(['NO BTTS', 'BTTS'], 
                                               round(btts_predictions['btts_no_pred'] * 100 / predictions, 2), 
                                               round(btts_predictions['btts_yes_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['NO BTTS', 'BTTS'], 
                                          [btts_predictions['btts_no_correct'], btts_predictions['btts_yes_correct']],
                                          [btts_predictions['btts_no_pred'] - btts_predictions['btts_no_correct'], btts_predictions['btts_yes_pred'] - btts_predictions['btts_yes_correct']])
        with col8:
            if btts_bets['btts_bets'] > 0:
                st.header("NO BTTS vs BTTS - porównanie liczby zakładów oraz ich skuteczności")
                data = {
                'Label': ["NO BTTS", "BTTS"],
                'Wszystkie': [btts_bets['btts_no_bets'], btts_bets['btts_yes_bets']],
                'Poprawne': [btts_bets['btts_no_correct'], btts_bets['btts_yes_correct']],
                'Procent przewidywań' : [str(round(btts_bets['btts_no_bets'] * 100 / btts_bets['btts_bets'], 2)) + "%", 
                                         str(round(btts_bets['btts_yes_bets'] * 100 / btts_bets['btts_bets'], 2)) + "%"],
                'Skuteczność' : [str(round(100 * btts_bets['btts_no_correct'] / max(btts_bets['btts_no_bets'], 1), 2)) + "%", 
                                 str(round( 100 * btts_bets['btts_yes_correct'] / max(btts_bets['btts_yes_bets'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.write('Rozkład wykonanych zakładów na zdarzenie BTTS')
                graphs_module.generate_pie_chart_binary(["NO BTTS", "BTTS"], 
                                               round(btts_bets['btts_no_bets'] * 100 / btts_bets['btts_bets'], 2), 
                                               round(btts_bets['btts_yes_bets'] * 100 / btts_bets['btts_bets'], 2))
                st.write('Wynik zakładów w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['NO BTTS', 'BTTS'],  
                                          [btts_bets['btts_no_correct'], btts_bets['btts_yes_correct']],
                                          [btts_bets['btts_no_bets'] - btts_bets['btts_no_correct'], btts_bets['btts_yes_bets'] - btts_bets['btts_yes_correct']])
        col9, col10 = st.columns(2)
        with col9:
            if result_bets['result_bets'] > 0:
                st.header("1x2 - porównanie liczby predykcji oraz ich skuteczności")
                data = {
                'Label': ["Gospodarz", "Remis", "Gość"],
                'Wszystkie': [result_predictions['home_win_pred'], result_predictions['draw_pred'], result_predictions['away_win_pred']],
                'Poprawne': [result_predictions['home_win_correct'], result_predictions['draw_correct'], result_predictions['away_win_correct']],
                'Procent przewidywań' : [str(round(result_predictions['home_win_pred'] * 100 / predictions, 2)) + "%", 
                                         str(round(result_predictions['draw_pred'] * 100 / predictions, 2)) + "%", 
                                         str(round(result_predictions['away_win_pred'] * 100 / predictions, 2)) + "%"],
                'Skuteczność' : [str(round(100 * result_predictions['home_win_correct'] / max(result_predictions['home_win_pred'], 1), 2)) + "%",
                                 str(round(100 * result_predictions['draw_correct'] / max(result_predictions['draw_pred'], 1), 2)) + "%",
                                 str(round(100 * result_predictions['away_win_correct'] / max(result_predictions['away_win_pred'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                #st.write(ou_predictions)
                st.write('Rozkład wykonanych przewidywań na rezultat spotkania')
                graphs_module.generate_pie_chart_result(["Gospodarz", "Remis", "Gość"], 
                                               round(result_predictions['home_win_pred'] * 100 / predictions, 2), 
                                               round(result_predictions['draw_pred'] * 100 / predictions, 2),
                                               round(result_predictions['away_win_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['Gospodarz', 'Remis', 'Gość'], 
                                          [result_predictions['home_win_correct'], result_predictions['draw_correct'], result_predictions['away_win_correct']],
                                          [result_predictions['home_win_pred'] - result_predictions['home_win_correct'], 
                                           result_predictions['draw_pred'] - result_predictions['draw_correct'],
                                           result_predictions['away_win_pred'] - result_predictions['away_win_correct']])
        with col10:
            if result_bets['result_bets'] > 0:
                st.header("NO BTTS vs BTTS - porównanie liczby zakładów oraz ich skuteczności")
                data = {
                'Label': ["Gospodarz", "Remis", "Gość"],
                'Wszystkie': [result_bets['home_win_bets'], result_bets['draw_bets'], result_bets['away_win_bets']],
                'Poprawne': [result_bets['home_win_correct'], result_bets['draw_correct'], result_bets['away_win_correct']],
                'Procent przewidywań' : [str(round(result_bets['home_win_bets'] * 100 / result_bets['result_bets'], 2)) + "%", 
                                         str(round(result_bets['draw_bets'] * 100 / result_bets['result_bets'], 2)) + "%",
                                         str(round(result_bets['away_win_bets'] * 100 / result_bets['result_bets'], 2)) + "%"],
                'Skuteczność' : [str(round(100 * result_bets['home_win_correct'] / max(result_bets['home_win_bets'], 1), 2)) + "%", 
                                 str(round(100 * result_bets['draw_correct'] / max(result_bets['draw_bets'], 1), 2)) + "%",
                                 str(round(100 * result_bets['away_win_correct'] / max(result_bets['away_win_bets'], 1), 2)) + "%"]
                }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.write('Rozkład wykonanych zakładów na rezultat spotkania')
                graphs_module.generate_pie_chart_result(["Gospodarz", "Remis", "Gość"], 
                                               round(result_bets['home_win_bets'] * 100 / result_bets['result_bets'], 2),
                                               round(result_bets['draw_bets'] * 100 / result_bets['result_bets'], 2),
                                               round(result_bets['away_win_bets'] * 100 / result_bets['result_bets'], 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
                graphs_module.generate_comparision(['Gospodarz', 'Remis', 'Gość'],  
                                          [result_bets['home_win_correct'], result_bets['draw_correct'], result_bets['away_win_correct']],
                                          [result_bets['home_win_bets'] - result_bets['home_win_correct'], 
                                           result_bets['draw_bets'] - result_bets['draw_correct'], 
                                           result_bets['away_win_bets'] - result_bets['away_win_correct']])
        #col11, col12 = st.columns(2)
        #with col11:
        #    st.header("Profit z zakładów - kolejka po kolejce")
        #with col12:
        #    st.header("Zmiana profitu w czasie")

    def generate_statistics(self, league, season, current_round):
        if current_round > 1:
            first_round, last_round = st.select_slider(
            "Zakres analizowanych rund",
            options=[x+1 for x in range(current_round)],
            value=(current_round,current_round))
        else:
            first_round, last_round = 1, 1
        tax_flag = st.checkbox("Uwzględnij podatek 12%")
        rounds = list(range(first_round, last_round + 1))
        rounds_str =','.join(map(str, rounds))
        query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where league = {} and season = {} and round in ({}) and result != '0'".format(league, season, rounds_str)
        #query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0'"
        #query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) = current_date - 1 and result != '0'"
        match_stats_df = pd.read_sql(query, self.conn)
        #TO-DO: Poniższe w oparciu o pole outcome w final_predictions / outcomes
        predictions = 0
        ou_predictions = {
            'correct_ou_pred' : 0,
            'over_pred' : 0,
            'over_correct' : 0,
            'under_pred' : 0,
            'under_correct' : 0
        }
        ou_bets = {
            'ou_bets' : 0,
            'correct_ou_bets' : 0,
            'over_bets' : 0,
            'over_correct' : 0,
            'under_bets' : 0,
            'under_correct': 0,
            'ou_profit_bets' : 0,
        }
        btts_predictions = {
            'correct_btts_pred' : 0,
            'btts_yes_pred' : 0,
            'btts_yes_correct' : 0,
            'btts_no_pred' : 0,
            'btts_no_correct' : 0
        }
        btts_bets = {
            'btts_bets' : 0,
            'correct_btts_bets' : 0,
            'btts_yes_bets' : 0,
            'btts_yes_correct' : 0,
            'btts_no_bets' : 0,
            'btts_no_correct' : 0,
            'btts_profit_bets' : 0,
        }
        result_predictions = {
            'correct_result_pred' : 0,
            'home_win_pred' : 0,
            'home_win_correct' : 0,
            'draw_pred' : 0,
            'draw_correct' : 0,
            'away_win_pred' : 0,
            'away_win_correct' : 0,
        }
        result_bets = {
            'result_bets' : 0,
            'correct_result_bets' : 0,
            'home_win_bets' : 0,
            'home_win_correct' : 0,
            'draw_bets' : 0,
            'draw_correct' : 0,
            'away_win_bets' : 0,
            'away_win_correct' : 0,
            'result_profit_bets' : 0,
        }

        tax = 0
        if tax_flag:
            tax = 0.12

        for _, row in match_stats_df.iterrows():
            id = row['id']
            query = 'select event_id from final_predictions where match_id = {}'.format(id)
            predictions_df = pd.read_sql(query, self.conn)
            query = 'select event_id, odds, bookmaker, EV from bets where match_id = {}'.format(id)
            bets_df = pd.read_sql(query, self.conn)
            for _, predict in predictions_df.iterrows():
                predictions = predictions + 1
                if predict['event_id'] == 8:
                    ou_predictions['over_pred'] = ou_predictions['over_pred'] + 1
                    if row['total'] > 2.5:
                        ou_predictions['over_correct'] = ou_predictions['over_correct'] + 1
                        ou_predictions['correct_ou_pred'] = ou_predictions['correct_ou_pred'] + 1
                elif predict['event_id'] == 12:
                    ou_predictions['under_pred'] = ou_predictions['under_pred'] + 1
                    if row['total'] < 2.5:
                        ou_predictions['under_correct'] = ou_predictions['under_correct'] + 1
                        ou_predictions['correct_ou_pred'] = ou_predictions['correct_ou_pred'] + 1
                elif predict['event_id'] == 1:
                    result_predictions['home_win_pred'] = result_predictions['home_win_pred'] + 1
                    if row['result'] == '1':
                        result_predictions['home_win_correct'] = result_predictions['home_win_correct'] + 1
                        result_predictions['correct_result_pred'] = result_predictions['correct_result_pred'] + 1
                elif predict['event_id'] == 2:
                    result_predictions['draw_pred'] = result_predictions['draw_pred'] + 1
                    if row['result'] == 'X':
                        result_predictions['draw_correct'] = result_predictions['draw_correct'] + 1
                        result_predictions['correct_result_pred'] = result_predictions['correct_result_pred'] + 1                        
                elif predict['event_id'] == 3:
                    result_predictions['away_win_pred'] = result_predictions['away_win_pred'] + 1
                    if row['result'] == '2':
                        result_predictions['away_win_correct'] = result_predictions['away_win_correct'] + 1
                        result_predictions['correct_result_pred'] = result_predictions['correct_result_pred'] + 1 
                elif predict['event_id'] == 6:
                    btts_predictions['btts_yes_pred'] = btts_predictions['btts_yes_pred'] + 1
                    if (row['home_goals'] >0 and row['away_goals'] > 0 ):
                        btts_predictions['btts_yes_correct'] = btts_predictions['btts_yes_correct'] + 1
                        btts_predictions['correct_btts_pred'] = btts_predictions['correct_btts_pred'] + 1
                elif predict['event_id'] == 172: 
                    btts_predictions['btts_no_pred'] = btts_predictions['btts_no_pred'] + 1
                    if not (row['home_goals'] > 0 and row['away_goals'] > 0):
                        btts_predictions['btts_no_correct'] = btts_predictions['btts_no_correct'] + 1
                        btts_predictions['correct_btts_pred'] = btts_predictions['correct_btts_pred'] + 1
                else:
                    pass

            for _, bet in bets_df.iterrows():
                if self.EV_plus and bet['EV'] < 0:
                    continue
                if bet['event_id'] in (8,12):
                        ou_bets['ou_bets'] = ou_bets['ou_bets'] + 1
                        ou_bets['ou_profit_bets'] = ou_bets['ou_profit_bets'] - 1
                if bet['event_id'] in (1,2,3):
                        result_bets['result_bets'] = result_bets['result_bets'] + 1
                        result_bets['result_profit_bets'] = result_bets['result_profit_bets'] - 1
                if bet['event_id'] in (6,172):
                        btts_bets['btts_bets'] = btts_bets['btts_bets'] + 1
                        btts_bets['btts_profit_bets'] = btts_bets['btts_profit_bets'] - 1

                if bet['event_id'] == 8:
                    ou_bets['over_bets'] = ou_bets['over_bets'] + 1
                    if row['total'] > 2.5:
                        ou_bets['correct_ou_bets'] = ou_bets['correct_ou_bets'] + 1
                        ou_bets['over_correct'] = ou_bets['over_correct'] + 1
                        ou_bets['ou_profit_bets'] = ou_bets['ou_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 12:
                    ou_bets['under_bets'] = ou_bets['under_bets'] + 1
                    if row['total'] < 2.5:
                        ou_bets['correct_ou_bets'] = ou_bets['correct_ou_bets'] + 1
                        ou_bets['under_correct'] = ou_bets['under_correct'] + 1
                        ou_bets['ou_profit_bets'] = ou_bets['ou_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 1:
                    result_bets['home_win_bets'] = result_bets['home_win_bets'] + 1
                    if row['result'] == '1':
                        result_bets['correct_result_bets'] = result_bets['correct_result_bets'] + 1
                        result_bets['home_win_correct'] = result_bets['home_win_correct'] + 1
                        result_bets['result_profit_bets'] = result_bets['result_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 2:
                    result_bets['draw_bets'] = result_bets['draw_bets'] + 1
                    if row['result'] == 'X':
                        result_bets['correct_result_bets'] = result_bets['correct_result_bets'] + 1
                        result_bets['draw_correct'] = result_bets['draw_correct'] + 1
                        result_bets['result_profit_bets'] = result_bets['result_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 3:
                    result_bets['away_win_bets'] = result_bets['away_win_bets'] + 1
                    if row['result'] == '2':
                        result_bets['correct_result_bets'] = result_bets['correct_result_bets'] + 1
                        result_bets['away_win_correct'] = result_bets['away_win_correct'] + 1
                        result_bets['result_profit_bets'] = result_bets['result_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 6: 
                    btts_bets['btts_yes_bets'] = btts_bets['btts_yes_bets'] + 1
                    if (row['home_goals'] >0 and row['away_goals'] > 0 ):
                        btts_bets['correct_btts_bets'] = btts_bets['correct_btts_bets'] + 1
                        btts_bets['btts_yes_correct'] = btts_bets['btts_yes_correct'] + 1
                        btts_bets['btts_profit_bets'] = btts_bets['btts_profit_bets'] + (bet['odds'] * (1-tax))
                elif bet['event_id'] == 172:
                    btts_bets['btts_no_bets'] = btts_bets['btts_no_bets'] + 1
                    if not (row['home_goals'] > 0 and row['away_goals'] > 0):
                        btts_bets['correct_btts_bets'] = btts_bets['correct_btts_bets'] + 1
                        btts_bets['btts_no_correct'] = btts_bets['btts_no_correct'] + 1
                        btts_bets['btts_profit_bets'] = btts_bets['btts_profit_bets'] + (bet['odds'] * (1-tax))
                else:
                    pass
        self.show_statistics(ou_predictions, btts_predictions, result_predictions,
                        first_round, last_round, ou_bets, btts_bets, result_bets, predictions)

    def single_team_data(self, team_id):
        query = "select name from teams where id = {}".format(team_id)
        team_name_df = pd.read_sql(query, self.conn)
        if not team_name_df.empty:
            team_name = team_name_df.loc[0, 'name']
        query = '''select m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.home_team_goals as home_goals, m.away_team_goals as away_goals, m.result as result
                    from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                    where cast(m.game_date as date) <= '{}' and (m.home_team = {} or m.away_team = {}) and m.result <> '0'
                    order by m.game_date desc'''.format(self.date, team_id, team_id)
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

    def match_pred_summary(self, id, result, home_goals, away_goals):
        st.header("Pomeczowe statystyki predykcji i zakładów")
        query = "select f.event_id as event_id, e.name as name from final_predictions f join events e on f.event_id = e.id where match_id = {}".format(id)
        final_predictions_df = pd.read_sql(query, self.conn)
        predicts = [""] * 3
        outcomes = [""] * 3
        correct = ["NIE"] * 3
        bet_placed = ["NIE"] * 3
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
        query = "select event_id as event_id, EV as EV from bets b where match_id = {}".format(id)
        final_bets_df = pd.read_sql(query, self.conn)
        for _, row in final_bets_df.iterrows():
            if row['event_id'] in (1,2,3):  
                if self.EV_plus:
                    if row['EV'] > 0:
                        bet_placed[2] = 'TAK'
                else:
                    bet_placed[2] = 'TAK'
            if row['event_id'] in (8,12):
                if self.EV_plus:
                    if row['EV'] > 0:
                        bet_placed[0] = 'TAK'
                else:
                    bet_placed[0] = 'TAK'
            if row['event_id'] in (6, 172):
                if self.EV_plus:
                    if row['EV'] > 0:
                        bet_placed[1] = 'TAK'
                else:
                    bet_placed[1] = 'TAK'
        final_predictions_df = pd.read_sql(query, self.conn)
        data = {
        'Zdarzenie': ["OU", "BTTS", "REZULTAT"],
        'Predykcja' : [x for x in predicts],
        'Obserwacja' : [x for x in outcomes],
        'Czy przewidywanie poprawne?' : [x for x in correct],
        'Czy postawiono?' : [x for x in bet_placed]
        }
        df = pd.DataFrame(data)
        df.index = range(1, len(df) + 1)
        #styled_df = df.style.applymap(graphs_module.highlight_cells_EV, subset = ['VB'])
        st.dataframe(df, use_container_width=True, hide_index=True)
        correct_pred = correct.count('TAK')
        no_bets = bet_placed.count('TAK')
        correct_bet = 0
        for i in range(len(correct)):
            if correct[i] == 'TAK' and bet_placed[i] == 'TAK':
                correct_bet = correct_bet + 1
        st.write("Liczba poprawnych predykcji: {}".format(correct_pred))
        st.write("Skuteczność predykcji dla analizowanego meczu: {:.2f}%".format(100 * correct_pred/len(predicts)))
        if no_bets > 0:
            st.write("Liczba zawartych zakładów: {}".format(no_bets))
            st.write("Liczba poprawych zakładów: {}".format(correct_bet))
            st.write("Skuteczność zakładów dla analizowanego meczu: {:.2f}%".format(100 * correct_bet / max(no_bets,1)))
        else:
            st.write("Dla wybranego meczu nie zawarto żadnych zakładów")
    
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
        dates = h2h_df['date'].dt.strftime('%d.%m.%y').tolist()
        home_team = h2h_df['home_team'].tolist()
        home_team_score = h2h_df['home_team_goals'].tolist()
        away_team = h2h_df['away_team'].tolist()
        away_team_score = h2h_df['away_team_goals'].tolist()

        st.header(f"Ostatnie {min(self.h2h, len(h2h_df))} bezpośrednie spotkania")
        tables_module.matches_list_h2h(dates, home_team, home_team_score, away_team, away_team_score)

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
        #st.write("{}; {}; {}; {}; {}".format(home_win[0][0], draw[0][0], guest_win[0][0], btts_no[0][0], btts_yes[0][0]))
        col1, col2 = st.columns(2)
        with col1:
            graphs_module.graph_winner(home_win[0][0], draw[0][0], guest_win[0][0])
        with col2:
            graphs_module.graph_btts(btts_no[0][0], btts_yes[0][0])

        col3, col4 = st.columns(2)
        with col3:
            graphs_module.graph_exact_goals(goals_no)
        with col4:
            graphs_module.graph_ou(under_2_5[0][0], over_2_5[0][0])
        
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

        #TO-DO: Zestawienie H2H
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



    def generate_schedule(self, league_id, round, season):
        if league_id == 25:
            query = '''select m.id as id, m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.result as result, m.home_team_goals as h_g, m.away_team_goals as a_g
                    from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                    where m.league = {} and m.round = {} and m.season = {} and m.game_date >= DATE_SUB('{}', INTERVAL 4 DAY)
                    order by m.game_date'''.format(league_id, round, season, self.date)
        else:
            query = '''select m.id as id, m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.result as result, m.home_team_goals as h_g, m.away_team_goals as a_g
                    from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                    where m.league = {} and m.round = {} and m.season = {} 
                    order by m.game_date'''.format(league_id, round, season)
        schedule_df = pd.read_sql(query,self.conn)
        for index, row in schedule_df.iterrows():
            button_label = "{} - {}".format(row.home, row.guest)
            if row.result != '0':
                button_label = button_label + ", wynik spotkania: {} - {}".format(row.h_g, row.a_g)
            else:
                button_label = button_label + ", data: {}".format(row.date.strftime('%d.%m.%y %H:%M'))
            if st.button(button_label, use_container_width=True):
                self.show_predictions(row.h_g, row.a_g, row.id, row.result)

    def predicts_per_team(self, team_name, key):
        query = "select event_id, outcome from final_predictions f join matches m on m.id = f.match_id where (m.home_team = {} or m.away_team = {}) and m.result != '0' order by m.game_date desc".format(key, key)
        predicts_df = pd.read_sql(query, self.conn)
        result_outcomes = []
        btts_outcomes = []
        ou_outcomes = []
        counter = 0
        if len(predicts_df) > 0:
            for _, row in predicts_df.iterrows():
                counter = counter + 1
                if counter * 3 == self.games:
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
                    'Skuteczność' : [str(suma * 100 / liczba) + "%"]
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
                    'Skuteczność' : [str(suma * 100 / liczba) + "%"]
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
                    'Skuteczność' : [str(suma * 100 / liczba) + "%"]
                    }
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                graphs_module.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)


    def show_teams(self, teams_dict):
        st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.years))
        for key, value in teams_dict.items():
            button_label = value
            if st.button(button_label, use_container_width = True):
                date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score, result = self.single_team_data(key)
                col1, col2 = st.columns(2)
                with col1:
                    with st.container():
                        graphs_module.goals_bar_chart(date[:self.games], opponent[:self.games], goals[:self.games], team_name, self.ou_line)
                with col2:
                    with st.container():
                        graphs_module.btts_bar_chart(date[:self.games], opponent[:self.games], btts[:self.games], team_name)
                col3, col4 = st.columns(2)
                with col3:
                    with st.container():
                        graphs_module.winner_bar_chart(opponent[:self.games], home_team[:self.games] ,result[:self.games], team_name)
                with col4:
                    with st.container():
                        tables_module.matches_list(date[:self.games], home_team[:self.games], home_team_score[:self.games], away_team[:self.games], away_team_score[:self.games], team_name)
                self.predicts_per_team(team_name, key)
                
