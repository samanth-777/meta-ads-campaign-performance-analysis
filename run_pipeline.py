#!/usr/bin/env python3
"""Run the full marketing analytics pipeline end-to-end."""

from __future__ import annotations

from src.clean_and_engineer import clean_and_engineer
from src.decision_engine import run_decision_engine
from src.eda import baseline_eda, load_raw
from src.segmentation import run_segmentation
from src.visualize import generate_figures


def main() -> None:
    print("0/4 Baseline EDA…")
    raw = load_raw()
    print(f"   {len(raw):,} ads loaded")
    print(baseline_eda(raw).to_string(index=False))

    print("\n1/4 Cleaning & engineering KPIs…")
    metrics = clean_and_engineer()
    print(f"   {len(metrics):,} rows with KPIs")

    print("\n2/4 Demographic segmentation…")
    segments = run_segmentation(metrics)
    print(segments["age_gender"].head(4).to_string(index=False))

    print("\n3/4 Classifying ads & exporting decisions…")
    decided, tables = run_decision_engine()
    print(decided["Decision"].value_counts().to_string())
    print("\n   Campaign summary:")
    cols = [
        "xyz_campaign_id",
        "Ads",
        "Spent",
        "Approved_Conversion",
        "CPA",
        "ROAS",
    ]
    print(tables["by_campaign"][cols].to_string(index=False))

    print("\n4/4 Rendering figures…")
    for path in generate_figures(decided):
        print(f"   {path}")

    print("\nPipeline complete.")
    print("  output/ad_performance_metrics.csv")
    print("  output/campaign_decisions_summary.xlsx")
    print("  output/audience_segments.csv")
    print("  reports/figures/*.png")


if __name__ == "__main__":
    main()
