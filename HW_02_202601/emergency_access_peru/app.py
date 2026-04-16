from __future__ import annotations

from pathlib import Path
import inspect

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from branca.colormap import linear

from src.question1_pipeline import run_question1_pipeline
from src.question2_pipeline import run_question2_pipeline
from src.question3_4_pipeline import run_question3_4_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent
TABLES_DIR = PROJECT_ROOT / "output" / "tables"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"

Q1_TABLE = TABLES_DIR / "q1_territorial_availability.csv"
Q1_QUALITY_TABLE = TABLES_DIR / "q1_data_quality_by_district.csv"
Q1_FIG_TOP_BOTTOM = FIGURES_DIR / "q1_top_bottom_districts.png"
Q1_FIG_SCATTER = FIGURES_DIR / "q1_facilities_vs_activity_scatter.png"
Q1_FIG_QUALITY = FIGURES_DIR / "q1_data_quality_footprint.png"
Q2_TABLE = TABLES_DIR / "q2_settlement_access.csv"
Q2_FIG_TOP_BOTTOM = FIGURES_DIR / "q2_top_bottom_access.png"
Q2_FIG_DIST = FIGURES_DIR / "q2_distance_distribution.png"
Q34_TABLE = TABLES_DIR / "q3_q4_combined_comparison.csv"
Q34_FIG_TOP_BOTTOM = FIGURES_DIR / "q3_top_bottom_combined.png"
Q34_FIG_SHIFT = FIGURES_DIR / "q4_rank_shift_distribution.png"
DISTRICTS_SHP = PROJECT_ROOT / "data" / "raw" / "District_Boundaries_of_Peru" / "DISTRITOS.shp"


def _normalize_ubigeo(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(6)
    )


def _q1_missing_only_mask(df: pd.DataFrame) -> pd.Series:
    needed = {
        "atenciones_missing_share",
        "atendidos_missing_share",
        "total_emergency_attentions",
        "total_emergency_attended",
    }
    if not needed.issubset(df.columns):
        return pd.Series(False, index=df.index)
    return (
        df["atenciones_missing_share"].ge(1.0)
        & df["atendidos_missing_share"].ge(1.0)
        & df["total_emergency_attentions"].eq(0)
        & df["total_emergency_attended"].eq(0)
    )


@st.cache_data(show_spinner=False)
def load_q1_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not Q1_TABLE.exists():
        return pd.DataFrame(), pd.DataFrame()
    q1 = pd.read_csv(Q1_TABLE)
    quality = pd.read_csv(Q1_QUALITY_TABLE) if Q1_QUALITY_TABLE.exists() else q1.copy()
    if "ubigeo" in q1.columns:
        q1["ubigeo"] = _normalize_ubigeo(q1["ubigeo"])
    if "ubigeo" in quality.columns:
        quality["ubigeo"] = _normalize_ubigeo(quality["ubigeo"])
    return q1, quality


@st.cache_data(show_spinner=False)
def load_q2_data() -> pd.DataFrame:
    if not Q2_TABLE.exists():
        return pd.DataFrame()
    q2 = pd.read_csv(Q2_TABLE)
    if "ubigeo" in q2.columns:
        q2["ubigeo"] = _normalize_ubigeo(q2["ubigeo"])
    return q2


@st.cache_data(show_spinner=False)
def load_q34_data() -> pd.DataFrame:
    if not Q34_TABLE.exists():
        return pd.DataFrame()
    q34 = pd.read_csv(Q34_TABLE)
    if "ubigeo" in q34.columns:
        q34["ubigeo"] = _normalize_ubigeo(q34["ubigeo"])
    return q34


@st.cache_data(show_spinner=False)
def load_district_shapes() -> gpd.GeoDataFrame:
    if not DISTRICTS_SHP.exists():
        return gpd.GeoDataFrame()
    districts = gpd.read_file(DISTRICTS_SHP)
    districts.columns = (
        districts.columns.str.lower().str.strip().str.replace(r"[^a-z0-9]+", "_", regex=True)
    )
    if "iddist" not in districts.columns:
        return gpd.GeoDataFrame()
    districts["ubigeo"] = _normalize_ubigeo(districts["iddist"])
    if districts.crs is None:
        districts = districts.set_crs(epsg=4326, allow_override=True)
    else:
        districts = districts.to_crs(epsg=4326)
    return districts[["ubigeo", "geometry"]].drop_duplicates("ubigeo").copy()


