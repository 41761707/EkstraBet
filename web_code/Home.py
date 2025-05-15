import streamlit as st
#st.set_page_config(layout="wide")
st.set_page_config(page_title = "Ekstrabet", page_icon = "⚽", layout="centered")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module

def main():
    #db_connect
    conn = db_module.db_connect()
    query_names = "select id, name from leagues where active = 1 order by country"
    leagues_df = pd.read_sql(query_names, conn)
    leagues_dict = leagues_df.set_index('id')['name'].to_dict()
    query_countries = "select l.id as id, c.emoji as country from leagues l join countries c on l.country = c.id where l.active = 1 order by l.country"
    league_country_df = pd.read_sql(query_countries, conn)
    league_country_dict = league_country_df.set_index('id')['country'].to_dict()
    st.title("Krzychu (Bet asystent): sezon 1")
    #st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.page_link("pages/Statystyki.py", label="Kącik statystyczny", icon="📊")
    st.page_link("pages/Bukmacherka.py", label="Kącik bukmacherski", icon="💸")
    with st.expander("Lista obsługiwanych lig"):
        for key, value in leagues_dict.items():
            st.page_link("pages/{}.py".format(value), label=value, icon = league_country_dict[key])
    with st.expander("O projekcie"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h2 style='color: #4fc3f7; border-bottom: 2px solid #4fc3f7; padding-bottom: 5px;'>Ekstrabet - Inteligentny Asystent Bukmacherski</h2>
            <p style='line-height: 1.6;'>
                Ekstrabet to zaawansowane narzędzie analityczne stworzone dla miłośników sportu i zakładów bukmacherskich. 
                Wykorzystując uczenie maszynowe i statystykę, pomaga w podejmowaniu świadomych decyzji przy obstawianiu meczów piłkarskich.
            </p>
            <div style='background-color: #2d2d2d; border-left: 4px solid #4fc3f7; padding: 10px; margin: 10px 0;'>
                <p style='margin: 0; color: #ffffff;'><strong>Główne założenia projektu:</strong></p>
                <ul style='margin-top: 5px; color: #e0e0e0;'>
                    <li>Analiza historycznych danych meczowych</li>
                    <li>Predykcja wyników spotkań</li>
                    <li>Identyfikacja wartościowych zakładów</li>
                    <li>Wizualizacja danych dla lepszego zrozumienia</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Zawartość strony"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h3 style='color: #4fc3f7;'>Co znajdziesz na naszej stronie:</h3>
            <div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;'>
                <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                    <h4 style='margin-top: 0; color: #4fc3f7;'>📊 Kącik statystyczny</h4>
                    <p style='font-size: 14px; color: #e0e0e0;'>Szczegółowe analizy drużyn, zawodników i trendów w różnych ligach.</p>
                </div>
                <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                    <h4 style='margin-top: 0; color: #4fc3f7;'>💸 Kącik bukmacherski</h4>
                    <p style='font-size: 14px; color: #e0e0e0;'>Rekomendacje zakładów oparte na modelach predykcyjnych.</p>
                </div>
                <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                    <h4 style='margin-top: 0; color: #4fc3f7;'>⚽ Baza lig</h4>
                    <p style='font-size: 14px; color: #e0e0e0;'>Dostęp do szczegółowych danych z wielu lig piłkarskich.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Planowane rozszerzenia"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h3 style='color: #4fc3f7;'>Rozwój projektu</h3>
            <div style='margin-top: 15px;'>
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>1</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Rozszerzenie o inne dyscypliny sportowe (hokej, koszykówka)</span>
                </div>
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>2</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Dodanie analizy w czasie rzeczywistym</span>
                </div>
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>3</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Integracja z API bukmacherów</span>
                </div>
                <div style='display: flex; align-items: center;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>4</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Personalizacja profili użytkowników</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Kontakt"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h3 style='color: #4fc3f7;'>Skontaktuj się z autorem</h3>
            <p style='margin-bottom: 20px; color: #e0e0e0;'>Masz pytania lub sugestie dotyczące projektu? Chętnie je poznamy!</p>
            <a href='https://41761707.github.io/' target='_blank' style='display: inline-block; background-color: #4fc3f7; color: #121212; padding: 10px 15px; border-radius: 5px; text-decoration: none; font-weight: bold; transition: background-color 0.3s;'>Odwiedź stronę autora</a>
            <p style='margin-top: 20px; font-size: 14px; color: #b0b0b0;'>Projekt rozwijany przez pasjonatów dla pasjonatów sportu</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("ℹ️ Notatka odnośnie danych"):
        st.markdown(
            """
            <style>
            .note-box {
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 10px;
                font-size: 15px;
                line-height: 1.6;
            }
            .note-box a {
                color: #2a8fbd;
                text-decoration: none;
            }
            .note-box a:hover {
                text-decoration: underline;
            }
            </style>
            <div class="note-box">
                <p>📚 Wszystkie dane wykorzystane w serwisie pochodzą ze stron o charakterze kronikarskim. Wykorzystywane są jedynie do celów edukacyjnych-badawczych i nie mają na celu naruszenia praw autorskich.</p>
                <p>💡 Przedstawione zakłady wykonywane są głównie hipotetycznie w celu sprawdzenia osiągnięć modeli. Przybliżają jedynie potencjalne zyski bądź straty wynikające z udziału w zakładach bukmacherskich stosując przedstawione wytyczne i nie stanowią oferty w rozumieniu prawa.</p>
                <p>📊 Dane odnośnie spotkań meczowych pochodzą z serwisu <a href="https://www.flashscore.pl" target="_blank">flashscore.pl</a>. Dodatkowe dane hokejowe zostały zaczerpnięte z <a href="https://api-web.nhle.com/" target="_blank">NHL API</a>.</p>
                <p>🧥 Zdjęcia koszulek hokejowych zapożyczono ze strony <a href="https://www.dailyfaceoff.com/" target="_blank">dailyfaceoff.com</a>.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    conn.close()

if __name__ == '__main__':
    main()
