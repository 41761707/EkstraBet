import streamlit as st
st.set_page_config(page_title = "Bundesliga", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(4, 11, "Bundesliga")

if __name__ == '__main__':
    main()