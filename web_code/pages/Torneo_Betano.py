import streamlit as st
st.set_page_config(page_title = "Torneo Betano", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(33, 1, "Torneo Betano")

if __name__ == '__main__':
    main()