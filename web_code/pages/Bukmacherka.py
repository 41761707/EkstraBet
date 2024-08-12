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
    conn = db_module.db_connect()
    with st.expander("Proponowane zakłady"):
        query = '''select l.name as LIGA, t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU
                    from bets b
                        join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                        join matches m on b.match_id = m.id
                        join teams t1 on m.home_team = t1.id
                        join teams t2 on m.away_team = t2.id
                        join events e on b.event_id = e.id
                        join leagues l on m.league = l.id
                        where cast(m.game_date as date) = current_date
                        order by b.EV desc'''
        bets_df = pd.read_sql(query, conn)
        bets_df.index = range(1, len(bets_df) + 1)
        st.dataframe(bets_df, use_container_width=True, hide_index=True)
    conn.close()
        

if __name__ == '__main__':
    main()