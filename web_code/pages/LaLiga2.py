import streamlit as st
st.set_page_config(page_title = "LaLiga2", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(14, 12, "LaLiga2")

if __name__ == '__main__':
    main()