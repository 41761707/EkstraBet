import streamlit as st
st.set_page_config(page_title = "Eerste Divisie", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(31, 12, "Eerste Divisie")

if __name__ == '__main__':
    main()