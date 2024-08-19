import numpy as np
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime




def matches_list(date, home_team, home_team_score, away_team, away_team_score, team_name):
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

def matches_list_h2h(date, home_team, home_team_score, away_team, away_team_score):
    data = {
    'Data': [x for x in date],
    'Gospodarz' : [x for x in home_team],
    'Wynik' : [str(x) + "-" + str(y) for x,y in zip(home_team_score, away_team_score)],
    'Gość' : [x for x in away_team],
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.dataframe(df, use_container_width=True, hide_index=True)

def increment_stat(team, teams_stats, result):
    position = -1 
    for i, subarray in enumerate(teams_stats):
        if subarray[0] == team:
            position = i
            break
    teams_stats[position][-2] += 1 #Liczba meczów
    teams_stats[position][result + 1] += 1
    if result == 0:
        teams_stats[position][-1] += 3
    elif result == 1:
        teams_stats[position][-1] += 1
    else:
        pass

def generate_traditional_table(teams_dict, results_df):
    teams_stats = [] #key, M, W, D, L, P
    for k in teams_dict.values():
        #Nazwa, zwycięstwa, remisy, porażki, liczba meczów, punkty
        teams_stats.append([k, 0, 0, 0, 0, 0])
    for _, row in results_df.iterrows():
        if row.result == '1':
            increment_stat(row.home_team, teams_stats, 0)
            increment_stat(row.away_team, teams_stats, 2)
        elif row.result == 'X':
            increment_stat(row.home_team, teams_stats, 1)
            increment_stat(row.away_team, teams_stats, 1)
        else:
            increment_stat(row.home_team, teams_stats, 2)
            increment_stat(row.away_team, teams_stats, 0)
    sorted_teams_stats = sorted(teams_stats, key=lambda x: x[-1], reverse=True)
    data = {
    'Nazwa drużyny': [x[0] for x in sorted_teams_stats],
    'Liczba meczów' : [x[4] for x in sorted_teams_stats],
    'Zwycięstwa' : [x[1] for x in sorted_teams_stats],
    'Remisy' : [x[2] for x in sorted_teams_stats],
    'Porażki' : [x[3] for x in sorted_teams_stats],
    'Punkty' : [x[5] for x in sorted_teams_stats]
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.table(df)
    st.write('''Uwaga - prezentowana tabela nie przedstawia podziałów na grupy, które mogą zaistnieć dla niektórych lig. 
        Zgodnie ze standardowym punktowaniem wyników poniżej zaprezentowano sumaryczne osiągnięcia zespołów biorących udział
        w danych rozgrywkach na przestrzeni całego sezonu.''')
    
def generate_ou_btts_table(teams_dict, results_df):
    table_dict = {}
    for k in teams_dict.values():
        table_dict[f'{k}_M'] = 0
        table_dict[f'{k}_BTTS'] = 0
        table_dict[f'{k}_OU_1_5'] = 0
        table_dict[f'{k}_OU_2_5'] = 0
        table_dict[f'{k}_OU_3_5'] = 0
    for _, row in results_df.iterrows():
        table_dict[f'{row.home_team}_M'] += 1
        table_dict[f'{row.away_team}_M'] += 1

        if row.home_team_goals > 0 and row.away_team_goals > 0:
            table_dict[f'{row.home_team}_BTTS'] += 1
            table_dict[f'{row.away_team}_BTTS'] += 1
        if row.home_team_goals + row.away_team_goals > 1.5:
            table_dict[f'{row.home_team}_OU_1_5'] += 1
            table_dict[f'{row.away_team}_OU_1_5'] += 1
        if row.home_team_goals + row.away_team_goals > 2.5:
            table_dict[f'{row.home_team}_OU_2_5'] += 1
            table_dict[f'{row.away_team}_OU_2_5'] += 1
        if row.home_team_goals + row.away_team_goals > 3.5:
            table_dict[f'{row.home_team}_OU_3_5'] += 1
            table_dict[f'{row.away_team}_OU_3_5'] += 1
            #Inkrement
    table_list = []
    for k in teams_dict.values():
        table_list.append([k,
                            table_dict[f'{k}_M'],
                            table_dict[f'{k}_BTTS'], 
                            table_dict[f'{k}_OU_1_5'],
                            table_dict[f'{k}_OU_2_5'],
                            table_dict[f'{k}_OU_3_5']])
    data = {
    'Nazwa drużyny': [x[0] for x in table_list],
    'Liczba meczów' : [x[1] for x in table_list],
    'BTTS' : ["{} ({}%)".format(x[2], round(x[2] * 100/max(x[1],1),2)) for x in table_list],
    'Over 1.5' : ["{} ({}%)".format(x[3], round(x[3] * 100/max(x[1],1),2)) for x in table_list],
    'Over 2.5' : ["{} ({}%)".format(x[4], round(x[4] * 100/max(x[1],1),2)) for x in table_list],
    'Over 3.5' : ["{} ({}%)".format(x[5], round(x[5] * 100/max(x[1],1),2)) for x in table_list]
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.table(df)