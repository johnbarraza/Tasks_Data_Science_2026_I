from __future__ import annotations

from pathlib import Path

import pandas as pd

from .geospatial import load_districts
from .metrics import build_q3_q4_combined_comparison
from .question1_pipeline import run_question1_pipeline
from .question2_pipeline import run_question2_pipeline
from .visualization import (
    plot_choropleth_q3_comparison,
    plot_q3_top_bottom_combined,
    plot_q4_rank_shift_distribution,
    plot_q4_sensitivity_scatter,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"

Q1_TABLE = TABLES_DIR / "q1_territorial_availability.csv"
Q2_TABLE = TABLES_DIR / "q2_settlement_access.csv"


def run_question3_4_pipeline() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    if not Q1_TABLE.exists():
        run_question1_pipeline()
    if not Q2_TABLE.exists():
        run_question2_pipeline()

    q1 = pd.read_csv(Q1_TABLE)
    q2 = pd.read_csv(Q2_TABLE)

    q34 = build_q3_q4_combined_comparison(q1=q1, q2=q2)
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

    districts = load_districts()
    plot_choropleth_q3_comparison(districts, q34, FIGURES_DIR / "q3_q4_choropleth_comparison.png")

    summary = [
        "# Question 3 and Question 4 Summary",
        "",
        "This file was generated from the combined Q3/Q4 pipeline.",
        f"Districts evaluated: {len(q34)}",
        "",
        "Q3 baseline score = 0.50 * Q1 + 0.50 * Q2",
        "Q4 alternative score = 0.30 * facility + 0.20 * activity + 0.50 * Q2",
        "",
        "Top 5 districts by baseline combined score:",
    ]
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
