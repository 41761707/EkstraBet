import streamlit as st
st.set_page_config(page_title = "Kącik bukmacherski", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    st.header("Kącik bukmacherski")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    odds_range =  st.slider("Dolna granica kursu", 1.0, 5.0, 1.5, 0.1)
    conn = db_module.db_connect()
    with st.expander("Poprzednie zakłady"):
        if st.button("Wczorajsze zakłady", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU,
                case when f.outcome then 'WYGRANA' else 'PRZEGRANA' end as Wynik
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                            and odds > {}
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
    with st.expander("Proponowane zakłady"):
        if st.button("TOP 5 + Polska (dla Kubona)", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, bm.name as BUKMACHER,
                       case when f.event_id in (8,12) then f.confidence - 20 else f.confidence end as PEWNOSC_MODELU
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join bookmakers bm on b.bookmaker = bm.id
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = current_date
                            and league in (1, 21, 2, 3, 4, 5, 6)
                            and odds > {}
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
        if st.button("Wszystkie ligi", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB,
                        case when f.event_id in (8,12) then f.confidence - 20 else f.confidence end as PEWNOSC_MODELU
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = current_date
                            and odds > {}
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
        if st.button("Tylko OU", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = current_date
                            and odds > {}
                            and f.event_id in (8,12)
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
        if st.button("Tylko BTTS", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = current_date
                            and f.event_id in (6, 172)
                            and odds > {}
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
        if st.button("Tylko REZULTAT", use_container_width= True):
            query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU
                        from bets b
                            join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                            join matches m on b.match_id = m.id
                            join teams t1 on m.home_team = t1.id
                            join teams t2 on m.away_team = t2.id
                            join events e on b.event_id = e.id
                            join leagues l on m.league = l.id
                            where cast(m.game_date as date) = current_date
                            and odds > {}
                            and f.event_id in (1,2,3)
                            order by b.EV desc'''.format(odds_range)
            bets_df = pd.read_sql(query, conn)
            bets_df.index = range(1, len(bets_df) + 1)
            st.dataframe(bets_df, use_container_width=True, hide_index=True)
    conn.close()
        

if __name__ == '__main__':
    main()