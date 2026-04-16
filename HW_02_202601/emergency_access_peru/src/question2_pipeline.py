from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .cleaning import clean_ipress
from .data_loader import load_ipress_raw
from .geospatial import (
    assign_points_to_districts,
    build_ipress_geodataframe,
    load_districts,
    load_populated_centers,
)
from .metrics import build_q2_settlement_access
from .visualization import plot_q2_distance_distribution, plot_q2_top_bottom_access


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"


def run_question2_pipeline() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    ipress_clean = clean_ipress(load_ipress_raw())
    districts = load_districts()
    centers = load_populated_centers()

    emergency_facilities = build_ipress_geodataframe(ipress_clean, emergency_only=True)
    emergency_facilities = assign_points_to_districts(emergency_facilities, districts)
    if "ubigeo_right" in emergency_facilities.columns:
        emergency_facilities["ubigeo"] = emergency_facilities["ubigeo_right"]
    elif "ubigeo" not in emergency_facilities.columns and "ubigeo_left" in emergency_facilities.columns:
        emergency_facilities["ubigeo"] = emergency_facilities["ubigeo_left"]
    emergency_facilities = emergency_facilities.dropna(subset=["ubigeo"]).copy()

    centers = assign_points_to_districts(centers, districts)
    centers["ubigeo"] = centers["ubigeo"].fillna(centers["ubigeo_from_code"])

    district_lookup = districts.drop_duplicates("ubigeo")[
        ["ubigeo", "department", "province", "district"]
    ].copy()
    centers = centers.drop(columns=["department", "province", "district"], errors="ignore")
    centers = centers.merge(district_lookup, on="ubigeo", how="left")
    centers = centers.dropna(subset=["ubigeo"]).copy()
    centers["center_id"] = range(1, len(centers) + 1)

    centers_3857 = centers.to_crs(epsg=3857)
    facilities_3857 = emergency_facilities.to_crs(epsg=3857)

    nearest = gpd.sjoin_nearest(
        centers_3857[
            [
                "center_id",
                "ubigeo",
                "department",
                "province",
                "district",
                "center_name",
                "center_category",
                "geometry",
            ]
        ],
        facilities_3857[["codigo_unico", "geometry"]],
        how="left",
        distance_col="distance_m",
    ).drop(columns=["index_right"], errors="ignore")

    nearest["matched_facility"] = nearest["codigo_unico"].notna()
    nearest["distance_km"] = nearest["distance_m"] / 1000
    nearest.loc[~nearest["matched_facility"], "distance_km"] = pd.NA

    center_access = pd.DataFrame(nearest.drop(columns=["geometry"]))
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
        "",
        "Top 5 districts (strongest settlement access):",
    ]
    for _, row in q2.head(5).iterrows():
        summary.append(
            f"- {row['department']} / {row['district']} "
            f"(score={row['q2_settlement_access_score']:.4f}, median_km={row['median_distance_km']:.2f})"
        )

    summary.append("")
    summary.append("Bottom 5 districts (weakest settlement access):")
    for _, row in q2.sort_values("rank_worst_to_best").head(5).iterrows():
        summary.append(
            f"- {row['department']} / {row['district']} "
            f"(score={row['q2_settlement_access_score']:.4f}, median_km={row['median_distance_km']:.2f})"
        )

    (TABLES_DIR / "q2_summary.md").write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    run_question2_pipeline()
