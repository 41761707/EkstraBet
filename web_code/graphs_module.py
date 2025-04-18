import numpy as np
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def generate_comparision(labels, wins, loses):
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
    ax.tick_params(colors='white', which='both', labelsize = 20)
    ax.set_facecolor('#291F1E')
    ax.legend()
    fig.patch.set_facecolor('black')

    for bars, outcomes in zip([bars1, bars2], [df['Wygrane'], df['Przegrane']]):
        for bar, outcome in zip(bars, outcomes):
            ax.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() - 1.5, 0.5), f'{int(outcome)}', 
                    ha='center', va='bottom', color='white', fontsize=20)

    # Wyświetlenie wykresu
    st.pyplot(fig)

def generate_pie_chart_binary(labels, type_a, type_b):
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

def generate_pie_chart_result(labels, type_a, type_b, type_c):
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

def highlight_cells_EV(val):
    color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else ''
    return color

def highlight_cells_profit(val):
    color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else 'background-color: lightcoral'
    return color

def highlight_cells_plus_minus(val):
    color = ''
    if val > 0:
        color = 'background-color: lightgreen; color : black'
    elif val < 0:
        color = 'background-color: lightcoral; color : black'
    return color
def goals_bar_chart(date, opponent, goals, team_name, ou_line):
    data = {
    'Date': [x for x in reversed(date)],
    'Opponent': [x for x in reversed(opponent)],
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

def btts_bar_chart(date, opponent, btts, team_name):
    data = {
    'Date': [x[:-3] for x in reversed(date)],
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

def graph_winner(home, draw, away):
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

def graph_exact_goals(goals_no):
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

def graph_btts(no, yes):
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

def goals_line_chart(date, opponent, goals, team_name, ou_line):
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

def winner_bar_chart(opponent, home_team, result, team_name):
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
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
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

def graph_ou(under, over, title):
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
    ax.set_title("Rozkład prawdopodobieństwa zdarzenia: {}".format(title), loc='left', fontsize=28, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, ppb in zip(bars, df['Ppb']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
            ha='center', va='bottom', color='black', fontsize=22)
    st.pyplot(fig)

def team_compare_graph(teams, accs, type = 'acc'):
    num_rows = len(teams)
    teams_accs = zip(teams,accs)
    average = accs[-1]
    teams_accs_sorted = sorted(teams_accs, key= lambda x: x[1])
    data = {
    'Label': [x[0] for x in teams_accs_sorted],
    'Results' : [x[1] for x in teams_accs_sorted]
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, num_rows))
    bars = ax.barh(
        df.index,
        df['Results'],
        color=['deepskyblue' if result == average else 'red' if result < average else 'green' for result in df['Results']])
    ax.grid(False)
    ax.set_yticks(df.index)
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title("Porównanie procenta dokładności predykcji", loc='left', fontsize=28, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, result in zip(bars, df['Results']):
        if type == 'profit':
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2, f'{float(result)} u', 
            ha='center', va='center', color='white', fontsize=22)
        else:  
            ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height() / 2, f'{float(result)}%', 
                ha='center', va='center', color='white', fontsize=22)
    st.pyplot(fig)


def side_bar_graph(labels, values, title):
    data = {
    'Label': [x for x in labels],
    'Results' : [x for x in values]
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df.index, df['Results'], color=['orangered', 'slategrey', 'lightgreen'])
    ax.grid(False)
    ax.set_yticks(df.index)
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title(title, loc='left', fontsize=30, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, result in zip(bars, df['Results']):
        ax.text(bar.get_width() - 5, bar.get_y() + bar.get_height() / 2, f'{float(result)} %', 
            ha='center', va='center', color='black', fontsize=22)
    st.pyplot(fig)


def winner_bar_chart_v2(results, team_name):
    wins = results.count('W')
    draws = results.count('X')
    loses = results.count('L')
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
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
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