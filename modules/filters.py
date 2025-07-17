import pandas as pd

def filter_by_tp(df: pd.DataFrame, tps: list[str]) -> pd.DataFrame:
    if not tps:
        return df
    return df[df["Training Packages"].isin(tps)]

def filter_by_qual(df: pd.DataFrame, quals: list[str]) -> pd.DataFrame:
    if not quals:
        return df
    return df[df["Latest Qualification"].isin(quals)]

def available_quals(df: pd.DataFrame, selected_tps: list[str]) -> list[str]:
    if not selected_tps:
        return sorted(df["Latest Qualification"].unique())
    sub = df[df["Training Packages"].isin(selected_tps)]
    return sorted(sub["Latest Qualification"].unique())
