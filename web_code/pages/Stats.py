import streamlit as st
st.set_page_config(page_title = "Kącik statystyczny", page_icon = "⚽", layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.header("Kącik statystyczny")

if __name__ == '__main__':
    main()