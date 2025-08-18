import streamlit as st
st.set_page_config(page_title = "Liga MX", page_icon = "⚽", layout="wide")

import base_site_module

def main():
    #league, season, name
    base = base_site_module.Base(19, 11, "Liga MX")

if __name__ == '__main__':
    main()