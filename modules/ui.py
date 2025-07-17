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
        "Qualification(s)",
        options=qual_options,
        default=[],
        disabled=aggregate,
        key="quals"
    )

    # Year range slider: extract unique years from period columns
    all_numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    years_int = sorted({int(c.split('_')[-1]) for c in all_numeric})
    start_year, end_year = st.sidebar.select_slider(
        "Select Year Range",
        options=years_int,
        value=(years_int[0], years_int[-1]) if years_int else (None, None),
        key="year_range"
    )

        # If only status is selected (no TP and no quals), read aggregated results from SA sheet
    if not tps and not quals:
        # Load SA aggregation sheet
        sa_df = pd.read_excel(dl.file_path, sheet_name="SA")
        # Extract numeric period columns within selected year range
        numeric_cols = [
            c for c in sa_df.columns
            if pd.api.types.is_numeric_dtype(sa_df[c])
            and start_year <= int(c.split('_')[-1]) <= end_year
        ]
        latest_period = numeric_cols[-1] if numeric_cols else ""

        st.header(f"{status} — 12-month Data")
        st.write(
            f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia"
        )
        # Filter row for selected status
        row = sa_df.loc[sa_df['Training Contract Status'] == status, numeric_cols]
        if row.empty:
            st.warning(f"No aggregated data found for {status} in SA sheet.")
            return
        totals = row.squeeze()

        # Plot single total line
        df_plot = pd.DataFrame({status: totals}).T
        df_plot = df_plot.T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)

        # Show total table
        total_row = {"Latest Qualification": f"Total {status}"}
        total_row.update({c: totals[c] for c in numeric_cols})
        table_display = pd.DataFrame([total_row])
        table_display = table_display.rename(columns={c: shorten_label(c) for c in numeric_cols})
        st.subheader("Aggregated Data Table")
        st.dataframe(table_display)
        return

    # Default qualifications logic
    if tps and not aggregate and not quals:
        quals = available_quals(df, tps)

    # Filter data based on selections
    sub = df
    if tps:
        sub = filter_by_tp(sub, tps)
    if not aggregate and quals:
        sub = filter_by_qual(sub, quals)

    # Determine numeric (period) columns within selected year range
    if years_int:
        numeric_cols = [
            c for c in sub.columns
            if pd.api.types.is_numeric_dtype(sub[c])
            and start_year <= int(c.split('_')[-1]) <= end_year
        ]
    else:
        numeric_cols = []
    latest_period = numeric_cols[-1] if numeric_cols else ""

    # Header and subtitle
    st.header(f"{status} — 12-month Data")
    st.write(
        f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia"
    )

    # Plot
    if aggregate and tps:
        agg_df = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        df_plot = agg_df.set_index("Training Packages")[numeric_cols].T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)
    else:
        df_plot = sub.set_index("Latest Qualification")[numeric_cols].T
        df_plot.index = [shorten_label(c) for c in df_plot.index]
        st.line_chart(df_plot)

    # Data table
    st.subheader("Data Table")
    if aggregate and tps:
        table_display = agg_df.rename(columns={c: shorten_label(c) for c in numeric_cols})
    else:
        subtable = sub.copy()
        totals = subtable[numeric_cols].sum()
        totals_dict = {col: totals[col] for col in numeric_cols}
        totals_dict["Latest Qualification"] = "Total of selected items"
        table = pd.concat([subtable, pd.DataFrame([totals_dict])], ignore_index=True)
        display_cols = ["Latest Qualification", "TDV", "Training Packages"] + numeric_cols
        table_display = table[display_cols].rename(columns={c: shorten_label(c) for c in numeric_cols})
    st.dataframe(table_display)

    # Download data with metadata
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        table_display.to_excel(writer, index=False, sheet_name="Data")
        metadata = {
            "Source": f"NCVER, Apprentices and trainees – {shorten_label(latest_period)} DataBuilder, {status} by 12 month series – South Australia",
            "Training Contract Status": status,
            "Training Packages": ", ".join(tps) if tps else "None",
            "Qualifications": ", ".join(quals) if quals else "None",
            "Years": f"{start_year} to {end_year}" if years_int else "None"
        }
        md_df = pd.DataFrame(list(metadata.items()), columns=["Description", "Value"])
        md_df.to_excel(writer, index=False, sheet_name="Metadata")
    towrite.seek(0)
    file_name = f"{status.lower().replace(' ', '_')}_data_{start_year}_to_{end_year}.xlsx"
    st.download_button(
        label="📥 Download data as Excel",
        data=towrite,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
