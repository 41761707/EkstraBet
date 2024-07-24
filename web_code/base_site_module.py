import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

import db_module

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

        query = "select last_update from leagues where id = {}".format(self.league)
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        self.update = results[0][0]
        self.name = name
        st.header(name)
        st.write("Ostatnia aktualizacja: {}".format(self.update))
        all_teams = "select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) where m.league = {} and m.season = {} order by t.name ".format(self.league, self.season)
        all_teams_df = pd.read_sql(all_teams, self.conn)
        teams_dict = all_teams_df.set_index('id')['name'].to_dict()
        #TO-DO: Przedstawianie historycznych predykcji
        #if self.round > 1 and self.league != 25 : #durne MLS
        with st.expander("Terminarz, poprzednia kolejka numer: {}".format(self.round-1)):
            self.generate_schedule(league, self.round-1, season)
        with st.expander("Terminarz, kolejka numer: {}".format(self.round)):
            self.generate_schedule(league, self.round, season)
        with st.expander("Zespoły w sezonie {}".format(self.years)):
            games = st.slider("Liczba analizowanych spotkań wstecz", 5, 15, 10)
            ou_line = st.slider("Linia Over/Under", 0.5, 4.5, 2.5, 0.5)
            self.show_teams( teams_dict, games, ou_line)
        with st.expander("Statystyki ligowe"):
            st.header("Charakterstyki ligi {}".format(self.name))
        with st.expander("Statystyki predykcji"):
            st.header("Podsumowanie predykcji wykonanych dla ligi {} w sezonie {}".format(self.name, self.years))
            self.generate_statistics(self.league, self.season, self.round)
                    
        self.conn.close()
    
    def generate_comparision(self, labels, wins, loses):
        data = {
        'Zakład': [x for x in labels],
        'Wygrane': [x for x in wins],
        'Przegrane': [x for x in loses],
        }
        df = pd.DataFrame(data)
        sns.set_theme(style="darkgrid")

        fig, ax = plt.subplots(figsize=(10, 6))
        width = 0.35  # Szerokość słupka
        x = df.index

        bars1 = ax.bar(x - width/2, df['Wygrane'], width, label='Wygrane', color='green')
        bars2 = ax.bar(x + width/2, df['Przegrane'], width, label='Przegrane', color='orangered')

        ax.grid(False)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{bet_type}" for bet_type in df['Zakład']])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(colors='white', which='both')
        ax.set_facecolor('#291F1E')
        ax.legend()
        fig.patch.set_facecolor('black')

        for bars, outcomes in zip([bars1, bars2], [df['Wygrane'], df['Przegrane']]):
            for bar, outcome in zip(bars, outcomes):
                ax.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() - 1.5, 0.5), f'{int(outcome)}', 
                        ha='center', va='bottom', color='white', fontsize=20)

        # Wyświetlenie wykresu
        st.pyplot(fig)
    def generate_pie_chart_binary(self, labels, type_a, type_b):
        # Dane do wykresu
        data = {
            'Label': [x for x in labels],
            'Ppb': [type_a, type_b],
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        
        # Ustawienia wykresu kołowego
        fig, ax = plt.subplots(figsize=(10, 6))
        wedges, texts, autotexts = ax.pie(df['Ppb'], labels=df['Label'], autopct='%1.1f%%', colors=['orangered', 'lightgreen'],
                                        textprops=dict(color="white"), startangle=140)
        
        # Ustawienia tytułu i koloru tła
        #ax.set_title(title, loc='left', fontsize=24, color='white', pad = 40)
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        ax.axis('equal')  # Utrzymanie proporcji koła
        
        # Ustawienia kolorów tekstów na biały
        for text in texts:
            text.set_color('white')
            text.set_fontsize(20)  # Zwiększenie czcionki napisów
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontsize(22)
        
        st.pyplot(fig)
        
    def generate_pie_chart_result(self, labels, type_a, type_b, type_c):
            # Data for the chart
            data = {
                'Label': [x for x in labels],
                'Ppb': [type_a, type_b, type_c],
            }
            sns.set_theme(style="darkgrid")
            df = pd.DataFrame(data)
            
            # Pie chart settings
            fig, ax = plt.subplots(figsize=(10, 6))
            wedges, texts, autotexts = ax.pie(df['Ppb'], labels=df['Label'], autopct='%1.1f%%', 
                                            colors=['orangered', 'lightgreen', 'skyblue'],
                                            textprops=dict(color="white"), startangle=140)
            
            # Background and title settings
            #ax.set_title(title, loc='left', fontsize=24, color='white', pad = 40)
            fig.patch.set_facecolor('black')  # Set the background color of the figure to black
            ax.axis('equal')  # Maintain aspect ratio
            
            # Set text colors to white and adjust font size
            for text in texts:
                text.set_color('white')
                text.set_fontsize(20)  # Increase the font size of labels
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(22)
            
            st.pyplot(fig)

    def show_statistics(self, no_events, ou_predictions, btts_predictions, result_predictions,
                        first_round, last_round, ou_bets, btts_bets, result_bets, predictions):
        col1, col2 = st.columns(2)
        with col1:
            ou_accuracy_pred = 0
            btts_accuracy_pred = 0
            result_accuracy_pred = 0
            if predictions != 0:
                predictions = predictions / no_events
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
            styled_df = df.style.applymap(self.highlight_cells_profit, subset = ['Profit (unit)'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        col3, col4 = st.columns(2)
        with col3:
            st.write("Obrazowe porównanie liczby poprawnych i niepoprawnych predykcji")
            self.generate_comparision(['OU', 'BTTS', 'REZULTAT'], 
                                      [ou_predictions['correct_ou_pred'], btts_predictions['correct_btts_pred'], result_predictions['correct_result_pred']], 
                                      [predictions - ou_predictions['correct_ou_pred'], predictions - btts_predictions['correct_btts_pred'], predictions - result_predictions['correct_result_pred']])
        with col4:
            st.write("Obrazowe porównanie liczby poprawnych i niepoprawnych zakładów")
            self.generate_comparision(['OU', 'BTTS', 'REZULTAT'], 
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
                self.generate_pie_chart_binary(['Under 2.5', 'Over 2.5'], 
                                               round(ou_predictions['under_pred'] * 100 / predictions, 2), 
                                               round(ou_predictions['over_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
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
                self.generate_pie_chart_binary(['Under 2.5', 'Over 2.5'], 
                                               round(ou_bets['under_bets'] * 100 / ou_bets['ou_bets'], 2), 
                                               round(ou_bets['over_bets'] * 100 / ou_bets['ou_bets'], 2))
                st.write('Wynik zakładów w zależności od typu zdarzenia')
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
                self.generate_pie_chart_binary(['NO BTTS', 'BTTS'], 
                                               round(btts_predictions['btts_no_pred'] * 100 / predictions, 2), 
                                               round(btts_predictions['btts_yes_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
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
                self.generate_pie_chart_binary(["NO BTTS", "BTTS"], 
                                               round(btts_bets['btts_no_bets'] * 100 / btts_bets['btts_bets'], 2), 
                                               round(btts_bets['btts_yes_bets'] * 100 / btts_bets['btts_bets'], 2))
                st.write('Wynik zakładów w zależności od typu zdarzenia')
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
                self.generate_pie_chart_result(["Gospodarz", "Remis", "Gość"], 
                                               round(result_predictions['home_win_pred'] * 100 / predictions, 2), 
                                               round(result_predictions['draw_pred'] * 100 / predictions, 2),
                                               round(result_predictions['away_win_pred'] * 100 / predictions, 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
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
                self.generate_pie_chart_result(["Gospodarz", "Remis", "Gość"], 
                                               round(result_bets['home_win_bets'] * 100 / result_bets['result_bets'], 2),
                                               round(result_bets['draw_bets'] * 100 / result_bets['result_bets'], 2),
                                               round(result_bets['away_win_bets'] * 100 / result_bets['result_bets'], 2))
                st.write('Wynik przewidywań w zależności od typu zdarzenia')
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
        EV_flag = st.checkbox("Tylko wartościowe zakłady")
        rounds = list(range(first_round, last_round + 1))
        rounds_str =','.join(map(str, rounds))
        query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where league = {} and season = {} and round in ({}) and result != '0'".format(league, season, rounds_str)
        #query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0'"
        match_stats_df = pd.read_sql(query, self.conn)
        no_events = 3 #OU, BTTS, RESULT
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
                if EV_flag and bet['EV'] < 0:
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
        self.show_statistics(no_events, ou_predictions, btts_predictions, result_predictions,
                        first_round, last_round, ou_bets, btts_bets, result_bets, predictions)

    def highlight_cells_EV(self, val):
        color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else ''
        return color
    
    def highlight_cells_profit(self, val):
        color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else 'background-color: lightcoral'
        return color
    
    def goals_bar_chart(self,date, opponent, goals, team_name, ou_line):
        data = {
        'Date': [x for x in reversed(date)],
        'Opponent': [x[:3] for x in reversed(opponent)],
        'Goals': [x for x in reversed(goals)],
        }
        df = pd.DataFrame(data)

        # Konfigurowanie stylu wykresu
        sns.set_theme(style="darkgrid")

        # Tworzenie wykresu goals
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Goals'], color='gray')
        avg_goals = df['Goals'].mean()
        hit_rate = (df['Goals'] > ou_line).mean() * 100
        # Ustawienia osi
        ax.grid(False)
        ax.axhline(y=ou_line, color='white', linestyle='--', linewidth=2)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Bramki w meczach: {} \nŚrednia: {:.1f} \nHitrate O {}: {:.1f}%".format(team_name, avg_goals, ou_line, hit_rate), loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

        # Kolorowanie pasków na czerwono lub zielono
        for bar, goals in zip(bars, df['Goals']):
            if goals > ou_line:
                bar.set_color('green')
            else:
                bar.set_color('red')
            ax.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() - 0.4, 0.5), f'{int(goals)}', 
                ha='center', va='bottom', color='white', fontsize=16)

        # Wyświetlenie wykresu
        st.pyplot(fig)

    def btts_bar_chart(self, date, opponent, btts, team_name):
        data = {
        'Date': [x for x in reversed(date)],
        'Opponent': [x[:3] for x in reversed(opponent)],
        'BTTS': [x for x in reversed(btts)],
        }
        df = pd.DataFrame(data)

        # Konfigurowanie stylu wykresu
        sns.set_theme(style="darkgrid")

        # Tworzenie wykresu goals
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['BTTS'], color='gray')
        hit_rate = (df['BTTS'] == 1).mean() * 100
        # Ustawienia osi
        ax.grid(False)
        ax.axhline(y=0, color='white', linestyle='-', linewidth=2, label='Goal Threshold')
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("BTTS w meczach: {} \nLiczba BTTS: {} \nHitrate BTTS: {:.1f}%".format(team_name, (df['BTTS'] == 1).sum(),  hit_rate), loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

        # Kolorowanie pasków na czerwono lub zielono
        for bar, btts in zip(bars, df['BTTS']):
            if btts == 1:
                bar.set_color('green')
            else:
                bar.set_color('red')

        # Wyświetlenie wykresu
        st.pyplot(fig)

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
        for index, row in data.iterrows():
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

    def matches_list(self, date, home_team, home_team_score, away_team, away_team_score, team_name):
        outcome = []
        for i in range(len(date)):
            if home_team[i] == team_name:
                if home_team_score[i] > away_team_score[i]:
                    outcome.append('✅')
                elif home_team_score[i] < away_team_score[i]:
                    outcome.append('❌')
                else:
                    outcome.append('🤝')
            else:
                if home_team_score[i] < away_team_score[i]:
                    outcome.append('✅')
                elif home_team_score[i] > away_team_score[i]:
                    outcome.append('❌')
                else:
                    outcome.append('🤝')
        data = {
        'Data': [x for x in date],
        'Gospodarz' : [x for x in home_team],
        'Wynik' : [str(x) + "-" + str(y) for x,y in zip(home_team_score, away_team_score)],
        'Gość' : [x for x in away_team],
        'Rezultat' : [x for x in outcome]
        }
        df = pd.DataFrame(data)
        df.index = range(1, len(df) + 1)
        st.dataframe(df, use_container_width=True, hide_index=True)

    def graph_winner(self, home, draw, away):
        # Dane do wykresu
        data = {
        'Label': ["Gospodarz", "Remis", "Gość"],
        'Ppb': [home, draw, away],
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        # Ustawienia wykresu
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Ppb'], color=['lightgreen', 'lightblue', 'orangered'])
        ax.grid(False)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Rozkład prawdopodobieństwa zdarzenia: Rezultat", loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        for bar, ppb in zip(bars, df['Ppb']):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
                ha='center', va='bottom', color='black', fontsize=22)
        st.pyplot(fig)

    def graph_ou(self, under, over):
         # Dane do wykresu
        data = {
        'Label': ["Under 2.5", "Over 2.5"],
        'Ppb': [under, over],
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        # Ustawienia wykresu
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Ppb'], color=['orangered', 'lightgreen'])
        ax.grid(False)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Rozkład prawdopodobieństwa zdarzenia: OU 2.5", loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        for bar, ppb in zip(bars, df['Ppb']):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
                ha='center', va='bottom', color='black', fontsize=22)
        st.pyplot(fig)

    def graph_exact_goals(self, goals_no):
         # Dane do wykresu
        data = {
        'Label': ["0 bramek", "1 bramka", "2 bramki", "3 bramki", "4 bramki", "5 bramek", "6 lub więcej"],
        'Ppb': [x for x in goals_no],
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        # Ustawienia wykresu
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Ppb'], color=['lightblue' for x in range(7)])
        ax.grid(False)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 13)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Rozkład ppb. zdarzenia: Dokładna liczba bramek", loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        for bar, ppb in zip(bars, df['Ppb']):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 3, f'{float(ppb)}%', 
                ha='center', va='bottom', color='black', fontsize=16)
        st.pyplot(fig)

    def graph_btts(self, no, yes):
        # Dane do wykresu
        data = {
        'Label': ["Nie", "Tak"],
        'Ppb': [no, yes],
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        # Ustawienia wykresu
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Ppb'], color=['orangered', 'lightgreen'])
        ax.grid(False)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Rozkład prawdopodobieństwa zdarzenia: BTTS", loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        for bar, ppb in zip(bars, df['Ppb']):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
                ha='center', va='bottom', color='black', fontsize=22)
        st.pyplot(fig)

    def goals_line_chart(self,date, opponent, goals, team_name, ou_line):
        data = {
        'Date': [x for x in reversed(date)],
        'Opponent': [x[:3] for x in reversed(opponent)],
        'Goals': [x for x in reversed(goals)],
        }
        df = pd.DataFrame(data)

        # Konfigurowanie stylu wykresu
        sns.set_theme(style="darkgrid")

        # Tworzenie wykresu goals
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df.index, df['Goals'], color='gray')
        avg_goals = df['Goals'].mean()
        hit_rate = (df['Goals'] > ou_line).mean() * 100
        # Ustawienia osi
        ax.grid(False)
        ax.axhline(y=ou_line, color='white', linestyle='-', linewidth=2)
        ax.set_xticks(df.index)
        ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("Bramki w meczach: {} \nŚrednia: {:.1f} \nHitrate O {}: {:.1f}%".format(team_name, avg_goals, ou_line, hit_rate), loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

        # Kolorowanie pasków na czerwono lub zielono
        for bar, goals in zip(bars, df['Goals']):
            if goals > ou_line:
                bar.set_color('green')
            else:
                bar.set_color('red')
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 0.25, f'{int(goals)}', 
                ha='center', va='bottom', color='black', fontsize=12)

        # Wyświetlenie wykresu
        st.pyplot(fig)

    def match_pred_summary(self, id, result, home_goals, away_goals):
        st.header("Pomeczowe statystyki predykcji i zakładów")
        EV_plus = st.checkbox("Uwzględnij tylko wartościowe zakłady (VB > 0)")
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
                if EV_plus:
                    if row['EV'] > 0:
                        bet_placed[2] = 'TAK'
                else:
                    bet_placed[2] = 'TAK'
            if row['event_id'] in (8,12):
                if EV_plus:
                    if row['EV'] > 0:
                        bet_placed[0] = 'TAK'
                else:
                    bet_placed[0] = 'TAK'
            if row['event_id'] in (6, 172):
                if EV_plus:
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
        #styled_df = df.style.applymap(self.highlight_cells_EV, subset = ['VB'])
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
            st.write("Skuteczność predykcji dla analizowanego meczu: {:.2f}%".format(100 * correct_bet / max(no_bets,1)))
        else:
            st.write("Dla wybranego meczu nie zawarto żadnych zakładów")

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
            self.graph_winner(home_win[0][0], draw[0][0], guest_win[0][0])
        with col2:
            self.graph_btts(btts_no[0][0], btts_yes[0][0])

        col3, col4 = st.columns(2)
        with col3:
            self.graph_exact_goals(goals_no)
        with col4:
            self.graph_ou(under_2_5[0][0], over_2_5[0][0])
        
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
        styled_df = df.style.applymap(self.highlight_cells_EV, subset = ['VB'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.write("Zakłady o współczynniku VB (Value Bet) większym od 0 (oznaczone jasnozielonym tłem) uznawane są za WARTE ROZPATRZENIA")
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

    def winner_bar_chart(self, opponent, home_team, away_team, result, team_name):
        wins, draws, loses = 0, 0, 0
        for i in range(len(opponent)):
            if home_team[i] == team_name:
                if result[i] == '1':
                    wins = wins + 1
                elif result[i] == 'X':
                    draws = draws + 1
                else:
                    loses = loses + 1
            else:
                if result[i] == '1':
                    loses = loses + 1
                elif result[i] == 'X':
                    draws = draws + 1
                else:
                    wins = wins + 1
        data = {
        'Label': ["Porażki", "Remisy", "Wygrane"],
        'Results' : [loses, draws, wins]
        }
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        # Ustawienia wykresu
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(df.index, df['Results'], color=['orangered', 'slategrey', 'lightgreen'])
        ax.grid(False)
        ax.set_yticks(df.index)
        ax.set_yticklabels([f"{label}" for label in df['Label']])
        ax.set_ylabel("")
        ax.set_xlabel("")
        ax.set_title("Rezultaty meczów: {}".format(team_name), loc='left', fontsize=24, color='white')
        ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
        ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
        fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
        for bar, result in zip(bars, df['Results']):
            ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2, f'{int(result)}', 
                ha='center', va='center', color='white', fontsize=22)
        st.pyplot(fig)

    def predicts_per_team(self, games, team_name, key):
        query = "select event_id, outcome from final_predictions f join matches m on m.id = f.match_id where (m.home_team = {} or m.away_team = {}) and m.result != '0' order by m.game_date desc".format(key, key)
        predicts_df = pd.read_sql(query, self.conn)
        result_outcomes = []
        btts_outcomes = []
        ou_outcomes = []
        counter = 0
        if len(predicts_df) > 0:
            for _, row in predicts_df.iterrows():
                counter = counter + 1
                if counter * 3 == games:
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
            st.header("Skuteczność predykcji ostatnich {} meczów z udziałem drużyny {}".format(min(games, len(predicts_df) // 3), team_name))
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
                self.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)
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
                self.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)
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
                self.generate_pie_chart_binary(['Niepoprawne', 'Poprawne'], liczba - suma, suma)


    def show_teams(self, teams_dict, games, ou_line):
        st.header("Drużyny grające w {} w sezonie {}:".format(self.name, self.years))
        for key, value in teams_dict.items():
            button_label = value
            if st.button(button_label, use_container_width = True):
                date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score, result = self.single_team_data(key)
                col1, col2 = st.columns(2)
                with col1:
                    with st.container():
                        self.goals_bar_chart(date[:games], opponent[:games], goals[:games], team_name, ou_line)
                with col2:
                    with st.container():
                        self.btts_bar_chart(date[:games], opponent[:games], btts[:games], team_name)
                col3, col4 = st.columns(2)
                with col3:
                    with st.container():
                        self.winner_bar_chart(opponent[:games], home_team[:games], away_team[:games] ,result[:games], team_name)
                with col4:
                    with st.container():
                        self.matches_list(date[:games], home_team[:games], home_team_score[:games], away_team[:games], away_team_score[:games], team_name)
                self.predicts_per_team(games, team_name, key)
                
