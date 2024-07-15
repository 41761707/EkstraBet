import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    base = base_site_module.Base(30, 1, 22, "K League 2", '2024-07-12')

if __name__ == '__main__':
    main()