from __future__ import annotations

from pathlib import Path

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
Q2_TABLE = TABLES_DIR / "q2_settlement_access.csv"
Q34_TABLE = TABLES_DIR / "q3_q4_combined_comparison.csv"

Q1_FIG_TOP_BOTTOM = FIGURES_DIR / "q1_top_bottom_districts.png"
Q1_FIG_SCATTER = FIGURES_DIR / "q1_facilities_vs_activity_scatter.png"
Q1_FIG_QUALITY = FIGURES_DIR / "q1_data_quality_footprint.png"
Q1_FIG_CHOROPLETH = FIGURES_DIR / "q1_choropleth_score.png"
Q2_FIG_TOP_BOTTOM = FIGURES_DIR / "q2_top_bottom_access.png"
Q2_FIG_DIST = FIGURES_DIR / "q2_distance_distribution.png"
Q34_FIG_TOP_BOTTOM = FIGURES_DIR / "q3_top_bottom_combined.png"
Q34_FIG_SENSITIVITY = FIGURES_DIR / "q4_sensitivity_scatter.png"
Q34_FIG_SHIFT = FIGURES_DIR / "q4_rank_shift_distribution.png"
Q34_FIG_CHOROPLETH = FIGURES_DIR / "q3_q4_choropleth_comparison.png"
DISTRICTS_SHP = PROJECT_ROOT / "data" / "raw" / "District_Boundaries_of_Peru" / "DISTRITOS.shp"


def _normalize_ubigeo(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(6)
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


def build_folium_map(
    districts: gpd.GeoDataFrame,
    q34_df: pd.DataFrame,
    metric_col: str,
    tooltip_label: str,
    dept_filter: str,
) -> str:
    data = q34_df.copy()
    data["ubigeo"] = _normalize_ubigeo(data["ubigeo"])
    gdf = districts.copy()
    gdf["ubigeo"] = _normalize_ubigeo(gdf["ubigeo"])
    if dept_filter != "All":
        data = data[data["departamento"] == dept_filter].copy()
    merged = gdf.merge(data, on="ubigeo", how="inner")
    if merged.empty:
        return ""
    center = merged.geometry.union_all().centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=6, tiles="CartoDB positron")
    vmin, vmax = float(merged[metric_col].min()), float(merged[metric_col].max())
    if vmin == vmax:
        vmax = vmin + 1e-6
    cmap = linear.RdYlGn_09.scale(vmin, vmax)
    cmap.caption = tooltip_label
    folium.GeoJson(
        merged,
        style_function=lambda f: {
            "fillColor": cmap(f["properties"][metric_col]),
            "color": "#444",
            "weight": 0.3,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "departamento", "provincia", "distrito",
                metric_col,
                "baseline_rank_best_to_worst",
                "alternative_rank_best_to_worst",
                "rank_shift_alt_minus_base",
                "q3_low_score_cause",
            ],
            aliases=[
                "Departamento", "Provincia", "Distrito",
                tooltip_label,
                "Rank baseline",
                "Rank alternativo",
                "Shift rank",
                "Low-score cause",
            ],
        ),
    ).add_to(m)
    cmap.add_to(m)
    return m.get_root().render()


def _img(path: Path, caption: str, why: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
        if why:
            st.caption(f"**Why this chart:** {why}")
    else:
        st.info(f"Figure not generated yet: `{path.name}` — run the pipeline from the sidebar.")


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Emergency Healthcare Access in Peru",
    page_icon="🏥",
    layout="wide",
)
st.title("Emergency Healthcare Access Inequality in Peru")
st.caption("District-level geospatial analytics pipeline · Python / Data Science HW2")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Pipeline Controls")
    st.markdown("Run pipelines to generate or refresh all outputs from source data.")
    if st.button("▶ Run Q1 pipeline", type="primary", use_container_width=True):
        with st.spinner("Running Q1 pipeline…"):
            run_question1_pipeline()
            load_q1_data.clear()
        st.success("Q1 done.")
    if st.button("▶ Run Q2 pipeline", use_container_width=True):
        with st.spinner("Running Q2 pipeline…"):
            run_question2_pipeline()
            load_q2_data.clear()
        st.success("Q2 done.")
    if st.button("▶ Run Q3 + Q4 pipeline", use_container_width=True):
        with st.spinner("Running Q3/Q4 pipeline…"):
            run_question3_4_pipeline()
            load_q34_data.clear()
        st.success("Q3/Q4 done.")
    st.divider()
    st.caption("All outputs are saved to `output/figures/` and `output/tables/`.")

