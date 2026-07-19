import streamlit as st
#st.set_page_config(layout="wide")
st.set_page_config(page_title = "Ekstrabet", page_icon = "⚽", layout="centered")
import pandas as pd

import db_module

def main():
    '''Główna funkcja aplikacji Streamlit'''
    conn = db_module.db_connect()
    query_names = "select id, name from leagues where active = 1 order by country"
    leagues_df = pd.read_sql(query_names, conn)
    leagues_dict = leagues_df.set_index('id')['name'].to_dict()
    query_countries = "select l.id as id, c.emoji as country from leagues l join countries c on l.country = c.id where l.active = 1 order by l.country"
    league_country_df = pd.read_sql(query_countries, conn)
    league_country_dict = league_country_df.set_index('id')['country'].to_dict()
    st.title("Krzychu (Bet asystent): sezon 1")
    st.write("Oficjalny start od momentu rozpoczęcia sezonu 2025/2026 dla każdej z lig")
    #st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.page_link("pages/Statystyki.py", label="Kącik statystyczny", icon="📊")
    st.page_link("pages/Bukmacherka.py", label="Kącik bukmacherski", icon="💸")
    with st.expander("Lista obsługiwanych lig"):
        for key, value in leagues_dict.items():
            st.page_link("pages/{}.py".format(value.replace(" ", "_")), label=value, icon=league_country_dict[key])
    with st.expander("Statystyki zawodników"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <p style='margin-bottom: 15px; color: #e0e0e0;'>Sprawdź szczegółowe statystyki i analizy zawodników z różnych dyscyplin sportowych:</p>
        </div>
        """, unsafe_allow_html=True)
        st.page_link("pages/Pilka-zawodnicy.py", label="⚽ Piłka nożna - Zawodnicy", icon="⚽")
        st.page_link("pages/NHL-zawodnicy.py", label="🏒 NHL - Zawodnicy", icon="🏒")
        st.page_link("pages/NBA-zawodnicy.py", label="🏀 NBA - Zawodnicy", icon="🏀")
    with st.expander("O projekcie"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h2 style='color: #4fc3f7; border-bottom: 2px solid #4fc3f7; padding-bottom: 5px;'>Ekstrabet - Asystent Statystyczno-Predykcyjny</h2>
            <p style='line-height: 1.6;'>
                Ekstrabet to zaawansowane narzędzie analityczne stworzone dla miłośników sportu. 
                Wykorzystując uczenie maszynowe i statystykę, pomaga w podejmowaniu świadomych decyzji przy obstawianiu meczów sportowych.
            </p>
            <div style='background-color: #2d2d2d; border-left: 4px solid #4fc3f7; padding: 10px; margin: 10px 0;'>
                <p style='margin: 0; color: #ffffff;'><strong>Główne założenia projektu:</strong></p>
                <ul style='margin-top: 5px; color: #e0e0e0;'>
                    <li>Analiza historycznych danych meczowych</li>
                    <li>Predykcja wyników spotkań</li>
                    <li>Identyfikacja wartościowych zakładów</li>
                    <li>Wizualizacja prezentowanych danych</li>
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
                        <p style='font-size: 14px; color: #e0e0e0;'>Szczegółowe analizy osiągnięć modeli oraz charakterystyk ligowych.</p>
                    </div>
                    <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                        <h4 style='margin-top: 0; color: #4fc3f7;'>💸 Kącik bukmacherski</h4>
                        <p style='font-size: 14px; color: #e0e0e0;'>Rekomendacje zakładów oparte na modelach predykcyjnych.</p>
                    </div>
                    <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                        <h4 style='margin-top: 0; color: #4fc3f7;'>⚽ Baza lig</h4>
                        <p style='font-size: 14px; color: #e0e0e0;'>Dostęp do szczegółowych danych oraz analiz z wielu lig.</p>
                    </div>
                    <div style='background: #2d2d2d; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border: 1px solid #444;'>
                        <h4 style='margin-top: 0; color: #4fc3f7;'>🏆 Wiele dyscyplin</h4>
                        <p style='font-size: 14px; color: #e0e0e0;'>System nie ogranicza się do jednego sportu - obecnie hokej i piłka nożna, w planach koszykówka i esport.</p>
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
                    <span style='font-weight: 500; color: #e0e0e0;'>Rozszerzenie o inne dyscypliny sportowe (np. koszykówka) oraz o esport (CS2, LOL)</span>
                </div>
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>2</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Dodanie analizy w czasie rzeczywistym w oparciu o dane użytkownika</span>
                </div>
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>3</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Utworzenie API do łatwiejszej integracji z systemem dla developerów</span>
                </div>
                <div style='display: flex; align-items: center;'>
                    <span style='background: #4fc3f7; color: #121212; border-radius: 50%; width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px;'>4</span>
                    <span style='font-weight: 500; color: #e0e0e0;'>Utworzenie profili użytkownika do personalizacji filtrów</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Informacja prawna dotycząca danych"):
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
                <p>📚 Wszystkie wyniki i statystyki prezentowane w serwisie stanowią fakty powszechnie dostępne i zostały zaczerpnięte z publicznych źródeł o charakterze kronikarskim. Opracowanie tych danych ma charakter wyłącznie edukacyjny i badawczy. Serwis nie rości sobie żadnych praw autorskich do danych ani materiałów pochodzących z podanych źródeł, a wszelkie prawa do nich należą do ich właścicieli.</p>
                <p>💡 Symulacje zakładów mają charakter czysto hipotetyczny, służą wyłącznie do testowania modeli i analiz statystycznych. Nie stanowią oferty ani zachęty do udziału w grach hazardowych w rozumieniu przepisów prawa.</p>   
                <p>📊 Źródła danych:
                    <br>– Mecze i statystyki piłkarskie: <a href="https://www.flashscore.pl" target="_blank">flashscore.pl</a>, <a href="https://optaplayerstats.statsperform.com/" target="_blank">opta.com</a>
                    <br>– Dane hokejowe: <a href="https://api-web.nhle.com/" target="_blank">NHL API</a>
                    <br>– Dane koszykarskie: <a href="https://www.flashscore.pl" target="_blank">flashscore.pl</a>
                </p> 
                <p>🧥 Materiały graficzne (koszulki hokejowe) pochodzą z <a href="https://www.dailyfaceoff.com/" target="_blank">dailyfaceoff.com</a> i pozostają własnością ich autorów. Zostały użyte wyłącznie w celach informacyjnych i ilustracyjnych.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.expander("Kontakt"):
        st.markdown("""
        <div style='padding: 10px; font-family: Arial, sans-serif; color: #e0e0e0;'>
            <h3 style='color: #4fc3f7;'>Skontaktuj się z autorem</h3>
            <p style='margin-bottom: 20px; color: #e0e0e0;'>Masz pytania lub sugestie dotyczące projektu? Chętnie je poznam!</p>
            <a href='https://41761707.github.io/' target='_blank' style='display: inline-block; background-color: #4fc3f7; color: #121212; padding: 10px 15px; border-radius: 5px; text-decoration: none; font-weight: bold; transition: background-color 0.3s;'>Odwiedź stronę autora</a>
            <p style='margin-top: 20px; font-size: 14px; color: #b0b0b0;'>Autor projektu: Radikey</p>
            <p style='margin-top: 20px; font-size: 14px; color: #b0b0b0;'>Projekt rozwijany przez pasjonatów dla pasjonatów</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("FAQ - Najczęściej zadawane pytania"):
        st.markdown("### Jak działają modele predykcyjne w Ekstrabet?")
        st.write("Nasze modele wykorzystują uczenie maszynowe do analizy historycznych danych meczowych, statystyk drużyn i zawodników. Algorytmy analizują wzorce w danych i na tej podstawie przewidują prawdopodobieństwa różnych wyników meczów. Więcej informacji zostanie opublikowanych w specjalej sekcji 'Działanie modeli'")
        
        st.markdown("### Ile lig i dyscyplin sportowych obsługuje system?")
        st.write("Obecnie Ekstrabet obsługuje ponad 30 lig piłkarskich z całego świata oraz hokej na lodzie (NHL). Pełna lista obsługiwanych lig znajduje się w sekcji 'Lista obsługiwanych lig' na stronie głównej. W planach mamy dodanie koszykówki oraz esportu.")
        
        st.markdown("### Czy mogę używać prognoz do realnych zakładów bukmacherskich?")
        st.write("Ekstrabet ma charakter edukacyjny i badawczy. Wszystkie symulacje zakładów są hipotetyczne i służą wyłącznie do testowania modeli. Nie zachęcamy do uczestnictwa w grach hazardowych.")
        
        st.markdown("### Skąd pochodzą dane używane w analizach?")
        st.write("Wszystkie dane pochodzą z publicznych źródeł: statystyki piłkarskie z flashscore.pl i opta.com, dane hokejowe z oficjalnego NHL API, a materiały graficzne z dailyfaceoff.com.")
        
        st.markdown("### Jaka jest dokładność prognoz systemu?")
        st.write("Dokładność modeli różni się w zależności od ligi i typu prognozy. Szczegółowe statystyki wydajności każdego modelu znajdziesz w 'Kąciku statystycznym'. Pamiętaj, że żaden model nie jest w 100% dokładny.")


    conn.close()

if __name__ == '__main__':
    main()
