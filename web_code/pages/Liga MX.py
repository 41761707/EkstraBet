import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import db_module
import base_site_module

def main():
    base = base_site_module.Base(19, 11, 2, "Liga MX", '2024-07-07')

if __name__ == '__main__':
    main()