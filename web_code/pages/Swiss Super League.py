import streamlit as st
st.set_page_config(page_title = "Swiss Super League", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    current_date = datetime.today().strftime('%Y-%m-%d')
    #league, season, round, name, current_date
    base = base_site_module.Base(23, 11, 5, "Swiss Super League ", current_date)

if __name__ == '__main__':
    main()