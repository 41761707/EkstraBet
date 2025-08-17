import streamlit as st
st.set_page_config(page_title = "Kącik bukmacherski", page_icon = "⚽", layout="wide")
import pandas as pd

import db_module

def config():
    st.header("Kącik bukmacherski")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.subheader("Konfiguracja prezentowanych danych")
    odds_range =  st.slider("Dolna granica kursu", 1.0, 5.0, 1.5, 0.1)
    from_now = st.checkbox("Zakłady tylko od aktualnego momentu")
    return odds_range, from_now    

def generate_dicts(query, conn):
    df = pd.read_sql(query, conn)
    return df.set_index('name')['id'].to_dict()

def generate_button(button_name, conn, type, where_clause):
    if type == -1: #Już zrealizowane
        query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as "DATA SPOTKANIA", b.odds as KURS, b.EV as VB, ROUND(p.value * 100, 2) as "PEWNOSC MODELU [%]",
                    case when fp.outcome then 'WYGRANA' else 'PRZEGRANA' end as Wynik
                            from bets b
                                join predictions p on (b.match_id = p.match_id and b.event_id = p.event_id and b.model_id = p.model_id)
                                join final_predictions fp on p.id = fp.predictions_id
                                join matches m on b.match_id = m.id
                                join teams t1 on m.home_team = t1.id
                                join teams t2 on m.away_team = t2.id
                                join events e on b.event_id = e.id
                                join leagues l on m.league = l.id'''
    else: #1 - przyszłe
        query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as "DATA SPOTKANIA", b.odds as KURS, b.EV as VB, ROUND(p.value * 100, 2)  as "PEWNOSC MODELU [%]"
                    from bets b
                        join predictions p on (b.match_id = p.match_id and b.event_id = p.event_id and b.model_id = p.model_id)
                        join final_predictions fp on p.id = fp.predictions_id
                        join matches m on b.match_id = m.id
                        join teams t1 on m.home_team = t1.id
                        join teams t2 on m.away_team = t2.id
                        join events e on b.event_id = e.id
                        join leagues l on m.league = l.id''' 
    query = query + where_clause
    if st.button(button_name, use_container_width = True):
        bets_df = pd.read_sql(query, conn)
        bets_df.index = range(1, len(bets_df) + 1)
        st.dataframe(bets_df, use_container_width=True, hide_index=True)

def main():
    conn = db_module.db_connect()
    odds_range, from_now = config()
    query = "select distinct id, name from leagues where active = 1 order by name"
    leagues_dict = generate_dicts(query, conn)
    chosen_leagues = st.multiselect(
    "Zakłady dla wybranych lig",
    [k for k in leagues_dict.keys()], default = [k for k in leagues_dict.keys()], placeholder="Wybierz ligi z listy")

    query = "select id, name from events where id in (1, 2, 3, 8, 12, 6, 172) order by name"
    events_dict = generate_dicts(query, conn)
    chosen_events = st.multiselect(
    "Wybrane zdarzenia",
    [k for k in events_dict.keys()], default = [k for k in events_dict.keys()], placeholder="Wybierz zdarzenia z listy")

    with st.expander("Poprzednie zakłady"):
        generate_button("Wczorajsze zakłady", conn, -1,
                        " where cast(m.game_date as date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) order by p.value desc".format(odds_range))
    
    with st.expander("Proponowane zakłady"):
        generate_button("TOP 5 + Polska (dla Kubona)", conn, 1, 
                        " where cast(m.game_date as date) = current_date and league in (1, 21, 2, 3, 4, 5, 6) order by b.EV desc".format(odds_range))
        generate_button("Wszystkie ligi", conn, 1, 
                        " where cast(m.game_date as date) = current_date order by p.value desc".format(odds_range))
        generate_button("Tylko OU", conn, 1, 
                        " where cast(m.game_date as date) = current_date and p.event_id in (8,12) order by b.EV desc".format(odds_range))
        generate_button("Tylko BTTS", conn, 1, 
                        " where cast(m.game_date as date) = current_date and p.event_id in (6, 172) order by b.EV desc".format(odds_range))
        generate_button("Tylko REZULTAT", conn, 1, 
                        " where cast(m.game_date as date) = current_date and p.event_id in (1,2,3) order by b.EV desc".format(odds_range))

        #Do ewentualnej poprawki w przyszłości
        if st.button("Ustawienia niestandardowe (definiowane na górze strony)", use_container_width=True):
            if len(chosen_leagues) == 0:
                st.subheader("Nie wybrano żadnych lig")
            elif len(chosen_events) == 0:
                st.subheader("Nie wybrano żadnych zdarzeń")
            else:
                base_query = '''SELECT 
                    l.name AS LIGA,
                    t1.name AS GOSPODARZ,
                    t2.name AS GOŚĆ,
                    e.name AS ZDARZENIE,
                    m.game_date AS "DATA SPOTKANIA",
                    b.odds AS KURS,
                    b.EV AS VB,
                    ROUND(p.value * 100, 2) AS "PEWNOSC MODELU [%]"
                FROM bets b
                JOIN predictions p ON (b.match_id = p.match_id AND b.event_id = p.event_id and b.model_id = p.model_id)
                JOIN final_predictions fp ON p.id = fp.predictions_id
                JOIN matches m ON b.match_id = m.id
                JOIN teams t1 ON m.home_team = t1.id
                JOIN teams t2 ON m.away_team = t2.id
                JOIN events e ON b.event_id = e.id
                JOIN leagues l ON m.league = l.id
                WHERE '''

                date_condition = '''m.game_date >= current_timestamp''' if from_now else '''CAST(m.game_date AS DATE) = current_date'''
                
                full_query = f'''
                    {base_query}
                    {date_condition}
                    AND b.odds >= {odds_range}
                    AND m.league IN ({",".join(str(leagues_dict[v]) for v in chosen_leagues)})
                    AND e.id IN ({",".join(str(events_dict[v]) for v in chosen_events)})
                    ORDER BY m.game_date
                '''

                # Wykonanie zapytania i wyświetlenie wyników
                bets_df = pd.read_sql(full_query, conn)
                bets_df.index = range(1, len(bets_df) + 1)
                st.dataframe(bets_df, use_container_width=True, hide_index=True)
    conn.close()
        

if __name__ == '__main__':
    main()