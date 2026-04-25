from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def _annotate_horizontal_bars(ax: plt.Axes, fmt: str = "{:.3f}") -> None:
    """Add readable value labels to horizontal bar charts."""
    xmin, xmax = ax.get_xlim()
    span = xmax - xmin if xmax > xmin else 1
    for patch in ax.patches:
        width = patch.get_width()
        y = patch.get_y() + patch.get_height() / 2
        x = width + span * 0.01
        ax.text(
            x,
            y,
            fmt.format(width),
            va="center",
            ha="left",
            fontsize=8,
            color="#333333",
        )


def plot_q1_top_bottom(
    district_df: pd.DataFrame,
    output_path: Path,
    n: int = 12,
    subtitle: str = "",
) -> None:
    sns.set_theme(style="whitegrid")
    top = district_df.nlargest(n, "q1_territorial_availability_score").copy()
    # Exclude score=0 from bottom panel: those are pure data gaps (0 facilities + all-missing
    # C1 rows), not genuine low-access districts. Show worst districts that have some data.
    has_data = district_df["q1_territorial_availability_score"].gt(0)
    bottom = district_df[has_data].nsmallest(n, "q1_territorial_availability_score").copy()
    top["district_label"] = (
        top["rank_best_to_worst"].astype(int).astype(str)
        + ". "
        + top["departamento"]
        + " / "
        + top["distrito"]
    )
    bottom["district_label"] = (
        bottom["rank_worst_to_best"].astype(int).astype(str)
        + ". "
        + bottom["departamento"]
        + " / "
        + bottom["distrito"]
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), constrained_layout=True)

    sns.barplot(
        data=top.sort_values("q1_territorial_availability_score", ascending=False),
        x="q1_territorial_availability_score",
        y="district_label",
        color="#4c9f70",
        ax=axes[0],
    )
    axes[0].set_title(f"Top {n} districts (highest Q1 scores)")
    axes[0].set_xlabel("Q1 score (0-1, higher is better)")
    axes[0].set_ylabel("")

    sns.barplot(
        data=bottom.sort_values("q1_territorial_availability_score", ascending=True),
        x="q1_territorial_availability_score",
        y="district_label",
        color="#c44e52",
        ax=axes[1],
    )
    axes[1].set_title(f"Bottom {n} districts (lowest positive Q1 scores)")
    axes[1].set_xlabel("Q1 score (0-1, higher is better)")
    axes[1].set_ylabel("")
    axes[0].set_xlim(0, 1.08)
    axes[1].set_xlim(0, 1.08)
    _annotate_horizontal_bars(axes[0])
    _annotate_horizontal_bars(axes[1])

    n_districts = len(district_df)
    base_title = "Question 1: Territorial availability of facilities and emergency activity"
    full_title = f"{base_title}\n{subtitle} — {n_districts:,} districts" if subtitle else f"{base_title} — {n_districts:,} districts"
    fig.suptitle(full_title, fontsize=13)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q1_scatter(district_df: pd.DataFrame, output_path: Path) -> None:
    sns.set_theme(style="ticks")
    fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)
    chart_df = district_df.copy()
    chart_df["total_emergency_attentions_plus1"] = (
        chart_df["total_emergency_attentions"].fillna(0) + 1
    )

    sns.scatterplot(
        data=chart_df,
        x="total_facilities",
        y="total_emergency_attentions_plus1",
        hue="availability_level",
        palette="viridis",
        alpha=0.8,
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_title("Facilities vs Emergency Activity (District Level)")
    ax.set_xlabel("Total facilities")
    ax.set_ylabel("Total emergency attentions + 1 (log scale)")
    ax.legend(title="Availability level", bbox_to_anchor=(1.02, 1), loc="upper left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q1_data_quality(district_df: pd.DataFrame, output_path: Path, n: int = 20) -> None:
    sns.set_theme(style="whitegrid")
    footprint = district_df.copy()
    footprint["combined_missing_share"] = (
        footprint["atenciones_missing_share"] + footprint["atendidos_missing_share"]
    ) / 2
    footprint["combined_zero_share"] = (
        footprint["atenciones_zero_share"] + footprint["atendidos_zero_share"]
    ) / 2
    footprint["district_label"] = footprint["departamento"] + " / " + footprint["distrito"]

    # Left panel: districts with highest number of missing rows (absolute burden).
    top_missing_rows = footprint.sort_values(
        ["atenciones_missing_rows", "atendidos_missing_rows", "c1_rows"],
        ascending=False,
    ).head(n)

    # Right panel: relationship between reporting volume and missing share.
    scatter_df = footprint[footprint["c1_rows"] > 0].copy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)

    sns.barplot(
        data=top_missing_rows.sort_values("atenciones_missing_rows", ascending=False),
        x="atenciones_missing_rows",
        y="district_label",
        color="#d95f02",
        ax=axes[0],
    )
    axes[0].set_title(f"Top {n} districts by missing emergency-attention rows")
    axes[0].set_xlabel("Missing rows in emergency attentions")
    axes[0].set_ylabel("")
    _annotate_horizontal_bars(axes[0], fmt="{:.0f}")

    sns.scatterplot(
        data=scatter_df,
        x="c1_rows",
        y="combined_missing_share",
        size="atenciones_missing_rows",
        sizes=(15, 180),
        alpha=0.55,
        color="#1f77b4",
        legend=False,
        ax=axes[1],
    )
    axes[1].set_title("Missing-share pattern vs reporting volume")
    axes[1].set_xlabel("Total C1 rows reported by district")
    axes[1].set_ylabel("Average missing share (attention + attended)")
    axes[1].set_ylim(0, 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q2_top_bottom_access(
    district_df: pd.DataFrame, output_path: Path, n: int = 12
) -> None:
    sns.set_theme(style="whitegrid")
    strongest = district_df.nlargest(n, "q2_settlement_access_score").copy()
    has_data = district_df["q2_settlement_access_score"].gt(0)
    weakest = district_df[has_data].nsmallest(n, "q2_settlement_access_score").copy()
    strongest["district_label"] = (
        strongest["rank_best_to_worst"].astype(int).astype(str)
        + ". "
        + strongest["department"]
        + " / "
        + strongest["district"]
    )
    weakest["district_label"] = (
        weakest["rank_worst_to_best"].astype(int).astype(str)
        + ". "
        + weakest["department"]
        + " / "
        + weakest["district"]
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), constrained_layout=True)

    sns.barplot(
        data=strongest.sort_values("q2_settlement_access_score", ascending=False),
        x="q2_settlement_access_score",
        y="district_label",
        color="#4c78a8",
        ax=axes[0],
    )
    axes[0].set_title(f"Top {n} districts (highest Q2 access scores)")
    axes[0].set_xlabel("Q2 score (0-1, higher is better)")
    axes[0].set_ylabel("")

    sns.barplot(
        data=weakest.sort_values("q2_settlement_access_score", ascending=True),
        x="q2_settlement_access_score",
        y="district_label",
        color="#dd8452",
        ax=axes[1],
    )
    axes[1].set_title(f"Bottom {n} districts (lowest positive Q2 scores)")
    axes[1].set_xlabel("Q2 score (0-1, higher is better)")
    axes[1].set_ylabel("")
    axes[0].set_xlim(0, 1.08)
    axes[1].set_xlim(0, 1.08)
    _annotate_horizontal_bars(axes[0])
    _annotate_horizontal_bars(axes[1])

    fig.suptitle(
        "Question 2: Populated-center access to emergency-related facilities",
        fontsize=14,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q2_distance_distribution(district_df: pd.DataFrame, output_path: Path) -> None:
    sns.set_theme(style="ticks")
    plot_df = district_df[district_df["median_distance_km"] > 0].copy()

    fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)
    sns.histplot(
        plot_df["median_distance_km"],
        bins=40,
        kde=True,
        color="#2c7fb8",
        ax=ax,
    )
    ax.set_title("Distribution of median center-to-emergency distance by district")
    ax.set_xlabel("Median distance to nearest emergency-related facility (km)")
    ax.set_ylabel("Number of districts")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q3_top_bottom_combined(
    district_df: pd.DataFrame, output_path: Path, n: int = 12
) -> None:
    sns.set_theme(style="whitegrid")
    strongest = district_df.nlargest(n, "q3_baseline_combined_score").copy()
    has_data = district_df["q3_baseline_combined_score"].gt(0)
    weakest = district_df[has_data].nsmallest(n, "q3_baseline_combined_score").copy()
    strongest["district_label"] = (
        strongest["baseline_rank_best_to_worst"].astype(int).astype(str)
        + ". "
        + strongest["departamento"]
        + " / "
        + strongest["distrito"]
    )
    weakest["district_label"] = (
        weakest["baseline_rank_best_to_worst"].astype(int).astype(str)
        + ". "
        + weakest["departamento"]
        + " / "
        + weakest["distrito"]
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), constrained_layout=True)

    sns.barplot(
        data=strongest.sort_values("q3_baseline_combined_score", ascending=False),
        x="q3_baseline_combined_score",
        y="district_label",
        color="#72b7b2",
        ax=axes[0],
    )
    axes[0].set_title(f"Top {n} districts (highest Q3 scores)")
    axes[0].set_xlabel("Q3 score (0-1, higher is better)")
    axes[0].set_ylabel("")

    sns.barplot(
        data=weakest.sort_values("q3_baseline_combined_score", ascending=True),
        x="q3_baseline_combined_score",
        y="district_label",
        color="#e07b7b",
        ax=axes[1],
    )
    axes[1].set_title(f"Bottom {n} districts (lowest positive Q3 scores)")
    axes[1].set_xlabel("Q3 score (0-1, higher is better)")
    axes[1].set_ylabel("")
    axes[0].set_xlim(0, 1.08)
    axes[1].set_xlim(0, 1.08)
    _annotate_horizontal_bars(axes[0])
    _annotate_horizontal_bars(axes[1])

    fig.suptitle(
        "Question 3: District comparison combining Q1 availability and Q2 access",
        fontsize=14,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q4_sensitivity_scatter(district_df: pd.DataFrame, output_path: Path) -> None:
    """XY scatter: baseline vs alternative score — diagonal = no change.

    Districts above the diagonal improved under the alternative specification;
    districts below it worsened. Color shows absolute rank shift magnitude.
    """
    sns.set_theme(style="ticks")
    df = district_df.dropna(
        subset=["q3_baseline_combined_score", "q4_alternative_combined_score"]
    ).copy()

    fig, ax = plt.subplots(figsize=(10, 9), constrained_layout=True)
    scatter = ax.scatter(
        df["q3_baseline_combined_score"],
        df["q4_alternative_combined_score"],
        c=df["abs_rank_shift"],
        cmap="YlOrRd",
        alpha=0.55,
        s=18,
        linewidths=0,
    )
    lims = [0, 1]
    ax.plot(lims, lims, "--", color="#555555", linewidth=1.2, label="No change")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("Q3 Baseline Combined Score", fontsize=11)
    ax.set_ylabel("Q4 Alternative Combined Score", fontsize=11)
    ax.set_title(
        "Q4 Sensitivity: baseline vs alternative score per district\n"
        "(above diagonal = improved; below = worsened under alternative)",
        fontsize=12,
    )
    ax.legend(fontsize=9)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.7)
    cbar.set_label("Absolute rank shift")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_q4_rank_shift_distribution(district_df: pd.DataFrame, output_path: Path) -> None:
    sns.set_theme(style="ticks")
    fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)
    sns.histplot(
        district_df["rank_shift_alt_minus_base"],
        bins=35,
        kde=True,
        color="#4d4d4d",
        ax=ax,
    )
    ax.axvline(0, color="#d62728", linestyle="--", linewidth=1.5)
    ax.set_title("Q4 Sensitivity: rank shift distribution (alternative minus baseline)")
    ax.set_xlabel("Rank shift (positive = district improves under alternative weighting)")
    ax.set_ylabel("Number of districts")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _normalize_ubigeo(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(6)
    )


