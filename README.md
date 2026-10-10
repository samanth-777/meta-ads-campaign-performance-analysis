# Facebook Ad Campaign Analytics & Optimization

Portfolio project that turns the public **KAG conversion** Facebook ads dataset into KPI-ready tables, a rule-based scale/pause/kill decision engine, and presentation figures for budget reallocation.

**Run the full pipeline**

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Or module-by-module:

```bash
python -m src.clean_and_engineer
python -m src.decision_engine
python -m src.visualize
```

| Artifact | Path |
|----------|------|
| Ad-level KPIs + decisions | `output/ad_performance_metrics.csv` |
| Campaign / demo rollups | `output/campaign_decisions_summary.xlsx` |
| Figures | `reports/figures/*.png` |

---

## Executive Summary

Audited **1,143 ads** across campaigns **916**, **936**, and **1178**.

| Metric | Value |
|--------|------:|
| Total spend audited | **$58,705.23** |
| Impressions | 213,434,828 |
| Clicks | 38,165 |
| Total conversions (enquiries) | 3,264 |
| Approved conversions (purchases) | **1,079** |
| Portfolio CPA | **$54.41** |
| Portfolio CPC | $1.54 |
| Portfolio CTR | 0.018% |
| Conversion rate (enquiry / click) | 8.55% |
| Customer acquisition rate | 2.83% |
| Estimated ROAS (tiered proxy) | **2.26×** |

**Budget waste signal:** **224 ads** classified **Discontinue**, carrying **$25,695.23** in spend (≈44% of budget). Of that, **$14,754.42** was spent on ads with **zero approved conversions**. Reallocating discontinue spend toward **Scale / Continue** ads (251 ads, $17,781.68 spend, CPA **$27.96**) is the primary optimization lever.

Decision mix: **251 Scale / Continue** · **668 Pause / Optimize** · **224 Discontinue**.

---

## KPI Definitions

| KPI | Formula |
|-----|---------|
| CTR (%) | `(Clicks / Impressions) × 100` |
| CPC | `Spent / Clicks` |
| Cost Per Total Conversion | `Spent / Total_Conversion` |
| CPA | `Spent / Approved_Conversion` |
| Conversion Rate (%) | `(Total_Conversion / Clicks) × 100` |
| Customer Acquisition Rate (%) | `(Approved_Conversion / Clicks) × 100` |
| ROAS (proxy) | `Estimated_Revenue / Spent` |

**ROAS proxy value tiers** (dataset has no revenue — documented assumptions in `src/clean_and_engineer.py`):

| Age band | Assumed value / approved conversion |
|----------|------------------------------------:|
| 30–34 | $150 |
| 35–39 | $120 |
| 40–44 | $100 |
| 45–49 | $80 |

Divide-by-zero is handled safely (NaN/inf → 0 for rates; cost metrics stay NaN when spend > 0 but conversions = 0 so the decision engine can flag waste).

---

## Decision Engine Benchmarks

Defined in `src/decision_engine.py`:

| Benchmark | Value | Rationale |
|-----------|------:|-----------|
| CPA benchmark | $55 | ≈ portfolio CPA ($54.41) |
| CPC ceiling | $1.75 | Slightly above portfolio CPC ($1.54) |
| High conversion rate | ≥ 10% | Above portfolio CVR (8.55%) |
| Volume floor | ≥ 10k impressions & ≥ 5 clicks | Consistent delivery |
| High-spend waste | Spend ≥ $20 with 0 approved | Clear discontinue |
| Prohibitive CPA | > 2× CPA benchmark ($110) | Uneconomic even with sales |

**Labels**

- **Scale / Continue** — high CVR (or strong acquisition rate), CPA ≤ $55, volume floor met  
- **Pause / Optimize** — moderate: CPC acceptable but approved conversion weak / thin volume  
- **Discontinue** — high spend with zero approved conversions, or prohibitive CPA  

---

## Demographic Insights

