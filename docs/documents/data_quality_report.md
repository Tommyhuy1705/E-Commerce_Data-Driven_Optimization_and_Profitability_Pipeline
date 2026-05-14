# Data Quality Report - ET Club

**Project:** DATAVISION 2026  
**Report Date:** 2026-05-08  
**Source:** `[DATAVISION2026]_VONG 2_DATASET/raw`  
**Pipeline:** `Datavision2026/src/data_pipeline.py`  
**Status:** Passed with documented caveats

---

## 1. Executive Summary

All 7 raw CSV files were loaded, typed, profiled, validated, and transformed into model-ready CSV/Parquet tables for Power BI and analysis. The dataset is usable for business analysis after applying the scope rules below:

- Annual trend and model tables exclude partial 2024 records because 2024 only contains January observations.
- Items with `sale_price < 1` are excluded from model revenue because they are extreme price anomalies and immaterial in value.
- Rows with missing transaction timestamps are retained in raw audit outputs but excluded from date-dependent trend and fulfillment calculations.
- Null `sold_at` in inventory and null shipping/return timestamps in orders are treated as business-state nulls where appropriate, not automatic data errors.
- Events with null `user_id` are retained for session funnel analysis but excluded from user-level LTV/RFM analysis.

## 2. Raw Table Profile

| Table | Rows | Columns | Duplicate PK | Key Nulls / Notes |
|---|---:|---:|---:|---|
| users | 100,000 | 15 | 0 | `city`: 958; `created_at`: 2,393 |
| products | 29,120 | 9 | 0 | `name`: 2; `brand`: 24 |
| distribution_centers | 10 | 4 | 0 | No nulls |
| orders | 125,226 | 9 | 0 | `created_at`: 3,063; timestamp nulls expected by status |
| order_items | 181,759 | 11 | 0 | `created_at`: 4,405; timestamp nulls expected by status |
| events | 2,431,963 | 13 | 0 | `user_id`: 1,125,671; `created_at`: 31,501; `city`: 23,080 |
| inventory_items | 490,705 | 12 | 0 | `sold_at`: 313,351; `created_at`: 4,405; `product_brand`: 401 |

## 3. Validation Results

### 3.1 Primary Keys and Foreign Keys

All primary keys are unique. All tested non-null foreign keys resolve to their parent table.

| Relationship | Checked Rows | Orphan Rows | Orphan % |
|---|---:|---:|---:|
| `orders.user_id -> users.id` | 125,226 | 0 | 0.0% |
| `order_items.order_id -> orders.order_id` | 181,759 | 0 | 0.0% |
| `order_items.user_id -> users.id` | 181,759 | 0 | 0.0% |
| `order_items.product_id -> products.id` | 181,759 | 0 | 0.0% |
| `products.distribution_center_id -> distribution_centers.id` | 29,120 | 0 | 0.0% |
| `inventory_items.product_id -> products.id` | 490,705 | 0 | 0.0% |
| `inventory_items.product_distribution_center_id -> distribution_centers.id` | 490,705 | 0 | 0.0% |
| `events.user_id -> users.id`, non-null only | 1,306,292 | 0 | 0.0% |

### 3.2 Date and Status Logic

| Check | Count | Treatment |
|---|---:|---|
| `shipped_at <= created_at` | 19 | Excluded from shipping SLA calculations; sample exported |
| `delivered_at <= shipped_at` | 6 | Excluded from delivery SLA calculations; sample exported |
| `returned_at <= delivered_at` | 5 | Excluded from return-lag calculations; sample exported |
| Cancelled orders with ship/delivery/return timestamps | 0 | Valid |
| Returned orders missing `delivered_at` | 305 | Kept for revenue/return counts; excluded from delivery-time analysis |
| Returned orders missing `returned_at` | 305 | Kept for revenue/return counts; excluded from return-lag analysis |
| Negative `num_of_item` | 0 | Valid |

### 3.3 Price and Product Logic

| Check | Count | Treatment |
|---|---:|---|
| `sale_price < 1` in `order_items` | 10 | Excluded from model revenue; retained in audit sample |
| `sale_price = 0` | 0 | Valid |
| Missing product cost after product join | 0 | Valid |
| Product `cost > retail_price` | 0 | Valid |
| Null product category/cost/retail price | 0 | Valid |

### 3.4 Customer and Demographic Logic

| Check | Count | Treatment |
|---|---:|---|
| Duplicate users | 0 | Valid |
| Null age | 0 | Valid |
| Null gender | 0 | Valid |
| Null city | 958 | Filled as `Unknown` in model-ready table |
| Invalid age, outside 13-120 | 1,685 | Clipped to [13, 120] for model-ready table |

### 3.5 Behavioral Events

| Check | Result | Treatment |
|---|---:|---|
| Event rows | 2,431,963 | Loaded and aggregated for Power BI |
| Sessions checked | 681,759 | Session-level funnel uses `session_id` |
| Session time regressions | 0 | Valid |
| Bot candidate user-day pairs, threshold >1000 events | 0 | No records removed |
| Null `user_id` events | 1,125,671, 46.3% | Kept for anonymous/session funnel; excluded from user-level metrics |
| Event source values not present in signup-source users table | `Adwords`, `YouTube` | Documented as different source definitions |

