# modules/ui.py
# with rounded numbers
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

    # Aggregate toggle
    aggregate = False
    if tps:
        aggregate = st.sidebar.checkbox(
            "Aggregate qualifications by Training Package",
            value=False,
            key="aggregate"
        )

    # Qualification selector
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

    # Year range slider
    all_numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    years_int = sorted({int(c.split('_')[-1]) for c in all_numeric})
    if years_int:
        start_year, end_year = st.sidebar.select_slider(
            "Select Year Range",
            options=years_int,
            value=(years_int[0], years_int[-1]),
            key="year_range"
        )
    else:
        start_year, end_year = None, None

    # Only status selected: SA sheet
    if not tps and not quals:
        sa_df = pd.read_excel(dl.file_path, sheet_name="SA")
        # Determine numeric cols within range
        numeric_cols = [
            c for c in sa_df.columns
            if pd.api.types.is_numeric_dtype(sa_df[c])
            and (start_year is None or (start_year <= int(c.split('_')[-1]) <= end_year))
        ]
        latest = numeric_cols[-1] if numeric_cols else ""

        st.header(f"{status} — 12-month Data")
        st.write(
            f"NCVER, Apprentices and trainees – {shorten_label(latest)} DataBuilder, {status} by 12 month series – South Australia"
        )
        row = sa_df.loc[sa_df['Training Contract Status'] == status, numeric_cols]
        if row.empty:
            st.warning(f"No aggregated data for {status} in SA sheet.")
            return
        totals = row.squeeze()

        # Plot total series
        plot_df = pd.DataFrame(
            {status: totals.values},
            index=[shorten_label(c) for c in numeric_cols]
        )
        fig = px.line(plot_df, markers=True)
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

                        # Show total table, round to nearest 5 (retain raw zeros)
        table_display = pd.DataFrame([{
            "Latest Qualification": f"Total {status}",
            **{shorten_label(c): totals[c] for c in numeric_cols}
        }])
        num_cols = [col for col in table_display.columns if col != "Latest Qualification"]
        raw = table_display[num_cols]
        rounded = (raw / 5).round() * 5
        # Replace non-zero raw values that round to 0 with "-"
        table_display[num_cols] = rounded.where((rounded != 0) | (raw == 0), "-")
        st.subheader("Aggregated Data Table")
        st.dataframe(table_display)
        return

    # Filter data
    sub = df.copy()
    if tps:
        sub = filter_by_tp(sub, tps)
    if not aggregate and quals:
        sub = filter_by_qual(sub, quals)

    # Determine numeric cols within range
    numeric_cols = [
        c for c in sub.columns
        if pd.api.types.is_numeric_dtype(sub[c])
        and (start_year is None or (start_year <= int(c.split('_')[-1]) <= end_year))
    ]
    latest = numeric_cols[-1] if numeric_cols else ""

    # Header
    st.header(f"{status} — 12-month Data")
    st.write(
        f"NCVER, Apprentices and trainees – {shorten_label(latest)} DataBuilder, {status} by 12 month series – South Australia"
    )

    # Plot and table
    if aggregate and tps:
        agg_df = sub.groupby("Training Packages")[numeric_cols].sum().reset_index()
        df_long = agg_df.melt(
            id_vars="Training Packages", value_vars=numeric_cols,
            var_name="Period", value_name="Value"
        )
        df_long["Period"] = df_long["Period"].apply(shorten_label)
        fig = px.line(
            df_long, x="Period", y="Value", color="Training Packages",
            markers=True, title="Aggregated by Training Package"
        )
        fig.update_layout(
            legend=dict(orientation="v", x=1.02, y=1),
            margin=dict(r=200), xaxis_title=None, yaxis_title=None
        )
        st.plotly_chart(fig, use_container_width=True)

                        # Show aggregated table, round to nearest 5 (retain raw zeros)
        table_display = agg_df.rename(columns={c: shorten_label(c) for c in numeric_cols})
        num_cols = [col for col in table_display.columns if col != "Training Packages"]
        raw = table_display[num_cols]
        rounded = (raw / 5).round() * 5
        # Replace non-zero raw values that round to 0 with "-"
        table_display[num_cols] = rounded.where((rounded != 0) | (raw == 0), "-")
        st.subheader("Aggregated Data Table")
        st.dataframe(table_display)

    else:
        df_long = sub.melt(
            id_vars="Latest Qualification", value_vars=numeric_cols,
            var_name="Period", value_name="Value"
        )
        df_long["Period"] = df_long["Period"].apply(shorten_label)
        fig = px.line(
            df_long, x="Period", y="Value", color="Latest Qualification",
            markers=True, title="Qualifications over Time"
        )
        fig.update_layout(
            legend=dict(orientation="v", x=1.02, y=1),
            margin=dict(r=200), xaxis_title=None, yaxis_title=None
        )
        st.plotly_chart(fig, use_container_width=True)

                        # Show detailed table, round to nearest 5 (retain raw zeros)
        totals = sub[numeric_cols].sum()
        table = pd.concat([
            sub,
            pd.DataFrame([{
                "Latest Qualification": "Total of selected items",
                **{c: totals[c] for c in numeric_cols}
            }])
        ], ignore_index=True)
        display_cols = ["Latest Qualification", "TDV", "Training Packages"] + numeric_cols
        table_display = table[display_cols].rename(columns={c: shorten_label(c) for c in numeric_cols})
        num_cols = [col for col in table_display.columns if col not in ["Latest Qualification","TDV","Training Packages"]]
        raw = table_display[num_cols]
        rounded = (raw / 5).round() * 5
        # Replace non-zero raw values that round to 0 with "-"
        table_display[num_cols] = rounded.where((rounded != 0) | (raw == 0), "-")
        st.subheader("Data Table")
        st.dataframe(table_display)

    # Download data with metadata
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        table_display.to_excel(writer, index=False, sheet_name="Data")
        metadata = {
            "Source": f"NCVER, Apprentices and trainees – {shorten_label(latest)} DataBuilder, {status} by 12 month series – South Australia",
            "Training Contract Status": status,
            "Training Packages": ", ".join(tps) if tps else "None",
            "Qualifications": ", ".join(quals) if quals else "None",
            "Years": f"{start_year} to {end_year}" if years_int else "None"
        }
        md_df = pd.DataFrame(list(metadata.items()), columns=["Description", "Value"])
        md_df.to_excel(writer, index=False, sheet_name="Metadata")
    towrite.seek(0)
    fname = f"{status.lower().replace(' ', '_')}_data_{start_year}_to_{end_year}.xlsx"
    st.download_button(
        label="📥 Download data as Excel",
        data=towrite,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )




    # Footer disclaimer
    st.markdown(
        """
        <div style='font-size:12px; color:gray; text-align:center; padding-top:20px;'>
        This platform includes data from the National Centre for Vocational Education Research (NCVER) under a Creative Commons Attribution 3.0 Australia licence.<br>
        The views and interpretations expressed are those of the author and do not necessarily reflect the views of NCVER.<br><br>
        © NCVER and the Commonwealth of Australia. All rights reserved. Some images, logos, and visual design elements may be subject to separate copyright.<br><br>
        Numbers are rounded to the nearest 5.<br>
        Zero (0) indicates an actual value of zero, while a dash (–) represents a non-zero number rounded to zero.<br>
        For important matters, cross-check the data with NCVER DataBuilder.
        </div>
        """,
        unsafe_allow_html=True
    )
