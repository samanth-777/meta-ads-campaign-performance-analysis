"""Business-rule ad classifier and campaign decision exports.

Benchmarks (documented assumptions)
-----------------------------------
Derived from portfolio-level totals on the KAG Facebook conversion dataset:

* Overall CPA ≈ $54.40  →  CPA_BENCHMARK = 55.0
* Overall CPC ≈ $1.54   →  CPC_BENCHMARK = 1.75  (slightly above mean;
  "acceptable" CPC ceiling for Pause/Optimize)
* Portfolio conversion rate (Total_Conversion / Clicks) ≈ 8.6%
  →  HIGH_CONVERSION_RATE = 10.0  (%; above portfolio)
* Consistent volume floor: Impressions >= 10_000 AND Clicks >= 5
* High-spend waste threshold: Spent >= 20.0 with zero approved conversions
* Prohibitive CPA: CPA > 2 × CPA_BENCHMARK (110.0) when any approved exist

Decision labels
---------------
* Scale / Continue  — high CVR, CPA below benchmark, consistent volume
* Pause / Optimize  — moderate: CPC acceptable but approved conversion weak
* Discontinue       — high spend + zero approved, or prohibitive CPA
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.clean_and_engineer import (
    DEFAULT_OUTPUT as METRICS_CSV,
    PROJECT_ROOT,
    clean_and_engineer,
)

OUTPUT_DIR = PROJECT_ROOT / "output"
DECISIONS_XLSX = OUTPUT_DIR / "campaign_decisions_summary.xlsx"

# Explicit benchmarks (USD / %)
CPA_BENCHMARK = 55.0
CPC_BENCHMARK = 1.75
HIGH_CONVERSION_RATE = 10.0  # percent
MIN_IMPRESSIONS = 10_000
MIN_CLICKS = 5
HIGH_SPEND_THRESHOLD = 20.0
PROHIBITIVE_CPA_MULTIPLIER = 2.0


def classify_ad(row: pd.Series) -> str:
    """Classify a single ad row into a decision category."""
    spent = float(row["Spent"])
    approved = float(row["Approved_Conversion"])
    cpa = row["CPA"]
    cpc = float(row.get("CPC", 0) or 0)
    cvr = float(row.get("Conversion_Rate", 0) or 0)
    impressions = float(row["Impressions"])
    clicks = float(row["Clicks"])
    car = float(row.get("Customer_Acquisition_Rate", 0) or 0)

    prohibitive_cpa = (
        pd.notna(cpa)
        and approved > 0
        and float(cpa) > CPA_BENCHMARK * PROHIBITIVE_CPA_MULTIPLIER
    )
    wasteful_zero = spent >= HIGH_SPEND_THRESHOLD and approved == 0

    if wasteful_zero or prohibitive_cpa:
        return "Discontinue"

    volume_ok = impressions >= MIN_IMPRESSIONS and clicks >= MIN_CLICKS
    cpa_ok = pd.notna(cpa) and float(cpa) > 0 and float(cpa) <= CPA_BENCHMARK
    high_cvr = cvr >= HIGH_CONVERSION_RATE
    # Also accept strong acquisition rate with below-benchmark CPA
    strong_acq = car >= 3.0 and cpa_ok

    if volume_ok and cpa_ok and (high_cvr or strong_acq):
        return "Scale / Continue"

    # Moderate: CPC still in band but approved conversion weak / thin volume
    if cpc <= CPC_BENCHMARK * 1.25 and approved <= 1:
        return "Pause / Optimize"

    if not cpa_ok and spent > 0 and approved > 0:
        return "Pause / Optimize"

    return "Pause / Optimize"


def apply_decisions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Decision"] = out.apply(classify_ad, axis=1)
    return out


def aggregate_stats(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Aggregate performance across age, gender, interest, campaign."""

    def _agg(group_cols: list[str]) -> pd.DataFrame:
        g = (
            df.groupby(group_cols, dropna=False)
            .agg(
                Ads=("ad_id", "count"),
                Impressions=("Impressions", "sum"),
                Clicks=("Clicks", "sum"),
                Spent=("Spent", "sum"),
                Total_Conversion=("Total_Conversion", "sum"),
                Approved_Conversion=("Approved_Conversion", "sum"),
                Estimated_Revenue=("Estimated_Revenue", "sum"),
                Scale_Continue=(
                    "Decision",
                    lambda s: int((s == "Scale / Continue").sum()),
                ),
                Pause_Optimize=(
                    "Decision",
                    lambda s: int((s == "Pause / Optimize").sum()),
                ),
                Discontinue=(
                    "Decision",
                    lambda s: int((s == "Discontinue").sum()),
                ),
            )
            .reset_index()
        )
        g["CTR"] = np.where(
            g["Impressions"] > 0, g["Clicks"] / g["Impressions"] * 100, 0.0
        )
        g["CPC"] = np.where(g["Clicks"] > 0, g["Spent"] / g["Clicks"], 0.0)
        g["CPA"] = np.where(
            g["Approved_Conversion"] > 0,
            g["Spent"] / g["Approved_Conversion"],
            np.nan,
        )
        g["Conversion_Rate"] = np.where(
            g["Clicks"] > 0, g["Total_Conversion"] / g["Clicks"] * 100, 0.0
        )
        g["ROAS"] = np.where(
            g["Spent"] > 0, g["Estimated_Revenue"] / g["Spent"], 0.0
        )
        return g.sort_values("Spent", ascending=False)

    decision_summary = (
        df.groupby("Decision", dropna=False)
        .agg(
            Ads=("ad_id", "count"),
            Spent=("Spent", "sum"),
            Impressions=("Impressions", "sum"),
            Clicks=("Clicks", "sum"),
            Total_Conversion=("Total_Conversion", "sum"),
            Approved_Conversion=("Approved_Conversion", "sum"),
            Estimated_Revenue=("Estimated_Revenue", "sum"),
        )
        .reset_index()
    )
    decision_summary["CPA"] = np.where(
        decision_summary["Approved_Conversion"] > 0,
        decision_summary["Spent"] / decision_summary["Approved_Conversion"],
        np.nan,
    )

    return {
        "by_decision": decision_summary,
        "by_age": _agg(["age"]),
        "by_gender": _agg(["gender"]),
        "by_age_gender": _agg(["age", "gender"]),
        "by_interest": _agg(["interest"]),
        "by_campaign": _agg(["xyz_campaign_id"]),
        "benchmarks": pd.DataFrame(
            [
                {
                    "CPA_BENCHMARK": CPA_BENCHMARK,
                    "CPC_BENCHMARK": CPC_BENCHMARK,
                    "HIGH_CONVERSION_RATE_PCT": HIGH_CONVERSION_RATE,
                    "MIN_IMPRESSIONS": MIN_IMPRESSIONS,
                    "MIN_CLICKS": MIN_CLICKS,
                    "HIGH_SPEND_THRESHOLD": HIGH_SPEND_THRESHOLD,
                    "PROHIBITIVE_CPA": CPA_BENCHMARK * PROHIBITIVE_CPA_MULTIPLIER,
                }
            ]
        ),
    }


def export_workbook(tables: dict[str, pd.DataFrame], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, frame in tables.items():
            # Excel sheet names max 31 chars
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)


def run_decision_engine(
    metrics_path: Path | str | None = None,
    write_metrics: bool = True,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Classify ads, write metrics CSV + summary workbook."""
    if metrics_path and Path(metrics_path).exists():
        df = pd.read_csv(metrics_path)
    else:
        # Ensure KPIs exist (pipeline can start here)
        df = clean_and_engineer(output_path=None)

    decided = apply_decisions(df)
    tables = aggregate_stats(decided)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if write_metrics:
        decided.to_csv(METRICS_CSV, index=False)
    export_workbook(tables, DECISIONS_XLSX)
    return decided, tables


def main() -> None:
    decided, tables = run_decision_engine()
    print(f"Wrote metrics → {METRICS_CSV} ({len(decided):,} rows)")
    print(f"Wrote summary → {DECISIONS_XLSX}")
    print(decided["Decision"].value_counts().to_string())
    print("\nCampaign rollup:")
    print(tables["by_campaign"].to_string(index=False))


if __name__ == "__main__":
    main()
