from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .cleaning import clean_ipress
from .data_loader import load_ipress_raw
from .geospatial import (
    assign_points_to_districts,
    build_ipress_geodataframe,
    compute_nearest_distances,
    load_districts,
    load_populated_centers,
)
from .metrics import build_q2_settlement_access
from .visualization import plot_q2_distance_distribution, plot_q2_top_bottom_access


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"


def prepare_populated_centers(districts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    centers = load_populated_centers()
    centers = assign_points_to_districts(centers, districts)
    centers["ubigeo"] = centers["ubigeo"].fillna(centers["ubigeo_from_code"])

    district_lookup = districts.drop_duplicates("ubigeo")[
        ["ubigeo", "department", "province", "district"]
    ].copy()
    centers = centers.drop(columns=["department", "province", "district"], errors="ignore")
    centers = centers.merge(district_lookup, on="ubigeo", how="left")
    centers = centers.dropna(subset=["ubigeo"]).copy()
    centers["center_id"] = range(1, len(centers) + 1)
    return centers


def prepare_facilities_for_distance(
    facilities: gpd.GeoDataFrame, districts: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    facilities = assign_points_to_districts(facilities, districts)
    if "ubigeo_right" in facilities.columns:
        facilities["ubigeo"] = facilities["ubigeo_right"]
    elif "ubigeo" not in facilities.columns and "ubigeo_left" in facilities.columns:
        facilities["ubigeo"] = facilities["ubigeo_left"]
    facilities = facilities.dropna(subset=["ubigeo"]).copy()
    return facilities


def compute_center_access_to_facilities(
    centers: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame,
) -> pd.DataFrame:
    center_cols = [
        "center_id",
        "ubigeo",
        "department",
        "province",
        "district",
        "center_name",
        "center_category",
        "geometry",
    ]

    if facilities.empty:
        center_access = pd.DataFrame(centers.drop(columns=["geometry"]))
        center_access["codigo_unico"] = pd.NA
        center_access["matched_facility"] = False
        center_access["distance_m"] = pd.NA
        center_access["distance_km"] = pd.NA
        return center_access

    centers_proj = centers.to_crs(epsg=32718)
    facilities_proj = facilities.to_crs(epsg=32718)

    nearest = compute_nearest_distances(
        centers_proj[center_cols],
        facilities_proj,
        distance_col="distance_m",
    )

    nearest["matched_facility"] = nearest["codigo_unico"].notna()
    nearest["distance_km"] = nearest["distance_m"] / 1000
    nearest.loc[~nearest["matched_facility"], "distance_km"] = pd.NA
    return pd.DataFrame(nearest.drop(columns=["geometry"]))


def build_observed_activity_facility_set(
    ipress_clean: pd.DataFrame,
    c1_clean: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Facilities with observed C1 emergency activity and valid coordinates."""
    c1_agg = (
        c1_clean.groupby("co_ipress", as_index=False)
        .agg(total_observed_emergency_attentions=("nro_total_atenciones_for_score", "sum"))
    )

    merged = ipress_clean.merge(
        c1_agg,
        left_on="codigo_unico",
        right_on="co_ipress",
        how="left",
    )
    merged["total_observed_emergency_attentions"] = merged[
        "total_observed_emergency_attentions"
    ].fillna(0)

    observed = merged[merged["total_observed_emergency_attentions"] > 0].copy()
    total_observed = len(observed)
    with_coords = int(observed["has_valid_coords"].sum())
    share_with_coords = with_coords / max(total_observed, 1)
    print(
        "[Q4 diagnostic] C1-observed facilities: "
        f"{total_observed} total, {with_coords} with valid coords "
        f"({share_with_coords:.1%})"
    )

    observed_with_coords = observed[observed["has_valid_coords"]].copy()
    return gpd.GeoDataFrame(
        observed_with_coords,
        geometry=gpd.points_from_xy(
            observed_with_coords["longitude"],
            observed_with_coords["latitude"],
        ),
        crs="EPSG:4326",
    )


def run_question2_pipeline() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    ipress_clean = clean_ipress(load_ipress_raw())
    districts = load_districts()
    centers = prepare_populated_centers(districts)

    emergency_facilities = build_ipress_geodataframe(ipress_clean, emergency_only=True)
    emergency_facilities = prepare_facilities_for_distance(emergency_facilities, districts)
    center_access = compute_center_access_to_facilities(centers, emergency_facilities)
    center_access.to_csv(
        PROCESSED_DIR / "q2_center_access.csv",
        index=False,
        encoding="utf-8",
    )

    q2 = build_q2_settlement_access(center_access, districts)
    q2.to_csv(TABLES_DIR / "q2_settlement_access.csv", index=False, encoding="utf-8")
    q2.head(20).to_csv(TABLES_DIR / "q2_top20_best_access.csv", index=False, encoding="utf-8")
    q2.sort_values("rank_worst_to_best").head(20).to_csv(
        TABLES_DIR / "q2_top20_weak_access.csv",
        index=False,
        encoding="utf-8",
    )

    plot_q2_top_bottom_access(q2, FIGURES_DIR / "q2_top_bottom_access.png")
    plot_q2_distance_distribution(q2, FIGURES_DIR / "q2_distance_distribution.png")

    summary = [
        "# Question 2 Summary",
        "",
        "This file was generated from the Q2 settlement access pipeline.",
        f"Districts evaluated: {len(q2)}",
        f"Populated centers analyzed: {len(center_access)}",
        f"Emergency-related facilities with valid coordinates: {len(emergency_facilities)}",
        "Distance CRS: EPSG:32718 (UTM zone 18S, metric). Peru spans zones 17S-19S; "
        "distances are proximity proxies, not travel times.",
        "",
        "Top 5 districts (strongest settlement access):",
    ]
    for _, row in q2.head(5).iterrows():
        summary.append(
            f"- {row['department']} / {row['district']} "
            f"(score={row['q2_settlement_access_score']:.4f}, "
            f"median_km={row['median_distance_km']:.2f}, "
            f"centers={int(row['total_populated_centers'])})"
        )

    summary.append("")
    summary.append("Bottom 5 districts (weakest settlement access):")
    for _, row in q2.sort_values("rank_worst_to_best").head(5).iterrows():
        summary.append(
            f"- {row['department']} / {row['district']} "
            f"(score={row['q2_settlement_access_score']:.4f}, "
            f"median_km={row['median_distance_km']:.2f}, "
            f"centers={int(row['total_populated_centers'])})"
        )

    (TABLES_DIR / "q2_summary.md").write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    run_question2_pipeline()