Lowest-CPA segment: **Men 30–34** at **$25.55 CPA** (299 approved conversions on $7,640.92 spend; **39.1 approved conversions per $1k**).

Highest-CPA segment: **Women 45–49** at **$119.94 CPA** (112 approved on $13,433.21) — primary Pause/Discontinue review cohort.

| Age × Gender | Spend | Approved | CPA |
|--------------|------:|--------:|----:|
| 30–34 M | $7,640.92 | 299 | **$25.55** |
| 30–34 F | $7,611.48 | 195 | $39.03 |
| 35–39 M | $5,051.08 | 112 | $45.10 |
| 40–44 M | $4,193.15 | 77 | $54.46 |
| 35–39 F | $6,061.35 | 95 | $63.80 |
| 45–49 M | $7,317.46 | 96 | $76.22 |
| 40–44 F | $7,396.58 | 93 | $79.53 |
| 45–49 F | $13,433.21 | 112 | $119.94 |

---

## Campaign-Level Breakdown

| Campaign | Ads | Spend | Approved | CPA | CPC | CTR | ROAS (proxy) |
|----------|----:|------:|---------:|----:|----:|----:|-------------:|
| **1178** | 625 | **$55,662.15** | 872 | $63.83 | $1.54 | 0.018% | 1.92× |
| **936** | 464 | $2,893.37 | 183 | **$15.81** | $1.46 | 0.024% | **7.83×** |
| **916** | 54 | $149.71 | 24 | **$6.24** | $1.32 | 0.023% | **20.11×** |

**1178 vs 936:** Campaign **1178** absorbs **95% of spend** but delivers a **$63.83 CPA** (above the $55 benchmark) and only **1.92×** proxy ROAS. Campaign **936** is far more efficient (**$15.81 CPA**, **7.83× ROAS**) at a fraction of the budget — a strong candidate for scaled testing while 1178 ads in the Discontinue bucket are cut.

---

## Figures

1. `reports/figures/cpa_vs_spend_by_decision.png` — CPA vs spend by decision category  
2. `reports/figures/demographic_heatmap_age_gender.png` — Age × Gender conversion efficiency  
3. `reports/figures/funnel_leakage.png` — Impressions → Clicks → Total → Approved  

---

## Resume Bullet Points

- Audited **$58,705** across **1,143 Facebook ads**, engineering CTR, CPC, CPA, conversion rate, acquisition rate, and tiered ROAS proxies from the KAG conversion dataset.  
- Built a rule-based decision engine that flagged **224 ads ($25,695 / 44% of spend)** for discontinuation, including **$14,754** with zero approved conversions.  
- Identified **Men 30–34** as the lowest-CPA segment (**$25.55**) versus **Women 45–49** at **$119.94**, guiding demographic budget shifts.  
- Showed campaign **936** at **$15.81 CPA / 7.83× ROAS** outperforming dominant campaign **1178** (**$63.83 CPA / 1.92× ROAS**), recommending reallocation from wasteful 1178 ads.  
- Delivered production-ready Python pipeline (`run_pipeline.py`) exporting CSV/XLSX rollups and Seaborn executive visuals for stakeholder review.

---

## Project Layout

```
data/KAG_conversion_data.csv          # Source (CR line terminators)
src/eda.py                            # Baseline EDA / campaign rollups
src/clean_and_engineer.py             # Load + KPI engineering
src/segmentation.py                   # Age × Gender / interest segments
src/decision_engine.py                # Classify + Excel aggregates
src/visualize.py                      # Seaborn figures
run_pipeline.py                       # End-to-end entrypoint
notebooks/                            # Executive summary companion
output/                               # Metrics CSV + decisions workbook
reports/figures/                      # PNGs
requirements.txt
```

## Data Notes

Source: [Kaggle — Sales Conversion Optimization](https://www.kaggle.com/datasets/loveall/clicks-conversion-tracking) (`KAG_conversion_data.csv`). The file uses **CR-only** line endings; `pandas.read_csv(..., lineterminator="\\r")` handles this safely.
