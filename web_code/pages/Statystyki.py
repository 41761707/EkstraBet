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
    with st.expander("Statystyki wszystkich predykcji"):
        query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) > '2024-07-01' and result != '0'"
        stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, 0)
    with st.expander("Statystyki z ostatniego tygodnia predykcji"):
        query = "select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where cast(game_date as date) >= current_date - 7 and result != '0'"
        stats_module.generate_statistics(query, tax_flag, 1, 1000, 3, conn, 0)
    conn.close()

if __name__ == '__main__':
    main()