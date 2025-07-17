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

    # Sidebar: filters
    tps = st.sidebar.multiselect(
        "Training Package(s)",
        options=sorted(df["Training Packages"].unique())
    )
    # Qualification options depend on selected TPs
    quals = st.sidebar.multiselect(
        "Qualification(s)\n(only shows aligned to selected TP)",
        options=available_quals(df, tps) if tps else []
    )

    # Aggregate toggle (only if TP selected)
    aggregate = False
    if tps:
        aggregate = st.sidebar.checkbox(
            "Aggregate qualifications by Training Package",
            value=False
        )

    # Show instructions until selection
    if not tps and not quals:
        st.write(
            """
            **Instructions**  
            1. Select a *Training Contract Status* from the sidebar.  
            2. Choose one or more *Training Packages* and/or *Qualifications*.  
            3. Optionally check the aggregation box to roll up by package.  
            """
        )
        st.info(
            "👉 Please select at least one *Training Package* or *Qualification* from the sidebar to continue."
        )
        return

    # Filter data
    sub = filter_by_tp(df, tps)
    sub = filter_by_qual(sub, quals)

    # Determine numeric (period) columns
    numeric_cols = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]
    latest_period = numeric_cols[-1] if numeric_cols else ""
    latest_period_simple = shorten_label(latest_period)

    # Header and subtitle
    st.header(f"{status} — Selected Data")
    st.write(
        f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, Contract status by 12 month series – South Australia"
    )

    # Aggregated view by Training Package
    if aggregate and tps:
        # Group and sum numeric columns by Training Packages
        agg_df = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        # Prepare for plotting: periods on x, packages as lines
        df_plot = agg_df.set_index("Training Packages")[numeric_cols].T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)

        # Show aggregated table (packages + periods)
        st.subheader("Aggregated Data Table")
        table_display = agg_df.rename(columns={c: shorten_label(c) for c in numeric_cols})
        st.dataframe(table_display)

        # Download aggregated data
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

    # Detailed view by Qualification
    # Plot qualifications over time
    df_plot = sub.set_index("Latest Qualification")[numeric_cols].T
    df_plot.index = [shorten_label(c) for c in df_plot.index]
    st.line_chart(df_plot)

    # Detailed data table with totals row
    subtable = sub.copy()
    totals = subtable[numeric_cols].sum()
    totals_dict = {col: totals[col] for col in numeric_cols}
    totals_dict["Latest Qualification"] = "Total of selected items"
    table = pd.concat([subtable, pd.DataFrame([totals_dict])], ignore_index=True)
    table_display = table.rename(columns={c: shorten_label(c) for c in numeric_cols})

    st.subheader("Data Table")
    st.dataframe(table_display)

    # Download detailed data
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
```
