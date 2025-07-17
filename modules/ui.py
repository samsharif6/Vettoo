# modules/ui.py

import io
import pandas as pd
import streamlit as st
import plotly.express as px
from modules.data_loader import DataLoader
from modules.filters import filter_by_tp, filter_by_qual, available_quals


def shorten_label(c: str) -> str:
    """
    If the column name contains a comma, return the part after the comma,
    else return the full column name.
    """
    return c.split(",", 1)[1].strip() if "," in c else c


def run_app():
    # Page config
    st.set_page_config(page_title="Vettoo Dashboard", layout="wide")
    st.title("🤖 Vettoo")
    st.subheader("Click less. Know more.")

    # Load data
    dl = DataLoader()
    status = st.sidebar.selectbox(
        "Training Contract Status",
        ["Commencements", "In-training", "Completions"],
        key="status"
    )
    df = dl.load_status(status)

    # Training package selector
    tps = st.sidebar.multiselect(
        "Training Package(s)",
        options=sorted(df["Training Packages"].unique()),
        key="tps"
    )

    # Qualifications selector (always available; filters by TP if chosen)
    if tps:
        qual_options = available_quals(df, tps)
    else:
        qual_options = sorted(df["Latest Qualification"].unique())
    quals = st.sidebar.multiselect(
        "Qualification(s) (start typing to filter)",
        options=qual_options,
        default=[],
        key="quals"
    )

    # Aggregate toggle
    aggregate = False
    if tps:
        aggregate = st.sidebar.checkbox(
            "Aggregate qualifications by Training Package",
            value=False,
            key="aggregate"
        )

    # Date period slider
    all_periods = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    sorted_periods = sorted(all_periods)
    start, end = st.sidebar.select_slider(
        "Select period range",
        options=sorted_periods,
        value=(sorted_periods[0], sorted_periods[-1])
    )
    start_idx = sorted_periods.index(start)
    end_idx = sorted_periods.index(end)
    period_range = sorted_periods[start_idx:end_idx+1]

    # Instruction guard
    if not tps and not quals:
        st.write(
            """
            **Instructions**  
            1. Choose a *Training Contract Status*.  
            2. Select one or more *Training Packages* and/or *Qualifications*.  
            3. Optionally check **Aggregate by Package**.  
            4. Use the **period slider** to zoom on date range.
            """
        )
        st.info("👉 Please select at least one package or qualification to proceed.")
        return

    # Default quals if none selected but TP chosen and not aggregating
    if tps and not aggregate and not quals:
        quals = available_quals(df, tps)

    # Filtering
    sub = df
    if tps:
        sub = filter_by_tp(sub, tps)
    if not aggregate and quals:
        sub = filter_by_qual(sub, quals)

    # Subset periods
    numeric_cols = period_range
    latest = numeric_cols[-1] if numeric_cols else ""

    # Header
    st.header(f"{status} — 12-month Data")
    st.write(f"NCVER, Apprentices and trainees – {shorten_label(latest)} DataBuilder, {status} by 12 month series – South Australia")

    # Plot
    if aggregate and tps:
        data = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        melt = data.melt(id_vars="Training Packages", value_vars=numeric_cols,
                         var_name="Period", value_name="Value")
        fig = px.line(
            melt, x="Period", y="Value", color="Training Packages",
            markers=True, title="Aggregated by Training Package"
        )
    else:
        data = sub.copy()
        melt = data.melt(id_vars="Latest Qualification", value_vars=numeric_cols,
                         var_name="Period", value_name="Value")
        fig = px.line(
            melt, x="Period", y="Value", color="Latest Qualification",
            markers=True, title="Qualifications over Time"
        )
    fig.update_layout(xaxis_title="Period", yaxis_title="Count", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("Data Table")
    if aggregate and tps:
        tbl = data.rename(columns={c: shorten_label(c) for c in numeric_cols})
    else:
        tbl = pd.concat([
            sub[["Latest Qualification","TDV","Training Packages"] + numeric_cols],
            pd.DataFrame([{"Latest Qualification":"Total of selected items", **{c: sub[c].sum() for c in numeric_cols}}])
        ], ignore_index=True)
        tbl = tbl.rename(columns={c: shorten_label(c) for c in numeric_cols})
    st.dataframe(tbl)

    # Download
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        tbl.to_excel(writer, index=False, sheet_name="Data")
        metadata = {
            "Source": f"NCVER, Apprentices and trainees – {shorten_label(latest)} DataBuilder, {status} by 12 month series – South Australia",
            "Period Range": f"{start} to {end}",
            "Training Packages": ", ".join(tps) if tps else "None",
            "Qualifications": ", ".join(quals) if quals else "None"
        }
        md_df = pd.DataFrame(
            list(metadata.items()),
            columns=["Description", "Value"]
        )
        md_df.to_excel(writer, index=False, sheet_name="Metadata")
    towrite.seek(0)
    fname = f"{status.lower().replace(' ','_')}_data_{start}_to_{end}.xlsx"
    st.download_button(
        "📥 Download data as Excel", data=towrite,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )