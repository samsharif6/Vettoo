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

    # Aggregate toggle (only if TP selected)
    aggregate = False
    if tps:
        aggregate = st.sidebar.checkbox(
            "Aggregate qualifications by Training Package",
            value=False,
            key="aggregate"
        )

    # Qualification selector (always available; filters by TP if chosen)
    if tps:
        qual_options = available_quals(df, tps)
    else:
        qual_options = sorted(df["Latest Qualification"].unique())
    quals = st.sidebar.multiselect(
        "Qualification(s) (start typing to filter)",
        options=qual_options,
        default=[],
        disabled=aggregate,
        key="quals"
    )

    # Year filter: extract unique years from annual columns
    # Identify all numeric period columns
    all_numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    # Get years by splitting on '_' and taking last 4 chars
    year_options = sorted({c.split('_')[-1] for c in all_numeric})
    years = st.sidebar.multiselect(
        "Year(s)",
        options=year_options,
        default=year_options,
        key="years"
    )

    # Show instructions until at least one filter selected
    if not tps and not quals and not years:
        st.write(
            """
            **Instructions**  
            1. Select a *Training Contract Status* from the sidebar.  
            2. Choose one or more *Training Packages* and/or *Qualifications*.  
            3. Optionally check **Aggregate qualifications by Training Package**.
            4. Select one or more *Year(s)* to filter the data.
            """
        )
        st.info(
            "👉 Please select at least one *Training Package*, *Qualification*, or *Year* to continue."
        )
        return

    # For detailed view, if no quals but TP chosen and not aggregating, default to all aligned
    if tps and not aggregate and not quals:
        quals = available_quals(df, tps)

    # Filtering data based on selections
    sub = df
    if tps:
        sub = filter_by_tp(sub, tps)
    if not aggregate and quals:
        sub = filter_by_qual(sub, quals)

    # Filter numeric columns by selected years
    numeric_cols = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]
    filtered_periods = [c for c in numeric_cols if c.split('_')[-1] in years]
    numeric_cols = filtered_periods
    latest_period = numeric_cols[-1] if numeric_cols else ""

    # Header and subtitle
    st.header(f"{status} — 12-month Data")
    st.write(
        f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia"
    )

    # Aggregated view by Training Package
    if aggregate and tps:
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
            table_display.to_excel(writer, index=False, sheet_name="Data")
            metadata = {
                "Source": f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia",
                "Training Contract Status": status,
                "Training Packages": ", ".join(tps),
                "Qualifications": "(aggregated by package)",
                "Years": ", ".join(years)
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
    display_cols = ["Latest Qualification", "TDV", "Training Packages"] + numeric_cols
    table = table[display_cols]
    table_display = table.rename(columns={c: shorten_label(c) for c in numeric_cols})

    st.subheader("Data Table")
    st.dataframe(table_display)

    # Download detailed data with metadata
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        table_display.to_excel(writer, index=False, sheet_name="Data")
        metadata = {
            "Source": f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia",
            "Training Contract Status": status,
            "Training Packages": ", ".join(tps) if tps else "None",
            "Qualifications": ", ".join(quals) if quals else "None",
            "Years": ", ".join(years)
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
