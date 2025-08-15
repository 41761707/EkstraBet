import streamlit as st
st.set_page_config(page_title = "2 Liga (Austria)", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, round, name
    base = base_site_module.Base(38, 12, "2 Liga (Austria)")

if __name__ == '__main__':
    main()