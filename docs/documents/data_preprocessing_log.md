# Data Preprocessing Log - Submission Ready

**Purpose:** This document is the report-ready "Nhat ky Du lieu" for DATAVISION 2026 Round 2. It explains how the raw ET Club data was ingested, validated, cleaned, transformed, and prepared for dashboarding and analysis.

## 1. Data Sources Used

Only the official contest dataset was used for the core analysis. No external benchmark, macroeconomic, marketing-spend, or shipping-cost dataset was used in the primary conclusions.

| Layer | File | Rows | Role in Analysis |
|---|---|---:|---|
| Master | `users.csv` | 100,000 | Customer demographics and signup traffic source |
| Master | `products.csv` | 29,120 | Product category, brand, department, cost, retail price |
| Master | `distribution_centers.csv` | 10 | Distribution center reference |
| Transaction | `orders.csv` | 125,226 | Order-level status and fulfillment timestamps |
| Transaction | `order_items.csv` | 181,759 | Item-level sale price and product keys |
| Behavioral | `events.csv` | 2,431,963 | Website/session funnel events |
| Operational | `inventory_items.csv` | 490,705 | Unit-level inventory, sold status, cost, DC |

## 2. Ingestion and Type Conversion

All CSV files were loaded with Python/Pandas. Large event data can be loaded through DuckDB when available. Timestamps were parsed with UTC handling and then standardized to timezone-naive datetimes for grouping and Power BI compatibility.

Datetime fields standardized:

- `orders`: `created_at`, `shipped_at`, `delivered_at`, `returned_at`
- `order_items`: `created_at`, `shipped_at`, `delivered_at`, `returned_at`
- `inventory_items`: `created_at`, `sold_at`
- `events`: `created_at`
- `users`: `created_at`

Primary keys were checked for duplicates. Result: duplicate primary key count is 0 in all 7 raw tables.

## 3. Missing Value Policy

Missing values were not handled with one blanket rule. Each field was classified by business meaning.

| Missing Field | Interpretation | Treatment |
|---|---|---|
| `orders.shipped_at`, `orders.delivered_at` | Expected for cancelled/processing orders | Keep; exclude from SLA calculations when timestamp is required |
| `orders.returned_at` | Expected for non-returned orders | Keep; use status to define returns |
| `inventory_items.sold_at` | Unsold inventory | Convert to `is_sold = 0`; not treated as missing data |
| `events.user_id` | Anonymous or unauthenticated session traffic | Keep for session funnel; exclude from user-level LTV/RFM |
| `users.city` | Optional demographic field | Fill as `Unknown` in model table |
| `products.name`, `products.brand` | Very small master-data gap | Keep; show as unknown/missing label if needed |
| Transaction `created_at` missing | Cannot support trend/time grouping | Exclude from date-dependent fact model; retain in raw audit |

## 4. Data Validation Checks

### Primary and Foreign Keys

All tested non-null foreign keys have 0 orphan rows:

- `orders.user_id -> users.id`
- `order_items.order_id -> orders.order_id`
- `order_items.user_id -> users.id`
- `order_items.product_id -> products.id`
- `products.distribution_center_id -> distribution_centers.id`
- `inventory_items.product_id -> products.id`
- `inventory_items.product_distribution_center_id -> distribution_centers.id`
- `events.user_id -> users.id`, checked only where `user_id` is non-null

### Date Logic

Small timestamp inconsistencies were found and documented:

| Issue | Count | Treatment |
|---|---:|---|
| `shipped_at <= created_at` | 19 | Remove from shipping-time metrics |
| `delivered_at <= shipped_at` | 6 | Remove from delivery-time metrics |
| `returned_at <= delivered_at` | 5 | Remove from return-lag metrics |
| Returned orders missing delivery/return timestamps | 305 | Keep in return counts/value; exclude from timestamp-based analysis |

### Price and Product Logic

