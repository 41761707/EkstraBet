import streamlit as st
st.set_page_config(page_title = "Swiss Super League", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(23, 12,"Swiss Super League")

if __name__ == '__main__':
    main()