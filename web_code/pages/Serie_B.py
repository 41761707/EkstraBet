import streamlit as st
st.set_page_config(page_title = "Serie B", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(26, 11, "Serie B")

if __name__ == '__main__':
    main()