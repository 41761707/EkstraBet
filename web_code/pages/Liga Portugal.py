import streamlit as st
st.set_page_config(page_title = "Liga Portugal", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(7, 11, "Liga Portugal")

if __name__ == '__main__':
    main()