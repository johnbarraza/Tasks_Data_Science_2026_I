from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize_column_name(name: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", str(name))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def normalize_code(series: pd.Series, width: int) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
    )
    return cleaned.str.zfill(width)


def percentile_rank(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    return series.rank(pct=True, method="average")


def minmax_scale(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    min_val = series.min()
    max_val = series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)


def availability_bucket(score: pd.Series) -> pd.Series:
    labels = [
        "Very low availability",
        "Low availability",
        "Medium availability",
        "High availability",
        "Very high availability",
    ]
    pct = score.rank(pct=True, method="average")
    bins = [-0.01, 0.2, 0.4, 0.6, 0.8, 1.0]
    return pd.cut(pct, bins=bins, labels=labels, include_lowest=True)
