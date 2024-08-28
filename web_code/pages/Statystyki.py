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
    with st.expander("Predykcje - statystyki"):
        if st.button("Statystyki wszystkich predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji, sezon 2023/24", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0' and season = 1"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji, sezon 2024/25", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0' and season = 11"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki predykcji z ostatniego tygodnia", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) >= current_date - 7 and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki wczorajszych predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) = current_date - 1 and result != '0'"
            stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, EV_plus)
        if st.button("Statystyki dzisiejszych predykcji", use_container_width=True):
            query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) = current_date and result != '0'"
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