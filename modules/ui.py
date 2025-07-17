# modules/ui.py

import io
import pandas as pd
import streamlit as st
from modules.data_loader import DataLoader
from modules.filters import filter_by_tp, filter_by_qual, available_quals


def shorten_label(c: str) -> str:
    """
    If the column name contains a comma, return the part after the comma,
    else return the full column name.
    """
    if "," in c:
        return c.split(",", 1)[1].strip()
    return c


def run_app():
    # Configure page
    st.set_page_config(page_title="Vettoo Dashboard", layout="wide")
    st.title("Vettoo Qualifications Dashboard")

    # Sidebar: status selector
    dl = DataLoader()
    status = st.sidebar.selectbox(
        "Training Contract Status",
        ["Commencements", "In-training", "Completions"]
    )
    df = dl.load_status(status)

    # Sidebar: filters
    tps = st.sidebar.multiselect(
        "Training Package(s)",
        options=sorted(df["Training Packages"].unique())
    )
    quals = st.sidebar.multiselect(
        "Qualification(s)\n(only shows aligned to selected TP)",
        options=available_quals(df, tps)
    )

    # Show instructions until user makes a selection
    if not tps and not quals:
        st.write(
            """
            **Instructions**  
            1. Select a *Training Contract Status* from the sidebar.  
            2. Then choose one or more *Training Packages* and/or *Qualifications*.  
            3. Once selection(s) are made, the chart and table will appear below.
            """
        )
        st.info(
            "👉 Please select at least one *Training Package* or *Qualification* from the sidebar to continue."
        )
        return

    # Apply filters to data
    sub = filter_by_tp(df, tps)
    sub = filter_by_qual(sub, quals)

    # Determine numeric period columns
    numeric_cols = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]
    latest_period = numeric_cols[-1] if numeric_cols else ""
    latest_period_simple = shorten_label(latest_period)

    # Header and subtitle
    st.header(f"{status} — Selected Data")
    st.write(
        f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, Contract status by 12 month series – South Australia"
    )

    # Plot qualifications over time (periods on x-axis, one line per qualification)
    df_plot = sub.set_index("Latest Qualification")[numeric_cols]
    df_plot = df_plot.T  # periods as index
    df_plot.index = [shorten_label(c) for c in df_plot.index]
    st.line_chart(df_plot)

    # Prepare data table
    # Create totals row only
    totals = sub[numeric_cols].sum()
    totals_dict = {col: totals[col] for col in numeric_cols}
    totals_dict["Latest Qualification"] = "Total of selected items"

    # Combine data and totals row
    table = pd.concat([sub, pd.DataFrame([totals_dict])], ignore_index=True)

    # Rename period columns for display
    rename_map = {c: shorten_label(c) for c in numeric_cols}
    table_display = table.rename(columns=rename_map)

    # Display table
    st.subheader("Data Table")
    st.dataframe(table_display)

    # Provide download button for Excel
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        table.to_excel(writer, index=False, sheet_name="Data")
    towrite.seek(0)

    st.download_button(
        label="📥 Download data as Excel",
        data=towrite,
        file_name=f"{status.replace(' ', '_')}_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )