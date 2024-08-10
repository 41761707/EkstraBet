import streamlit as st
st.set_page_config(page_title = "MLS", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(25, 1, "MLS")

if __name__ == '__main__':
    main()