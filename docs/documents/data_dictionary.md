# Data Dictionary - ET Club Analytics

**Project:** DATAVISION 2026  
**Version:** 1.0  
**Date:** May 2026  
**Owner:** Data Engineering Team

---

## 📋 Mục Lục

1. [Fact Tables](#fact-tables)
2. [Dimension Tables](#dimension-tables)
3. [Aggregated Tables](#aggregated-tables)
4. [Data Types & Conventions](#data-types--conventions)

---

## Fact Tables

### Fact_Transactions

**Description:** Mỗi dòng là một item trong một order. Chứa dữ liệu bán hàng chi tiết.

**Row Count:** 168,528  
**Primary Key:** `order_item_id`  
**Foreign Keys:** `order_id`, `user_id`, `product_id`, `date_key`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| order_item_id | INT | NO | Unique ID for each line item | 12345 |
| order_id | INT | NO | Foreign key to orders | 5678 |
| user_id | INT | NO | Customer ID | 999 |
| product_id | INT | NO | Product ID | 42 |
| date_key | VARCHAR(8) | NO | Date in YYYYMMDD format (from created_at) | 20231215 |
| sale_price | DECIMAL(10,2) | NO | Actual selling price ($) | 89.99 |
| cost | DECIMAL(10,2) | YES | Cost from Dim_Products | 45.00 |
| gross_profit | DECIMAL(10,2) | YES | Calculated: sale_price - cost | 44.99 |
| status | VARCHAR(50) | YES | Order status (Completed, Returned, Cancelled, Processing) | Completed |
| is_returned | TINYINT | NO | 1 if returned, 0 otherwise | 0 |

**Key Business Logic:**
- `gross_profit` = `sale_price` - `cost` (pre-calculated for Power BI performance)
- `is_returned` derived from `status == 'Returned'`
- Model scope excludes partial 2024, missing order dates, and `sale_price < $1`
- `GMV_All_Status`, `Recognized_Revenue`, `Revenue_Lost_Cancelled`, `Return_Value`, and `Processing_Backlog_Value` are separated to avoid mixing all-status GMV with recognized revenue

---

### Fact_Inventory

**Description:** Mỗi dòng là một unit của sản phẩm trong một distribution center. Focus trên unsold inventory để phân tích.

**Row Count:** 490,705  
**Primary Key:** `inventory_id`  
**Foreign Keys:** `product_id`, `center_id`, `created_date_key`, `sold_date_key`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| inventory_id | INT | NO | Unique ID for each inventory unit | 54321 |
| product_id | INT | NO | Product ID | 42 |
| center_id | INT | NO | Distribution Center ID | 3 |
| cost | DECIMAL(10,2) | NO | Unit cost | 30.00 |
| is_sold | TINYINT | NO | 1 if sold, 0 if unsold | 0 |
| created_at | DATETIME | NO | Date item was added to inventory | 2023-06-15 |
| sold_at | DATETIME | YES | Date item was sold (NULL if unsold) | NULL |
| holding_days | INT | NO | Days in inventory (2024-01-17 - created_at) | 247 |
| sunk_cost_risk | DECIMAL(10,2) | NO | cost × (1 - is_sold) | 30.00 |
| holding_cost_estimate | DECIMAL(10,2) | NO | Holding cost estimate to cutoff, using annualized carrying-rate assumption | 7.50 |

**Key Business Logic:**
- `is_sold` = 1 if `sold_at` is not null
- `holding_days` = Days from `created_at` to cutoff (2024-01-17)
- `sunk_cost_risk` = Cost of unsold items (opportunity cost)
- `holding_cost_estimate` = 25% annual carrying-rate assumption prorated by holding_days; interpret as a proxy to cutoff, not true recurring annual cost
- **Note:** low sell-through and aged unsold inventory indicate inventory planning risk

---

### Agg_Funnel_Monthly

**Description:** Pre-aggregated marketing funnel data từ 2.4M raw events. Mỗi dòng là event counts cho một (month, event_type, traffic_source).

**Row Count:** 1,828  
**Primary Key:** (year_month, event_type, traffic_source)  
**Foreign Keys:** None (direct aggregation)

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| year_month | DATE | NO | Date (first day of month) | 2023-06-01 |
| event_type | VARCHAR(50) | NO | Type of event | home, department, product, cart, purchase, cancel |
| traffic_source | VARCHAR(50) | NO | Source of traffic | Email, Organic, Search, Adwords |
| event_count | INT | NO | Total events in period | 5432 |
| unique_users | INT | NO | Unique user count | 1234 |

**Key Business Logic:**
- Aggregated from raw `events.csv` (2.4M rows) to reduce Power BI file size
- Formula: `GROUP BY (year_month, event_type, traffic_source) SUM(1) COUNT(DISTINCT user_id)`
- **Importance:** This is the ONLY way to load funnel data into Power BI without crashing
- Event types:
  * `product` = User viewed product detail (845.6K total)
  * `cart` = Added to cart / cart step (595.9K total)
  * `department` = Department/category navigation (595.3K total)
  * `home` = Homepage event (87.7K total)
  * `purchase` = Completed purchase (181.7K total)
  * `cancel` = Cart abandoned or purchase cancelled (125.5K total)

**⚠️ Critical Note:** `cancel` event is different from "cancelled order". It's session/cart abandonment.

---

## Dimension Tables

### Dim_Users

**Description:** Customer master data with demographics, acquisition source, RFM segment, and clustering label.

**Row Count:** 100,000  
**Primary Key:** `user_id`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| user_id | INT | NO | Customer ID (PK) | 999 |
| age | INT | YES | Age of customer | 28 |
| gender | VARCHAR(10) | YES | M/F/Other | M |
| country | VARCHAR(50) | YES | Country | United States |
| city | VARCHAR(50) | YES | City | New York |
| traffic_source | VARCHAR(50) | YES | Acquisition source (from signup) | Email, Search, Organic |
| Recency | INT | YES | Days since last purchase | 120 |
| Frequency | INT | YES | Number of orders | 1 |
| Monetary | DECIMAL(12,2) | YES | Total value of orders | 150.00 |
| rfm_segment | VARCHAR(20) | YES | RFM Segment: Champions, Loyal, At Risk, About to Lose, Lost | Lost |
| cluster_label | VARCHAR(50) | YES | K-Means cluster (Phase 3 only) | Selective Buyers |

**Key Business Logic:**
- `Recency`, `Frequency`, `Monetary` calculated as of 2023-12-31
- `rfm_segment` derived from R/F/M scores (quintile-based)
- RFM Segments:
  * **Champions:** R≥13 (high recency, frequency, monetary)
  * **Loyal:** 10≤score<13
  * **At Risk:** 7≤score<10
  * **About to Lose:** 4≤score<7
  * **Lost:** score<4
- `cluster_label` is NULL if Phase 3 (K-Means) not completed

---

### Dim_Products

**Description:** Product master data with category, brand, pricing, cost, and department.

**Row Count:** 29,120  
**Primary Key:** `product_id`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| product_id | INT | NO | Product ID (PK) | 42 |
| category | VARCHAR(100) | YES | Product category | Outerwear & Coats |
| brand | VARCHAR(100) | YES | Brand name | Nike |
| retail_price | DECIMAL(10,2) | YES | MSRP (recommended selling price) | 199.99 |
| cost | DECIMAL(10,2) | YES | Cost of goods sold (COGS) | 100.00 |
| department | VARCHAR(50) | YES | Business unit | Menswear |

**Key Business Logic:**
- `cost` should always be < `retail_price` (validation in Phase 1)
- **Note:** Actual `sale_price` may differ from `retail_price` if discounts applied
- In this dataset: **No discounting detected** → Sale price ≈ Retail price
- 26 unique categories across products

---

### Dim_DCs (Distribution Centers)

**Description:** Distribution center locations and metadata.

**Row Count:** 10  
**Primary Key:** `dc_id`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| dc_id | INT | NO | DC ID (PK) | 1 |
| name | VARCHAR(100) | NO | DC name | DC - New York |
| location | VARCHAR(100) | YES | Full address | 123 Main St, NY 10001 |
| state | VARCHAR(2) | YES | State code | NY |
| region | VARCHAR(50) | YES | Geographic region | Northeast |

**Key Business Logic:**
- All 10 DCs are in USA
- Used for inventory distribution analysis

---

### Dim_Date

**Description:** Standard date dimension for time intelligence and filtering.

**Row Count:** 1,843 (2019-01-01 to 2024-01-17)  
**Primary Key:** `date_key`

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| date_key | VARCHAR(8) | NO | Date in YYYYMMDD format (PK) | 20231215 |
| date | DATE | NO | Full date | 2023-12-15 |
| year | INT | NO | Year | 2023 |
| month | INT | NO | Month (1-12) | 12 |
| quarter | INT | NO | Quarter (1-4) | 4 |
| day_of_week | INT | NO | Day of week (0=Mon, 6=Sun) | 4 |
| week_of_year | INT | NO | Week number (1-53) | 50 |
| year_month | VARCHAR(7) | NO | YYYY-MM format | 2023-12 |
| is_weekend | TINYINT | NO | 1 if Saturday/Sunday, 0 otherwise | 0 |

**Key Business Logic:**
- **Must be marked as Date Table in Power BI** for time intelligence functions
- Used for all revenue trending and YoY comparisons
- Format `date_key` as text (YYYYMMDD) to avoid regional date format issues

---

## Aggregated Tables

All aggregated tables are stored in `data/processed/` as `.parquet` files.

### List of All Processed Tables

| Table Name | Source | Row Count | Purpose |
|------------|--------|-----------|---------|
| fact_transactions.parquet | orders + order_items + products | 168.5K | Primary fact for revenue/profit |
| fact_inventory.parquet | inventory_items enriched | 490.7K | Inventory analysis |
| agg_funnel_monthly.parquet | events aggregated | 1,828 | Marketing funnel (lightweight) |
| dim_users.parquet | users + rfm | 100.0K | Customer dimension |
| dim_products.parquet | products | 29.1K | Product dimension |
| dim_dcs.parquet | distribution_centers | 10 | DC dimension |
| dim_date.parquet | generated date table | 1,843 | Time intelligence |

### Additional Analysis Files (CSVs)

| File | Phase | Purpose |
|------|-------|---------|
| rfm_segment_analysis.csv | 2 | RFM segment profiles & metrics |
| cohort_retention_analysis.csv | 2 | Signup cohort retention rates |
| ltv_cac_analysis.csv | 2 | Unit economics (LTV, CAC, ratio) |
| annual_revenue_analysis.csv | 2 | GMV, recognized revenue, gross profit, leakage, and YoY growth |
| category_performance_analysis.csv | 2 | Category KPIs & quadrant assignment |
| return_cost_analysis.csv | 2 | Return metrics & cost quantification |
| funnel_analysis.csv | 2 | Conversion funnel rates by traffic source |
| journey_funnel_by_source.csv | 2 | Source-level e-commerce journey reach and product/cart/purchase CVR |
| traffic_source_performance.csv | 2 | Traffic source purchase-intensity analysis; no ROI conclusion without spend data |
| basket_affinity_analysis.csv | 2 | Category pair support, confidence, lift, and bundle/cross-sell action |
| price_band_performance.csv | 2 | Department/category/price-band margin, leakage, return, and pricing/PDP action |
| inventory_turnover_analysis.csv | 2 | Sell-through by category & DC |
| holding_cost_analysis.csv | 2 | Frozen capital & holding costs |
| inventory_abc_aging_by_category_dc.csv | 2 | ABC class, aged inventory cost, sell-through, and category-DC inventory action |
| return_cancel_root_cause_proxy.csv | 2 | Proxy root-cause table for return/cancel/processing risk by category-brand-price-fulfillment bucket |
| fulfillment_performance.csv | 2 | Order fulfillment KPIs |
| clustering_analysis.csv | 3 | K-Means cluster profiles (if Phase 3 done) |
| demand_forecast_12m.csv | 3 | Baseline 12-month demand forecast; check model summary before use |

---

## Data Types & Conventions

### Naming Conventions

| Type | Prefix | Example |
|------|--------|---------|
| Fact Table | `Fact_` | `Fact_Transactions` |
| Dimension Table | `Dim_` | `Dim_Users` |
| Aggregated Table | `Agg_` | `Agg_Funnel_Monthly` |
| Measure | `[Brackets]` | `[Total Revenue]` |

### Column Naming

- **Fact Tables:** lowercase with underscores (`order_id`, `sale_price`)
- **Dimension Tables:** lowercase with underscores (`user_id`, `product_id`)
- **Calculated Columns:** PascalCase (`Recency`, `GrossProfit`)
- **Date fields:** Always include `_at` or `_date` suffix (`created_at`, `date_key`)

### Data Type Standards

| Type | Usage | Example |
|------|-------|---------|
| `INT` | IDs, counts, integers | user_id, order_count |
| `DECIMAL(10,2)` | Money amounts | sale_price, cost |
| `DATE` | Date only | created_date |
| `DATETIME` | Date + time | created_at, updated_at |
| `VARCHAR(n)` | Text, categories | status, traffic_source |
| `TINYINT` | Boolean flags | is_returned, is_sold |

### Null Value Policy

- **FK columns:** Should NOT be NULL (data quality issue)
- **Money columns:** Should NOT be NULL (data quality issue)
- **Status fields:** May be NULL if field not applicable
- **Demographic fields:** May be NULL if data not collected
- **Dates:** Should NOT be NULL for fact records

---

## Validation Rules

| Table | Column | Rule | Impact |
|-------|--------|------|--------|
| fact_transactions | sale_price | Must be >= $1 | Outliers removed during cleaning |
| fact_transactions | cost | Must be > 0 | Missing costs filled from dim_products |
| fact_inventory | is_sold | Must be 0 or 1 | Boolean validation in data pipeline |
| fact_inventory | holding_days | Must be >= 0 | Negative days clipped to 0 |
| dim_products | cost | Must be < retail_price | Validation in Phase 1 EDA |
| dim_users | age | Should be 13-120 | Invalid ages flagged in data quality |
| dim_date | date_key | Format YYYYMMDD | Parsed as text, not date |

---

## Known Data Limitations & Assumptions

### 1. **2024 Partial Year Data**
- Data includes orders from Jan 1 - Jan 17, 2024
- For YoY analysis, use only 2019-2023 data
- Flag: `orders['is_2024_partial'] = True`

### 2. **Null Shipped & Delivered Dates**
- ~35% orders have NULL `shipped_at`, `delivered_at`
- Likely due to: Cancelled orders (no shipping), Processing orders
- Not a data quality issue, but expected business scenario

### 3. **Different Traffic Source Definitions**
- `users.traffic_source` is the signup/acquisition source.
- `events.traffic_source` is the session source and includes `Adwords` and `YouTube`.
- Do not compare signup source and session source as if they are the same attribution field.

### 4. **Anonymous Events**
- 1,125,671 events, or 46.3%, have null `user_id`.
- These rows are retained for session funnel analysis.
- They are excluded from user-level RFM/LTV metrics.

### 5. **Inventory Overstock Distributed Evenly**
- 63% unsold across all 10 DCs (each DC has ~31K unsold)
- Even distribution indicates **systemic forecasting issue**, not DC-specific problem
- No single DC is underperforming

### 6. **No Discounting Detected**
- Actual sale prices ≈ retail prices across dataset
- No systematic discounting strategy observed
- ET Club relies on full-price sales (competitive advantage)

### 7. **No Net Profit Inputs**
- Dataset does not include marketing spend, shipping cost, tax, discount, payment fee, or return reason.
- Use gross profit and operational proxies, not net profit, true CAC, or true ROAS.

---

## Questions & Support

**For data issues, see:** `docs/documents/data_quality_report.md`  
**For data relationships, see:** `docs/documents/entity_relationship.md`

---

**Last Updated:** May 2026  
**Next Review:** After each phase completion
