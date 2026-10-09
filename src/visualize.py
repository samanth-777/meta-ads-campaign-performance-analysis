"""Presentation-grade Seaborn figures for the ad optimization report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.clean_and_engineer import PROJECT_ROOT
from src.decision_engine import run_decision_engine

FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

DECISION_ORDER = ["Scale / Continue", "Pause / Optimize", "Discontinue"]
DECISION_PALETTE = {
    "Scale / Continue": "#2A9D8F",
    "Pause / Optimize": "#E9C46A",
    "Discontinue": "#E76F51",
}


def _setup_style() -> None:
    sns.set_theme(style="whitegrid", context="talk", font_scale=0.9)
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
        }
    )


def plot_cpa_vs_spend(df: pd.DataFrame, out_dir: Path) -> Path:
    """1. CPA vs Spend by decision category."""
    plot_df = df.copy()
    # Ads with zero approved conversions have NaN CPA — plot at a high
    # sentinel so wasteful spend is visible, tagged via Decision.
    plot_df["CPA_plot"] = plot_df["CPA"].fillna(plot_df["Spent"].clip(lower=1) * 2)
    plot_df = plot_df[plot_df["Spent"] > 0]

    fig, ax = plt.subplots(figsize=(11, 7))
    sns.scatterplot(
        data=plot_df,
        x="Spent",
        y="CPA_plot",
        hue="Decision",
        hue_order=DECISION_ORDER,
        palette=DECISION_PALETTE,
        alpha=0.65,
        s=55,
        edgecolor="white",
        linewidth=0.3,
        ax=ax,
    )
    ax.axhline(
        55.0,
        color="#264653",
        linestyle="--",
        linewidth=1.2,
        label="CPA benchmark ($55)",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Ad Spend (USD, log scale)")
    ax.set_ylabel("CPA (USD, log scale; NaN→sentinel)")
    ax.set_title("CPA vs Spend by Decision Category")
    ax.legend(title="Decision", loc="upper left", frameon=True)
    path = out_dir / "cpa_vs_spend_by_decision.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_demographic_heatmap(df: pd.DataFrame, out_dir: Path) -> Path:
    """2. Age × Gender conversion-efficiency heatmap (Approved / Spent * 1000)."""
    grouped = (
        df.groupby(["age", "gender"], as_index=False)
        .agg(Spent=("Spent", "sum"), Approved=("Approved_Conversion", "sum"))
    )
    # Conversions per $1,000 spent — higher is more efficient
    grouped["Conv_per_1k"] = np.where(
        grouped["Spent"] > 0,
        grouped["Approved"] / grouped["Spent"] * 1000.0,
        0.0,
    )
    pivot = grouped.pivot(index="age", columns="gender", values="Conv_per_1k")
    # Stable age order
    age_order = ["30-34", "35-39", "40-44", "45-49"]
    pivot = pivot.reindex(age_order)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "Approved conversions per $1k spend"},
        ax=ax,
    )
    ax.set_title("Demographic Conversion Efficiency (Age × Gender)")
    ax.set_xlabel("Gender")
    ax.set_ylabel("Age band")
    path = out_dir / "demographic_heatmap_age_gender.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_funnel_leakage(df: pd.DataFrame, out_dir: Path) -> Path:
    """3. Funnel: Impressions → Clicks → Total Conversions → Approved."""
    stages = [
        ("Impressions", int(df["Impressions"].sum())),
        ("Clicks", int(df["Clicks"].sum())),
        ("Total Conversions", int(df["Total_Conversion"].sum())),
        ("Approved Conversions", int(df["Approved_Conversion"].sum())),
    ]
    labels = [s[0] for s in stages]
    values = [s[1] for s in stages]
    top = values[0]
    widths = [v / top for v in values]
    # Center bars as a funnel
    lefts = [(1 - w) / 2 for w in widths]
    colors = ["#264653", "#2A9D8F", "#E9C46A", "#E76F51"]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(len(labels))[::-1]
    ax.barh(y_pos, widths, left=lefts, color=colors, height=0.65, edgecolor="white")
    for y, label, value, width, left in zip(
        y_pos, labels, values, widths, lefts
    ):
        pct = value / top * 100
        ax.text(
            0.5,
            y,
            f"{label}: {value:,.0f}  ({pct:.3f}% of impressions)",
            ha="center",
            va="center",
            color="white" if width > 0.25 else "#1a1a1a",
            fontsize=11,
            fontweight="bold",
        )
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("Funnel Leakage: Impressions → Approved Conversions")
    sns.despine(left=True, bottom=True)
    path = out_dir / "funnel_leakage.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_figures(df: pd.DataFrame | None = None) -> list[Path]:
    _setup_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    if df is None:
        df, _ = run_decision_engine()
    paths = [
        plot_cpa_vs_spend(df, FIGURES_DIR),
        plot_demographic_heatmap(df, FIGURES_DIR),
        plot_funnel_leakage(df, FIGURES_DIR),
    ]
    return paths


def main() -> None:
    paths = generate_figures()
    for p in paths:
        print(f"Saved {p}")


if __name__ == "__main__":
    main()
