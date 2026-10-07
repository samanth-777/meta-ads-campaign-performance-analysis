"""Baseline exploratory data analysis for the Meta / KAG ads dataset.

Day-1 workspace helper: load the CR-terminated CSV, print shape / schema /
campaign mix, and write a lightweight summary for later pipeline stages.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "KAG_conversion_data.csv"
EDA_SUMMARY = PROJECT_ROOT / "output" / "eda_baseline_summary.csv"


def load_raw(path: Path | str = DEFAULT_INPUT) -> pd.DataFrame:
    """Load KAG conversion data (CR line terminators)."""
    df = pd.read_csv(path, lineterminator="\r")
    df = df.dropna(how="all")
    df.columns = [c.strip() for c in df.columns]
    return df.reset_index(drop=True)


def baseline_eda(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute campaign-level baseline rollups used in early exploration."""
    if df is None:
        df = load_raw()

    summary = (
        df.groupby("xyz_campaign_id", as_index=False)
        .agg(
            ads=("ad_id", "count"),
            impressions=("Impressions", "sum"),
            clicks=("Clicks", "sum"),
            spent=("Spent", "sum"),
            total_conversion=("Total_Conversion", "sum"),
            approved_conversion=("Approved_Conversion", "sum"),
        )
        .sort_values("spent", ascending=False)
    )
    return summary


def main() -> None:
    df = load_raw()
    print(f"Loaded {len(df):,} ads from {DEFAULT_INPUT.name}")
    print(f"Columns: {list(df.columns)}")
    print("\nAge bands:", df["age"].value_counts().to_dict())
    print("Gender:", df["gender"].value_counts().to_dict())
    print("Interests (nunique):", df["interest"].nunique())

    summary = baseline_eda(df)
    EDA_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(EDA_SUMMARY, index=False)
    print("\nCampaign baseline:")
    print(summary.to_string(index=False))
    print(f"\nWrote {EDA_SUMMARY}")


if __name__ == "__main__":
    main()
