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

def show_distribution(title, labels, values):
    st.write(title)
    total = sum(values)
    if total == 0:
        percentages = [0 for _ in values]
    else:
        percentages = [round(v * 100 / total, 2) for v in values]
    graphs_module.generate_pie_chart(labels, percentages)

def show_comparison(title, labels, correct, incorrect):
    st.write(title)
    graphs_module.generate_comparision(labels, correct, incorrect)

def show_ou_statistics(ou_predictions, ou_bets):
    col1, col2 = st.columns(2)
    labels = ['Under 2.5', 'Over 2.5']
    with col1:
        st.header("OU - Predykcje")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [ou_predictions['under'], ou_predictions['over'], ou_predictions['under'] + ou_predictions['over']],
            'Poprawne': [ou_predictions['under_correct'], ou_predictions['over_correct'], ou_predictions['under_correct'] + ou_predictions['over_correct']],
            '% wszystkich': [
                f"{round(100 * ou_predictions['under'] / max(ou_predictions['under'] + ou_predictions['over'], 1), 2)}%",
                f"{round(100 * ou_predictions['over'] / max(ou_predictions['under'] + ou_predictions['over'], 1), 2)}%",
                "100%"
            ],
            'Skuteczność': [
                f"{round(100 * ou_predictions['under_correct'] / max(ou_predictions['under'], 1), 2)}%",
                f"{round(100 * ou_predictions['over_correct'] / max(ou_predictions['over'], 1), 2)}%",
                f"{round(100 * (ou_predictions['under_correct'] + ou_predictions['over_correct']) / max(ou_predictions['under'] + ou_predictions['over'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if ou_predictions['under'] + ou_predictions['over'] > 0:
            show_distribution('Rozkład wykonanych przewidywań na zdarzenie OU', labels, [ou_predictions['under'], ou_predictions['over']])
            show_comparison('Wynik przewidywań w zależności od typu zdarzenia', labels,
                            [ou_predictions['under_correct'], ou_predictions['over_correct']],
                            [ou_predictions['under'] - ou_predictions['under_correct'], ou_predictions['over'] - ou_predictions['over_correct']])
    with col2:
        st.header("OU - Zakłady")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [ou_bets['under'], ou_bets['over'], ou_bets['under'] + ou_bets['over']],
            'Poprawne': [ou_bets['under_correct'], ou_bets['over_correct'], ou_bets['under_correct'] + ou_bets['over_correct']],
            'Profit (unit)': [str(round(ou_bets['profit_under'], 2)), str(round(ou_bets['profit_over'], 2)), str(round(ou_bets['profit_under'] + ou_bets['profit_over'], 2))],
            'Skuteczność': [
                f"{round(100 * ou_bets['under_correct'] / max(ou_bets['under'], 1), 2)}%",
                f"{round(100 * ou_bets['over_correct'] / max(ou_bets['over'], 1), 2)}%",
                f"{round(100 * (ou_bets['under_correct'] + ou_bets['over_correct']) / max(ou_bets['under'] + ou_bets['over'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        styled_df = df.style.applymap(graphs_module.highlight_cells_profit, subset=['Profit (unit)'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        if ou_bets['under'] + ou_bets['over'] > 0:
            show_distribution('Rozkład wykonanych zakładów na zdarzenie OU', labels, [ou_bets['under'], ou_bets['over']])
            show_comparison('Wynik zakładów w zależności od typu zdarzenia', labels,
                            [ou_bets['under_correct'], ou_bets['over_correct']],
                            [ou_bets['under'] - ou_bets['under_correct'], ou_bets['over'] - ou_bets['over_correct']])

def show_btts_statistics(btts_predictions, btts_bets):
    col1, col2 = st.columns(2)
    labels = ['NO BTTS', 'BTTS']
    with col1:
        st.header("BTTS - Predykcje")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [btts_predictions['no'], btts_predictions['yes'], btts_predictions['no'] + btts_predictions['yes']],
            'Poprawne': [btts_predictions['no_correct'], btts_predictions['yes_correct'], btts_predictions['no_correct'] + btts_predictions['yes_correct']],
            '% wszystkich': [
                f"{round(100 * btts_predictions['no'] / max(btts_predictions['no'] + btts_predictions['yes'], 1), 2)}%",
                f"{round(100 * btts_predictions['yes'] / max(btts_predictions['no'] + btts_predictions['yes'], 1), 2)}%",
                "100%" ],
            'Skuteczność': [
                f"{round(100 * btts_predictions['no_correct'] / max(btts_predictions['no'], 1), 2)}%",
                f"{round(100 * btts_predictions['yes_correct'] / max(btts_predictions['yes'], 1), 2)}%",
                f"{round(100 * (btts_predictions['no_correct'] + btts_predictions['yes_correct']) / max(btts_predictions['no'] + btts_predictions['yes'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if btts_predictions['no'] + btts_predictions['yes'] > 0:
            show_distribution('Rozkład wykonanych przewidywań na zdarzenie BTTS', labels, [btts_predictions['no'], btts_predictions['yes']])
            show_comparison('Wynik przewidywań w zależności od typu zdarzenia', labels,
                        [btts_predictions['no_correct'], btts_predictions['yes_correct']],
                        [btts_predictions['no'] - btts_predictions['no_correct'], btts_predictions['yes'] - btts_predictions['yes_correct']])
    with col2:
        st.header("BTTS - Zakłady")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [btts_bets['no'], btts_bets['yes'], btts_bets['no'] + btts_bets['yes']],
            'Poprawne': [btts_bets['no_correct'], btts_bets['yes_correct'], btts_bets['no_correct'] + btts_bets['yes_correct']],
            'Profit (unit)': [str(round(btts_bets['profit_no'], 2)), str(round(btts_bets['profit_yes'], 2)), str(round(btts_bets['profit_no'] + btts_bets['profit_yes'], 2))],
            'Skuteczność': [
                f"{round(100 * btts_bets['no_correct'] / max(btts_bets['no'], 1), 2)}%",
                f"{round(100 * btts_bets['yes_correct'] / max(btts_bets['yes'], 1), 2)}%",
                f"{round(100 * (btts_bets['no_correct'] + btts_bets['yes_correct']) / max(btts_bets['no'] + btts_bets['yes'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        styled_df = df.style.applymap(graphs_module.highlight_cells_profit, subset=['Profit (unit)'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        if btts_bets['no'] + btts_bets['yes'] > 0:
            show_distribution('Rozkład wykonanych zakładów na zdarzenie BTTS', labels, [btts_bets['no'], btts_bets['yes']])
            show_comparison('Wynik zakładów w zależności od typu zdarzenia', labels,
                        [btts_bets['no_correct'], btts_bets['yes_correct']],
                        [btts_bets['no'] - btts_bets['no_correct'], btts_bets['yes'] - btts_bets['yes_correct']])

def show_result_statistics(result_predictions, result_bets):
    col1, col2 = st.columns(2)
    labels = ['Gospodarz', 'Remis', 'Gość']
    with col1:
        st.header("REZULTAT - Predykcje")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [result_predictions['home'], result_predictions['draw'], result_predictions['away'], result_predictions['home'] + result_predictions['draw'] + result_predictions['away']],
            'Poprawne': [result_predictions['home_correct'], result_predictions['draw_correct'], result_predictions['away_correct'], result_predictions['home_correct'] + result_predictions['draw_correct'] + result_predictions['away_correct']],
            '% wszystkich': [
                f"{round(100 * result_predictions['home'] / max(result_predictions['home'] + result_predictions['draw'] + result_predictions['away'], 1), 2)}%",
                f"{round(100 * result_predictions['draw'] / max(result_predictions['home'] + result_predictions['draw'] + result_predictions['away'], 1), 2)}%",
                f"{round(100 * result_predictions['away'] / max(result_predictions['home'] + result_predictions['draw'] + result_predictions['away'], 1), 2)}%",
                "100%"],
            'Skuteczność': [
                f"{round(100 * result_predictions['home_correct'] / max(result_predictions['home'], 1), 2)}%",
                f"{round(100 * result_predictions['draw_correct'] / max(result_predictions['draw'], 1), 2)}%",
                f"{round(100 * result_predictions['away_correct'] / max(result_predictions['away'], 1), 2)}%",
                f"{round(100 * (result_predictions['home_correct'] + result_predictions['draw_correct'] + result_predictions['away_correct']) / max(result_predictions['home'] + result_predictions['draw'] + result_predictions['away'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if result_predictions['home'] + result_predictions['draw'] + result_predictions['away'] > 0:
            show_distribution('Rozkład wykonanych przewidywań na zdarzenie REZULTAT', labels, [result_predictions['home'], result_predictions['draw'], result_predictions['away']])
            show_comparison('Wynik przewidywań w zależności od typu zdarzenia', labels,
                        [result_predictions['home_correct'], result_predictions['draw_correct'], result_predictions['away_correct']],
                        [result_predictions['home'] - result_predictions['home_correct'], result_predictions['draw'] - result_predictions['draw_correct'], result_predictions['away'] - result_predictions['away_correct']])
    with col2:
        st.header("REZULTAT - Zakłady")
        data = {
            'Typ': labels + ['Wszystkie'],
            'Wszystkie': [result_bets['home'], result_bets['draw'], result_bets['away'], result_bets['home'] + result_bets['draw'] + result_bets['away']],
            'Poprawne': [result_bets['home_correct'], result_bets['draw_correct'], result_bets['away_correct'], result_bets['home_correct'] + result_bets['draw_correct'] + result_bets['away_correct']],
            'Profit (unit)': [str(round(result_bets['profit_home'], 2)), str(round(result_bets['profit_draw'], 2)), str(round(result_bets['profit_away'], 2)), str(round(result_bets['profit_home'] + result_bets['profit_draw'] + result_bets['profit_away'], 2))],
            'Skuteczność': [
                f"{round(100 * result_bets['home_correct'] / max(result_bets['home'], 1), 2)}%",
                f"{round(100 * result_bets['draw_correct'] / max(result_bets['draw'], 1), 2)}%",
                f"{round(100 * result_bets['away_correct'] / max(result_bets['away'], 1), 2)}%",
                f"{round(100 * (result_bets['home_correct'] + result_bets['draw_correct'] + result_bets['away_correct']) / max(result_bets['home'] + result_bets['draw'] + result_bets['away'], 1), 2)}%"
            ]
        }
        df = pd.DataFrame(data)
        styled_df = df.style.applymap(graphs_module.highlight_cells_profit, subset=['Profit (unit)'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        if result_bets['home'] + result_bets['draw'] + result_bets['away'] > 0:
            show_distribution('Rozkład wykonanych zakładów na zdarzenie REZULTAT', labels, [result_bets['home'], result_bets['draw'], result_bets['away']])
            show_comparison('Wynik zakładów w zależności od typu zdarzenia', labels,
                        [result_bets['home_correct'], result_bets['draw_correct'], result_bets['away_correct']],
                        [result_bets['home'] - result_bets['home_correct'], result_bets['draw'] - result_bets['draw_correct'], result_bets['away'] - result_bets['away_correct']])

def show_all_statistics(stat_type, ou_predictions=None, btts_predictions=None, result_predictions=None,
                        ou_bets=None, btts_bets=None, result_bets=None):
    if stat_type == 'ou':
        show_ou_statistics(ou_predictions, ou_bets)
    elif stat_type == 'btts':
        show_btts_statistics(btts_predictions, btts_bets)
    elif stat_type == 'result':
        show_result_statistics(result_predictions, result_bets)
    elif stat_type == 'all':
        show_ou_statistics(ou_predictions, ou_bets)
        show_btts_statistics(btts_predictions, btts_bets)
        show_result_statistics(result_predictions, result_bets)

def generate_ou_statistics(df, tax):
    ou_pred = df[df['event_id'].isin([8, 12])]
    ou_bets_df = df[df['bet_event_id'].isin([8, 12]) & df['bet_outcome'].notnull()]
    return {
        'pred': {
            'correct': int(ou_pred['pred_outcome'].sum()),
            'over': int((ou_pred['event_id'] == 8).sum()),
            'over_correct': int(ou_pred[(ou_pred['event_id'] == 8) & (ou_pred['pred_outcome'] == 1)].shape[0]),
            'under': int((ou_pred['event_id'] == 12).sum()),
            'under_correct': int(ou_pred[(ou_pred['event_id'] == 12) & (ou_pred['pred_outcome'] == 1)].shape[0])
        },
        'bets': {
            'total': len(ou_bets_df),
            'correct': int(ou_bets_df['bet_outcome'].sum()),
            'over': int((ou_bets_df['bet_event_id'] == 8).sum()),
            'over_correct': int(ou_bets_df[(ou_bets_df['bet_event_id'] == 8) & (ou_bets_df['bet_outcome'] == 1)].shape[0]),
            'under': int((ou_bets_df['bet_event_id'] == 12).sum()),
            'under_correct': int(ou_bets_df[(ou_bets_df['bet_event_id'] == 12) & (ou_bets_df['bet_outcome'] == 1)].shape[0]),
            'profit_under' : float(
                ou_bets_df[ou_bets_df['bet_event_id'] == 12].apply(
                    lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
                ).sum()
            ),
            'profit_over' : float(
                ou_bets_df[ou_bets_df['bet_event_id'] == 8].apply(
                    lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
                ).sum()
            )
        }
    }

def generate_btts_statistics(df, tax):
    btts_pred = df[df['event_id'].isin([6, 172])]
    btts_bets_df = df[df['bet_event_id'].isin([6, 172]) & df['bet_outcome'].notnull()]
    return {
        'pred': {
            'correct': int(btts_pred['pred_outcome'].sum()),
            'yes': int((btts_pred['event_id'] == 6).sum()),
            'yes_correct': int(btts_pred[(btts_pred['event_id'] == 6) & (btts_pred['pred_outcome'] == 1)].shape[0]),
            'no': int((btts_pred['event_id'] == 172).sum()),
            'no_correct': int(btts_pred[(btts_pred['event_id'] == 172) & (btts_pred['pred_outcome'] == 1)].shape[0])
        },
        'bets': {
            'total': len(btts_bets_df),
            'correct': int(btts_bets_df['bet_outcome'].sum()),
            'yes': int((btts_bets_df['bet_event_id'] == 6).sum()),
            'yes_correct': int(btts_bets_df[(btts_bets_df['bet_event_id'] == 6) & (btts_bets_df['bet_outcome'] == 1)].shape[0]),
            'no': int((btts_bets_df['bet_event_id'] == 172).sum()),
            'no_correct': int(btts_bets_df[(btts_bets_df['bet_event_id'] == 172) & (btts_bets_df['bet_outcome'] == 1)].shape[0]),
            'profit_yes' : float(
                btts_bets_df[btts_bets_df['bet_event_id'] == 6].apply(
                    lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
                ).sum()
            ),  
            'profit_no' : float(
                btts_bets_df[btts_bets_df['bet_event_id'] == 172].apply(
                    lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
                ).sum()
            )
        }
    }

def generate_result_statistics(df, tax):
    result_pred = df[df['event_id'].isin([1, 2, 3])]
    result_bets_df = df[df['bet_event_id'].isin([1, 2, 3]) & df['bet_outcome'].notnull()]
    profit_home = float(
        result_bets_df[result_bets_df['bet_event_id'] == 1].apply(
            lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
        ).sum()
    )
    profit_draw = float(
        result_bets_df[result_bets_df['bet_event_id'] == 2].apply(
            lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
        ).sum()
    )
    profit_away = float(
        result_bets_df[result_bets_df['bet_event_id'] == 3].apply(
            lambda x: (x['odds'] * (1 - tax)) - 1 if x['bet_outcome'] == 1 else -1, axis=1
        ).sum()
    )
    return {
        'pred': {
            'correct': int(result_pred['pred_outcome'].sum()),
            'home': int((result_pred['event_id'] == 1).sum()),
            'home_correct': int(result_pred[(result_pred['event_id'] == 1) & (result_pred['pred_outcome'] == 1)].shape[0]),
            'draw': int((result_pred['event_id'] == 2).sum()),
            'draw_correct': int(result_pred[(result_pred['event_id'] == 2) & (result_pred['pred_outcome'] == 1)].shape[0]),
            'away': int((result_pred['event_id'] == 3).sum()),
            'away_correct': int(result_pred[(result_pred['event_id'] == 3) & (result_pred['pred_outcome'] == 1)].shape[0])
        },
        'bets': {
            'total': len(result_bets_df),
            'correct': int(result_bets_df['bet_outcome'].sum()),
            'home': int((result_bets_df['bet_event_id'] == 1).sum()),
            'home_correct': int(result_bets_df[(result_bets_df['bet_event_id'] == 1) & (result_bets_df['bet_outcome'] == 1)].shape[0]),
            'draw': int((result_bets_df['bet_event_id'] == 2).sum()),
            'draw_correct': int(result_bets_df[(result_bets_df['bet_event_id'] == 2) & (result_bets_df['bet_outcome'] == 1)].shape[0]),
            'away': int((result_bets_df['bet_event_id'] == 3).sum()),
            'away_correct': int(result_bets_df[(result_bets_df['bet_event_id'] == 3) & (result_bets_df['bet_outcome'] == 1)].shape[0]),
            'profit_home': profit_home,
            'profit_draw': profit_draw,
            'profit_away': profit_away
        }
    }

def generate_statistics(query, tax_flag, conn, EV_plus, stat_type='all'):
    tax = 0.12 if tax_flag else 0
    stats_query = f"""
        SELECT
            m.id,
            m.result,
            m.home_team_goals,
            m.away_team_goals,
            p.event_id,
            fp.outcome AS pred_outcome,
            b.event_id AS bet_event_id,
            b.odds,
            b.EV,
            b.outcome AS bet_outcome
        FROM matches m
        JOIN predictions p ON p.match_id = m.id
        JOIN final_predictions fp ON fp.predictions_id = p.id
        JOIN bets b ON b.match_id = m.id AND b.event_id = p.event_id and b.model_id = p.model_id
        WHERE {query}
    """
    df = pd.read_sql(stats_query, conn)
    #if EV_plus:
    #    df = df[(df['EV'].isnull()) | (df['EV'] >= 0)]

    results = {}
    if stat_type in ['all', 'ou']:
        results['ou'] = generate_ou_statistics(df, tax)
    if stat_type in ['all', 'btts']:
        results['btts'] = generate_btts_statistics(df, tax)
    if stat_type in ['all', 'result']:
        results['result'] = generate_result_statistics(df, tax)

    show_all_statistics(stat_type,
                        ou_predictions=results.get('ou', {}).get('pred'),
                        btts_predictions=results.get('btts', {}).get('pred'),
                        result_predictions=results.get('result', {}).get('pred'),
                        ou_bets=results.get('ou', {}).get('bets'),
                        btts_bets=results.get('btts', {}).get('bets'),
                        result_bets=results.get('result', {}).get('bets'))
    
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
                        count(case when p.event_id in (1,2,3) then 1 end) as result_predictions,
                        count(case when p.event_id in (1,2,3) and fp.outcome = 1 then 1 end) as results_correct,
                        count(case when p.event_id in (8, 12) then 1 end) as ou_predictions,
                        count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) as ou_correct,
                        count(case when p.event_id in (6, 172) then 1 end) as btts_predictions,
                        count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) as btts_correct
                    from predictions p
                        join final_predictions fp on fp.predictions_id = p.id
                        join matches m on p.match_id = m.id
                        where m.season = {} and m.result != '0'
                            and (m.home_team = {} or m.away_team = {})'''.format(season_id, k, k)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        if results[0][0] > 0:
            predictions_total.append([v, results[0][0], results[0][1], results[0][2], results[0][3], results[0][4], results[0][5]])
            predictions_ratio.append([v, round(results[0][1] / results[0][0], 2), round(results[0][3] / results[0][2], 2) ,round(results[0][5] / results[0][4], 2)])

    query = ''' select
                    count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (8, 12) then 1 end) * 100 as ou_avg,
                    count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (6, 172) then 1 end) * 100 as btts_avg,
                    count(case when p.event_id in (1, 2, 3) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (1, 2, 3) then 1 end) * 100 as result_avg,
                    count(case when p.event_id in (1,2,3) then 1 end) as result_predictions,
                    count(case when p.event_id in (1,2,3) and fp.outcome = 1 then 1 end) as results_correct,
                    count(case when p.event_id in (8, 12) then 1 end) as ou_predictions,
                    count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) as ou_correct,
                    count(case when p.event_id in (6, 172) then 1 end) as btts_predictions,
                    count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) as btts_correct
                from predictions p
                    join final_predictions fp on fp.predictions_id = p.id
                    join matches m on p.match_id = m.id and m.result != '0'
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
                        count(case when p.event_id in (1,2,3) then 1 end) as result_predictions,
                        count(case when p.event_id in (1,2,3) and fp.outcome = 1 then 1 end) as results_correct,
                        count(case when p.event_id in (8, 12) then 1 end) as ou_predictions,
                        count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) as ou_correct,
                        count(case when p.event_id in (6, 172) then 1 end) as btts_predictions,
                        count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) as btts_correct
                    from predictions p
                        join final_predictions fp on fp.predictions_id = p.id
                        join matches m on p.match_id = m.id
                        where m.season = {} and m.result != '0'
                            and m.league = {}'''.format(season_id, k)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        if results[0][0] > 0:
            predictions_total.append([v, results[0][0], results[0][1], results[0][2], results[0][3], results[0][4], results[0][5]])
            predictions_ratio.append([v, round(results[0][1] / results[0][0], 2), round(results[0][3] / results[0][2], 2) ,round(results[0][5] / results[0][4], 2)])

    query = ''' select
                    count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (8, 12) then 1 end) * 100 as ou_avg,
                    count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (6, 172) then 1 end) * 100 as btts_avg,
                    count(case when p.event_id in (1, 2, 3) and fp.outcome = 1 then 1 end) / count(case when p.event_id in (1, 2, 3) then 1 end) * 100 as result_avg,
                    count(case when p.event_id in (1,2,3) then 1 end) as result_predictions,
                    count(case when p.event_id in (1,2,3) and fp.outcome = 1 then 1 end) as results_correct,
                    count(case when p.event_id in (8, 12) then 1 end) as ou_predictions,
                    count(case when p.event_id in (8, 12) and fp.outcome = 1 then 1 end) as ou_correct,
                    count(case when p.event_id in (6, 172) then 1 end) as btts_predictions,
                    count(case when p.event_id in (6, 172) and fp.outcome = 1 then 1 end) as btts_correct
                from predictions p
                    join final_predictions fp on fp.predictions_id = p.id
                    join matches m on p.match_id = m.id and m.result != '0'
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





