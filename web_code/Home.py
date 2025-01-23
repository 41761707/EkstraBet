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
        st.write("Krótki opis po co i dlaczego")
    with st.expander("Zawartość strony"):
        st.write("Krótki opis co strona oferuje")
    with st.expander("Planowane rozszerzenia"):
        st.write("Krótki opis w jakim kierunku planowany jest rozwój strony")
    with st.expander("Kontakt"):
        st.write("Strona autora: https://41761707.github.io/")
    with st.expander("Notatka odnośnie danych"):
        st.write("Wszystkie dane wykorzystane w serwisie pochodzą ze stron o charakterze kronikarskim. Wykorzystywane są jedynie do celów edukacyjnych-badawczych i nie mają na celu naruszenia praw autorskich.")
        st.write("Przedstawione zakłady wykonywane są głównie hipotetycznie w celu sprawdzenia osiągnięć modelów. Przybliżają jedynie potencjalne zyski bądź straty wynikające z udziału w zakładach bukmacherskich stosująć przedstawione wytyczne i nie stanowią oferty w rozumieniu prawa.")
        st.write("Dane odnośnie spotkań meczowych pochodzą z serwisu www.flashscore.pl. Dodatkowe dane hokejowe zostały zaczerpnięte z NHL API (https://api-web.nhle.com/)")
        st.write("Zdjęcia koszulek hokejowych zapożyczono ze strony https://www.dailyfaceoff.com/")



    conn.close()

if __name__ == '__main__':
    main()
