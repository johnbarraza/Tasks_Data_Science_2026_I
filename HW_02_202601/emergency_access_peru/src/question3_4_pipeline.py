from __future__ import annotations

from pathlib import Path

import pandas as pd

from .cleaning import clean_c1, clean_ipress
from .data_loader import load_c1_raw, load_ipress_raw
from .geospatial import load_districts
from .metrics import build_q2_settlement_access, build_q3_q4_combined_comparison
from .question1_pipeline import run_question1_pipeline
from .question2_pipeline import (
    build_observed_activity_facility_set,
    compute_center_access_to_facilities,
    prepare_facilities_for_distance,
    prepare_populated_centers,
    run_question2_pipeline,
)
from .visualization import (
    plot_choropleth_q3_comparison,
    plot_q3_top_bottom_combined,
    plot_q4_rank_shift_distribution,
    plot_q4_sensitivity_scatter,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"

Q1_TABLE = TABLES_DIR / "q1_territorial_availability.csv"
Q2_TABLE = TABLES_DIR / "q2_settlement_access.csv"


def run_question3_4_pipeline() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    if not Q1_TABLE.exists():
        run_question1_pipeline()
    if not Q2_TABLE.exists():
        run_question2_pipeline()

    q1 = pd.read_csv(Q1_TABLE)
    q2_baseline = pd.read_csv(Q2_TABLE)

    districts = load_districts()
    ipress_clean = clean_ipress(load_ipress_raw())
    c1_clean = clean_c1(load_c1_raw())
    observed_facilities = build_observed_activity_facility_set(ipress_clean, c1_clean)
    observed_facilities = prepare_facilities_for_distance(observed_facilities, districts)
    centers = prepare_populated_centers(districts)
    center_access_observed = compute_center_access_to_facilities(
        centers,
        observed_facilities,
    )
    center_access_observed.to_csv(
        PROCESSED_DIR / "q2_center_access_observed_activity.csv",
        index=False,
        encoding="utf-8",
    )
    q2_alternative = build_q2_settlement_access(center_access_observed, districts)
    q2_alternative.to_csv(
        TABLES_DIR / "q2_observed_activity_access.csv",
        index=False,
        encoding="utf-8",
    )

    q34 = build_q3_q4_combined_comparison(
        q1=q1,
        q2_baseline=q2_baseline,
        q2_alternative=q2_alternative,
    )
    q34.to_csv(TABLES_DIR / "q3_q4_combined_comparison.csv", index=False, encoding="utf-8")

    q34.sort_values("abs_rank_shift", ascending=False).head(30).to_csv(
        TABLES_DIR / "q4_top30_rank_shift.csv",
        index=False,
        encoding="utf-8",
    )
    q34.sort_values("q3_baseline_combined_score", ascending=True).head(200).to_csv(
        TABLES_DIR / "q3_low_score_diagnostics.csv",
        index=False,
        encoding="utf-8",
    )

    plot_q3_top_bottom_combined(q34, FIGURES_DIR / "q3_top_bottom_combined.png")
    plot_q4_rank_shift_distribution(q34, FIGURES_DIR / "q4_rank_shift_distribution.png")
    plot_q4_sensitivity_scatter(q34, FIGURES_DIR / "q4_sensitivity_scatter.png")

    plot_choropleth_q3_comparison(districts, q34, FIGURES_DIR / "q3_q4_choropleth_comparison.png")

    observed_total = len(observed_facilities)
    summary = [
        "# Question 3 and Question 4 Summary",
        "",
        "This file was generated from the combined Q3/Q4 pipeline.",
        f"Districts evaluated: {len(q34)}",
        f"C1-observed facilities with valid coordinates used in Q4: {observed_total}",
        "",
        "Q3 baseline score = 0.50 * Q1 + 0.50 * Q2 structural-category access",
        "Q4 alternative score = 0.50 * Q1 + 0.50 * Q2 C1-observed activity access",
        "Q4 is a definition sensitivity: structural emergency proxy vs observed C1 activity.",
        "",
        "Top 5 districts by baseline combined score:",
    ]
    if observed_total < 100:
        summary.insert(
            5,
            "Caveat: fewer than 100 C1-observed facilities with valid coordinates were "
            "available, so Q4 also reflects reporting coverage limitations.",
        )
    for _, row in q34.head(5).iterrows():
        summary.append(
            f"- {row['departamento']} / {row['distrito']} "
            f"(base={row['q3_baseline_combined_score']:.4f}, alt={row['q4_alternative_combined_score']:.4f})"
        )

    summary.append("")
    summary.append("Most sensitive districts by absolute rank shift:")
    for _, row in q34.sort_values("abs_rank_shift", ascending=False).head(10).iterrows():
        summary.append(
            f"- {row['departamento']} / {row['distrito']} "
            f"(shift={int(row['rank_shift_alt_minus_base'])}, "
            f"base_rank={int(row['baseline_rank_best_to_worst'])}, "
            f"alt_rank={int(row['alternative_rank_best_to_worst'])})"
        )

    summary.append("")
    summary.append("Low-score cause profile (all districts):")
    for cause, count in q34["q3_low_score_cause"].value_counts(dropna=False).items():
        summary.append(f"- {cause}: {int(count)}")

    (TABLES_DIR / "q3_q4_summary.md").write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    run_question3_4_pipeline()
