from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import availability_bucket, minmax_scale


def _name_agg(series: pd.Series) -> str:
    valid = series.dropna().astype(str).str.strip()
    return valid.iloc[0] if not valid.empty else ""


def build_q1_territorial_availability(
    ipress: pd.DataFrame, c1: pd.DataFrame
) -> pd.DataFrame:
    ipress_district = (
        ipress.groupby("ubigeo", as_index=False)
        .agg(
            departamento_ipress=("departamento", _name_agg),
            provincia_ipress=("provincia", _name_agg),
            distrito_ipress=("distrito", _name_agg),
            total_facilities=("codigo_unico", "nunique"),
            emergency_proxy_facilities=("emergency_proxy", "sum"),
            facilities_missing_coords=("coords_missing_raw", "sum"),
        )
        .copy()
    )

    c1_district = (
        c1.groupby("ubigeo", as_index=False)
        .agg(
            departamento_c1=("departamento", _name_agg),
            provincia_c1=("provincia", _name_agg),
            distrito_c1=("distrito", _name_agg),
            c1_rows=("ubigeo", "size"),
            total_emergency_attentions=("nro_total_atenciones_for_score", "sum"),
            total_emergency_attended=("nro_total_atendidos_for_score", "sum"),
            reporting_ipress_count=("co_ipress", "nunique"),
            atenciones_missing_rows=("atenciones_missing_raw", "sum"),
            atendidos_missing_rows=("atendidos_missing_raw", "sum"),
            atenciones_zero_rows=("atenciones_zero_raw", "sum"),
            atendidos_zero_rows=("atendidos_zero_raw", "sum"),
        )
        .copy()
    )

    district = ipress_district.merge(c1_district, on="ubigeo", how="outer")

    for col in [
        "total_facilities",
        "emergency_proxy_facilities",
        "facilities_missing_coords",
        "c1_rows",
        "total_emergency_attentions",
        "total_emergency_attended",
        "reporting_ipress_count",
        "atenciones_missing_rows",
        "atendidos_missing_rows",
        "atenciones_zero_rows",
        "atendidos_zero_rows",
    ]:
        district[col] = district[col].fillna(0)

    district["departamento"] = district["departamento_c1"].fillna(
        district["departamento_ipress"]
    )
    district["provincia"] = district["provincia_c1"].fillna(district["provincia_ipress"])
    district["distrito"] = district["distrito_c1"].fillna(district["distrito_ipress"])

    district["atenciones_missing_share"] = np.where(
        district["c1_rows"] > 0,
        district["atenciones_missing_rows"] / district["c1_rows"],
        0.0,
    )
    district["atendidos_missing_share"] = np.where(
        district["c1_rows"] > 0,
        district["atendidos_missing_rows"] / district["c1_rows"],
        0.0,
    )
    district["atenciones_zero_share"] = np.where(
        district["c1_rows"] > 0,
        district["atenciones_zero_rows"] / district["c1_rows"],
        0.0,
    )
    district["atendidos_zero_share"] = np.where(
        district["c1_rows"] > 0,
        district["atendidos_zero_rows"] / district["c1_rows"],
        0.0,
    )
    district["activity_quality_tag"] = np.select(
        [
            district["atenciones_missing_rows"].gt(0) & district["atenciones_zero_rows"].gt(0),
            district["atenciones_missing_rows"].gt(0),
            district["atenciones_zero_rows"].gt(0),
        ],
        [
            "Missing and zero activity values present",
            "Missing activity values present",
            "Zero activity values present",
        ],
        default="No missing or zero activity values",
    )

    district["facility_component"] = (
        0.60 * minmax_scale(np.log1p(district["total_facilities"]))
        + 0.40 * minmax_scale(np.log1p(district["emergency_proxy_facilities"]))
    )
    district["activity_component"] = (
        0.50 * minmax_scale(np.log1p(district["total_emergency_attentions"]))
        + 0.50 * minmax_scale(np.log1p(district["total_emergency_attended"]))
    )

    district["q1_territorial_availability_score"] = (
        0.50 * district["facility_component"] + 0.50 * district["activity_component"]
    )
    district["availability_level"] = availability_bucket(
        district["q1_territorial_availability_score"]
    )
    district["rank_best_to_worst"] = (
        district["q1_territorial_availability_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    district["rank_worst_to_best"] = (
        district["q1_territorial_availability_score"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )

    columns = [
        "ubigeo",
        "departamento",
        "provincia",
        "distrito",
        "total_facilities",
        "emergency_proxy_facilities",
        "facilities_missing_coords",
        "c1_rows",
        "reporting_ipress_count",
        "total_emergency_attentions",
        "total_emergency_attended",
        "atenciones_missing_rows",
        "atendidos_missing_rows",
        "atenciones_zero_rows",
        "atendidos_zero_rows",
        "atenciones_missing_share",
        "atendidos_missing_share",
        "atenciones_zero_share",
        "atendidos_zero_share",
        "activity_quality_tag",
        "facility_component",
        "activity_component",
        "q1_territorial_availability_score",
        "availability_level",
        "rank_best_to_worst",
        "rank_worst_to_best",
    ]
    return district[columns].sort_values("rank_best_to_worst").reset_index(drop=True)


def build_q2_settlement_access(
    center_access: pd.DataFrame, districts: pd.DataFrame
) -> pd.DataFrame:
    district_access = (
        center_access.groupby("ubigeo", as_index=False)
        .agg(
            department=("department", _name_agg),
            province=("province", _name_agg),
            district=("district", _name_agg),
            total_populated_centers=("center_id", "count"),
            matched_centers=("matched_facility", "sum"),
            mean_distance_km=("distance_km", "mean"),
            median_distance_km=("distance_km", "median"),
            p90_distance_km=("distance_km", lambda x: x.quantile(0.90)),
            max_distance_km=("distance_km", "max"),
            share_over_10km=("distance_km", lambda x: (x > 10).mean()),
            share_over_20km=("distance_km", lambda x: (x > 20).mean()),
        )
        .copy()
    )

    district_base = districts[["ubigeo", "department", "province", "district"]].drop_duplicates()
    district_access = district_base.merge(district_access, on="ubigeo", how="left", suffixes=("", "_agg"))

    district_access["department"] = district_access["department_agg"].fillna(
        district_access["department"]
    )
    district_access["province"] = district_access["province_agg"].fillna(district_access["province"])
    district_access["district"] = district_access["district_agg"].fillna(district_access["district"])
    district_access = district_access.drop(
        columns=["department_agg", "province_agg", "district_agg"],
        errors="ignore",
    )

    count_cols = ["total_populated_centers", "matched_centers"]
    for col in count_cols:
        district_access[col] = district_access[col].fillna(0)

    no_match_mask = district_access["matched_centers"].eq(0)

    metric_cols = [
        "mean_distance_km",
        "median_distance_km",
        "p90_distance_km",
        "max_distance_km",
        "share_over_10km",
        "share_over_20km",
    ]
    for col in metric_cols:
        district_access[col] = district_access[col].fillna(0)

    district_access["unmatched_centers"] = (
        district_access["total_populated_centers"] - district_access["matched_centers"]
    )
    district_access["coverage_share"] = np.where(
        district_access["total_populated_centers"] > 0,
        district_access["matched_centers"] / district_access["total_populated_centers"],
        0.0,
    )

    max_distance_proxy = district_access.loc[~no_match_mask, "median_distance_km"].max()
    if max_distance_proxy <= 0:
        max_distance_proxy = 1.0
    distance_proxy = district_access["median_distance_km"].copy()
    distance_proxy.loc[no_match_mask] = max_distance_proxy * 1.1

    district_access["distance_component"] = 1 - minmax_scale(np.log1p(distance_proxy))
    district_access["coverage_component"] = district_access["coverage_share"]
    district_access["q2_settlement_access_score"] = (
        0.65 * district_access["distance_component"]
        + 0.35 * district_access["coverage_component"]
    )
    district_access["q2_access_level"] = availability_bucket(
        district_access["q2_settlement_access_score"]
    )
    district_access["rank_best_to_worst"] = (
        district_access["q2_settlement_access_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    district_access["rank_worst_to_best"] = (
        district_access["q2_settlement_access_score"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )

    columns = [
        "ubigeo",
        "department",
        "province",
        "district",
        "total_populated_centers",
        "matched_centers",
        "unmatched_centers",
        "coverage_share",
        "mean_distance_km",
        "median_distance_km",
        "p90_distance_km",
        "max_distance_km",
        "share_over_10km",
        "share_over_20km",
        "coverage_component",
        "distance_component",
        "q2_settlement_access_score",
        "q2_access_level",
        "rank_best_to_worst",
        "rank_worst_to_best",
    ]
    return district_access[columns].sort_values("rank_best_to_worst").reset_index(drop=True)


def build_q3_q4_combined_comparison(
    q1: pd.DataFrame, q2: pd.DataFrame
) -> pd.DataFrame:
    q1_view = q1[
        [
            "ubigeo",
            "departamento",
            "provincia",
            "distrito",
            "c1_rows",
            "atenciones_missing_share",
            "atendidos_missing_share",
            "facility_component",
            "activity_component",
            "total_emergency_attentions",
            "total_emergency_attended",
            "q1_territorial_availability_score",
        ]
    ].copy()
    q2_view = q2[
        [
            "ubigeo",
            "department",
            "province",
            "district",
            "total_populated_centers",
            "matched_centers",
            "coverage_share",
            "median_distance_km",
            "coverage_component",
            "distance_component",
            "q2_settlement_access_score",
        ]
    ].copy()

    merged = q1_view.merge(
        q2_view,
        on="ubigeo",
        how="outer",
        suffixes=("_q1", "_q2"),
    )

    merged["departamento"] = merged["departamento"].fillna(merged["department"])
    merged["provincia"] = merged["provincia"].fillna(merged["province"])
    merged["distrito"] = merged["distrito"].fillna(merged["district"])
    merged = merged.drop(columns=["department", "province", "district"], errors="ignore")

    score_cols = [
        "c1_rows",
        "atenciones_missing_share",
        "atendidos_missing_share",
        "facility_component",
        "activity_component",
        "total_emergency_attentions",
        "total_emergency_attended",
        "total_populated_centers",
        "matched_centers",
        "coverage_share",
        "median_distance_km",
        "q1_territorial_availability_score",
        "coverage_component",
        "distance_component",
        "q2_settlement_access_score",
    ]
    for col in score_cols:
        merged[col] = merged[col].fillna(0.0)

    merged["q3_baseline_combined_score"] = (
        0.50 * merged["q1_territorial_availability_score"]
        + 0.50 * merged["q2_settlement_access_score"]
    )
    merged["q4_alternative_combined_score"] = (
        0.30 * merged["facility_component"]
        + 0.20 * merged["activity_component"]
        + 0.50 * merged["q2_settlement_access_score"]
    )

    merged["baseline_rank_best_to_worst"] = (
        merged["q3_baseline_combined_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    merged["alternative_rank_best_to_worst"] = (
        merged["q4_alternative_combined_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    merged["rank_shift_alt_minus_base"] = (
        merged["baseline_rank_best_to_worst"] - merged["alternative_rank_best_to_worst"]
    )
    merged["abs_rank_shift"] = merged["rank_shift_alt_minus_base"].abs()
    merged["q3_baseline_level"] = availability_bucket(merged["q3_baseline_combined_score"])
    merged["q4_alternative_level"] = availability_bucket(merged["q4_alternative_combined_score"])

    # Diagnostic tags to separate "missing-driven" low scores from observed low access.
    merged["q1_missing_dominant"] = (
        merged["atenciones_missing_share"].ge(1.0)
        & merged["atendidos_missing_share"].ge(1.0)
        & merged["total_emergency_attentions"].eq(0)
        & merged["total_emergency_attended"].eq(0)
        & merged["c1_rows"].gt(0)
    )
    merged["q1_reported_zero_activity"] = (
        merged["atenciones_missing_share"].lt(1.0)
        & merged["atendidos_missing_share"].lt(1.0)
        & merged["total_emergency_attentions"].eq(0)
        & merged["total_emergency_attended"].eq(0)
        & merged["c1_rows"].gt(0)
    )
    merged["q2_no_matched_centers"] = (
        merged["total_populated_centers"].gt(0) & merged["matched_centers"].eq(0)
    )
    merged["q2_observed_low_access"] = (
        merged["matched_centers"].gt(0) & merged["q2_settlement_access_score"].lt(0.40)
    )
    merged["q3_low_score_cause"] = np.select(
        [
            merged["q1_missing_dominant"] & merged["q2_no_matched_centers"],
            merged["q1_missing_dominant"],
            merged["q1_reported_zero_activity"],
            merged["q2_no_matched_centers"],
            merged["q2_observed_low_access"],
        ],
        [
            "Missing-dominant activity and no matched centers",
            "Missing-dominant activity",
            "Reported zero emergency activity",
            "No populated-center to emergency-facility match",
            "Observed low geospatial access",
        ],
        default="Mixed/other profile",
    )

    columns = [
        "ubigeo",
        "departamento",
        "provincia",
        "distrito",
        "c1_rows",
        "atenciones_missing_share",
        "atendidos_missing_share",
        "total_emergency_attentions",
        "total_emergency_attended",
        "total_populated_centers",
        "matched_centers",
        "coverage_share",
        "median_distance_km",
        "q1_territorial_availability_score",
        "q2_settlement_access_score",
        "q3_baseline_combined_score",
        "q4_alternative_combined_score",
        "baseline_rank_best_to_worst",
        "alternative_rank_best_to_worst",
        "rank_shift_alt_minus_base",
        "abs_rank_shift",
        "q1_missing_dominant",
        "q1_reported_zero_activity",
        "q2_no_matched_centers",
        "q2_observed_low_access",
        "q3_low_score_cause",
        "q3_baseline_level",
        "q4_alternative_level",
        "facility_component",
        "activity_component",
        "distance_component",
        "coverage_component",
    ]
    return merged[columns].sort_values("baseline_rank_best_to_worst").reset_index(drop=True)