def build_comparison_map_html(
    districts: gpd.GeoDataFrame,
    q34_df: pd.DataFrame,
    metric_col: str,
    tooltip_label: str,
    selected_departamento: str,
) -> str:
    metric_data = q34_df.copy()
    metric_data["ubigeo"] = _normalize_ubigeo(metric_data["ubigeo"])
    districts = districts.copy()
    districts["ubigeo"] = _normalize_ubigeo(districts["ubigeo"])
    if selected_departamento != "All departments":
        metric_data = metric_data[metric_data["departamento"] == selected_departamento].copy()
    merged = districts.merge(metric_data, on="ubigeo", how="inner")
    if merged.empty:
        return ""

    center = merged.geometry.union_all().centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=6, tiles="CartoDB positron")

    min_val = float(merged[metric_col].min())
    max_val = float(merged[metric_col].max())
    if min_val == max_val:
        max_val = min_val + 1e-6
    cmap = linear.YlOrRd_09.scale(min_val, max_val)
    cmap.caption = tooltip_label

    folium.GeoJson(
        merged,
        style_function=lambda feature: {
            "fillColor": cmap(feature["properties"][metric_col]),
            "color": "#5c5c5c",
            "weight": 0.3,
            "fillOpacity": 0.72,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "departamento",
                "provincia",
                "distrito",
                metric_col,
                "baseline_rank_best_to_worst",
                "alternative_rank_best_to_worst",
                "rank_shift_alt_minus_base",
            ],
            aliases=[
                "Departamento",
                "Provincia",
                "Distrito",
                tooltip_label,
                "Rank baseline",
                "Rank alternativo",
                "Shift rank (alt-base)",
            ],
            localize=True,
        ),
    ).add_to(m)
    cmap.add_to(m)
    return m.get_root().render()


def _show_image_if_exists(path: Path, caption: str) -> None:
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"Missing figure: `{path.name}`. Run the Q1 pipeline first.")


def _q1_figure_paths(omit_missing_q1: bool) -> tuple[Path, Path, Path]:
    suffix = "omitting_missing" if omit_missing_q1 else "including_missing"
    top_bottom = FIGURES_DIR / f"q1_top_bottom_districts_{suffix}.png"
    scatter = FIGURES_DIR / f"q1_facilities_vs_activity_scatter_{suffix}.png"
    quality = FIGURES_DIR / f"q1_data_quality_footprint_{suffix}.png"
    # Fallback to legacy names if mode-specific files are not available yet.
    if not top_bottom.exists():
        top_bottom = Q1_FIG_TOP_BOTTOM
    if not scatter.exists():
        scatter = Q1_FIG_SCATTER
    if not quality.exists():
        quality = Q1_FIG_QUALITY
    return top_bottom, scatter, quality


def _run_q1_pipeline_with_mode(omit_missing_q1: bool) -> str:
    # Streamlit can keep stale module objects during hot-reload. This guards both signatures.
    params = inspect.signature(run_question1_pipeline).parameters
    if "omit_missing_only" in params:
        run_question1_pipeline(omit_missing_only=omit_missing_q1)
        return "mode_supported"
    run_question1_pipeline()
    return "legacy_signature"


st.set_page_config(page_title="Emergency Healthcare Access in Peru", layout="wide")
st.title("Emergency Healthcare Access Inequality in Peru")
st.caption("Homework 2 - District-level emergency access analytics")

with st.sidebar:
    st.header("Pipeline Controls")
    st.write("Use these buttons to refresh outputs from source files.")
    omit_missing_q1 = st.toggle(
        "Omit missing-only districts in Q1",
        value=False,
        help=(
            "If True, Q1 charts/tables exclude districts where emergency activity is "
            "100% missing (both attentions and attended)."
        ),
    )
    st.caption(f"Omit missing-only Q1: `{omit_missing_q1}`")
    if st.button("Run Q1 pipeline", type="primary", width="stretch"):
        with st.spinner("Running question 1 pipeline..."):
            q1_run_mode = _run_q1_pipeline_with_mode(omit_missing_q1)
            load_q1_data.clear()
        if q1_run_mode == "legacy_signature":
            st.warning(
                "Q1 pipeline ran with legacy signature (without omit_missing_only parameter). "
                "If this persists, restart Streamlit."
            )
        else:
            st.success("Q1 pipeline finished and outputs were refreshed.")
    if st.button("Run Q2 pipeline", width="stretch"):
        with st.spinner("Running question 2 pipeline..."):
            run_question2_pipeline()
            load_q2_data.clear()
        st.success("Q2 pipeline finished and outputs were refreshed.")
    if st.button("Run Q3 + Q4 pipeline", width="stretch"):
        with st.spinner("Running question 3/4 pipeline..."):
            run_question3_4_pipeline()
            load_q34_data.clear()
        st.success("Q3/Q4 pipeline finished and outputs were refreshed.")