def plot_choropleth_q1_score(
    districts_gdf: gpd.GeoDataFrame,
    q1_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Static choropleth: Q1 territorial availability score by district."""
    gdf = districts_gdf.copy()
    gdf["ubigeo"] = _normalize_ubigeo(gdf["ubigeo"])
    scores = q1_df[["ubigeo", "q1_territorial_availability_score"]].copy()
    scores["ubigeo"] = _normalize_ubigeo(scores["ubigeo"])

    merged = gdf.merge(scores, on="ubigeo", how="left")

    fig, ax = plt.subplots(1, 1, figsize=(12, 14), constrained_layout=True)
    merged.plot(
        column="q1_territorial_availability_score",
        ax=ax,
        legend=True,
        cmap="RdYlGn",
        missing_kwds={"color": "lightgrey", "label": "No data"},
        legend_kwds={
            "label": "Q1 Territorial Availability Score",
            "shrink": 0.55,
            "orientation": "horizontal",
        },
        linewidth=0.1,
        edgecolor="0.5",
    )
    ax.set_title(
        "Q1: Territorial Availability Score by District\n"
        "(facility footprint + emergency activity, log-scaled)",
        fontsize=13,
    )
    ax.axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_choropleth_q3_comparison(
    districts_gdf: gpd.GeoDataFrame,
    q34_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Side-by-side static choropleth: baseline vs alternative combined score."""
    gdf = districts_gdf.copy()
    gdf["ubigeo"] = _normalize_ubigeo(gdf["ubigeo"])
    scores = q34_df[
        ["ubigeo", "q3_baseline_combined_score", "q4_alternative_combined_score"]
    ].copy()
    scores["ubigeo"] = _normalize_ubigeo(scores["ubigeo"])

    merged = gdf.merge(scores, on="ubigeo", how="left")

    vmin = float(
        merged[["q3_baseline_combined_score", "q4_alternative_combined_score"]]
        .min()
        .min()
    )
    vmax = float(
        merged[["q3_baseline_combined_score", "q4_alternative_combined_score"]]
        .max()
        .max()
    )

    pairs = [
        ("q3_baseline_combined_score", "Q3 Baseline Combined Score\n(50% Q1 + 50% Q2 structural)"),
        (
            "q4_alternative_combined_score",
            "Q4 Alternative Combined Score\n(50% Q1 + 50% Q2 C1-observed)",
        ),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(22, 14), constrained_layout=True)
    for ax, (col, title) in zip(axes, pairs):
        merged.plot(
            column=col,
            ax=ax,
            legend=True,
            cmap="RdYlGn",
            vmin=vmin,
            vmax=vmax,
            missing_kwds={"color": "lightgrey", "label": "No data"},
            legend_kwds={"label": title, "shrink": 0.45, "orientation": "horizontal"},
            linewidth=0.1,
            edgecolor="0.5",
        )
        ax.set_title(title, fontsize=12)
        ax.axis("off")

    fig.suptitle(
        "Q3 vs Q4: Baseline and Alternative Combined Access Score by District",
        fontsize=14,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
