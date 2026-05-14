# Entity Relationship Diagram - ET Club Data Model

**Project:** DATAVISION 2026  
**Version:** 1.0  
**Date:** May 2026

---

## 📊 Conceptual Data Model

```
                                 ┌──────────────────┐
                                 │   Dim_Date       │
                                 │──────────────────│
                                 │ date_key (PK)    │
                                 │ date             │
                                 │ year, month      │
                                 │ quarter, week    │
                                 │ day_of_week      │
                                 │ year_month       │
                                 └────────┬─────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
        ┌───────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
        │ Fact_Transactions  │  │ Fact_Inventory  │  │ Agg_Funnel_     │
        │────────────────────│  │─────────────────│  │ Monthly         │
        │ order_item_id (PK) │  │ inventory_id(PK)│  │─────────────────│
        │ order_id           │  │ product_id (FK) │  │ year_month (PK) │
        │ user_id (FK) ──┐   │  │ center_id (FK)  │  │ event_type (PK) │
        │ product_id (FK)├──┐│  │ cost            │  │ traffic_source  │
        │ date_key (FK)──┤  ││  │ is_sold         │  │ event_count     │
        │ sale_price      │  ││  │ holding_days    │  │ unique_users    │
        │ cost            │  ││  │ sunk_cost_risk  │  └─────────────────┘
        │ gross_profit    │  ││  │ holding_cost    │
        │ status          │  ││  └────────┬────────┘
        │ is_returned     │  ││           │
        └────────┬────────┘  ││       ┌───▼──────────────┐
                 │           ││       │   Dim_Products   │
                 │           ││       │──────────────────│
         ┌───────▼────────────┘│       │ product_id (PK) │
         │                     │       │ category        │
    ┌────▼───────────┐    ┌────▼─────┐ brand           │
    │   Dim_Users    │    │Dim_DCs   │ retail_price    │
    │────────────────│    │──────────│ cost            │
    │ user_id (PK)   │    │dc_id(PK) │ department      │
    │ age            │    │ name     │ └────────────────┘
    │ gender         │    │ location │
    │ country        │    │ state    │
    │ city           │    │ region   │
    │ traffic_source │    └──────────┘
    │ Recency        │
    │ Frequency      │
    │ Monetary       │
    │ rfm_segment    │
    │ cluster_label  │
    └────────────────┘
```

---

## 🔗 Relationship Matrix

### Core Relationships

| From Table | PK | → | To Table | FK | Cardinality | Type |
|------------|----|-|-|--------|------------|------|
| Fact_Transactions | order_item_id | → | Dim_Users | user_id | N:1 | Many-to-One |
| Fact_Transactions | order_item_id | → | Dim_Products | product_id | N:1 | Many-to-One |
| Fact_Transactions | order_item_id | → | Dim_Date | date_key | N:1 | Many-to-One |
| Fact_Inventory | inventory_id | → | Dim_Products | product_id | N:1 | Many-to-One |
| Fact_Inventory | inventory_id | → | Dim_DCs | center_id | N:1 | Many-to-One |
| Fact_Inventory | inventory_id | → | Dim_Date | date_key (created) | N:1 | Many-to-One |
| Agg_Funnel_Monthly | N/A | → | Dim_Date | year_month | N:1 | Implicit |

### Relationship Cardinality Details

#### Fact_Transactions → Dim_Users
```
- Direction: Many-to-One
- Cardinality: Multiple transactions per user (average 3-4)
- Active: YES (used for filtering & slicing)
- Data Integrity: 100% (no orphaned records)
```

#### Fact_Transactions → Dim_Products
```
- Direction: Many-to-One
- Cardinality: Multiple transactions per product (varies by popularity)
- Active: YES (used for category filtering)
- Data Integrity: 100%
```

#### Fact_Transactions → Dim_Date
```
- Direction: Many-to-One
- Cardinality: Multiple transactions per day (400-800 per day avg)
- Active: YES (critical for time-based analysis)
- Data Integrity: 100%
```

#### Fact_Inventory → Dim_Products
```
- Direction: Many-to-One
- Cardinality: Multiple inventory units per product
- Active: YES (used for product-level inventory drill-down)
- Data Integrity: 100%
```

#### Fact_Inventory → Dim_DCs
```
- Direction: Many-to-One
- Cardinality: Multiple units per DC (~31K units per DC)
- Active: YES (used for DC-level analysis)
- Data Integrity: 100%
```

---

