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
    st.title("Vettoo – Your data buddy in the VET world.")
    st.subheader("Click less. Know more.")

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

    # Sidebar: qualification selector (detailed view only; empty by default)
    all_quals = available_quals(df, tps) if tps else []
    quals = st.sidebar.multiselect(
        "Qualification(s)\n(only shows aligned to selected TP)",
        options=all_quals,
        default=[],
        disabled=aggregate
    )

    # Show instructions until training package selected
    if not tps:
        st.write(
            """
            **Instructions**  
            1. Select a *Training Contract Status* from the sidebar.  
            2. Choose one or more *Training Packages*.
            """
        )
        st.info(
            "👉 Please select at least one *Training Package* to continue."
        )
        return

    # For detailed view, if no quals selected, show all by default
    if not aggregate and not quals:
        quals = all_quals

    # Filter data by package, then by qualification if not aggregating
    sub_tp = filter_by_tp(df, tps)
    sub = sub_tp if aggregate else filter_by_qual(sub_tp, quals)

    # Determine numeric (period) columns
    numeric_cols = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]
    latest_period_simple = shorten_label(numeric_cols[-1]) if numeric_cols else ""

    # Header and subtitle
    st.header(f"{status} — 12-month Data")
    st.write(
        f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, {status} by 12 month series – South Australia"
    )

    # Aggregated view by Training Package
    if aggregate:
        agg_df = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        df_plot = agg_df.set_index("Training Packages")[numeric_cols].T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)

        st.subheader("Aggregated Data Table")
        table_display = agg_df.rename(columns={c: shorten_label(c) for c in numeric_cols})
        st.dataframe(table_display)

        # Download aggregated data with metadata
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
            # Data sheet
            table_display.to_excel(writer, index=False, sheet_name="Data")
            # Metadata sheet
            metadata = {
                "Source": f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, {status} by 12 month series – South Australia",
                "Training Contract Status": status,
                "Training Packages": ", ".join(tps),
                "Qualifications": "(aggregated by package)",
            }
            md_df = pd.DataFrame(list(metadata.items()), columns=["Description", "Value"])
            md_df.to_excel(writer, index=False, sheet_name="Metadata")
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
    df_plot = sub.set_index("Latest Qualification")[numeric_cols].T
    df_plot.index = [shorten_label(c) for c in df_plot.index]
    st.line_chart(df_plot)

    # Prepare detailed table with totals row
    subtable = sub.copy()
    totals = subtable[numeric_cols].sum()
    totals_dict = {col: totals[col] for col in numeric_cols}
    totals_dict["Latest Qualification"] = "Total of selected items"
    table = pd.concat([subtable, pd.DataFrame([totals_dict])], ignore_index=True)
    # Select only desired columns
    display_cols = ["Latest Qualification", "TDV", "Training Packages"] + numeric_cols
    table = table[display_cols]
    # Rename period columns for display
    rename_map = {c: shorten_label(c) for c in numeric_cols}
    table_display = table.rename(columns=rename_map)

    st.subheader("Data Table")
    st.dataframe(table_display)

    # Download detailed data with metadata
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        # Data sheet
        table_display.to_excel(writer, index=False, sheet_name="Data")
        # Metadata sheet
        metadata = {
            "Source": f"NCVER, Apprentices and trainees – {latest_period_simple} DataBuilder, {status} by 12 month series – South Australia",
            "Training Contract Status": status,
            "Training Packages": ", ".join(tps),
            "Qualifications": ", ".join(quals) if quals else "All aligned qualifications",
        }
        md_df = pd.DataFrame(list(metadata.items()), columns=["Description", "Value"])
        md_df.to_excel(writer, index=False, sheet_name="Metadata")
    towrite.seek(0)
    file_name = f"{status.lower().replace(' ', '_')}_NCVER_data.xlsx"
    st.download_button(
        label="📥 Download data as Excel",
        data=towrite,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
