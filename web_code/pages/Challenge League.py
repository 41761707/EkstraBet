import streamlit as st
st.set_page_config(page_title = "Challenge League", page_icon = "⚽", layout="wide")
import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(39, 12, "Challenge League")

if __name__ == '__main__':
    main()