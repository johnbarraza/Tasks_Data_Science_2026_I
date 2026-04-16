from __future__ import annotations

import pandas as pd

from .utils import normalize_code, normalize_column_name


EMERGENCY_PROXY_CATEGORIES = {
    "I-4",
    "II-1",
    "II-2",
    "II-E",
    "III-1",
    "III-2",
    "III-E",
}


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: normalize_column_name(col) for col in df.columns}
    return df.rename(columns=renamed)


def _parse_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )


def clean_ipress(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = _standardize_columns(df).copy()
    cleaned["ubigeo"] = normalize_code(cleaned["ubigeo"], width=6)
    cleaned["codigo_unico"] = normalize_code(cleaned["codigo_unico"], width=8)
    cleaned["categoria"] = cleaned["categoria"].astype(str).str.strip().str.upper()
    cleaned["estado"] = cleaned["estado"].astype(str).str.strip().str.upper()

    # In this IPRESS extract, NORTE stores longitude and ESTE stores latitude.
    cleaned["longitude"] = _parse_numeric(cleaned["norte"])
    cleaned["latitude"] = _parse_numeric(cleaned["este"])
    cleaned["latitude_missing_raw"] = cleaned["latitude"].isna()
    cleaned["longitude_missing_raw"] = cleaned["longitude"].isna()
    cleaned["coords_missing_raw"] = (
        cleaned["latitude_missing_raw"] | cleaned["longitude_missing_raw"]
    )
    cleaned["has_valid_coords"] = cleaned["latitude"].between(-20, 5) & cleaned[
        "longitude"
    ].between(-90, -60)

    cleaned["emergency_proxy"] = cleaned["categoria"].isin(EMERGENCY_PROXY_CATEGORIES)
    cleaned = cleaned.drop_duplicates(subset=["codigo_unico"], keep="first")
    return cleaned


def clean_c1(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = _standardize_columns(df).copy()
    cleaned["ubigeo"] = normalize_code(cleaned["ubigeo"], width=6)
    cleaned["co_ipress"] = normalize_code(cleaned["co_ipress"], width=8)

    cleaned["anho"] = pd.to_numeric(cleaned["anho"], errors="coerce")
    cleaned["mes"] = pd.to_numeric(cleaned["mes"], errors="coerce")

    cleaned["nro_total_atenciones_raw"] = cleaned["nro_total_atenciones"]
    cleaned["nro_total_atendidos_raw"] = cleaned["nro_total_atendidos"]

    cleaned["nro_total_atenciones"] = _parse_numeric(cleaned["nro_total_atenciones_raw"])
    cleaned["nro_total_atendidos"] = _parse_numeric(cleaned["nro_total_atendidos_raw"])

    cleaned["atenciones_missing_raw"] = cleaned["nro_total_atenciones"].isna()
    cleaned["atendidos_missing_raw"] = cleaned["nro_total_atendidos"].isna()
    cleaned["atenciones_zero_raw"] = (
        cleaned["nro_total_atenciones"].notna() & cleaned["nro_total_atenciones"].eq(0)
    )
    cleaned["atendidos_zero_raw"] = (
        cleaned["nro_total_atendidos"].notna() & cleaned["nro_total_atendidos"].eq(0)
    )

    # Keep score-ready versions without losing raw missingness information.
    cleaned["nro_total_atenciones_for_score"] = cleaned["nro_total_atenciones"].fillna(0)
    cleaned["nro_total_atendidos_for_score"] = cleaned["nro_total_atendidos"].fillna(0)
    cleaned["has_nonzero_activity"] = cleaned["nro_total_atenciones_for_score"] > 0
    return cleaned
