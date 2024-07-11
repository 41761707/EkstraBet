import streamlit as st
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
    ax.set_title("Bramki w meczach: {}, \nŚrednia: {:.1f} \nHitrate O2.5: {:.1f}%".format(team_name, avg_goals, hit_rate), loc='left', fontsize=24, color='white')
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

def single_team_data(team_id, games, conn):
    query = "select name from teams where id = {}".format(team_id)
    team_name_df = pd.read_sql(query,conn)
    if not team_name_df.empty:
        team_name = team_name_df.loc[0, 'name']
    query = '''select m.home_team as home_id, t1.name as home, m.away_team as guest_id, t2.name as guest, m.game_date as date, m.home_team_goals + m.away_team_goals as goals_total
                from matches m join teams t1 on t1.id = m.home_team join teams t2 on t2.id = m.away_team 
                where m.home_team = {} or m.away_team = {} 
                order by m.game_date desc'''.format(team_id, team_id)
    data = pd.read_sql(query,conn)
    date = []
    opponent = []
    goals = []
    for index, row in data.iterrows():
        if int(row.goals_total) == 0:
            goals.append(0.4)
        else:
            goals.append(int(row.goals_total))
        date.append(row.date.strftime('%m.%d'))
        if row.home_id == team_id:
            opponent.append(row.guest)
        else:
            opponent.append(row.home)
    goals_bar_chart(date[:games], opponent[:games], goals[:games], team_name)

def main():
    conn = db_module.db_connect()
    all_teams = "select distinct t.id, t.name from matches m join teams t on m.home_team = t.id where m.league = 1"
    all_teams_df = pd.read_sql(all_teams, conn)
    teams_dict = all_teams_df.set_index('id')['name'].to_dict()
    games = st.slider("Liczba analizowanych spotkań", 5, 15, 10)
    st.header("Drużyny z min. 1 meczem w Ekstrakalsie: ")
    for key, value in teams_dict.items():
        button_label = value
        if st.button(button_label, use_container_width = True):
            single_team_data(key, games, conn)
        
    #games = st.slider("Liczba analizowanych spotkań", 5, 15, 10)
    #single_team_data(4, games, conn)
    conn.close()

if __name__ == '__main__':
    main()