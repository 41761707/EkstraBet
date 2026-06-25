import streamlit as st
st.set_page_config(page_title = "Betclic 1 Liga", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(21, 11, "Betclic 1 Liga")

if __name__ == '__main__':
    main()