## 📈 Star Schema Structure

### Star Schema Overview

```
                            ┌─────────────────┐
                            │   Dim_Date      │
                            │  (1,843 rows)   │
                            └────────┬────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────┐        ┌──────────────────┐      ┌─────────────────────┐
│ Fact_Transactions│        │ Fact_Inventory   │      │ Agg_Funnel_Monthly  │
│ (168.5K rows)    │        │ (490.7K rows)    │      │ (1,828 rows)         │
└─────────┬────────┘        └─────────┬────────┘      └─────────────────────┘
          │                           │
    ┌─────┴─────┐             ┌──────┴──────┐
    │           │             │             │
    ▼           ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Dim_Users │  │Dim_       │  │Dim_DCs   │  │Dim_      │
│(100.0K)   │  │Products   │  │(10 rows) │  │Products  │
│          │  │(29.1K)     │  │          │  │(29.1K)    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Why This Structure?

1. **Denormalized dimensions:** Fast queries, simple slicing
2. **Aggregated funnel table:** Reduces 2.4M events to 400 rows
3. **Multiple fact tables:** Separate transaction and inventory analysis paths
4. **Conformed dimensions:** Dim_Products & Dim_Date shared across facts

---

## 🔄 Data Flow & Transformations

```
┌─────────────────────────────────────────────────────────────┐
│                    RAW DATA SOURCES                         │
│  (7 CSV files in data/raw/)                                 │
└─┬──────────────────┬──────────────────┬────────────────────┘
  │                  │                  │
  ▼                  ▼                  ▼
orders.csv    order_items.csv      events.csv
(125.2K)      (181.8K raw)            (2.4M)
  │                  │                  │
  └─────────┬────────┘                  │
            │                           │
            ▼                           ▼
  ┌──────────────────────┐    ┌──────────────────┐
  │ CLEAN & VALIDATE     │    │ DETECT BOTS      │
  │ (Phase 1)            │    │ AGGREGATE        │
  │ - validate dates     │    │ (Group by month, │
  │ - calc gross_profit  │    │  event_type,     │
  │ - detect outliers    │    │  traffic_source) │
  └──────────┬───────────┘    └────────┬─────────┘
             │                         │
             ▼                         ▼
  ┌──────────────────────┐    ┌──────────────────────┐
  │ FACT_TRANSACTIONS    │    │ AGG_FUNNEL_MONTHLY   │
  │ (168.5K rows)        │    │ (1,828 rows)          │
  │ Processed ✅         │    │ Processed ✅         │
  └──────────┬───────────┘    └──────────┬───────────┘
             │                           │
             │                           │
  ┌──────────▼────────────────────────────────────────┐
  │              POWER BI DATA MODEL                  │
  │  (Import mode, relationships established)         │
  │  (4 Dashboard Pages)                              │
  └───────────────────────────────────────────────────┘
```

### ETL Process Steps

#### Step 1: Load Raw CSVs
```python
orders = pd.read_csv('data/raw/orders.csv', parse_dates=[...])
order_items = pd.read_csv('data/raw/order_items.csv')
events = pd.read_csv('data/raw/events.csv', parse_dates=[...])
users = pd.read_csv('data/raw/users.csv')
products = pd.read_csv('data/raw/products.csv')
dcs = pd.read_csv('data/raw/distribution_centers.csv')
inventory = pd.read_csv('data/raw/inventory_items.csv', parse_dates=[...])
```

#### Step 2: Validate & Clean
```python
# Check date logic, remove outliers, detect bots
# Fill missing values, validate FKs
```

#### Step 3: Transform & Enrich
```python
# Calculate RFM, gross profit, holding days
# Aggregate funnel data (2.43M -> 1,828 rows)
```

#### Step 4: Create Dimension Tables
```python
dim_users = users.merge(rfm, on='user_id')
dim_products = products[['id', 'category', 'cost', ...]]
dim_date = pd.date_range('2019-01-01', '2024-01-17').to_frame()
dim_dcs = dcs
```

#### Step 5: Create Fact Tables
```python
fact_transactions = order_items.merge(orders).merge(dim_products)
fact_inventory = inventory.merge(dim_products).merge(dim_dcs)
agg_funnel = events.groupby([month, event_type, source]).sum()
```

#### Step 6: Export to Parquet
```python
fact_transactions.to_parquet('data/processed/fact_transactions.parquet')
dim_users.to_parquet('data/processed/dim_users.parquet')
# ... etc
```

#### Step 7: Load to Power BI
```
In Power BI:
  1. Get Data → Parquet
  2. Select all 7 .parquet files
  3. Establish relationships (date table first)
  4. Hide foreign key columns
  5. Create DAX measures
  6. Build dashboard pages
