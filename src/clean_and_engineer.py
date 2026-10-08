"""Load KAG conversion data and engineer marketing KPIs.

The source CSV uses classic Mac CR (\\r) line terminators. pandas is
instructed to treat CR as the line terminator so rows parse correctly.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "KAG_conversion_data.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "ad_performance_metrics.csv"

# ---------------------------------------------------------------------------
# ROAS proxy assumptions (dataset has no revenue column)
# ---------------------------------------------------------------------------
# Approved conversions are valued by age-band LTV tiers (USD). Younger
# cohorts are assumed to have higher lifetime value for this product line.
APPROVED_VALUE_TIERS_USD: dict[str, float] = {
    "30-34": 150.0,  # Tier A — highest assumed LTV
    "35-39": 120.0,  # Tier B
    "40-44": 100.0,  # Tier C
    "45-49": 80.0,   # Tier D — lowest assumed LTV
}
DEFAULT_APPROVED_VALUE_USD = 100.0


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise divide; replace NaN/inf from zero denominators with NaN."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator.astype(float) / denominator.astype(float)
    return result.replace([np.inf, -np.inf], np.nan)


def load_raw_data(path: Path | str = DEFAULT_INPUT) -> pd.DataFrame:
    """Load the CR-terminated KAG conversion CSV into a DataFrame."""
    path = Path(path)
    # Explicit CR terminator — the file uses \\r only (no LF).
    df = pd.read_csv(path, lineterminator="\r")
    df = df.dropna(how="all")
    # Strip accidental whitespace from string columns / column names
    df.columns = [c.strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def engineer_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Add CTR, CPC, CPA, conversion rates, and ROAS proxy columns.

    Divide-by-zero policy
    ---------------------
    * Ratio KPIs that are undefined (zero denominator) become NaN, then
      filled with 0.0 so downstream aggregates stay numeric.
    * Cost metrics with zero activity (no clicks / no conversions) are
      filled with 0.0 when spend is also 0; when spend > 0 but the
      conversion denominator is 0, CPA-style metrics stay as a large
      sentinel (NaN→ filled after decision engine may flag separately).
      Here we fill cost-per-* NaNs with 0 when Spent==0, else leave a
      high-cost proxy of NaN that decision_engine treats as prohibitive.
    """
    out = df.copy()

    # CTR (%) = (Clicks / Impressions) * 100
    out["CTR"] = safe_divide(out["Clicks"], out["Impressions"]) * 100.0
    out["CTR"] = out["CTR"].fillna(0.0)

    # CPC = Spent / Clicks
    out["CPC"] = safe_divide(out["Spent"], out["Clicks"])
    out["CPC"] = out["CPC"].fillna(0.0)

    # Cost Per Total Conversion = Spent / Total_Conversion
    out["Cost_Per_Total_Conversion"] = safe_divide(
        out["Spent"], out["Total_Conversion"]
    )
    # Zero spend + zero conversions → 0; spend with zero conversions → NaN
    # (decision engine reads Approved_Conversion==0 + spend for discontinue)
    mask_zero_spend = out["Spent"] <= 0
    out.loc[mask_zero_spend, "Cost_Per_Total_Conversion"] = out.loc[
        mask_zero_spend, "Cost_Per_Total_Conversion"
    ].fillna(0.0)

    # CPA = Spent / Approved_Conversion
    out["CPA"] = safe_divide(out["Spent"], out["Approved_Conversion"])
    out.loc[mask_zero_spend, "CPA"] = out.loc[mask_zero_spend, "CPA"].fillna(0.0)

    # Conversion Rate (%) = (Total_Conversion / Clicks) * 100
    out["Conversion_Rate"] = (
        safe_divide(out["Total_Conversion"], out["Clicks"]) * 100.0
    )
    out["Conversion_Rate"] = out["Conversion_Rate"].fillna(0.0)

    # Customer Acquisition Rate (%) = (Approved_Conversion / Clicks) * 100
    out["Customer_Acquisition_Rate"] = (
        safe_divide(out["Approved_Conversion"], out["Clicks"]) * 100.0
    )
    out["Customer_Acquisition_Rate"] = out["Customer_Acquisition_Rate"].fillna(0.0)

    # ROAS proxy = estimated_revenue / Spent
    # estimated_revenue = Approved_Conversion * age-tier value
    out["Approved_Value_USD"] = (
        out["age"].map(APPROVED_VALUE_TIERS_USD).fillna(DEFAULT_APPROVED_VALUE_USD)
    )
    out["Estimated_Revenue"] = out["Approved_Conversion"] * out["Approved_Value_USD"]
    out["ROAS"] = safe_divide(out["Estimated_Revenue"], out["Spent"])
    out["ROAS"] = out["ROAS"].fillna(0.0)

    # Replace residual inf (defensive)
    numeric_cols = out.select_dtypes(include=[np.number]).columns
    out[numeric_cols] = out[numeric_cols].replace([np.inf, -np.inf], np.nan)

    return out


def clean_and_engineer(
    input_path: Path | str = DEFAULT_INPUT,
    output_path: Path | str | None = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """Full clean + KPI engineering step. Optionally writes CSV handoff."""
    df = load_raw_data(input_path)
    metrics = engineer_kpis(df)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metrics.to_csv(output_path, index=False)
    return metrics


def main() -> None:
    metrics = clean_and_engineer()
    print(f"Wrote {len(metrics):,} rows → {DEFAULT_OUTPUT}")
    print(
        "KPI columns:",
        [
            "CTR",
            "CPC",
            "Cost_Per_Total_Conversion",
            "CPA",
            "Conversion_Rate",
            "Customer_Acquisition_Rate",
            "ROAS",
        ],
    )


if __name__ == "__main__":
    main()
