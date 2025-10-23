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

def increment_stat(team, teams_stats, result, goals_for=0, goals_against=0):
    """
    Aktualizuje statystyki drużyny w tabeli ligowej.
    
    Args:
        team: nazwa drużyny
        teams_stats: lista statystyk wszystkich drużyn
        result: wynik meczu (0=zwycięstwo, 1=remis, 2=porażka)
        goals_for: bramki zdobyte przez drużynę
        goals_against: bramki stracone przez drużynę
    """
    for team_stat in teams_stats:
        if team_stat[0] == team:
            team_stat[4] += 1  # Liczba meczów
            team_stat[result + 1] += 1  # Zwycięstwa/remisy/porażki
            team_stat[6] += goals_for  # Bramki zdobyte
            team_stat[7] += goals_against  # Bramki stracone
            
            # Punkty: 3 za zwycięstwo, 1 za remis, 0 za porażkę
            if result == 0:  # Zwycięstwo
                team_stat[5] += 3
            elif result == 1:  # Remis
                team_stat[5] += 1
            break

def generate_traditional_table(teams_dict, results_df, type):
    """
    Generuje tradycyjną tabelę ligową z rozszerzonymi statystykami.
    
    Args:
        teams_dict: słownik z nazwami drużyn
        results_df: DataFrame z wynikami meczów
        type: typ tabeli ('traditional', 'home', 'away')
    """
    # Inicjalizacja statystyk: [nazwa, zwycięstwa, remisy, porażki, mecze, punkty, bramki_zdobyte, bramki_stracone]
    teams_stats = []
    for team_name in teams_dict.values():
        teams_stats.append([team_name, 0, 0, 0, 0, 0, 0, 0])
    
    # Przetwarzanie wyników meczów
    for _, row in results_df.iterrows():
        home_goals = row.home_team_goals
        away_goals = row.away_team_goals
        
        if row.result == '1':  # Zwycięstwo gospodarza
            if type == 'traditional':
                increment_stat(row.home_team, teams_stats, 0, home_goals, away_goals)  # Zwycięstwo
                increment_stat(row.away_team, teams_stats, 2, away_goals, home_goals)  # Porażka
            elif type == 'home':
                increment_stat(row.home_team, teams_stats, 0, home_goals, away_goals)
            elif type == 'away':
                increment_stat(row.away_team, teams_stats, 2, away_goals, home_goals)
                
        elif row.result == 'X':  # Remis
            if type == 'traditional':
                increment_stat(row.home_team, teams_stats, 1, home_goals, away_goals)
                increment_stat(row.away_team, teams_stats, 1, away_goals, home_goals)
            elif type == 'home':
                increment_stat(row.home_team, teams_stats, 1, home_goals, away_goals)
            elif type == 'away':
                increment_stat(row.away_team, teams_stats, 1, away_goals, home_goals)
                
        else:  # row.result == '2' - Zwycięstwo gościa
            if type == 'traditional':
                increment_stat(row.home_team, teams_stats, 2, home_goals, away_goals)  # Porażka
                increment_stat(row.away_team, teams_stats, 0, away_goals, home_goals)  # Zwycięstwo
            elif type == 'home':
                increment_stat(row.home_team, teams_stats, 2, home_goals, away_goals)
            elif type == 'away':
                increment_stat(row.away_team, teams_stats, 0, away_goals, home_goals)
    
    # Sortowanie według punktów (malejąco), następnie według różnicy bramek (malejąco)
    sorted_teams_stats = sorted(teams_stats, key=lambda x: (x[5], x[6] - x[7]), reverse=True)
    
    # Przygotowanie danych do tabeli
    data = {
        'Nazwa drużyny': [team[0] for team in sorted_teams_stats],
        'Liczba meczów': [team[4] for team in sorted_teams_stats],
        'Zwycięstwa': [team[1] for team in sorted_teams_stats],
        'Remisy': [team[2] for team in sorted_teams_stats],
        'Porażki': [team[3] for team in sorted_teams_stats],
        'Bramki': [f"{team[6]}:{team[7]}" for team in sorted_teams_stats],
        '+/-': [team[6] - team[7] for team in sorted_teams_stats],
        'Punkty': [team[5] for team in sorted_teams_stats]
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

def league_stats(labels, values, values_percentage):
    data = {
        'Zdarzenie' : [x for x in reversed(labels)],
        'Liczba wystąpień' : [x for x in reversed(values)],
        'Procent wystąpień' : [str(x) + "%" for x in reversed(values_percentage)]
    } 
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.table(df)