q1_df, quality_df = load_q1_data()
q2_df = load_q2_data()
q34_df = load_q34_data()
district_shapes = load_district_shapes()
q1_missing_only_mask = _q1_missing_only_mask(q1_df) if not q1_df.empty else pd.Series(dtype=bool)
q1_view = q1_df[~q1_missing_only_mask].copy() if (omit_missing_q1 and not q1_df.empty) else q1_df.copy()
quality_view = (
    quality_df[~_q1_missing_only_mask(quality_df)].copy()
    if (omit_missing_q1 and not quality_df.empty)
    else quality_df.copy()
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Tab 1 - Data & Methodology",
        "Tab 2 - Static Analysis",
        "Tab 3 - GeoSpatial Results",
        "Tab 4 - Interactive Exploration",
    ]
)

with tab1:
    st.subheader("Problem Statement")
    st.write(
        "This project evaluates inequality in emergency healthcare access at district level "
        "in Peru by combining facility availability and emergency care activity."
    )

    st.subheader("Data Sources")
    st.markdown(
        "- MINSA IPRESS facilities (`IPRESS.csv`)\n"
        "- SUSALUD emergency production (`ConsultaC1_2026_v4.csv`)\n"
        "- Populated centers (`CCPP_IGN100K.shp`)\n"
        "- District boundaries (`DISTRITOS.shp`)"
    )

    st.subheader("Current Methodology Status")
    st.markdown(
        "- Question 1 is implemented with a **hybrid territorial availability score**.\n"
        "- Missing and zero values are **kept**, mapped, and reported by district.\n"
        "- Question 2 is implemented with nearest-facility geospatial access.\n"
        "- Questions 3 and 4 compare baseline vs alternative weighting and rank shifts."
    )

    st.subheader("Limitations")
    st.markdown(
        "- Some emergency activity rows include non-numeric placeholders; they are tracked as missing.\n"
        "- District shapefile attributes are incomplete in current raw files and need validation."
    )

with tab2:
    st.subheader("Question 1 - Territorial Availability")
    if q1_view.empty:
        st.warning("No Q1 output found yet. Run the pipeline from the sidebar.")
    else:
        q1_fig_top_bottom, q1_fig_scatter, q1_fig_quality = _q1_figure_paths(omit_missing_q1)
        if omit_missing_q1:
            st.info(
                f"Q1 filtered view active: {int((~q1_missing_only_mask).sum()):,} districts shown, "
                f"{int(q1_missing_only_mask.sum()):,} missing-only districts omitted."
            )
        c1, c2, c3 = st.columns(3)
        c1.metric("Districts", f"{len(q1_view):,}")
        c2.metric(
            "Districts with missing activity rows",
            f"{int((q1_view['atenciones_missing_rows'] > 0).sum()):,}",
        )
        c3.metric(
            "Districts with zero activity rows",
            f"{int((q1_view['atenciones_zero_rows'] > 0).sum()):,}",
        )

        st.markdown(
            "The score combines facility footprint and emergency activity components. "
            "Higher values indicate stronger territorial availability."
        )

        _show_image_if_exists(
            q1_fig_top_bottom,
            "Top and bottom districts by territorial availability score",
        )
        _show_image_if_exists(
            q1_fig_scatter,
            "Facilities vs emergency activity at district level",
        )
        _show_image_if_exists(
            q1_fig_quality,
            "Data quality footprint: missing and zero shares",
        )

        st.markdown("---")
        st.subheader("Question 2 - Settlement Access")
        if q2_df.empty:
            st.info("No Q2 output found yet. Run the Q2 pipeline from the sidebar.")
        else:
            s1, s2, s3 = st.columns(3)
            s1.metric("Q2 districts", f"{len(q2_df):,}")
            s2.metric("Avg median distance (km)", f"{q2_df['median_distance_km'].mean():.2f}")
            s3.metric("Avg coverage share", f"{q2_df['coverage_share'].mean():.3f}")

            _show_image_if_exists(
                Q2_FIG_TOP_BOTTOM,
                "Top and bottom districts by settlement access score",
            )
        _show_image_if_exists(
            Q2_FIG_DIST,
            "Distribution of district median distance to nearest emergency facility",
        )

        st.markdown("---")
        st.subheader("Questions 3 & 4 - Combined Score and Sensitivity")
        if q34_df.empty:
            st.info("No Q3/Q4 output found yet. Run the Q3 + Q4 pipeline from the sidebar.")
        else:
            t1, t2, t3 = st.columns(3)
            t1.metric("Q3/Q4 districts", f"{len(q34_df):,}")
            t2.metric("Mean abs rank shift", f"{q34_df['abs_rank_shift'].mean():.2f}")
            t3.metric("Max abs rank shift", f"{int(q34_df['abs_rank_shift'].max())}")

            _show_image_if_exists(
                Q34_FIG_TOP_BOTTOM,
                "Top and bottom districts by baseline combined score (Q3)",
            )
            _show_image_if_exists(
                Q34_FIG_SHIFT,
                "Sensitivity analysis: distribution of rank shifts (Q4)",
            )