# ── Load data ──────────────────────────────────────────────────────────────────
q1_df, quality_df = load_q1_data()
q2_df = load_q2_data()
q34_df = load_q34_data()
district_shapes = load_district_shapes()

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Tab 1 — Data & Methodology",
    "📊 Tab 2 — Static Analysis",
    "🗺️ Tab 3 — GeoSpatial Results",
    "🔍 Tab 4 — Interactive Exploration",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DATA & METHODOLOGY
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Problem Statement")
    st.markdown(
        """
        **Which districts in Peru appear relatively better or worse served in emergency
        healthcare access, and what evidence supports that conclusion?**

        This project builds a district-level geospatial analytics pipeline combining
        health facility data, emergency care production records, populated-center locations,
        and district boundaries to construct and compare analytical access measures across
        Peru's ~1,874 districts.
        """
    )

    st.subheader("Datasets Used")
    st.markdown(
        """
        | Dataset | Source | Key variables used |
        |---|---|---|
        | IPRESS health facilities | MINSA / datosabiertos.gob.pe | Facility category, coordinates (NORTE/ESTE), UBIGEO |
        | Emergency production (C1) | SUSALUD / datos.susalud.gob.pe | Emergency attentions, attended, UBIGEO, IPRESS code |
        | Populated centers | IGN / datosabiertos.gob.pe | Point geometry, UBIGEO code |
        | District boundaries | d2cml-ai / GitHub | Polygon geometry, UBIGEO (IDDIST) |
        """
    )

    st.subheader("Data Cleaning Decisions")
    with st.expander("See full cleaning summary"):
        st.markdown(
            """
            **IPRESS coordinates**: The source file stores longitude in the `NORTE` column and
            latitude in `ESTE` — the labels are swapped. The pipeline corrects this before building
            geometries. Coordinate validity is checked against Peru's bounding box
            (lat −20 to +5, lon −90 to −60).

            **Emergency activity (C1)**: Missing and zero values are **kept**, not dropped.
            Each district is tagged with the share of missing and zero rows so analysts can
            distinguish data-quality-limited scores from genuinely low-activity districts.
            Score columns use `fillna(0)` to avoid propagating NaN through arithmetic.

            **Duplicate facilities**: Deduplicated by `codigo_unico` (unique facility code),
            keeping the first occurrence.

            **CRS handling**: All geometries stored in EPSG:4326 (WGS84) for compatibility
            with Folium. Distance calculations use EPSG:3857 (Web Mercator projected) to obtain
            metric distances in kilometres via `sjoin_nearest`.

            **Emergency-proxy categories**: Only facilities with category I-4, II-1, II-2,
            II-E, III-1, III-2, or III-E are considered emergency-capable. This subset is
            used for Q2 distance analysis and as a weighted component in Q1.
            """
        )

    st.subheader("Metric Construction")
    with st.expander("Q1 — Territorial Availability Score"):
        st.markdown(
            r"""
            Measures facility footprint and emergency activity at district level.

            $$\text{facility\_component} = 0.6 \cdot \text{minmax}(\log(1+\text{facilities}))
            + 0.4 \cdot \text{minmax}(\log(1+\text{emergency\_proxy\_facilities}))$$

            $$\text{activity\_component} = 0.5 \cdot \text{minmax}(\log(1+\text{atenciones}))
            + 0.5 \cdot \text{minmax}(\log(1+\text{atendidos}))$$

            $$Q1 = 0.5 \cdot \text{facility\_component} + 0.5 \cdot \text{activity\_component}$$

            Log-scaling handles the extreme right skew (Lima has 600+ facilities; most districts
            have 1–5). Min-max normalization maps all components to [0, 1].
            """
        )
    with st.expander("Q2 — Settlement Access Score"):
        st.markdown(
            r"""
            Measures how close populated centers are to the nearest emergency-capable facility.

            For each populated center: straight-line distance (km) to nearest emergency facility
            using `gpd.sjoin_nearest` in EPSG:3857. Aggregated to district level.

            $$\text{distance\_component} = 1 - \text{minmax}(\log(1+\text{median\_distance\_km}))$$

            $$Q2 = 0.65 \cdot \text{distance\_component} + 0.35 \cdot \text{coverage\_share}$$

            where `coverage_share` = fraction of populated centers with a matched facility.
            Districts with no matched centers receive the maximum-distance penalty.
            """
        )
    with st.expander("Q3 Baseline and Q4 Alternative Combined Scores"):
        st.markdown(
            r"""
            **Q3 Baseline** — equal weight on availability and spatial access:
            $$Q3 = 0.5 \cdot Q1 + 0.5 \cdot Q2$$

            **Q4 Alternative** — equal thirds across three components; Q2 re-specified
            using *mean* distance (more sensitive to extreme outliers) and a 20 km threshold
            penalty:

            $$\text{alt\_Q2} = 0.45 \cdot (1 - \text{minmax}(\log(1+\text{mean\_dist})))
            + 0.30 \cdot \text{coverage\_share}
            + 0.25 \cdot (1 - \text{share\_over\_20km})$$

            $$Q4 = \tfrac{1}{3} \cdot \text{facility} + \tfrac{1}{3} \cdot \text{activity}
            + \tfrac{1}{3} \cdot \text{alt\_Q2}$$

            The alternative differs conceptually in three ways: (1) equal weight across
            components instead of 50 % on Q2, (2) mean vs median distance, (3) explicit
            20 km threshold penalty.
            """
        )

    st.subheader("Limitations")
    st.markdown(
        """
        - **Straight-line distances** are a proxy; actual travel time depends on road
          infrastructure and terrain, especially in the Amazon and highlands.
        - **No population weighting**: a district with 10,000 people and 2 facilities
          ranks the same as one with 100 people and 2 facilities.
        - **Facility capability not differentiated** beyond the emergency-proxy category
          filter. A Level I-4 facility is much smaller than a Level III-E hospital.
        - **Temporal aggregation**: the C1 dataset aggregates production across all
          available years; seasonal or year-to-year variation is not captured.
        - **Missing C1 data**: some districts appear in the IPRESS registry but have
          no C1 reporting rows, or have rows with missing activity values. Their scores
          are facility-only and may understate actual activity.
        """
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STATIC ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Q1 ──────────────────────────────────────────────────────────────────
    st.subheader("Q1 — Territorial Availability")
    if q1_df.empty:
        st.warning("No Q1 output. Run the Q1 pipeline from the sidebar.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Districts evaluated", f"{len(q1_df):,}")
        m2.metric(
            "Districts with missing activity",
            f"{int((q1_df['atenciones_missing_rows'] > 0).sum()):,}",
        )
        m3.metric(
            "Districts with zero activity",
            f"{int((q1_df['atenciones_zero_rows'] > 0).sum()):,}",
        )

        _img(
            Q1_FIG_TOP_BOTTOM,
            "Top 12 and bottom 12 districts by territorial availability score",
            why=(
                "Directly answers Q1. Horizontal bars allow district-name readability. "
                "Chosen over a ranked table because relative magnitude is immediately visible. "
                "Bottom panel excludes score=0 districts (pure data gaps with no facilities) "
                "to show genuinely underserved districts."
            ),
        )
        _img(
            Q1_FIG_SCATTER,
            "Facilities vs emergency activity — colored by availability level",
            why=(
                "Tests whether facility count predicts emergency volume at district level. "
                "Log scale on Y-axis handles the extreme right skew. Color by availability "
                "level shows whether the composite score aligns with the raw data. "
                "Chosen over a correlation coefficient because it reveals outlier structure."
            ),
        )
        _img(
            Q1_FIG_QUALITY,
            "Data quality footprint: missing-row burden by district",
            why=(
                "This dataset contains substantial missing activity values. This chart "
                "separates districts whose low Q1 scores are data-quality-limited from "
                "those that are genuinely low-activity. Not found in alternatives that "
                "simply drop missing rows — our approach tracks and reports them."
            ),
        )

    st.divider()

    # ── Q2 ──────────────────────────────────────────────────────────────────
    st.subheader("Q2 — Settlement Access")
    if q2_df.empty:
        st.info("No Q2 output. Run the Q2 pipeline from the sidebar.")
    else:
        s1, s2, s3 = st.columns(3)
        s1.metric("Districts evaluated", f"{len(q2_df):,}")
        s2.metric("Avg median distance (km)", f"{q2_df['median_distance_km'].mean():.1f}")
        s3.metric("Share of districts >20 km avg", f"{(q2_df['share_over_20km'] > 0.5).mean():.1%}")

        _img(
            Q2_FIG_TOP_BOTTOM,
            "Top 12 and bottom 12 districts by settlement access score",
            why=(
                "Directly answers Q2. Top districts are dense urban areas (Lima-Callao) "
                "where populated centers are metres from facilities. Bottom districts are "
                "remote Amazon/jungle areas where the nearest emergency facility may be "
                "100+ km away. Chosen over a scatter because ranking is the core Q2 output."
            ),
        )
        _img(
            Q2_FIG_DIST,
            "Distribution of median center-to-emergency-facility distance by district",
            why=(
                "Shows the shape of the access inequality — whether it is a gradual gradient "
                "or a bimodal split between accessible and remote districts. KDE overlay "
                "highlights the long right tail of very remote districts. Chosen over a "
                "box-and-whisker because individual district density is visible."
            ),
        )

    st.divider()

    # ── Q3/Q4 ────────────────────────────────────────────────────────────────
    st.subheader("Q3 & Q4 — Combined Score and Sensitivity Analysis")
    if q34_df.empty:
        st.info("No Q3/Q4 output. Run the Q3 + Q4 pipeline from the sidebar.")
    else:
        t1, t2, t3 = st.columns(3)
        t1.metric("Districts evaluated", f"{len(q34_df):,}")
        t2.metric("Mean absolute rank shift", f"{q34_df['abs_rank_shift'].mean():.1f}")
        t3.metric("Max absolute rank shift", f"{int(q34_df['abs_rank_shift'].max()):,}")

        _img(
            Q34_FIG_TOP_BOTTOM,
            "Top 12 and bottom 12 districts by baseline combined score (Q3)",
            why=(
                "Answers Q3 directly. Combines Q1 (territorial availability) and Q2 "
                "(settlement access) into one ranking. Districts that appear here but not "
                "in Q1 or Q2 alone changed due to the combined weighting."
            ),
        )
        _img(
            Q34_FIG_SENSITIVITY,
            "Q4 Sensitivity: baseline vs alternative score per district (above diagonal = improved under alternative)",
            why=(
                "The primary Q4 visualization. Each point is a district; the diagonal is "
                "'no change'. Points above the diagonal improved under the alternative "
                "specification (equal-thirds weighting + mean distance). Color encodes "
                "absolute rank shift. Chosen over a rank-shift histogram alone because it "
                "shows WHICH districts changed, not just how many."
            ),
        )
        _img(
            Q34_FIG_SHIFT,
            "Distribution of rank shifts (alternative minus baseline) across all districts",
            why=(
                "Complements the scatter by showing the overall stability of the ranking "
                "system. A tight distribution near zero indicates robust results; a wide "
                "spread indicates high methodological sensitivity."
            ),
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GEOSPATIAL RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Static Geospatial Maps")
    st.markdown(
        "Choropleth maps show the spatial distribution of access scores across Peru's districts. "
        "Green = better served · Red = worse served · Grey = no data."
    )

    _img(
        Q1_FIG_CHOROPLETH,
        "Q1: Territorial availability score by district",
        why=(
            "Reveals geographic clustering invisible in rankings: most underserved districts "
            "concentrate in the Amazon basin and central highlands, while coastal urban "
            "areas (Lima, Arequipa, Trujillo) dominate the top tier."
        ),
    )
    _img(
        Q34_FIG_CHOROPLETH,
        "Q3 vs Q4: Baseline (left) and alternative (right) combined score — same colour scale",
        why=(
            "Side-by-side comparison on the same scale shows WHERE the two specifications "
            "disagree. Districts that change colour between maps are the most sensitive to "
            "the definition of access used."
        ),
    )

    st.divider()
    st.subheader("District-level Results Tables")

    if q1_df.empty:
        st.warning("No Q1 output. Run the pipeline from the sidebar.")
    else:
        departments = ["All departments"] + sorted(q1_df["departamento"].dropna().unique().tolist())
        selected_dep = st.selectbox("Filter all tables by department", departments)

        def _dept_filter(df: pd.DataFrame, col: str = "departamento") -> pd.DataFrame:
            if selected_dep == "All departments":
                return df
            return df[df[col] == selected_dep]

        with st.expander("Q1 — Territorial Availability", expanded=True):
            st.dataframe(
                _dept_filter(q1_df)[
                    ["rank_best_to_worst", "ubigeo", "departamento", "provincia", "distrito",
                     "total_facilities", "emergency_proxy_facilities",
                     "total_emergency_attentions", "q1_territorial_availability_score",
                     "availability_level", "activity_quality_tag"]
                ].sort_values("rank_best_to_worst"),
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("Q1 — Data Quality Mapping"):
            st.dataframe(
                _dept_filter(quality_df)[
                    ["ubigeo", "departamento", "distrito", "c1_rows",
                     "atenciones_missing_rows", "atenciones_zero_rows",
                     "atenciones_missing_share", "atenciones_zero_share",
                     "activity_quality_tag"]
                ].sort_values(["atenciones_missing_rows", "atenciones_zero_rows"], ascending=False),
                use_container_width=True,
                hide_index=True,
            )

        if not q2_df.empty:
            with st.expander("Q2 — Settlement Access"):
                st.dataframe(
                    _dept_filter(q2_df, col="department")[
                        ["rank_best_to_worst", "ubigeo", "department", "province", "district",
                         "total_populated_centers", "matched_centers", "coverage_share",
                         "median_distance_km", "share_over_20km",
                         "q2_settlement_access_score", "q2_access_level"]
                    ].sort_values("rank_best_to_worst"),
                    use_container_width=True,
                    hide_index=True,
                )

        if not q34_df.empty:
            with st.expander("Q3/Q4 — Combined Comparison"):
                st.dataframe(
                    _dept_filter(q34_df)[
                        ["baseline_rank_best_to_worst", "alternative_rank_best_to_worst",
                         "rank_shift_alt_minus_base", "ubigeo",
                         "departamento", "provincia", "distrito",
                         "q1_territorial_availability_score", "q2_settlement_access_score",
                         "q3_baseline_combined_score", "q4_alternative_combined_score",
                         "q3_low_score_cause", "q3_baseline_level"]
                    ].sort_values("baseline_rank_best_to_worst"),
                    use_container_width=True,
                    hide_index=True,
                )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INTERACTIVE EXPLORATION
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Interactive District Map")
    st.markdown(
        "Select a metric and filter by department to explore district-level scores interactively. "
        "Hover over any district to see its scores, ranking, and low-score cause."
    )

    if q34_df.empty:
        st.info("Run the Q3 + Q4 pipeline to enable the interactive map.")
    elif district_shapes.empty:
        st.warning("District shapefile not found. Check `data/raw/District_Boundaries_of_Peru/`.")
    else:
        col_metric, col_dept = st.columns(2)
        with col_metric:
            metric_options = [
                ("q3_baseline_combined_score", "Q3 Baseline Combined Score"),
                ("q4_alternative_combined_score", "Q4 Alternative Combined Score"),
                ("rank_shift_alt_minus_base", "Q4 Rank Shift (alt − baseline)"),
                ("q1_territorial_availability_score", "Q1 Territorial Availability"),
                ("q2_settlement_access_score", "Q2 Settlement Access"),
            ]
            metric_option = st.selectbox(
                "Metric to map",
                options=metric_options,
                format_func=lambda x: x[1],
            )
        with col_dept:
            dept_options = ["All"] + sorted(q34_df["departamento"].dropna().unique().tolist())
            selected_dept = st.selectbox("Filter by department", dept_options)

        map_html = build_folium_map(
            districts=district_shapes,
            q34_df=q34_df,
            metric_col=metric_option[0],
            tooltip_label=metric_option[1],
            dept_filter=selected_dept,
        )
        if map_html:
            components.html(map_html, height=680, scrolling=False)
        else:
            st.warning("No district geometry matched the selected filter.")

        st.divider()
        st.subheader("District Lookup")
        st.markdown("Search for a specific district to compare all its scores.")
        if not q34_df.empty:
            search = st.text_input("District name (partial match, case-insensitive)")
            if search:
                matches = q34_df[
                    q34_df["distrito"].str.contains(search, case=False, na=False)
                ][
                    ["departamento", "provincia", "distrito",
                     "q1_territorial_availability_score", "q2_settlement_access_score",
                     "q3_baseline_combined_score", "q4_alternative_combined_score",
                     "baseline_rank_best_to_worst", "alternative_rank_best_to_worst",
                     "rank_shift_alt_minus_base", "q3_low_score_cause"]
                ].sort_values("baseline_rank_best_to_worst")
                if matches.empty:
                    st.info("No districts found matching that name.")
                else:
                    st.dataframe(matches, use_container_width=True, hide_index=True)