```

---

## 📊 Dimensional Attributes

### Dim_Users Attributes
- **Demographic:** age, gender, country, city
- **Acquisition:** traffic_source
- **RFM:** Recency, Frequency, Monetary
- **Segmentation:** rfm_segment, cluster_label

**Usage:** Customer analytics, segmentation, LTV calculations

### Dim_Products Attributes
- **Classification:** category, department, brand
- **Pricing:** retail_price, cost
- **Margin:** Gross margin = (retail_price - cost) / retail_price

**Usage:** Product performance, category analysis, inventory valuation

### Dim_DCs Attributes
- **Location:** name, address, state, region
- **Count:** 10 DCs across USA

**Usage:** Regional inventory analysis, DC performance

### Dim_Date Attributes
- **Time Hierarchy:** year → quarter → month → week → day
- **Attributes:** day_of_week, is_weekend, year_month
- **Purpose:** Time-based slicing, YoY/QoQ/MoM analysis

**Usage:** All trending, forecasting, time intelligence

---

## 🔐 Data Governance & Lineage

### Column Lineage

| Processed Column | Source Column(s) | Calculation | Table |
|------------------|------------------|-------------|-------|
| gross_profit | sale_price, cost | sale_price - cost | Fact_Transactions |
| is_returned | status | status == 'Returned' | Fact_Transactions |
| holding_days | created_at | today - created_at | Fact_Inventory |
| sunk_cost_risk | cost, is_sold | cost × (1 - is_sold) | Fact_Inventory |
| holding_cost | cost, holding_days | cost × 0.25 / 365 × days | Fact_Inventory |
| Recency | created_at | 2023-12-31 - max(order_date) | Dim_Users |
| Frequency | order_id | count(distinct order_id) | Dim_Users |
| Monetary | sale_price | sum(gross_profit) | Dim_Users |
| rfm_segment | R/F/M scores | Rule-based mapping | Dim_Users |

### Data Quality Rules

| Rule | Source | Validation | Action if Fail |
|------|--------|-----------|---|
| PK uniqueness | All tables | DISTINCT count | Reject load |
| FK referential integrity | All FKs | Match to parent PK | Log warning |
| Date logic | Orders | shipped_at > created_at | Document outlier |
| Price validation | fact_transactions | sale_price >= $1 | Exclude from revenue |
| Date ranges | Dim_Date | 2019-01-01 to 2024-01-17 | OK (partial 2024) |
| Margin >=0% | products | cost < retail_price | Validated ✅ |

---

## 🎯 Dimension Grain

| Dimension | Grain | Cardinality |
|-----------|-------|------|
| Dim_Date | Day | 1,843 |
| Dim_Users | Customer | 100,000 |
| Dim_Products | Product | 29,120 |
| Dim_DCs | Distribution Center | 10 |

---

## 📌 Power BI Relationship Configuration

### In Power BI Model View:

```
From Table        Cardinality   Cross Filter   Active   Relationship Key
─────────────────────────────────────────────────────────────────────────
Dim_Date    →  Fact_Transactions    1:*        Both     YES    date_key
Dim_Users   →  Fact_Transactions    1:*        Both     YES    user_id
Dim_Products → Fact_Transactions    1:*        Both     YES    product_id

Dim_Date    →  Fact_Inventory       1:*        Both     YES    date_key
Dim_Products → Fact_Inventory       1:*        Both     YES    product_id
Dim_DCs     →  Fact_Inventory       1:*        Both     YES    center_id

Agg_Funnel  →  Dim_Date            (Implicit)  Both     NO     year_month
```

**Notes:**
- All relationships are **Active** for power
- Cross-filter direction: Both (allows two-way filtering)
- Foreign key columns should be **Hidden** from end-user view

---

## ✅ Relationship Validation Checklist

- [ ] All PK columns are unique
- [ ] All FK columns reference valid PKs
- [ ] No orphaned records (100% FK match)
- [ ] Cardinality matches business logic
- [ ] Relationships created in Power BI
- [ ] Foreign key columns hidden from reports
- [ ] Dim_Date marked as official date table

---

**Last Updated:** May 2026  
**Next Review:** After dashboard deployment
