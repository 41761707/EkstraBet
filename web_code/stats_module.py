import numpy as np
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import plotly.express as px

import graphs_module
import tables_module

def show_statistics(no_events, ou_predictions, btts_predictions, result_predictions,
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
        st.header("Wszystkie przewidywnia")
        data = {
        'Zdarzenie': ["OU", "BTTS", "REZULTAT"],
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
        st.header("Wszystkie zakłady")
        data = {
        'Zdarzenie': ["OU", "BTTS", "REZULTAT"],
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
            'Zdarzenie': ["Under 2.5", "Over 2.5"],
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
            graphs_module.generate_pie_chart(['Under 2.5', 'Over 2.5'], 
                                            [round(ou_predictions['under_pred'] * 100 / predictions, 2), 
                                            round(ou_predictions['over_pred'] * 100 / predictions, 2)])
            st.write('Wynik przewidywań w zależności od typu zdarzenia')
            graphs_module.generate_comparision(['Under 2.5', 'Over 2.5'], 
                                        [ou_predictions['under_correct'], ou_predictions['over_correct']],
                                        [ou_predictions['under_pred'] - ou_predictions['under_correct'], ou_predictions['over_pred'] - ou_predictions['over_correct']])
    with col6:
        if ou_bets['ou_bets'] > 0:
            st.header("Under vs Over - porównanie liczby zakładów oraz ich skuteczności")
            data = {
            'Zdarzenie': ["Under 2.5", "Over 2.5"],
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
            graphs_module.generate_pie_chart(['Under 2.5', 'Over 2.5'], 
                                            [round(ou_bets['under_bets'] * 100 / ou_bets['ou_bets'], 2), 
                                            round(ou_bets['over_bets'] * 100 / ou_bets['ou_bets'], 2)])
            st.write('Wynik zakładów w zależności od typu zdarzenia')
            graphs_module.generate_comparision(['Under 2.5', 'Over 2.5'], 
                                        [ou_bets['under_correct'], ou_bets['over_correct']],
                                        [ou_bets['under_bets'] - ou_bets['under_correct'], ou_bets['over_bets'] - ou_bets['over_correct']])
    col7, col8 = st.columns(2)
    with col7:
        if predictions > 0:
            st.header("NO BTTS vs BTTS - porównanie liczby predykcji oraz ich skuteczności")
            data = {
            'Zdarzenie': ["NO BTTS", "BTTS"],
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
            graphs_module.generate_pie_chart(['NO BTTS', 'BTTS'], 
                                            [round(btts_predictions['btts_no_pred'] * 100 / predictions, 2), 
                                            round(btts_predictions['btts_yes_pred'] * 100 / predictions, 2)])
            st.write('Wynik przewidywań w zależności od typu zdarzenia')
            graphs_module.generate_comparision(['NO BTTS', 'BTTS'], 
                                        [btts_predictions['btts_no_correct'], btts_predictions['btts_yes_correct']],
                                        [btts_predictions['btts_no_pred'] - btts_predictions['btts_no_correct'], btts_predictions['btts_yes_pred'] - btts_predictions['btts_yes_correct']])
    with col8:
        if btts_bets['btts_bets'] > 0:
            st.header("NO BTTS vs BTTS - porównanie liczby zakładów oraz ich skuteczności")
            data = {
            'Zdarzenie': ["NO BTTS", "BTTS"],
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
            graphs_module.generate_pie_chart(["NO BTTS", "BTTS"], 
                                            [round(btts_bets['btts_no_bets'] * 100 / btts_bets['btts_bets'], 2), 
                                            round(btts_bets['btts_yes_bets'] * 100 / btts_bets['btts_bets'], 2)])
            st.write('Wynik zakładów w zależności od typu zdarzenia')
            graphs_module.generate_comparision(['NO BTTS', 'BTTS'],  
                                        [btts_bets['btts_no_correct'], btts_bets['btts_yes_correct']],
                                        [btts_bets['btts_no_bets'] - btts_bets['btts_no_correct'], btts_bets['btts_yes_bets'] - btts_bets['btts_yes_correct']])
    col9, col10 = st.columns(2)
    with col9:
        if result_bets['result_bets'] > 0:
            st.header("1x2 - porównanie liczby predykcji oraz ich skuteczności")
            data = {
            'Zdarzenie': ["Gospodarz", "Remis", "Gość"],
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
            st.header("1x2 - porównanie liczby zakładów oraz ich skuteczności")
            data = {
            'Zdarzenie': ["Gospodarz", "Remis", "Gość"],
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

def generate_statistics(query, tax_flag, first_round, last_round, no_events, conn, EV_plus):
    match_stats_df = pd.read_sql(query, conn)
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
        predictions_df = pd.read_sql(query, conn)
        query = 'select event_id, odds, bookmaker, EV from bets where match_id = {}'.format(id)
        bets_df = pd.read_sql(query, conn)
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
            if EV_plus and bet['EV'] < 0:
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
    show_statistics(no_events, ou_predictions, btts_predictions, result_predictions,
                    first_round, last_round, ou_bets, btts_bets, result_bets, predictions)
    
def league_charachteristics(conn, league_id, season_id, teams_dict, no_games):
    tab1, tab2, tab3 = st.tabs(["OU", "BTTS", "REZULTAT"])
    with tab1:
        st.write("OU")
        query = ''' select
                        sum(case when home_team_goals + away_team_goals > 2.5 then 1 else 0 end) as O,
                        sum(case when home_team_goals + away_team_goals < 2.5 then 1 else 0 end) as U,
                        avg(home_team_goals + away_team_goals) as A
                    from matches
                    where league = {}
                        and season = {}
                        and result != '0'
            '''.format(league_id, season_id)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        labels_table = ['Under 2.5', 'Over 2.5']
        values = [results[0][1], results[0][0]]
        values_percentage = [round(results[0][1] * 100 / no_games, 2), round(results[0][0] * 100 / no_games, 2)]
        title = "Procentowy rozkład OU w lidze"
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Średnia bramek w meczu: {}".format(round(results[0][2], 2)))
            tables_module.league_stats(labels_table, values , values_percentage)
        with col2:
            graphs_module.side_bar_graph(labels_table, values_percentage, title)
    with tab2:
        st.write("BTTS")
        query = ''' select
                        sum(case when home_team_goals > 0 and away_team_goals > 0 then 1 else 0 end) as BTTS,
                        sum(case when home_team_goals = 0 or  away_team_goals = 0 then 1 else 0 end) as NO_BTTS
                    from matches
                    where league = {}
                        and season = {}
                        and result != '0'
            '''.format(league_id, season_id)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        labels_table = ['NO BTTS', 'BTTS']
        values = [results[0][1], results[0][0]]
        values_percentage = [round(results[0][1] * 100 / no_games, 2), round(results[0][0] * 100 / no_games, 2)]
        title = "Procentowy rozkład BTTS w lidze"
        col1, col2 = st.columns(2)
        with col1:
            tables_module.league_stats(labels_table, values , values_percentage)
        with col2:
            graphs_module.side_bar_graph(labels_table, values_percentage, title)
    with tab3:
        st.write("REZULTAT")
        query = ''' select
                        sum(case when result = '1' then 1 else 0 end) as HOME_WINS,
                        sum(case when result = 'X' then 1 else 0 end) as DRAWS,
                        sum(case when result = '2' then 1 else 0 end) as AWAY_WINS
                    from matches
                    where league = {}
                        and season = {}
                        and result != '0'
            '''.format(league_id, season_id)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        labels_table = ['Wygrana gościa', 'Remis', 'Wygrana gospodarza']
        values = [results[0][2], results[0][1], results[0][0]]
        values_percentage = [round(results[0][2] * 100 / no_games, 2), round(results[0][1] * 100 / no_games, 2), round(results[0][0] * 100 / no_games, 2)]
        title = "Procentowy rozkład zwycięstw w lidze"
        col1, col2 = st.columns(2)
        with col1:
            tables_module.league_stats(labels_table, values , values_percentage)
        with col2:
            graphs_module.side_bar_graph(labels_table, values_percentage, title)

        st.subheader("Zwycięstwa - podział na drużyny")
        

def aggreate_acc_graph(title, teams, predictions, corrects, acc):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(title)
        data = {
        'Drużyna' : teams,
        'Liczba predykcji' : predictions,
        'Poprawne' : corrects,
        'Skuteczność (%)' : acc
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        if acc is not None:
            graphs_module.team_compare_graph(teams, acc)

def aggreate_acc_profit(title, args):
    col1, col2 = st.columns(2)
    teams = [arg[0] for arg in args]
    profit = [arg[1] for arg in args]
    with col1:
        st.subheader(title)
        data = {
        'Drużyna' : teams,
        'Profit [u]' : profit
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        if args[1] is not None:
            graphs_module.team_compare_graph(teams, profit, type = 'profit')

def aggregate_team_acc(teams_dict, league_id, season_id, conn):
    predictions_ratio = [] #team, result_ratio, ou_ratio, btts_ratio
    predictions_total = []
    for k,v in teams_dict.items():
        #OU - predykcje per team
        query = '''select 
                        count(case when f.event_id in (1,2,3) then 1 end) as result_predictions,
                        count(case when f.event_id in (1,2,3) and f.outcome = 1 then 1 end) as results_correct,
                        count(case when f.event_id in (8, 12) then 1 end) as ou_predictions,
                        count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) as ou_correct,
                        count(case when f.event_id in (6, 172) then 1 end) as btts_predictions,
                        count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) as btts_correct
                    from final_predictions f
                        join matches m on f.match_id = m.id
                        where m.season = {} and m.result != '0'
                            and (m.home_team = {} or m.away_team = {})'''.format(season_id, k, k)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        if results[0][0] > 0:
            predictions_total.append([v, results[0][0], results[0][1], results[0][2], results[0][3], results[0][4], results[0][5]])
            predictions_ratio.append([v, round(results[0][1] / results[0][0], 2), round(results[0][3] / results[0][2], 2) ,round(results[0][5] / results[0][4], 2)])

    query = ''' select
                    count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) / count(case when f.event_id in (8, 12) then 1 end) * 100 as ou_avg,
                    count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) / count(case when f.event_id in (6, 172) then 1 end) * 100 as btts_avg,
                    count(case when f.event_id in (1, 2, 3) and f.outcome = 1 then 1 end) / count(case when f.event_id in (1, 2, 3) then 1 end) * 100 as result_avg,
                    count(case when f.event_id in (1,2,3) then 1 end) as result_predictions,
                    count(case when f.event_id in (1,2,3) and f.outcome = 1 then 1 end) as results_correct,
                    count(case when f.event_id in (8, 12) then 1 end) as ou_predictions,
                    count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) as ou_correct,
                    count(case when f.event_id in (6, 172) then 1 end) as btts_predictions,
                    count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) as btts_correct
                from final_predictions f
                    join matches m on f.match_id = m.id and m.result != '0'
                    where m.season = {}
                        and m.league = {}'''.format(season_id, league_id) 
    cursor = conn.cursor()
    cursor.execute(query)
    avgs = cursor.fetchall()
    teams = [x[0] for x in predictions_total]
    teams.append('ŚREDNIA')
    ou_number = [x[3] for x in predictions_total]
    ou_number.append(int(avgs[0][5]))
    ou_correct = [x[4] for x in predictions_total]
    ou_correct.append(int(avgs[0][6]))

    btts_number = [x[5] for x in predictions_total]
    btts_number.append(int(avgs[0][7]))
    btts_correct = [x[6] for x in predictions_total]
    btts_correct.append(int(avgs[0][8]))

    result_number = [x[1] for x in predictions_total]
    result_number.append(int(avgs[0][3]))
    result_correct = [x[2] for x in predictions_total]
    result_correct.append(int(avgs[0][4]))
    
    ou_acc = [int(x[2] * 100) for x in predictions_ratio]
    btts_acc = [int(x[3] * 100) for x in predictions_ratio]
    result_acc = [int(x[1] * 100) for x in predictions_ratio]
    if avgs[0][0] is None:
        ou_acc.append(0)
    else:
        ou_acc.append(round(float(avgs[0][0]), 2))
    if avgs[0][1] is None:
        btts_acc.append(0)
    else:
        btts_acc.append(round(float(avgs[0][1]), 2))
    if avgs[0][2] is None:
        result_acc.append(0)
    else:
        result_acc.append(round(float(avgs[0][2]), 2))

    tab1, tab2, tab3 = st.tabs(["Predykcje OU", "Predykcje BTTS", "Predykcje REZULTAT"])
    with tab1:
        aggreate_acc_graph("Porównanie dokładności predykcji OU między drużynami", teams, ou_number, ou_correct, ou_acc)
    with tab2:
        aggreate_acc_graph("Porównanie dokładności predykcji BTTS między drużynami", teams, btts_number, btts_correct, btts_acc)

    with tab3:
        aggreate_acc_graph("Porównanie dokładności predykcji REZULTAT między drużynami", teams, result_number, result_correct, result_acc)


def aggregate_leagues_acc(season_id, conn):
    all_leagues = "select distinct id, name from leagues where active = 1".format()
    all_leagues_df = pd.read_sql(all_leagues, conn)
    leagues_dict = all_leagues_df.set_index('id')['name'].to_dict()
    query = "select count(*) from final_predictions"
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    predictions = results[0][0] // 3
    predictions_ratio = [] #team, result_ratio, ou_ratio, btts_ratio
    predictions_total = []
    for k,v in leagues_dict.items():
        query = '''select 
                        count(case when f.event_id in (1,2,3) then 1 end) as result_predictions,
                        count(case when f.event_id in (1,2,3) and f.outcome = 1 then 1 end) as results_correct,
                        count(case when f.event_id in (8, 12) then 1 end) as ou_predictions,
                        count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) as ou_correct,
                        count(case when f.event_id in (6, 172) then 1 end) as btts_predictions,
                        count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) as btts_correct
                    from final_predictions f
                        join matches m on f.match_id = m.id
                        where m.season = {} and m.result != '0'
                            and m.league = {}'''.format(season_id, k)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        if results[0][0] > 0:
            predictions_total.append([v, results[0][0], results[0][1], results[0][2], results[0][3], results[0][4], results[0][5]])
            predictions_ratio.append([v, round(results[0][1] / results[0][0], 2), round(results[0][3] / results[0][2], 2) ,round(results[0][5] / results[0][4], 2)])

    query = ''' select
                    count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) / count(case when f.event_id in (8, 12) then 1 end) * 100 as ou_avg,
                    count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) / count(case when f.event_id in (6, 172) then 1 end) * 100 as btts_avg,
                    count(case when f.event_id in (1, 2, 3) and f.outcome = 1 then 1 end) / count(case when f.event_id in (1, 2, 3) then 1 end) * 100 as result_avg,
                    count(case when f.event_id in (1,2,3) then 1 end) as result_predictions,
                    count(case when f.event_id in (1,2,3) and f.outcome = 1 then 1 end) as results_correct,
                    count(case when f.event_id in (8, 12) then 1 end) as ou_predictions,
                    count(case when f.event_id in (8, 12) and f.outcome = 1 then 1 end) as ou_correct,
                    count(case when f.event_id in (6, 172) then 1 end) as btts_predictions,
                    count(case when f.event_id in (6, 172) and f.outcome = 1 then 1 end) as btts_correct
                from final_predictions f
                    join matches m on f.match_id = m.id and m.result != '0'
                    where m.season = {}'''.format(season_id) 
    cursor = conn.cursor()
    cursor.execute(query)
    avgs = cursor.fetchall()
    teams = [x[0] for x in predictions_total]
    teams.append('ŚREDNIA')
    ou_number = [x[3] for x in predictions_total]
    ou_number.append(int(avgs[0][5]))
    ou_correct = [x[4] for x in predictions_total]
    ou_correct.append(int(avgs[0][6]))

    btts_number = [x[5] for x in predictions_total]
    btts_number.append(int(avgs[0][7]))
    btts_correct = [x[6] for x in predictions_total]
    btts_correct.append(int(avgs[0][8]))

    result_number = [x[1] for x in predictions_total]
    result_number.append(int(avgs[0][3]))
    result_correct = [x[2] for x in predictions_total]
    result_correct.append(int(avgs[0][4]))
    
    ou_acc = [int(x[2] * 100) for x in predictions_ratio]
    ou_acc.append(round(float(avgs[0][0]), 2))
    btts_acc = [int(x[3] * 100) for x in predictions_ratio]
    btts_acc.append(round(float(avgs[0][1]), 2))
    result_acc = [int(x[1] * 100) for x in predictions_ratio]
    result_acc.append(round(float(avgs[0][2]), 2))

    tab1, tab2, tab3 = st.tabs(["Predykcje OU", "Predykcje BTTS", "Predykcje REZULTAT"])
    with tab1:
        aggreate_acc_graph("Porównanie dokładności predykcji OU między ligami", teams, ou_number, ou_correct, ou_acc)

    with tab2:
        aggreate_acc_graph("Porównanie dokładności predykcji BTTS między ligami", teams, btts_number, btts_correct, btts_acc)

    with tab3:
        aggreate_acc_graph("Porównanie dokładności predykcji REZULTAT między ligami", teams, result_number, result_correct, result_acc)


def aggregate_leagues_profit(season_id, conn):
    all_leagues = "select distinct id, name from leagues where active = 1".format()
    all_leagues_df = pd.read_sql(all_leagues, conn)
    leagues_dict = all_leagues_df.set_index('id')['name'].to_dict()
    bets_ratio = [] #team, result_ratio, ou_ratio, btts_ratio
    bets_total = []
    bets_profit = []
    for k,v in leagues_dict.items():
        query = '''select 
                        count(case when b.event_id in (1, 2, 3) then 1 end) as result_bets,
                        count(case when b.event_id in (1, 2, 3) and b.outcome = 1 then 1 end) as results_correct,
                        count(case when b.event_id in (8, 12) then 1 end) as ou_bets,
                        count(case when b.event_id in (8, 12) and b.outcome = 1 then 1 end) as ou_correct,
                        count(case when b.event_id in (6, 172) then 1 end) as btts_bets,
                        count(case when b.event_id in (6, 172) and b.outcome = 1 then 1 end) as btts_correct,
                        sum(case 
							when b.event_id IN (1, 2, 3) AND b.outcome = 1 THEN b.odds - 1
							when b.event_id IN (1, 2, 3) AND b.outcome = 0 THEN -1
							else 0 end ) as result_profit,
                        sum(case 
							when b.event_id IN (8, 12) AND b.outcome = 1 THEN b.odds - 1
							when b.event_id IN (8, 12) AND b.outcome = 0 THEN -1
							else 0 end ) as ou_profit,
                        sum(case 
							when b.event_id IN (6, 172) AND b.outcome = 1 THEN b.odds - 1
							when b.event_id IN (6, 172) AND b.outcome = 0 THEN -1
							else 0 end ) as btts_profit  
                    from bets b
                        join matches m on b.match_id = m.id
                        where m.season = {} and m.result != '0'
                            and m.league = {}'''.format(season_id, k)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        if results[0][0] > 0:
            bets_total.append([v, results[0][0], results[0][1], results[0][2], results[0][3], results[0][4], results[0][5]])
            bets_ratio.append([v, round(results[0][1] / results[0][0], 2), round(results[0][3] / results[0][2], 2) ,round(results[0][5] / results[0][4], 2)])
            bets_profit.append([v, round(results[0][6], 2), round(results[0][7], 2), round(results[0][8], 2)])
    query = ''' select
                    'SUMA' as league_name,
                    sum(case 
                        when b.event_id IN (1, 2, 3) AND b.outcome = 1 THEN b.odds - 1
                        when b.event_id IN (1, 2, 3) AND b.outcome = 0 THEN -1
                        else 0 end ) as result_profit,
                    sum(case 
                        when b.event_id IN (8, 12) AND b.outcome = 1 THEN b.odds - 1
                        when b.event_id IN (8, 12) AND b.outcome = 0 THEN -1
                        else 0 end ) as ou_profit,
                    sum(case 
                        when b.event_id IN (6, 172) AND b.outcome = 1 THEN b.odds - 1
                        when b.event_id IN (6, 172) AND b.outcome = 0 THEN -1
                        else 0 end ) as btts_profit,
                        count(case when b.event_id in (1, 2, 3) then 1 end) as result_bets,
                        count(case when b.event_id in (1, 2, 3) and b.outcome = 1 then 1 end) as results_correct,
                        count(case when b.event_id in (8, 12) then 1 end) as ou_bets,
                        count(case when b.event_id in (8, 12) and b.outcome = 1 then 1 end) as ou_correct,
                        count(case when b.event_id in (6, 172) then 1 end) as btts_bets,
                        count(case when b.event_id in (6, 172) and b.outcome = 1 then 1 end) as btts_correct
                from bets b
                    join matches m on b.match_id = m.id
                    where m.season = {} and m.result != '0' '''.format(season_id) 
    cursor = conn.cursor()
    cursor.execute(query)
    all_bets = cursor.fetchall()
    #bets_profit.append([all_bets[0][0], round(all_bets[0][1], 2), round(all_bets[0][2], 2), round(all_bets[0][3], 2)])
    result_to_graph = []
    ou_to_graph = []
    btts_to_graph = []
    for element in bets_profit:
        result_to_graph.append([element[0], element[1]])
        ou_to_graph.append([element[0], element[2]])
        btts_to_graph.append([element[0], element[3]])

    result_to_graph.sort(key=lambda x: x[1], reverse=True)
    ou_to_graph.sort(key=lambda x: x[1], reverse=True)
    btts_to_graph.sort(key=lambda x: x[1], reverse=True)
    
    tab1, tab2, tab3 = st.tabs(["Profit z zakładów OU", "Profit z zakładów BTTS", "Profit z zakładów REZULTAT"])

    with tab1:
        aggreate_acc_profit("Porównanie profitu z zakładów OU między ligami", ou_to_graph)
    with tab2:
        aggreate_acc_profit("Porównanie profitu z zakładów BTTS między ligami", btts_to_graph) 
    with tab3:
        aggreate_acc_profit("Porównanie profitu z zakładów REZULTAT między ligami", result_to_graph)





