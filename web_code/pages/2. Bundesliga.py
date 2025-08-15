import streamlit as st
st.set_page_config(page_title = "2. Bundesliga", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(20, 12, "2. Bundesliga")

if __name__ == '__main__':
    main()