import mysql.connector
import pandas as pd
import numpy as np
import sys
import streamlit as st

def db_connect():
    # Połączenie z bazą danych MySQL z użyciem sekretów
    conn = mysql.connector.connect(
        host=st.secrets["MYSQL_HOST"],
        user=st.secrets["MYSQL_USER"],
        password=st.secrets["MYSQL_PASSWORD"],
        database=st.secrets["MYSQL_DATABASE"]
    )
    return conn