"""Demographic audience segmentation on engineered ad KPIs.

Builds Age × Gender (and interest) segments with CTR / CPC / CPA rollups so
the decision engine and README can cite audience efficiency.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.clean_and_engineer import PROJECT_ROOT, clean_and_engineer

SEGMENTS_CSV = PROJECT_ROOT / "output" / "audience_segments.csv"


def build_segments(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Aggregate KPIs across demographic and interest cuts."""

    def _roll(cols: list[str]) -> pd.DataFrame:
        g = (
            df.groupby(cols, dropna=False)
            .agg(
                ads=("ad_id", "count"),
                impressions=("Impressions", "sum"),
                clicks=("Clicks", "sum"),
                spent=("Spent", "sum"),
                total_conversion=("Total_Conversion", "sum"),
                approved_conversion=("Approved_Conversion", "sum"),
            )
            .reset_index()
        )
        g["CTR"] = np.where(
            g["impressions"] > 0, g["clicks"] / g["impressions"] * 100, 0.0
        )
        g["CPC"] = np.where(g["clicks"] > 0, g["spent"] / g["clicks"], 0.0)
        g["CPA"] = np.where(
            g["approved_conversion"] > 0,
            g["spent"] / g["approved_conversion"],
            np.nan,
        )
        g["conversion_rate"] = np.where(
            g["clicks"] > 0, g["total_conversion"] / g["clicks"] * 100, 0.0
        )
        return g.sort_values("CPA", na_position="last")

    return {
        "age_gender": _roll(["age", "gender"]),
        "age": _roll(["age"]),
        "gender": _roll(["gender"]),
        "interest": _roll(["interest"]),
    }


def lowest_cpa_segment(segments: pd.DataFrame) -> pd.Series:
    """Return the Age × Gender row with the lowest finite CPA."""
    valid = segments.dropna(subset=["CPA"])
    return valid.loc[valid["CPA"].idxmin()]


def run_segmentation(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if df is None:
        df = clean_and_engineer(output_path=None)
    tables = build_segments(df)
    SEGMENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    tables["age_gender"].to_csv(SEGMENTS_CSV, index=False)
    return tables


def main() -> None:
    tables = run_segmentation()
    best = lowest_cpa_segment(tables["age_gender"])
    print("Age × Gender segments (head):")
    print(tables["age_gender"].head(8).to_string(index=False))
    print(
        f"\nLowest-CPA segment: {best['age']} {best['gender']} "
        f"@ ${best['CPA']:.2f} CPA"
    )
    print(f"Wrote {SEGMENTS_CSV}")


if __name__ == "__main__":
    main()
