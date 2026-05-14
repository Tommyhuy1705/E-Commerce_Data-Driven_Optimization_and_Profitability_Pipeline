# Phase 1: ETL and Data Cleaning

**Status:** Completed and rerun on 2026-05-08  
**Main script:** `Datavision2026/src/data_pipeline.py`  
**Dataset root:** `[DATAVISION2026]_VONG 2_DATASET`

## Objective

Load the 7 official raw CSV files, validate schema and data quality, document caveats, engineer model-ready metrics, and export clean CSV/Parquet tables for Power BI and analysis.

## Raw Inputs

| File | Rows | Key |
|---|---:|---|
| `users.csv` | 100,000 | `id` |
| `products.csv` | 29,120 | `id` |
| `distribution_centers.csv` | 10 | `id` |
| `orders.csv` | 125,226 | `order_id` |
| `order_items.csv` | 181,759 | `id` |
| `events.csv` | 2,431,963 | `id` |
| `inventory_items.csv` | 490,705 | `id` |

## Completed Checks

- [x] Load all 7 raw CSV files.
- [x] Convert timestamp fields with UTC-safe parsing.
- [x] Check row counts, column counts, memory usage, null counts, and duplicate primary keys.
- [x] Validate order date sequences:
  - `shipped_at <= created_at`: 19 rows
  - `delivered_at <= shipped_at`: 6 rows
  - `returned_at <= delivered_at`: 5 rows
- [x] Validate order status consistency:
  - Cancelled orders with fulfillment timestamps: 0 rows
  - Returned orders missing delivery/return timestamps: 305 rows
- [x] Validate price and product logic:
  - `sale_price < 1`: 10 rows, excluded from model revenue
  - missing product cost after join: 0 rows
  - product `cost > retail_price`: 0 rows
- [x] Validate demographics:
  - duplicate users: 0
  - null city: 958, filled as `Unknown`
  - invalid age outside 13-120: 1,685, clipped in model table
- [x] Validate event behavior:
  - sessions checked: 681,759
  - session time regressions: 0
  - bot candidates above `>1000 events/user-day`: 0
  - null `user_id` events retained for session funnel: 1,125,671
- [x] Validate foreign keys. All tested non-null FK relationships have 0 orphan rows.
- [x] Export issue samples for audit under `interim/quality_samples`.

## Cleaning and Transformation Rules

| Area | Rule |
|---|---|
| Annual trends | Use 2019-2023; exclude partial 2024 from YoY conclusions |
| Revenue recognition | `Complete` and `Shipped` statuses only |
| Backlog | `Processing` tracked separately as open value |
| Leakage | `Cancelled` and `Returned` tracked separately from revenue |
| Price outliers | Exclude `sale_price < 1` from model revenue |
| Missing dates | Keep in raw audit; exclude from date-dependent facts/fulfillment metrics |
| Anonymous events | Keep for session funnel; exclude from user-level LTV/RFM |
| Inventory `sold_at` null | Treat as unsold stock, not missing data |

## Feature Engineering

- `gross_profit = sale_price - cost`
- `is_recognized_revenue = status in ["Complete", "Shipped"]`
- `GMV_All_Status`
- `Recognized_Revenue`
- `Recognized_Gross_Profit`
- `Revenue_Lost_Cancelled`
- `Return_Value`
- `Processing_Backlog_Value`
- `is_sold`
- `holding_days`
- `sunk_cost_risk`
- `holding_cost_estimate`
- RFM features and segments for customer analysis

## Processed Outputs

| Output | Rows | Use |
|---|---:|---|
| `fact_transactions.csv/parquet` | 168,528 | Item-level revenue, margin, leakage |
| `agg_funnel_monthly.csv/parquet` | 1,828 | Monthly event-source funnel |
| `fact_inventory.csv/parquet` | 490,705 | Inventory and holding-cost analysis |
| `dim_users.csv/parquet` | 100,000 | Customer dimension and RFM |
| `dim_products.csv/parquet` | 29,120 | Product dimension |
| `dim_dcs.csv/parquet` | 10 | Distribution center dimension |
| `dim_date.csv/parquet` | 1,843 | Date table |

## Audit Artifacts

| Artifact | Purpose |
|---|---|
| `interim/phase1_quality_summary.json` | Full structured validation summary |
| `interim/phase1_validation_summary.csv` | Flat checklist for reporting |
| `interim/bot_candidates.csv` | Bot-threshold output |
| `interim/quality_samples/*.csv` | Sample rows for documented issues |
| `docs/documents/data_quality_report.md` | Detailed quality report |
| `docs/documents/data_preprocessing_log.md` | Submission-ready Data Log |

## Final Assessment

Phase 1 is complete and fit for scoring under the "Khai thac va Tien xu ly du lieu" criterion. The current documentation is aligned with the raw dataset and provides both methodology and reproducible evidence.