with tab3:
    st.subheader("District-level Results Tables")
    if q1_view.empty:
        st.warning("No Q1 output found yet. Run the pipeline from the sidebar.")
    else:
        if omit_missing_q1:
            st.info(
                f"Q1 tables filtered: {int((~q1_missing_only_mask).sum()):,} shown / "
                f"{int(q1_missing_only_mask.sum()):,} omitted (missing-only)."
            )
        departments = sorted(q1_view["departamento"].dropna().unique().tolist())
        selected_dep = st.selectbox(
            "Filter by department",
            options=["All departments"] + departments,
            index=0,
        )
        filtered = (
            q1_view
            if selected_dep == "All departments"
            else q1_view[q1_view["departamento"] == selected_dep]
        )

        st.write("Top districts by territorial availability")
        st.dataframe(
            filtered[
                [
                    "rank_best_to_worst",
                    "ubigeo",
                    "departamento",
                    "provincia",
                    "distrito",
                    "total_facilities",
                    "total_emergency_attentions",
                    "q1_territorial_availability_score",
                    "availability_level",
                ]
            ].sort_values("rank_best_to_worst"),
            width="stretch",
            hide_index=True,
        )

        st.write("District quality mapping (missing and zero activity)")
        st.dataframe(
            quality_view[
                [
                    "ubigeo",
                    "departamento",
                    "distrito",
                    "c1_rows",
                    "atenciones_missing_rows",
                    "atenciones_zero_rows",
                    "atenciones_missing_share",
                    "atenciones_zero_share",
                    "activity_quality_tag",
                ]
            ].sort_values(["atenciones_missing_rows", "atenciones_zero_rows"], ascending=False),
            width="stretch",
            hide_index=True,
        )

        st.write("Question 2 district access table")
        if q2_df.empty:
            st.info("No Q2 output found yet. Run the Q2 pipeline from the sidebar.")
        else:
            st.dataframe(
                q2_df[
                    [
                        "rank_best_to_worst",
                        "ubigeo",
                        "department",
                        "province",
                        "district",
                        "median_distance_km",
                        "coverage_share",
                        "share_over_20km",
                        "q2_settlement_access_score",
                        "q2_access_level",
                    ]
                ].sort_values("rank_best_to_worst"),
                width="stretch",
                hide_index=True,
            )

        st.write("Questions 3/4 combined comparison table")
        if q34_df.empty:
            st.info("No Q3/Q4 output found yet. Run the Q3 + Q4 pipeline from the sidebar.")
        else:
            st.dataframe(
                q34_df[
                    [
                        "baseline_rank_best_to_worst",
                        "alternative_rank_best_to_worst",
                        "rank_shift_alt_minus_base",
                        "ubigeo",
                        "departamento",
                        "provincia",
                        "distrito",
                        "q3_baseline_combined_score",
                        "q4_alternative_combined_score",
                        "q1_territorial_availability_score",
                        "q2_settlement_access_score",
                        "q3_low_score_cause",
                    ]
                ].sort_values("baseline_rank_best_to_worst"),
                width="stretch",
                hide_index=True,
            )

with tab4:
    st.subheader("Interactive Exploration")
    if q34_df.empty:
        st.info("Run Q3 + Q4 pipeline to enable interactive map exploration.")
    elif district_shapes.empty:
        st.warning("District shapefile could not be loaded for mapping.")
    else:
        c1, c2 = st.columns([2, 2])
        with c1:
            metric_option = st.selectbox(
                "Map metric",
                options=[
                    ("q3_baseline_combined_score", "Q3 baseline combined score"),
                    ("q4_alternative_combined_score", "Q4 alternative combined score"),
                    ("rank_shift_alt_minus_base", "Q4 rank shift (alt-base)"),
                    ("q1_territorial_availability_score", "Q1 territorial score"),
                    ("q2_settlement_access_score", "Q2 settlement access score"),
                ],
                format_func=lambda x: x[1],
            )
        with c2:
            departments = sorted(q34_df["departamento"].dropna().unique().tolist())
            selected_dep = st.selectbox(
                "Filter map by department",
                options=["All departments"] + departments,
                index=0,
            )

        map_html = build_comparison_map_html(
            districts=district_shapes,
            q34_df=q34_df,
            metric_col=metric_option[0],
            tooltip_label=metric_option[1],
            selected_departamento=selected_dep,
        )
        if map_html:
            components.html(map_html, height=680, scrolling=False)
        else:
            st.warning("No district geometry matched the selected filter.")
