import streamlit as st
st.set_page_config(page_title = "Ligue 2", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(13, 11, "Ligue 2")

if __name__ == '__main__':
    main()