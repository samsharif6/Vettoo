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
    return c.split(",", 1)[1].strip() if "," in c else c


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

    # Sidebar: training package selector
    tps = st.sidebar.multiselect(
        "Training Package(s)",
        options=sorted(df["Training Packages"].unique())
    )

    # Aggregate toggle (only if TP selected)
    aggregate = False
    if tps:
        aggregate = st.sidebar.checkbox(
            "Aggregate qualifications by Training Package",
            value=False
        )

    # Sidebar: qualification selector (only when not aggregating)
    if not aggregate:
        all_quals = available_quals(df, tps) if tps else []
        quals = st.sidebar.multiselect(
            "Qualification(s)\n(only shows aligned to selected TP)",
            options=all_quals,
            default=[]
        )
    else:
        quals = []  # ignore qualifications when aggregating

    # Show instructions until valid selection
    if not tps or (not aggregate and not quals):
        st.write(
            """
            **Instructions**  
            1. Select a *Training Contract Status* from the sidebar.  
            2. Choose one or more *Training Packages*.  
            3. Optionally check **Aggregate qualifications by Training Package**.  
            4. If **Aggregate** is unchecked, select at least one *Qualification* to display detailed data.  
            """
        )
        st.info(
            "👉 Please select at least one *Training Package*, and if not aggregating, at least one *Qualification*."
        )
        return

    # Filter data by package, then by qualification if not aggregating
    sub_tp = filter_by_tp(df, tps)
    if aggregate:
        sub = sub_tp
    else:
        sub = filter_by_qual(sub_tp, quals)

    # Determine numeric (period) columns
    numeric_cols = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]
    latest_period_simple = shorten_label(numeric_cols[-1]) if numeric_cols else ""

    # Header and subtitle
    st.header(f"{status} — Selected Data")
    st.write(
        f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, Contract status by 12 month series – South Australia"
    )

    ### Aggregated view by Training Package ###
    if aggregate:
        agg_df = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        df_plot = agg_df.set_index("Training Packages")[numeric_cols].T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)

        st.subheader("Aggregated Data Table")
        table_display = agg_df.rename(columns={c: shorten_label(c) for c in numeric_cols})
        st.dataframe(table_display)

        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
            table_display.to_excel(writer, index=False, sheet_name="Data")
        towrite.seek(0)
        file_name = f"{status.lower().replace(' ', '_')}_by_package.xlsx"
        st.download_button(
            label="📥 Download aggregated data as Excel",
            data=towrite,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return

    ### Detailed view by Qualification ###
    df_plot = sub.set_index("Latest Qualification")[numeric_cols].T
    df_plot.index = [shorten_label(c) for c in df_plot.index]
    st.line_chart(df_plot)

    subtable = sub.copy()
    totals = subtable[numeric_cols].sum()
    totals_dict = {col: totals[col] for col in numeric_cols}
    totals_dict["Latest Qualification"] = "Total of selected items"
    table = pd.concat([subtable, pd.DataFrame([totals_dict])], ignore_index=True)
    table_display = table.rename(columns={c: shorten_label(c) for c in numeric_cols})

    st.subheader("Data Table")
    st.dataframe(table_display)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        table.to_excel(writer, index=False, sheet_name="Data")
    towrite.seek(0)
    file_name = f"{status.lower().replace(' ', '_')}_NCVER_data.xlsx"
    st.download_button(
        label="📥 Download data as Excel",
        data=towrite,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
