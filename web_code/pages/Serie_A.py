import streamlit as st
st.set_page_config(page_title = "Serie A", page_icon = "⚽", layout="wide")
import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(5, 11, "Serie A")

if __name__ == '__main__':
    main()