# DATAVISION 2026 - ET Club Analytics Dashboard

> **Vòng 2 - Phân Tích Doanh Thu & Tối Ưu Hóa Hoạt Động** | Tháng 5/2026

## 📋 Mục Lục

1. [Giới Thiệu Dự Án](#giới-thiệu-dự-án)
2. [Câu Hỏi Kinh Doanh & Red Thread](#câu-hỏi-kinh-doanh--red-thread)
3. [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
4. [Chuẩn Bị Môi Trường](#chuẩn-bị-môi-trường)
5. [Quy Trình ETL & Phân Tích](#quy-trình-etl--phân-tích)
6. [Kiến Trúc Star Schema](#kiến-trúc-star-schema)
7. [Công Cụ & Công Nghệ](#công-cụ--công-nghệ)
8. [Timeline & Giai Đoạn](#timeline--giai-đoạn)
9. [Hướng Dẫn Chạy](#hướng-dẫn-chạy)
10. [Liên Hệ & Support](#liên-hệ--support)

---

## 🎯 Giới Thiệu Dự Án

Dự án **DATAVISION 2026 - ET Club** là bài phân tích chuyên sâu về hiện trạng kinh doanh của một doanh nghiệp e-commerce thời trang. Sau khi chuẩn hóa lại định nghĩa metric, trọng tâm phân tích là: **recognized revenue tăng hơn 23 lần trong giai đoạn 2019→2023**, nhưng chất lượng tăng trưởng còn bị bào mòn bởi status leakage, retention thấp và tồn kho chưa bán lớn.

### Khách Hàng
- **Công ty:** ET Club (E-commerce Apparel & Fashion)
- **Lĩnh vực:** Bán lẻ quần áo online qua 10 Distribution Centers (DCs) tại Mỹ
- **Dữ liệu:** 2019-2024, trong đó phân tích xu hướng năm dùng 2019-2023 vì 2024 chưa đủ năm
- **Quy mô raw:** 100,000 users, 125,226 orders, 181,759 order items, 490,705 inventory items, 2,431,963 events
- **Quy mô processed chính:** 168,528 fact transactions, 100,000 dim users, 29,120 dim products, 1,828 monthly funnel rows

### Mục Tiêu Chính
- ✅ Chuẩn hóa bộ KPI quản trị: tách **GMV all-status**, **recognized revenue**, **recognized gross profit** và **status leakage**
- ✅ Xác định các điểm nghẽn trên 4 trụ cột: Khách hàng, Sản phẩm & Doanh thu, Marketing & Chuyển đổi, Vận hành & Chuỗi cung ứng
- ✅ Chuẩn bị dữ liệu sạch dạng CSV/Parquet cho Power BI và báo cáo phân tích
- ✅ Đưa ra khuyến nghị hành động dựa trên bằng chứng dữ liệu, đồng thời ghi rõ giới hạn vì dataset chưa có marketing spend, discount, tax, shipping cost và net profit

---

## 💡 Câu Hỏi Kinh Doanh & Red Thread

### Câu Hỏi Chính
**"ET Club tăng trưởng rất nhanh, nhưng chất lượng tăng trưởng đang bị rò rỉ ở đâu và cần ưu tiên hành động gì?"**

### Sợi Chỉ Đỏ (The Narrative)

#### Tầng 1 - Recognized Revenue: Tăng Nhanh, Gross Margin Ổn Định
| Năm | Recognized revenue | Gross Margin % |
|-----|---------|---|
| 2019 | $122.6K | 51.8% |
| 2023 | $2.819M | 51.9% |

👉 **Insight:** Gross margin ổn định quanh 51.9% → vấn đề cốt lõi không nằm ở COGS trực tiếp, mà ở chất lượng chuyển hóa từ demand/order value sang doanh thu hợp lệ.

---

#### Tầng 2 - Status Leakage & Operating Cost Ẩn
| Vấn đề | Định Lượng | Tác Động |
|-------|-----------|---------|
| **Status Leakage** | $4.50M, tương đương 44.9% GMV 2019-2023 | GMV bị inflate nếu dùng làm revenue |
| **No Valid Purchase Users** | 50.5% users | Nhiều user không tạo đơn Complete/Shipped |
| **One-Time Buyers** | 76.6% valid customers | Repeat thấp, LTV/CAC theo giả định chỉ 1.1:1 |
| **Inventory Overstock** | 313,351 unsold units, sell-through 36.1% | Vốn đóng băng $8.98M + holding cost ước tính $4.47M |
| **Returns** | 16,896 returned items, return value $1.014M | Chi phí reverse logistics ước tính $337.9K nếu $20/return |

👉 **Insight:** Tăng trưởng volume kéo theo rò rỉ ở trạng thái đơn hàng, retention và tồn kho. Đây là nhóm vấn đề cần xử lý trước khi mở rộng acquisition.

---

#### Tầng 3 - Giới Hạn Dữ Liệu & External Context
| Yếu Tố | Trạng thái hiện tại | Cách sử dụng |
|--------|----------|---|
| Marketing spend/CAC thực tế | Chưa có trong dataset | Không kết luận ROI; chỉ phân tích traffic source performance |
| Shipping cost/return reason/discount/tax | Chưa có trong dataset | Không kết luận net profit hay contribution margin |
| US CPI/Drewry WCI | Planned external enrichment | Chỉ dùng khi có nguồn external được tải và kiểm chứng |

👉 **Insight:** Báo cáo hiện tại ưu tiên kết luận có thể chứng minh trực tiếp từ raw/processed data; các giả định chi phí được ghi rõ là giả định.

---

### Kết Luận
> **ET Club đang tăng trưởng nhanh nhưng chưa đủ chất lượng:** chỉ 55.1% GMV all-status chuyển thành recognized revenue, hơn một nửa user chưa có đơn hợp lệ, 76.6% valid buyers chỉ mua một lần, và 313K inventory units vẫn chưa bán. Ưu tiên chiến lược nên chuyển từ tăng volume thuần túy sang giảm leakage, tăng repeat, tối ưu checkout và giải phóng tồn kho.

---

## 📁 Cấu Trúc Thư Mục

```
DATAVISION2026_ET_CLUB/
│
├── 📂 data/
│   ├── raw/                          <- 7 file CSV gốc (KHÔNG PUSH)
│   │   ├── orders.csv
│   │   ├── order_items.csv
│   │   ├── inventory_items.csv
│   │   ├── events.csv
│   │   ├── users.csv
│   │   ├── products.csv
│   │   └── distribution_centers.csv
│   ├── external/                     <- US CPI, Drewry WCI (KHÔNG PUSH)
│   ├── interim/                      <- Dữ liệu nháp đang xử lý (KHÔNG PUSH)
│   └── processed/                    <- Data clean, aggregated (KHÔNG PUSH)
│
├── 📂 docs/
│   ├── report/                       <- Báo cáo vòng 2 (Word/PDF)
│   ├── tasks/                        <- Giao việc chi tiết theo phase
│   │   ├── phase_1_etl.md
│   │   ├── phase_2_analysis.md
│   │   ├── phase_3_advanced.md
│   │   └── phase_4_dashboard.md
│   └── documents/                    <- Mô tả dữ liệu chi tiết
│       ├── data_dictionary.md
│       ├── data_quality_report.md
│       ├── data_preprocessing_log.md
│       └── entity_relationship.md
│
├── 📂 notebooks/
│   ├── 1.0_eda_orders_inventory.ipynb
│   ├── 2.0_bot_filtering_events.ipynb
│   └── 3.0_rfm_prophet_modeling.ipynb
│
├── 📂 src/
│   ├── __init__.py
│   ├── data_pipeline.py              <- Script chính: clean + aggregate
│   ├── external_api.py               <- Crawl/download US CPI, Drewry WCI
│   └── ml_models.py                  <- K-Means clustering, Prophet forecast
│
├── 📂 powerbi/
│   ├── ET_Club_Dashboard.pbix        <- Dashboard chính
│   └── dax_measures.txt              <- Backup các DAX measures phức tạp
│
├── .gitignore                        <- Ignore data/, logs/, tmp/
├── requirements.txt                  <- Danh sách thư viện Python
└── README.md                         <- File này
```

---

## ⚙️ Chuẩn Bị Môi Trường

### 1. Clone Repo & Tạo Virtual Environment

```bash
cd ...\DATAVISION2026_ET_CLUB

# Tạo virtual environment
python -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt

# (Optional) Cài jupyter để làm notebook
pip install jupyter jupyterlab
```

### 2. Chuẩn Bị Data

- Đặt 7 file CSV gốc vào `data/raw/` (từ folder `[DATAVISION2026]_VÒNG 2_DATASET`)
- Các file nên có: `orders.csv`, `order_items.csv`, `inventory_items.csv`, `events.csv`, `users.csv`, `products.csv`, `distribution_centers.csv`

### 3. Chuẩn Bị External Data

```bash
# Các file sẽ được download tự động từ:
# - FRED API (https://fred.stlouisfed.org) → data/external/CPIAUCSL.csv
# - Drewry WCI (public reports) → data/external/drewry_wci.csv
# Xem chi tiết tại src/external_api.py

# Planned enrichment, chưa bắt buộc cho kết quả hiện tại:
# - CPI hoặc inflation index
# - Shipping/freight benchmark
# - Marketing spend, discount, return reason nếu doanh nghiệp bổ sung
#
# Lưu ý: không kết luận ROI, CAC thực tế, net profit hoặc contribution margin
# nếu chưa có dữ liệu chi phí tương ứng.
```

---

## 🔄 Quy Trình ETL & Phân Tích

### Bước 1: Data Ingestion & Cleaning (Phase 1)

**Script chính:** `src/data_pipeline.py`

```python
# Load CSV
orders = pd.read_csv('<dataset_root>/raw/orders.csv', parse_dates=[...])
items = pd.read_csv('<dataset_root>/raw/order_items.csv')
events = pd.read_csv('<dataset_root>/raw/events.csv', parse_dates=[...])

# Validate & Clean
# - Check null logic (e.g., shipped_at > created_at)
# - Remove outliers (sale_price < $1)
# - Detect bots (>1000 events/user/day)

# Feature Engineering
# - is_recognized_revenue = status in ["Complete", "Shipped"]
# - GMV_All_Status, Recognized_Revenue, Recognized_Gross_Profit
# - Revenue_Lost_Cancelled, Return_Value, Processing_Backlog_Value
# - RFM chỉ tính trên recognized orders; giữ No Purchase / No Valid Purchase
# - Gross Profit = sale_price - cost, Holding Days = cutoff - created_at
# - Return Rate per user, category, etc.

# Aggregation cho Power BI
# - Agg_Funnel_Monthly: 2.43M events → 1,828 rows
# - Annual_Revenue: recognized revenue + margin + YoY%
# - Status_Leakage, Category_Performance, Funnel, Fulfillment, Inventory
```

### Bước 2: Exploratory Data Analysis (Phase 2)

**Notebooks:** `notebooks/1.0_eda_*.ipynb`

4 trụ cột phân tích:

| Trụ Cột | Metric Chính | Tool |
|--------|-------------|------|
| **A. Khách Hàng** | RFM, Cohort, Repeat Rate, LTV/CAC giả định | Pandas |
| **B. Sản Phẩm** | Recognized Revenue, Gross Margin, Leakage, Return Rate | Pandas |
| **C. Marketing** | Funnel, Source Journey, Traffic Source Performance, CVR | Events + Agg_Funnel_Monthly |
| **D. Kho Bãi** | Sell-Through, ABC Aging, Frozen Capital, Holding Cost, Fulfillment | Inventory + Orders |
| **E. E-commerce Domain** | Basket Affinity, Price Band, Return/Cancel Proxy | Transactions + Products + Orders |

### Bước 3: Advanced Modeling (Phase 3 - Nếu Có Thời Gian)

**Script chính:** `src/ml_models.py`

- **Customer Clustering:** dùng scikit-learn nếu môi trường có sẵn; fallback hiện tại là rule-based 7 cluster
- **Demand Forecasting:** dùng Prophet nếu môi trường có sẵn; fallback hiện tại là `seasonal_naive_fallback`
- **Model caution:** `phase3_model_summary.csv` đánh dấu forecast chỉ nên dùng làm baseline khi MAPE còn cao

### Bước 4: Power BI Dashboard (Phase 4)

**File chính:** `powerbi/ET_Club_Dashboard.pbix`

4 trang (Pages):
1. **Executive Summary:** KPIs, Revenue trend, Margin waterfall
2. **Customer Analytics:** RFM segments, Cohort heatmap, LTV/CAC
3. **Product & Operations:** Category matrix, price-band action, inventory ABC-aging, return/cancel proxy
4. **Marketing Funnel:** Event/session/user funnel, source journey, traffic source performance, CVR by channel
5. **E-commerce Playbook:** basket affinity, bundle test candidates, markdown/rebalance actions

---

## 🏗️ Kiến Trúc Star Schema

```
                                    Dim_Date
                    ┌───────────────────────────────────┐
                    │ • date_key (PK)                   │
                    │ • date                            │
                    │ • year, month, quarter            │
                    │ • day_of_week, is_weekend         │
                    └───────────────────────────────────┘
                            │
             ┌──────────────┼──────────────┬─────────────┐
             │              │              │             │
        ┌────▼────┐ ┌───────▼────┐ ┌──────▼──────┐ ┌────▼─────┐
        │ Fact_   │ │ Agg_       │ │ Fact_       │ │ Fact_    │
        │Trans-  │ │ Funnel_    │ │ Inventory   │ │ Orders   │
        │actions │ │ Monthly (*)│ │             │ │ (Dim)    │
        └────┬────┘ └───────┬────┘ └──────┬──────┘ └────┬─────┘
             │              │              │             │
             └──────────────┼──────────────┴─────────────┘
                            │
        ┌───────────────────┼──────────────┬──────────────┐
        │                   │              │              │
   ┌────▼──────┐  ┌────────▼────┐  ┌─────▼──────┐  ┌────▼──────┐
   │Dim_Users  │  │Dim_Products │  │Dim_DCs     │  │Dim_External
   │           │  │             │  │            │  │(CPI, WCI) 
   └───────────┘  └─────────────┘  └────────────┘  └───────────┘

(*) Agg_Funnel_Monthly: Aggregated từ 2.43M raw events
    → Không load raw 2.43M vào Power BI (file quá nặng)
    → Pre-aggregate: (year_month, event_type, traffic_source, count, unique_users)
    → 1,828 rows, file nhẹ, tốc độ xử lý tức thì
```

### Chi Tiết Các Bảng

#### **Fact_Transactions** (168,528 rows)
| Cột | Kiểu | Mô Tả |
|-----|------|-------|
| order_item_id | PK | ID duy nhất cho mỗi dòng order |
| order_id | FK | Link tới order_date |
| user_id | FK | Link tới customer |
| product_id | FK | Link tới product info |
| date_key | FK | Link tới Dim_Date |
| sale_price | Numeric | Giá bán thực tế |
| cost | Numeric | Giá vốn (từ products) |
| gross_profit | Calculated | = sale_price - cost |
| status | String | Complete, Shipped, Processing, Returned, Cancelled |
| is_returned | Boolean | 1 nếu returned, 0 nếu không |
| is_gmv | Boolean | 1 nếu `sale_price >= 1` |
| is_recognized_revenue | Boolean | 1 nếu status thuộc Complete/Shipped |
| GMV_All_Status | Numeric | GMV gồm mọi status hợp lệ |
| Recognized_Revenue | Numeric | Doanh thu chính, chỉ Complete/Shipped |
| Revenue_Lost_Cancelled | Numeric | Giá trị đơn Cancelled |
| Return_Value | Numeric | Giá trị đơn Returned |
| Processing_Backlog_Value | Numeric | Giá trị đơn Processing |

#### **Agg_Funnel_Monthly** (1,828 rows)
| Cột | Mô Tả |
|-----|-------|
| year_month | 2019-01, 2019-02, ... |
| event_type | home, department, product, cart, purchase, cancel |
| traffic_source | (Organic, Search, Email, Adwords, ...) |
| event_count | Tổng số events |
| unique_users | Số user duy nhất |

#### **Fact_Inventory** (490,705 rows - all inventory items)
| Cột | Mô Tả |
|-----|-------|
| inventory_id | PK |
| product_id | FK |
| center_id | FK (Distribution Center) |
| cost | Giá vốn |
| is_sold | 1 nếu đã bán, 0 nếu còn tồn |
| holding_days | Số ngày đang ở kho |
| sunk_cost_risk | = cost × (1 - is_sold) |
| holding_cost_estimate | Chi phí lưu kho ước tính đến cutoff |

#### **Dim_Users** (100,000 rows)
| Cột | Mô Tả |
|-----|-------|
| user_id | PK |
| age, gender, country, city | Demographics |
| traffic_source | Nguồn đăng ký đầu tiên |
| Recency, Frequency, Monetary | RFM chỉ trên Complete/Shipped |
| return_rate_pct | Return rate theo user |
| rfm_segment | Champions, Loyal, At Risk, About to Lose, Lost, No Purchase / No Valid Purchase |
| cluster_label | Có trong `dim_users_with_clusters`, 7 label rule-based/fallback |

#### **Dim_Products** (29,120 products)
| Cột | Mô Tả |
|-----|-------|
| product_id | PK |
| category | (Outerwear, Jeans, Tops, ...) |
| brand | Product brand |
| retail_price | MSRP |
| cost | COGS |
| department | Business unit |

---

## 🛠️ Công Cụ & Công Nghệ

| Lớp | Công Cụ | Tác Dụng |
|-----|---------|---------|
| **Data Processing** | Pandas, PyArrow, Fastparquet | Clean, transform, xuất CSV/Parquet |
| **Analysis Querying** | Pandas, DuckDB | Aggregation, validation, EDA |
| **Analysis & Modeling** | Scikit-learn, Prophet, fallback logic | Clustering, forecasting nếu dependency có sẵn |
| **Visualization** | Power BI Desktop | Dashboard, reports |
| **Notebooks** | Jupyter Lab | EDA, nháp thuật toán |
| **Scripting** | Python 3.10+ | Automation, ETL pipelines |
| **Version Control** | Git + GitHub | Team collaboration |

---

## 📅 Timeline & Giai Đoạn

### Phase 1: ETL & Data Cleaning (06-07 May)
- [x] Cleaning từng bảng CSV
- [x] Feature Engineering (RFM, Gross Profit, Holding Days)
- [x] Chuẩn hóa metrics: GMV, recognized revenue, leakage, backlog
- [x] Xuất CSV + Parquet cho Power BI
- [ ] **Commit:** `feat: complete data ingestion and cleaning pipeline`

### Phase 2: Phân Tích 4 Trụ Cột (08-10 May)
- [x] RFM Segmentation & Cohort Analysis
- [x] Revenue Waterfall & Category Matrix
- [x] Funnel Analysis & Traffic Source Performance
- [x] Inventory Turnover, Holding Cost & Fulfillment
- [ ] **Commit:** `feat: complete 4-pillar analysis notebooks`

### Phase 3: Advanced Modeling (10-11 May - Nếu Có Thời Gian)
- [x] Rule-based customer clustering fallback
- [x] Seasonal naive demand forecasting fallback
- [ ] Optional: chạy lại bằng scikit-learn/Prophet khi dependency sẵn sàng
- [ ] **Commit:** `feat: add advanced ML models`

### Phase 4: Power BI Dashboard (11-13 May)
- [ ] Build 4 dashboard pages
- [ ] DAX measures testing
- [ ] Chèn hình từ Power BI vào báo cáo markdown/Word
- [ ] **Commit:** `feat: deliver Power BI dashboard v1.0`

---

## ▶️ Hướng Dẫn Chạy

### 1. Chạy ETL Pipeline (Data Cleaning)

```bash
# Activate venv
venv\Scripts\activate

# Chạy script chính
python src/data_pipeline.py --dataset-root "H:\Datavision\[DATAVISION2026]_VÒNG 2_DATASET"

# Output: 
#   - <dataset_root>/processed/fact_transactions.parquet
#   - <dataset_root>/processed/agg_funnel_monthly.parquet
#   - <dataset_root>/processed/fact_inventory.parquet
#   - <dataset_root>/processed/dim_users.parquet
#   - <dataset_root>/processed/dim_products.parquet
#   - <dataset_root>/processed/dim_dcs.parquet
#   - <dataset_root>/processed/dim_date.parquet
#   - CSV companion cho tất cả bảng trên
```

### 2. Chạy Phase 2 & Phase 3

```bash
python src/phase2_analysis.py --dataset-root "...\[DATAVISION2026]_VÒNG 2_DATASET"
python src/ml_models.py --dataset-root "...\[DATAVISION2026]_VÒNG 2_DATASET"

# Output bổ sung:
#   - annual_revenue_analysis.csv
#   - status_leakage_analysis.csv
#   - category_performance_analysis.csv
#   - rfm_segment_analysis.csv
#   - cohort_retention_analysis.csv
#   - traffic_source_performance.csv
#   - funnel_analysis.csv
#   - fulfillment_performance.csv
#   - clustering_analysis.csv
#   - demand_forecast_12m.csv
#   - phase3_model_summary.csv
```

### 3. Làm Notebook Exploratory Analysis

```bash
# Mở Jupyter Lab
jupyter lab

# Mở notebooks/:
#   1.0_eda_orders_inventory.ipynb
#   2.0_bot_filtering_events.ipynb
#   3.0_rfm_prophet_modeling.ipynb
```

### 4. Download External Data (CPI, WCI)

```bash
# Planned, chỉ chạy khi đã có API/source rõ ràng:
python src/external_api.py
#
# Expected:
#   <dataset_root>/external/CPIAUCSL.csv
#   <dataset_root>/external/drewry_wci.csv
```

### 5. Mở Power BI Dashboard

```bash
# Mở file planned:
powerbi/ET_Club_Dashboard.pbix

# Refresh data from:
# ...\[DATAVISION2026]_VÒNG 2_DATASET\processed\
# Check DAX measures tại powerbi/dax_measures.txt
```

---

## 📖 Hướng Dẫn Tài Liệu

### Trong Thư Mục `docs/tasks/`
Mỗi file .md có:
- **Mô tả giai đoạn**
- **Checklist tasks** (dùng [ ] để mark hoàn thành)
- **Kết quả mong đợi**
- **Time estimate**

### Trong Thư Mục `docs/documents/`
- **data_dictionary.md:** Tất cả cột, kiểu dữ liệu, mô tả
- **data_quality_report.md:** Null%, outliers, anomalies
- **data_preprocessing_log.md:** Nhật ký dữ liệu đưa thẳng vào báo cáo PDF
- **entity_relationship.md:** Diagram & relationships giữa tables

---

## 🤝 Liên Hệ & Support

**Nếu gặp vấn đề:**

1. **Data issue:** Check `docs/documents/data_quality_report.md`
2. **Code error:** Chạy lại từng phase bằng `--dataset-root` và kiểm tra console output
3. **Power BI issue:** Refresh từ folder `processed/`; file `powerbi/dax_measures.txt` hiện là planned nếu cần backup DAX
4. **Timeline issue:** Update task status ở `docs/tasks/phase_*.md`

---

**Version:** 1.0.0 | **Last Updated:** 08 May 2026 | **Status:** Phase 1/2/3 refreshed, Power BI dashboard pending
