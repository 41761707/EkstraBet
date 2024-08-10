import streamlit as st
st.set_page_config(page_title = "K League 2", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(30, 1, "K League 2")

if __name__ == '__main__':
    main()