Event types in the raw file are `home`, `department`, `product`, `cart`, `purchase`, and `cancel`. The source event data should not be relabeled as `page_view` or `cart_add` in the final report.

## 4. Cleaning and Preprocessing Actions

| Area | Action | Rationale |
|---|---|---|
| Datetime | Parsed UTC timestamps and removed timezone for consistent grouping | Avoid regional/timezone inconsistency |
| 2024 partial data | Flagged/excluded from annual model tables | Prevent false YoY decline from incomplete year |
| Revenue anomaly | Excluded 10 rows with `sale_price < 1` from model revenue | Materiality is negligible; prevents skew in price analytics |
| Costs and profit | Joined products to order items and calculated `gross_profit = sale_price - cost` | Required for margin and profitability analysis |
| Status metrics | Created `is_recognized_revenue` for `Complete` and `Shipped` | Separates real revenue from backlog/cancel/return leakage |
| Users | Filled missing city as `Unknown`; clipped invalid ages | Preserve rows while controlling demographic outliers |
| Inventory | Created `is_sold`, `holding_days`, `sunk_cost_risk`, `holding_cost_estimate` | Supports supply-chain and working-capital analysis |
| Events | Aggregated 2.43M events into monthly source-event table | Keeps Power BI model light while preserving funnel signal |

## 5. Model Scope Reconciliation

The raw dataset is preserved. The Power BI model focuses on analysis-ready rows.

| Reconciliation Item | Value |
|---|---:|
| Raw order-item rows | 181,759 |
| Rows excluded for `sale_price < 1` | 10 |
| Rows after price filter | 181,749 |
| Eligible rows after excluding 2024 partial and missing order dates | 168,537 |
| Final `fact_transactions` rows | 168,528 |
| Raw GMV, all status | $10,827,118.91 |
| Model-scope GMV | $10,029,376.13 |
| GMV removed from model scope | $797,742.78 |

The difference between eligible rows and final fact rows is caused by sub-$1 price rows inside the eligible period. The excluded GMV is mostly partial-2024 and missing-date scope, not deletion of valid historical business records.

## 6. Processed Outputs

| Output | Rows | Purpose |
|---|---:|---|
| `fact_transactions.csv/parquet` | 168,528 | Item-level transaction fact for recognized revenue, leakage, margin |
| `agg_funnel_monthly.csv/parquet` | 1,828 | Monthly event-source funnel aggregate |
| `fact_inventory.csv/parquet` | 490,705 | Inventory unit fact for sell-through and holding cost |
| `dim_users.csv/parquet` | 100,000 | Customer dimension with RFM fields |
| `dim_products.csv/parquet` | 29,120 | Product dimension |
| `dim_dcs.csv/parquet` | 10 | Distribution center dimension |
| `dim_date.csv/parquet` | 1,843 | Date dimension from 2019-01-01 to 2024-01-17 |

## 7. Audit Trail

Pipeline outputs are stored under `[DATAVISION2026]_VONG 2_DATASET/interim`:

- `phase1_quality_summary.json`: full structured quality report.
- `phase1_validation_summary.csv`: flat validation checklist for reporting.
- `bot_candidates.csv`: bot threshold result.
- `quality_samples/`: sample records for each documented data issue.

Sample files exported:

| Sample File | Rows |
|---|---:|
| `orders_shipped_before_created.csv` | 19 |
| `orders_delivered_before_shipped.csv` | 6 |
| `orders_returned_before_delivered.csv` | 5 |
| `returned_orders_missing_timestamps.csv` | 50 |
| `order_items_sale_price_lt_1.csv` | 10 |
| `events_null_user_id_sample.csv` | 50 |
| `inventory_missing_created_at_sample.csv` | 50 |
| `products_missing_name_or_brand_sample.csv` | 26 |

## 8. Limitations and Assumptions

1. **No net profit fields.** Dataset has product cost but not shipping cost, payment fee, warehouse labor, tax, discount, return reason, or marketing spend. Therefore the report uses gross profit and operational proxies, not net profit.
2. **Traffic source definitions differ.** `users.traffic_source` is signup/acquisition source, while `events.traffic_source` is session source. They are analyzed separately.
3. **Anonymous traffic is material.** 46.3% of events do not have `user_id`; funnel analysis must be session-based, while user LTV/RFM uses users and orders.
4. **Partial 2024.** 2024 is not used for annual trend conclusions.
5. **Inventory null `sold_at`.** Null `sold_at` means unsold stock, not missing data.

## 9. Sign-Off for Analysis

The dataset is fit for the contest analysis after applying the documented preprocessing rules. The most important governance decision is to clearly separate:

- Raw all-status GMV from recognized revenue.
- Session-source funnel from signup-source customer LTV.
- Business-state nulls from true missing values.
- Full raw audit data from model-scope data used for yearly trend and Power BI.
