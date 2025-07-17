# modules/plotter.py

import streamlit as st
import pandas as pd                 # ← add this

def plot_time_series(df: pd.DataFrame):
    # if your year-columns aren’t strict “20XX” strings, use numeric detection:
    data_cols = df.select_dtypes(include="number").columns.tolist()
    
    # now plot
    st.line_chart(
        df
        .set_index("Latest Qualification")[data_cols]
        .T
    )
