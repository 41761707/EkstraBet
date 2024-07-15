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
    query_names = "select id, name from leagues"
    leagues_df = pd.read_sql(query_names, conn)
    leagues_dict = leagues_df.set_index('id')['name'].to_dict()
    query_countries = "select l.id as id, c.emoji as country from leagues l join countries c on l.country = c.id"
    league_country_df = pd.read_sql(query_countries, conn)
    league_country_dict = league_country_df.set_index('id')['country'].to_dict()
    st.title("Ekstrabet: sezon 1")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.header("Lista obsługiwanych lig:")
    for key, value in leagues_dict.items():
        st.page_link("pages/{}.py".format(value), label=value, icon = league_country_dict[key])



    conn.close()

if __name__ == '__main__':
    main()