| Check | Result | Treatment |
|---|---:|---|
| `sale_price < 1` | 10 rows | Exclude from model revenue; retain in audit sample |
| `sale_price = 0` | 0 rows | No action |
| Missing product cost after join | 0 rows | Valid |
| Product `cost > retail_price` | 0 rows | Valid |

### Event Quality

Events were validated at session level:

- 681,759 sessions checked.
- 0 session time regressions.
- 0 bot candidates under the rule `>1000 events per user-day`.
- `events.traffic_source` and `users.traffic_source` differ by definition. Events include `Adwords` and `YouTube`; users include `Search` and `Display`.

## 5. Scope Decisions for Analysis

The raw data remains unchanged. Processed model tables use defined business scope:

1. **Annual trend scope:** use 2019-2023; exclude partial 2024 from YoY conclusions.
2. **Revenue recognition:** recognized revenue = `sale_price` for item status `Complete` or `Shipped`.
3. **Backlog:** `Processing` is not recognized revenue; it is treated as open pipeline/backlog.
4. **Leakage:** `Cancelled` and `Returned` are separated from recognized revenue and analyzed as lost/reversed value.
5. **Outlier treatment:** `sale_price < 1` is excluded from model revenue because it has negligible monetary impact but can distort price distributions.
6. **Funnel analysis:** use `session_id` and `event_type`; do not require `user_id`.
7. **Customer value analysis:** use `users`, `orders`, and `order_items`; require identifiable `user_id`.

## 6. Feature Engineering

| Feature | Formula / Logic | Purpose |
|---|---|---|
| `gross_profit` | `sale_price - product cost` | Profitability and margin analysis |
| `is_recognized_revenue` | status in `Complete`, `Shipped` | Separates recognized revenue from leakage/backlog |
| `GMV_All_Status` | all model-scope `sale_price` | Total order value before status filtering |
| `Recognized_Revenue` | `sale_price` if recognized, else 0 | Revenue dashboard metric |
| `Recognized_Gross_Profit` | `gross_profit` if recognized, else 0 | Profit dashboard metric |
| `Revenue_Lost_Cancelled` | `sale_price` if `Cancelled`, else 0 | Status leakage metric |
| `Return_Value` | `sale_price` if `Returned`, else 0 | Return leakage metric |
| `Processing_Backlog_Value` | `sale_price` if `Processing`, else 0 | Open order value |
| `is_sold` | inventory `sold_at` not null | Sell-through analysis |
| `holding_days` | cutoff date minus inventory `created_at` | Inventory age |
| `sunk_cost_risk` | inventory cost if unsold, else 0 | Frozen-capital proxy |
| RFM fields | recency, frequency, monetary on recognized orders | Customer segmentation |

## 7. Processed Data Model

| Output Table | Rows | Source and Scope |
|---|---:|---|
| `fact_transactions` | 168,528 | Item-level transaction fact, excluding partial 2024, missing dates, and sub-$1 items |
| `agg_funnel_monthly` | 1,828 | Monthly aggregation of event count and unique users by source and event type |
| `fact_inventory` | 490,705 | Unit-level inventory with sold/unsold and cost-risk fields |
| `dim_users` | 100,000 | User dimension with cleaned demographics and RFM segment |
| `dim_products` | 29,120 | Product dimension |
| `dim_dcs` | 10 | Distribution center dimension |
| `dim_date` | 1,843 | Date dimension |

## 8. Audit Files

The pipeline exports auditable files under `[DATAVISION2026]_VONG 2_DATASET/interim`:

- `phase1_quality_summary.json`
- `phase1_validation_summary.csv`
- `bot_candidates.csv`
- `quality_samples/*.csv`

These files make the preprocessing decisions reproducible and allow the report numbers to be traced back to raw records.

## 9. AI and External Data Declaration

AI tools were used as support for code drafting, documentation drafting, and analytical framing. All numeric results in this preprocessing log come from the local raw dataset and the reproducible Python pipeline. No external data source was used in the core preprocessing outputs.
