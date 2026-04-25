from __future__ import annotations

from pathlib import Path

import pandas as pd

from .cleaning import clean_c1, clean_ipress
from .data_loader import load_c1_raw, load_ipress_raw
from .geospatial import load_districts
from .metrics import build_q1_territorial_availability
from .visualization import (
    plot_choropleth_q1_score,
    plot_q1_data_quality,
    plot_q1_scatter,
    plot_q1_top_bottom,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"


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


def _recompute_q1_ranks(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.copy()
    ranked["rank_best_to_worst"] = (
        ranked["q1_territorial_availability_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    ranked["rank_worst_to_best"] = (
        ranked["q1_territorial_availability_score"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )
    return ranked.sort_values("rank_best_to_worst").reset_index(drop=True)


def run_question1_pipeline(omit_missing_only: bool = False) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    ipress_raw = load_ipress_raw()
    c1_raw = load_c1_raw()

    ipress_clean = clean_ipress(ipress_raw)
    c1_clean = clean_c1(c1_raw)

    ipress_clean.to_csv(PROCESSED_DIR / "ipress_clean.csv", index=False, encoding="utf-8")
    c1_clean.to_csv(PROCESSED_DIR / "c1_clean.csv", index=False, encoding="utf-8")

    q1_full = build_q1_territorial_availability(ipress_clean, c1_clean)
    missing_only_mask = _q1_missing_only_mask(q1_full)
    omitted_count = int(missing_only_mask.sum())
    q1 = q1_full[~missing_only_mask].copy() if omit_missing_only else q1_full.copy()
    q1_omitting_missing = _recompute_q1_ranks(q1_full[~missing_only_mask].copy())

    q1.to_csv(TABLES_DIR / "q1_territorial_availability.csv", index=False, encoding="utf-8")
    q1_omitting_missing.to_csv(
        TABLES_DIR / "q1_territorial_availability_omitting_missing.csv",
        index=False,
        encoding="utf-8",
    )
    q1.head(20).to_csv(TABLES_DIR / "q1_top20_districts.csv", index=False, encoding="utf-8")
    q1.sort_values("q1_territorial_availability_score", ascending=True).head(20).to_csv(
        TABLES_DIR / "q1_bottom20_districts.csv",
        index=False,
        encoding="utf-8",
    )
    q1.sort_values(
        ["atenciones_missing_rows", "atendidos_missing_rows"],
        ascending=False,
    ).to_csv(
        TABLES_DIR / "q1_data_quality_by_district.csv",
        index=False,
        encoding="utf-8",
    )

    mode_suffix = "omitting_missing" if omit_missing_only else "including_missing"
    top_bottom_main = FIGURES_DIR / "q1_top_bottom_districts.png"
    scatter_main = FIGURES_DIR / "q1_facilities_vs_activity_scatter.png"
    quality_main = FIGURES_DIR / "q1_data_quality_footprint.png"
    top_bottom_mode = FIGURES_DIR / f"q1_top_bottom_districts_{mode_suffix}.png"
    scatter_mode = FIGURES_DIR / f"q1_facilities_vs_activity_scatter_{mode_suffix}.png"
    quality_mode = FIGURES_DIR / f"q1_data_quality_footprint_{mode_suffix}.png"

    mode_label = "Missing-only districts omitted" if omit_missing_only else "All districts included (missing activity tracked)"
    plot_q1_top_bottom(q1, top_bottom_main, subtitle=mode_label)
    plot_q1_scatter(q1, scatter_main)
    plot_q1_data_quality(q1, quality_main)
    plot_q1_top_bottom(q1, top_bottom_mode, subtitle=mode_label)
    plot_q1_scatter(q1, scatter_mode)
    plot_q1_data_quality(q1, quality_mode)

    sensitivity_label = (
        f"Sensitivity: {omitted_count:,} missing-dominant districts omitted"
    )
    plot_q1_top_bottom(
        q1_omitting_missing,
        FIGURES_DIR / "q1_top_bottom_districts_omitting_missing.png",
        subtitle=sensitivity_label,
    )
    plot_q1_scatter(
        q1_omitting_missing,
        FIGURES_DIR / "q1_facilities_vs_activity_scatter_omitting_missing.png",
    )
    plot_q1_data_quality(
        q1_omitting_missing,
        FIGURES_DIR / "q1_data_quality_footprint_omitting_missing.png",
    )

    districts = load_districts()
    plot_choropleth_q1_score(districts, q1, FIGURES_DIR / "q1_choropleth_score.png")

    summary = [
        "# Question 1 Summary",
        "",
        "This file was generated from the Q1 territorial availability pipeline.",
        f"Omit missing-only districts mode: {omit_missing_only}",
        f"Missing-only districts omitted: {omitted_count if omit_missing_only else 0}",
        f"Q1 sensitivity table omits missing-dominant districts: {omitted_count}",
        f"Number of districts in table: {len(q1)}",
        f"Number of districts in Q1 sensitivity table: {len(q1_omitting_missing)}",
        f"Figure suffix generated: {mode_suffix}",
        "",
        "Data quality mapping (kept, not dropped):",
        f"- Districts with at least one missing emergency attention row: {int((q1['atenciones_missing_rows'] > 0).sum())}",
        f"- Districts with at least one zero emergency attention row: {int((q1['atenciones_zero_rows'] > 0).sum())}",
        "",
        "Top 5 districts (best availability score):",
    ]
    for _, row in q1.head(5).iterrows():
        summary.append(
            f"- {row['departamento']} / {row['distrito']} (score={row['q1_territorial_availability_score']:.4f})"
        )

    summary.append("")
    summary.append("Bottom 5 districts (lowest availability score):")
    for _, row in q1.sort_values("rank_worst_to_best").head(5).iterrows():
        summary.append(
            f"- {row['departamento']} / {row['distrito']} (score={row['q1_territorial_availability_score']:.4f})"
        )

    (TABLES_DIR / "q1_summary.md").write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    run_question1_pipeline(omit_missing_only=False)
