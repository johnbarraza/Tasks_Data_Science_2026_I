from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .utils import normalize_code, normalize_column_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DISTRICTS_PATH = RAW_DIR / "District_Boundaries_of_Peru" / "DISTRITOS.shp"
CENTERS_PATH = RAW_DIR / "Populated_Centers" / "CCPP_IGN100K.shp"


def _normalize_geo_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    rename_map = {col: normalize_column_name(col) for col in gdf.columns}
    return gdf.rename(columns=rename_map)


def load_districts() -> gpd.GeoDataFrame:
    districts = gpd.read_file(DISTRICTS_PATH)
    districts = _normalize_geo_columns(districts)
    districts["ubigeo"] = normalize_code(districts["iddist"], width=6)
    districts["department"] = districts["departamen"].astype(str).str.strip().str.upper()
    districts["province"] = districts["provincia"].astype(str).str.strip().str.upper()
    districts["district"] = districts["distrito"].astype(str).str.strip().str.upper()
    if districts.crs is None:
        districts = districts.set_crs(epsg=4326, allow_override=True)
    return districts[["ubigeo", "department", "province", "district", "geometry"]].copy()


def load_populated_centers() -> gpd.GeoDataFrame:
    centers = gpd.read_file(CENTERS_PATH)
    centers = _normalize_geo_columns(centers)

    code_candidates = [
        col
        for col in centers.columns
        if "codigo" in col or col in {"c_digo", "codigo", "c_d_int"}
    ]
    if not code_candidates:
        raise ValueError("Could not find a populated-center code column for UBIGEO extraction.")
    code_col = code_candidates[0]

    centers["center_code_raw"] = centers[code_col].astype(str).str.strip()
    centers["ubigeo_from_code"] = normalize_code(centers["center_code_raw"], width=10).str[:6]
    centers["center_name"] = centers.get("nom_poblad", "").astype(str).str.strip().str.upper()
    centers["center_category"] = centers.get("categoria", "").astype(str).str.strip().str.upper()
    centers["district_name_raw"] = centers.get("dist", "").astype(str).str.strip().str.upper()
    centers["province_name_raw"] = centers.get("prov", "").astype(str).str.strip().str.upper()
    centers["department_name_raw"] = centers.get("dep", "").astype(str).str.strip().str.upper()

    if centers.crs is None:
        centers = centers.set_crs(epsg=4326, allow_override=True)

    keep_cols = [
        "center_code_raw",
        "ubigeo_from_code",
        "center_name",
        "center_category",
        "district_name_raw",
        "province_name_raw",
        "department_name_raw",
        "geometry",
    ]
    return centers[keep_cols].copy()


def build_ipress_geodataframe(
    ipress_df: pd.DataFrame, emergency_only: bool = True
) -> gpd.GeoDataFrame:
    facilities = ipress_df.copy()
    if emergency_only:
        facilities = facilities[facilities["emergency_proxy"]].copy()

    facilities = facilities[facilities["has_valid_coords"]].copy()
    facilities = facilities.dropna(subset=["longitude", "latitude"])

    gdf = gpd.GeoDataFrame(
        facilities,
        geometry=gpd.points_from_xy(facilities["longitude"], facilities["latitude"]),
        crs="EPSG:4326",
    )
    return gdf


def assign_points_to_districts(
    points: gpd.GeoDataFrame, districts: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    join_cols = ["ubigeo", "department", "province", "district", "geometry"]
    district_view = districts[join_cols].copy()

    assigned = gpd.sjoin(
        points,
        district_view,
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")
    return assigned


def compute_nearest_distances(
    centers: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame,
    distance_col: str = "distance_m",
) -> gpd.GeoDataFrame:
    """Nearest straight-line distance from each center to the closest facility.

    Both inputs must already be in the same projected metric CRS (e.g. EPSG:32718).
    Returns centers with distance_col and 'codigo_unico' columns added.
    """
    result = gpd.sjoin_nearest(
        centers,
        facilities[["codigo_unico", "geometry"]],
        how="left",
        distance_col=distance_col,
    ).drop(columns=["index_right"], errors="ignore")
    return result
