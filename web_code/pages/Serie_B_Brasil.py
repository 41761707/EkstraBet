import streamlit as st
st.set_page_config(page_title = "Serie B Brasil", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(35, 1, "Serie A Brasil")

if __name__ == '__main__':
    main()