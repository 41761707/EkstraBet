import streamlit as st
st.set_page_config(page_title = "Chance liga", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(12, 11, "Chance liga")

if __name__ == '__main__':
    main()