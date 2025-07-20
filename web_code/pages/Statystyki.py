import stats_module
import base_site_module
import db_module
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
st.set_page_config(page_title="Kącik statystyczny",
                   page_icon="⚽", layout="wide")


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
            query = "cast(game_date as date) > '2024-07-01' and result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki predykcji, sezon 2024/25", use_container_width=True):
            query = "result != '0' and season = 11"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki predykcji, sezon 2025/26", use_container_width=True):
            query = "result != '0' and season = 12"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki predykcji z ostatniego miesiąca", use_container_width=True):
            query = "cast(game_date as date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) and result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki predykcji z ostatniego tygodnia", use_container_width=True):
            query = "cast(m.game_date as date) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) and m.result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki wczorajszych predykcji", use_container_width=True):
            query = "cast(m.game_date as date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) and m.result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Statystyki dzisiejszych predykcji", use_container_width=True):
            query = "cast(game_date as date) = current_date and result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all')
        if st.button("Ustawienia niestandardowe (definiowane na górze strony)", use_container_width=True):
            if len(chosen_leagues) == 0:
                st.subheader("Nie wybrano żadnych lig")
            else:
                query = '''league in ({}) and season = 11 and result != '0' '''.format(",".join([str(leagues_dict[v]) for v in chosen_leagues]))
                stats_module.generate_statistics(query, tax_flag, conn, EV_plus, 'all')
                
    with st.expander("Predykcje - porównanie między ligami"):
        if st.button("Sezon 2024/25", use_container_width=True):
            stats_module.aggregate_leagues_acc(11, conn)
        if st.button("Sezon 2025/26", use_container_width=True):
            stats_module.aggregate_leagues_acc(12, conn)
    with st.expander("Profit z zakładów - porównanie między ligami"):
        if st.button("Profit, sezon 2024/25", use_container_width=True):
            stats_module.aggregate_leagues_profit(11, conn)
        if st.button("Profit, sezon 2025/26", use_container_width=True):
            stats_module.aggregate_leagues_profit(12, conn)
    with st.expander("Charakterystyki ligowe - porównanie"):
        st.write("Charakterystyki ligowe - porównanie")
    with st.expander("Pewność modelu a poprawność"):
        st.write("Pewność modelu a poprawność")
    with st.expander("Kurs wybranego zakładu a poprawość"):
        st.write("Kurs wybranego zakładu a poprawość")
    conn.close()


if __name__ == '__main__':
    main()
