import streamlit as st
st.set_page_config(page_title = "2 Liga (Austria)", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    #current_date = datetime.today().strftime('%Y-%m-%d')
    #league, season, round, name, current_date
    #base = base_site_module.Base(1, 11, 1, "Ekstraklasa", current_date)
    st.header("2 Liga (Austria) - brak danych")

if __name__ == '__main__':
    main()