import streamlit as st
st.set_page_config(page_title = "Super Lig", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(24, 12, "Super Lig")

if __name__ == '__main__':
    main()