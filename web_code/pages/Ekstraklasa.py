import streamlit as st
st.set_page_config(page_title = "Ekstraklasa", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module

def goals_bar_chart(date, opponent, goals, team_name):
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
    hit_rate = (df['Goals'] > 2.5).mean() * 100
    # Ustawienia osi
    ax.grid(False)
    ax.axhline(y=2.5, color='white', linestyle='-', linewidth=2, label='Goal Threshold: 2.5')
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Bramki w meczach: {} \nŚrednia: {:.1f} \nHitrate O2.5: {:.1f}%".format(team_name, avg_goals, hit_rate), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

    # Kolorowanie pasków na czerwono lub zielono
    for bar, goals in zip(bars, df['Goals']):
        if goals > 2.5:
            bar.set_color('green')
        else:
            bar.set_color('red')
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 0.25, f'{int(goals)}', 
            ha='center', va='bottom', color='black', fontsize=12)

    # Wyświetlenie wykresu
    st.pyplot(fig)

def btts_bar_chart(date, opponent, btts, team_name):
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
    ax.set_title("BTTS w meczach: {} \nŚrednia \nHitrate BTTS: {:.1f}%".format(team_name, hit_rate), loc='left', fontsize=24, color='white')
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

def single_team_data(team_id, conn):
    query = "select name from teams where id = {}".format(team_id)
    team_name_df = pd.read_sql(query,conn)
    if not team_name_df.empty:
        team_name = team_name_df.loc[0, 'name']
    query = '''select m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.home_team_goals as home_goals, m.away_team_goals as away_goals
                from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                where m.home_team = {} or m.away_team = {} 
                order by m.game_date desc'''.format(team_id, team_id)
    data = pd.read_sql(query,conn)
    date = []
    opponent = []
    goals = []
    btts = []
    home_team = []
    home_team_score = []
    away_team = []
    away_team_score = []
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
        date.append(row.date.strftime('%d.%m'))
        #OPPONENT
        if row.home_id == team_id:
            opponent.append(row.guest)
        else:
            opponent.append(row.home)
        #HOME AND AWAY
        home_team.append(row.home)
        home_team_score.append(row.home_goals)
        away_team.append(row.guest)
        away_team_score.append(row.away_goals)
    return date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score

def matches_list(date, home_team, home_team_score, away_team, away_team_score):
    data = {
    'Data': [x for x in date],
    'Gospodarz' : [x for x in home_team],
    'WynikH' : [x for x in home_team_score],
    'WynikA' : [x for x in away_team_score],
    'Gość' : [x for x in away_team],
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    #st.table(df)
    th = [('text-align', 'center')]
    td = [('text-align', 'center')]
    styles = [dict(selector="th", props=th), dict(selector="td", props=td)]
    st.dataframe(df.style.set_table_styles(styles), use_container_width=True, hide_index=True)

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
    ax.set_xticklabels([f"{label}" for label in df['Label']])
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
    ax.set_xticklabels([f"{label}" for label in df['Label']])
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

def show_predictions(home, guest, id, conn):
    query = "select value from predictions where match_id = {} and event_id = {}".format(id, 1)
    home_win = pd.read_sql(query, conn).to_numpy()
    query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 2)
    draw = pd.read_sql(query, conn).to_numpy()
    query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 3)
    guest_win = pd.read_sql(query, conn).to_numpy()
    query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 6)
    btts_no = pd.read_sql(query, conn).to_numpy()
    query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 172)
    btts_yes = pd.read_sql(query, conn).to_numpy()
    st.write("{}; {}; {}; {}; {}".format(home_win[0][0], draw[0][0], guest_win[0][0], btts_no[0][0], btts_yes[0][0]))
    col1, col2, col3 = st.columns(3)
    with col1:
        graph_winner(home_win[0][0], draw[0][0], guest_win[0][0])
    with col2:
        graph_btts(btts_no[0][0], btts_yes[0][0])
    with col3:
        graph_btts(btts_no[0][0], btts_yes[0][0])

def generate_schedule(league_id, round, season, conn):
     query = '''select m.id as id, m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date
                from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                where m.league = {} and m.round = {} and m.season = {}
                order by m.game_date desc'''.format(league_id, round, season)
     schedule_df = pd.read_sql(query,conn)
     for index, row in schedule_df.iterrows():
        button_label = "{} - {}, {}".format(row.home, row.guest, row.date)
        if st.button(button_label, use_container_width=True):
            show_predictions(row.home, row.guest, row.id, conn)

def show_teams(conn, teams_dict):
    games = st.slider("Liczba analizowanych spotkań", 5, 15, 10)
    st.header("Drużyny grające w Ekstraklasie w sezonie 2023/24:")
    for key, value in teams_dict.items():
        button_label = value
        if st.button(button_label, use_container_width = True):
            date, opponent, goals, btts, team_name, home_team, home_team_score, away_team, away_team_score = single_team_data(key, conn)
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    goals_bar_chart(date[:games], opponent[:games], goals[:games], team_name)

            # W kolumnie 2 tworzymy dwa wiersze
            with col2:
                with st.container():
                    btts_bar_chart(date[:games], opponent[:games], btts[:games], team_name)
            matches_list(date[:games], home_team[:games], home_team_score[:games], away_team[:games], away_team_score[:games])

def main():
    league = 1 #Ekstraklasa
    season = 11 #2024/25
    round = 1 #1. kolejka
    st.header("Ekstraklasa")
    conn = db_module.db_connect()
    all_teams = "select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) where m.league = 1 and m.season = 11"
    all_teams_df = pd.read_sql(all_teams, conn)
    teams_dict = all_teams_df.set_index('id')['name'].to_dict()
    with st.expander("Terminarz, kolejka numer: {}".format(1)):
        generate_schedule(league, round, season, conn)
    with st.expander("Zespoły"):
        show_teams(conn, teams_dict)
                
    conn.close()

if __name__ == '__main__':
    main()