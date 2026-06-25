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

@st.cache_data(ttl=300)
def get_sports_data():
    """Pobiera dostępne sporty"""
    conn = db_module.db_connect()
    query = "SELECT ID, NAME FROM sports ORDER BY ID"
    sports_df = pd.read_sql(query, conn)
    conn.close()
    return dict(zip(sports_df['NAME'], sports_df['ID']))

@st.cache_data(ttl=300)
def get_event_families_data(sport_id):
    """Pobiera rodziny zdarzeń dla danego sportu"""
    conn = db_module.db_connect()
    query = f"""SELECT ef.ID, ef.SPORT_ID, ef.NAME, s.NAME as sport_name, ef.description
                FROM event_families ef
                LEFT JOIN sports s ON ef.SPORT_ID = s.ID
                WHERE ef.SPORT_ID = {sport_id}
                ORDER BY ef.ID"""
    families_df = pd.read_sql(query, conn)
    conn.close()
    return families_df

@st.cache_data(ttl=300)
def get_models_for_family(sport_id, family_name):
    """Pobiera modele dla danej rodziny zdarzeń"""
    conn = db_module.db_connect()
    query = f"""SELECT DISTINCT m.ID, m.NAME
                FROM models m
                JOIN event_model_families emf ON m.ID = emf.MODEL_ID
                JOIN event_families ef ON emf.EVENT_FAMILY_ID = ef.ID
                WHERE m.active = 1 
                AND m.SPORT_ID = {sport_id}
                AND ef.NAME = '{family_name}'
                ORDER BY m.ID"""
    models_df = pd.read_sql(query, conn)
    conn.close()
    return dict(zip(models_df['NAME'], models_df['ID'])) if not models_df.empty else {}


def main():
    st.header("Kącik statystyczny")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    conn = db_module.db_connect()
    
    # Pobieranie danych o sportach
    sports_dict = get_sports_data()
    sports_names = list(sports_dict.keys())
    
    # Układ 4-kolumnowy: Sport + 3 modele
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_sport_name = st.selectbox("Wybierz sport:", sports_names, key='sport_select')
        sport_id = sports_dict[selected_sport_name]
    
    # Pobieranie modeli dla każdej rodziny zdarzeń
    models_result = get_models_for_family(sport_id, 'REZULTAT')
    models_ou = get_models_for_family(sport_id, 'OU')
    models_btts = get_models_for_family(sport_id, 'BTTS')
    
    # Ustawienie domyślnych modeli (pierwszy z listy lub None)
    model_result = [list(models_result.values())[0]] if models_result else None
    model_ou = [list(models_ou.values())[0]] if models_ou else None
    model_btts = [list(models_btts.values())[0]] if models_btts else None
    
    # Selectboxy dla modeli w pozostałych kolumnach
    with col2:
        if models_result:
            selected_result_model = st.selectbox("Model REZULTAT:", list(models_result.keys()), key='result_model')
            model_result = [models_result[selected_result_model]]
        else:
            st.info("Brak dostępnych modeli REZULTAT dla tego sportu")
    with col3:
        if models_ou:
            selected_ou_model = st.selectbox("Model OU:", list(models_ou.keys()), key='ou_model')
            model_ou = [models_ou[selected_ou_model]]
        else:
            st.info("Brak dostępnych modeli OU dla tego sportu")
    with col4:
        if models_btts:
            selected_btts_model = st.selectbox("Model BTTS:", list(models_btts.keys()), key='btts_model')
            model_btts = [models_btts[selected_btts_model]]
        else:
            st.info("Brak dostępnych modeli BTTS dla tego sportu")
    
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
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki predykcji, sezon 2024/25", use_container_width=True):
            query = "result != '0' and season = 11"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki predykcji, sezon 2025/26", use_container_width=True):
            query = "result != '0' and season = 12"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki predykcji z ostatniego miesiąca", use_container_width=True):
            query = "cast(game_date as date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) and result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki predykcji z ostatniego tygodnia", use_container_width=True):
            query = "cast(m.game_date as date) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) and m.result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki wczorajszych predykcji", use_container_width=True):
            query = "cast(m.game_date as date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) and m.result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Statystyki dzisiejszych predykcji", use_container_width=True):
            query = "cast(game_date as date) = current_date and result != '0'"
            stats_module.generate_statistics(
                query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
        if st.button("Ustawienia niestandardowe (definiowane na górze strony)", use_container_width=True):
            if len(chosen_leagues) == 0:
                st.subheader("Nie wybrano żadnych lig")
            else:
                query = '''league in ({}) and season = 11 and result != '0' '''.format(",".join([str(leagues_dict[v]) for v in chosen_leagues]))
                stats_module.generate_statistics(query, tax_flag, conn, EV_plus, 'all', model_result, model_ou, model_btts)
                
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
