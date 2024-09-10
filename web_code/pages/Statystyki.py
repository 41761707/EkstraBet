import streamlit as st
st.set_page_config(page_title = "Kącik statystyczny", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module
import stats_module

def main():
    st.header("Kącik statystyczny")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    conn = db_module.db_connect()
    tax_flag = st.checkbox("Uwzględnij podatek 12%")
    EV_plus = st.checkbox("Uwzględnij tylko wartościowe zakłady (VB > 0)")
    st.subheader("Ustawienia niestandardowe")
    query = "select distinct id, name from leagues where active = 1 order by name"
    all_leagues_df = pd.read_sql(query, conn)
    leagues_dict = all_leagues_df .set_index('name')['id'].to_dict()
    chosen_leagues = st.multiselect(
    "Statystyki dla wybranych lig",
    [k for k in leagues_dict.keys()], placeholder="Wybierz ligi z listy")
    with st.expander("Predykcje - statystyki"):
        if st.button("Statystyki wszystkich predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji, sezon 2023/24", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where result != '0' and season = 1"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji, sezon 2024/25", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where result != '0' and season = 11"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji z ostatniego tygodnia", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki wczorajszych predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki dzisiejszych predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) = current_date and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Ustawienia niestandardowe (definiowane na górze strony)", use_container_width=True):
            if len(chosen_leagues) == 0:
                st.subheader("Nie wybrano żadnych lig")
            else:
                query = '''select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches 
                        where league in ({}) and season = 11 and result != '0' '''.format(",".join([str(leagues_dict[v]) for v in chosen_leagues]))
                stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
    with st.expander("Predykcje - porównanie między ligami"):
        if st.button("Sezon 2023/24", use_container_width= True):
            stats_module.aggregate_leagues_acc(1, conn)
        if st.button("Sezon 2024/25", use_container_width= True):
            stats_module.aggregate_leagues_acc(11, conn)
    with st.expander("Charakterystyki ligowe - porównanie"):
        st.write("Charakterystyki ligowe - porównanie")
    conn.close()

if __name__ == '__main__':
    main()