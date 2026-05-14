# End-to-End E-Commerce Analytics: Phân Tích Điểm Nghẽn Vận Hành và Xây Dựng Mô Hình Dự Báo Nhu Cầu

**Tác giả:** Trần Viết Gia Huy  
**Vai trò:** Data Analyst  
**Bối cảnh:** Phân tích dữ liệu thực tế (3.35M+ dòng) của nền tảng E-commerce giai đoạn 2019-2023

## Mục Lục

1. [Tổng Quan](#tổng-quan)
2. [Bài Toán Kinh Doanh](#bài-toán-kinh-doanh)
3. [Tài Liệu Báo Cáo](#tài-liệu-báo-cáo)
4. [Cấu Trúc Dữ Liệu - Fact & Dimension Tables](#cấu-trúc-dữ-liệu---fact--dimension-tables)
5. [Power BI Dashboard](#power-bi-dashboard)
6. [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
7. [Chuẩn Bị Môi Trường](#chuẩn-bị-môi-trường)
8. [Quy Trình ETL Và Phân Tích](#quy-trình-etl-và-phân-tích)
9. [Các Insight Chính](#các-insight-chính)
10. [Khuyến Nghị Hành Động](#khuyến-nghị-hành-động)
11. [Tài Liệu Tham Khảo](#tài-liệu-tham-khảo)

## Tổng Quan

Dự án này phân tích hoạt động kinh doanh e-commerce trong giai đoạn 2019-2023, với **mục tiêu cốt lõi** là bóc tách nguyên nhân khiến biên lợi nhuận ròng bị thu hẹp dù GMV tăng trưởng gấp **23 lần**, từ đó đề xuất **Khung hành động dựa trên dữ liệu** (Data-driven Action Framework).

### Kết Quả Chính

- **Recognized Revenue:** Tăng từ $121.6K (2019) → $2.82M (2023) - CAGR 87.9%
- **Gross Merchandise Value (GMV):** $10.83M, tương ứng $3.10M gross profit
- **Gross Margin:** Bất biến ở ~51.9% (vấn đề không phải COGS mà chi phí vận hành)
- **Status Leakage:** $4M (44.9% GMV) mất mát qua trạng thái không sinh lợi (Cancelled/Processing/Returned)
- **Repeat Purchase Rate:** 50.4% users mua một lần, LTV:CAC chỉ 1.1:1
- **Frozen Capital:** $8.98M bị kẹt trong tồn kho, sell-through chỉ 36.1%

### Các Trụ Cột Phân Tích

Báo cáo cấu trúc xung quanh 6 insight chính:

1. **Tăng trưởng chủ yếu từ volume, chưa từ hiệu quả**
2. **Rò rỉ doanh thu qua Processing backlog ($2M), Returns ($1M), Cancellations ($1M)**
3. **Khủng hoảng giữ chân khách hàng - chuyên tập trung vào acquisition, quên retention**
4. **Điểm nghẽn tại cart: 63% add-to-cart nhưng chỉ 42% checkout, 41% cancel rate tại checkout**
5. **Phân tầng chất lượng ẩn trong danh mục - Jeans doanh thu cao nhưng margin 46.5%, return rate 12.3%**
6. **Tồn kho mùa vụ không giải phóng kịp thời thành dead stock (Outerwear, Sweaters, Hoodies)**

## Bài Toán Kinh Doanh

### Câu Hỏi Trung Tâm

Doanh thu tăng 23x trong 5 năm, nhưng **tại sao net margin vẫn bị ép chặt?** Vấn đề nằm ở đâu và nên ưu tiên hành động gì trước?

### Bối Cảnh Kinh Tế Vĩ Mô

Giai đoạn 2019-2023 chứng kiến:
- US CPI tăng 14% (đỉnh lạm phát 2021-2022)
- Drewry World Container Index bùng nổ 3-5 lần
- Chuỗi cung ứng toàn cầu gặp đứt gãy do COVID-19

Với 10 distribution centers trải dài khắp nước Mỹ, các biến động này **giáng đòn trực tiếp** vào logistics, human cost kho bãi, và xử lý hoàn trả.

## Tài Liệu Báo Cáo

- **Báo cáo chính:** [reports/Report.pdf](reports/Report.pdf)
- **Dashboard visuals:** [reports/Dashboard](reports/Dashboard)
- **Processed datasets:** [data/processed/](data/processed/)

## Cấu Trúc Dữ Liệu - Fact & Dimension Tables

Dự án sử dụng **star schema** để tối ưu hiệu suất truy vấn và phân tích trong Power BI. Dữ liệu raw được chuẩn hóa thành 3 fact tables và 5 dimension tables.

### Quy Trình Tiền Xử Lý Dữ Liệu (Data Cleaning)

Quy trình tiền xử lý tập trung vào 6 nhóm chính:

| Nhóm Xử Lý | Vấn Đề Phát Hiện | Cách Xử Lý | Mục Đích |
|---|---|---|---|
| **Chuyển đổi kiểu dữ liệu** | Trường thời gian ở dạng chuỗi | Chuyển created_at, shipped_at, delivered_at, returned_at sang datetime; tạo year, month, date_key | Phân tích xu hướng, cohort, SLA |
| **Missing Values** | Thiếu city, brand, product_name | Gán Unknown cho trường mô tả; giữ null có ý nghĩa nghiệp vụ | Không làm mất dữ liệu, vẫn đảm bảo KPI |
| **Outliers/Dữ Liệu Nhiễu** | 10 dòng sale_price < $1; 1,685 dòng tuổi ngoài hợp lý | Loại giá bán bất thường; chuẩn hóa tuổi 13-120 | Tránh méo GMV, AOV, margin |
| **Dữ Liệu Trùng Lặp** | Kiểm tra primary key ở 7 bảng | Kiểm tra duplicate record | Đảm bảo mỗi thực thể ghi nhận một lần |
| **Toàn Vẹn Khóa** | Kiểm tra orphan key | Kiểm tra orders→order_items→products→users→inventory_items | Đảm bảo join an toàn |
| **Chuẩn Bị Biến Phân Tích** | Raw data thiếu chỉ số e-commerce | Tạo GMV, recognized revenue, gross profit, margin, AOV, conversion rate, repeat rate, return rate, inventory aging, sell-through | Chuẩn hóa metric cho báo cáo |

**Kết quả:** 168,528 dòng từ 181,759 order_items raw (7 bảng gốc: users, products, distribution_centers, orders, order_items, events, inventory_items)

### Fact Tables

| Tên Bảng | Raw | Processed | Grain | Khóa Chính | Vai Trò |
|---|---:|---:|---|---|---|
| **Fact_Orders** | 125,226 | 122,158 | Mỗi đơn hàng | order_id | Phân tích thành công/thất bại đơn, SLA fulfillment, trạng thái |
| **Fact_Order_Items** | 181,759 | 168,528 | Mỗi line item | order_id + product_id | Doanh thu, gross profit, status leakage, return value, AOV |
| **Fact_Inventory** | 490,705 | 490,705 | Mỗi inventory item | id | Tồn kho, sell-through, holding days, frozen capital, aging |
| **Agg_Funnel_Monthly** | 2.43M events | 1,828 | year_month × event × traffic_source | year_month + event_type + source | Funnel tối ưu, user journey, traffic quality |

### Dimension Tables

| Tên Bảng | Raw | Processed | Grain | Khóa Chính | Nội Dung |
|---|---:|---:|---|---|---|
| **Dim_Users** | 100,000 | 100,000 | Mỗi user | user_id | Hồ sơ khách hàng, city, created_at, age, cohort |
| **Dim_Users_RFM** | 75,000 | 75,000 | Mỗi user đã mua | user_id | RFM scores, segment (Champion/Loyal/At Risk/About to Lose/No Purchase) |
| **Dim_Products** | 29,120 | 29,120 | Mỗi product | product_id | Tên, brand, category, department, retail_price, cost, distribution_center_id |
| **Dim_Distribution_Centers** | 10 | 10 | Mỗi DC | distribution_center_id | Tên DC, state, region |
| **Dim_Date** | 1,826 | 1,826 | Mỗi ngày | date_key | year, quarter, month, week, weekday, is_weekend |

### Các Biến Chính Được Chuẩn Hóa

| Chỉ Số | Định Nghĩa | Scope |
|---|---|---|
| **GMV** | Tổng sale_price tất cả orders (all statuses) | Toàn bộ dữ liệu |
| **Recognized Revenue** | Sale_price từ Complete + Shipped orders | Chỉ tính lợi nhuận hợp lệ |
| **Gross Profit** | sale_price - cost | Trên từng order item |
| **Gross Margin %** | Gross Profit / Revenue × 100 | Margin chân thực |
| **Status Leakage** | GMV - Recognized Revenue | Mất mát qua Cancelled/Processing/Returned |
| **AOV** | Revenue / Number of Orders | Doanh thu bình quân mỗi đơn |
| **Conversion Rate** | # session có purchase / total # session | Session-level, từ events table |
| **Repeat Purchase Rate** | # khách hàng 2+ đơn / total customers | Tỷ lệ quay lại mua |
| **Return Rate %** | returned_value / total_value × 100 | Tỷ lệ hàng hoàn trả |
| **Sell-through %** | # sold items / # received items × 100 | Hiệu suất bán hàng |
| **Inventory Aging (days)** | (snapshot_date - created_date) | Số ngày hàng chưa bán |
| **Frozen Capital** | sum(cost) cho unsold items | Vốn bị kẹt |
| **Holding Cost (annual %)** | 22% × frozen_capital | Chi phí lưu kho |

### Mối Quan Hệ (Relationships)

```
Fact_Order_Items ──[user_id]──> Dim_Users
                  ──[user_id]──> Dim_Users_RFM
                  ──[product_id]──> Dim_Products
                  ──[order_date_key]──> Dim_Date

Fact_Inventory    ──[product_id]──> Dim_Products
                  ──[distribution_center_id]──> Dim_Distribution_Centers
                  ──[created_date_key]──> Dim_Date

Agg_Funnel_Monthly ──[user_id]──> Dim_Users
                   ──[date_key]──> Dim_Date
```

## Power BI Dashboard

File Power BI: [powerbi/ET_Club_Dashboard.pbix](powerbi/ET_Club_Dashboard.pbix)

Dashboard bao gồm 5 trang phân tích với 30+ visual, được xây dựng dựa trên star schema và aggregate tables để tối ưu hóa tốc độ truy vấn.

### Trang 1: Executive Overview
- **KPI chính:** GMV, Recognized Revenue, Gross Profit, Gross Margin %, Status Leakage, AOV
- **Xu hướng:** Revenue & GM growth 2019-2023 (line chart)
- **Mục tiêu:** Đọc nhanh sức khỏe kinh doanh tổng thể

### Trang 2: Customer & Marketing Funnel
- **RFM Distribution:** Phân bố khách hàng theo segment (Champions/Loyal/At Risk/About to Lose/No Purchase)
- **Website Funnel:** Product Views → Add to Cart → Purchase, tỷ lệ cancel session
- **Traffic Source Performance:** Revenue events, user registrations, Purchase/User ratio theo kênh (Email/Adwords/Facebook/Organic)
- **Mục tiêu:** Xác định điểm nghẽn conversion và hiệu suất kênh acquisition vs re-engagement

### Trang 3: Product & Revenue Analysis
- **Category Quadrant:** Phân tích bubble chart (Revenue × Gross Margin % × Status Leakage %)
- **Price Band Performance:** Doanh thu, margin, return rate theo price tier (Men/Women)
- **Mục tiêu:** Tìm nhóm Star (scale), Fix, Markdown hoặc Stop-buy

### Trang 4: Operations & Root Causes
- **Inventory Metrics:** Sell-through %, frozen capital, holding cost theo category
- **Top Return/Cancel Clusters:** Danh sách chi tiết department, category, brand, price band, fulfillment status
- **Mục tiêu:** Phát hiện tồn kho cần markdown/rebalance và nguyên nhân cancel/return

### Trang 5: Forecast & Recommendations
- **12-Month Demand Forecast:** Dự báo theo category chính (Jeans, Outerwear & Coats, Sweaters)
- **Inventory Action Recommendations:** Monitor vs Markdown with guardrail vs Rebalance by DC
- **Mục tiêu:** Hướng dẫn hành động procurement và markdown cho 2024

## Cấu Trúc Thư Mục

```
E-Commerce Data-Driven Optimization & Profitability Pipeline/
├── data/
│   ├── raw/                     # Dữ liệu nguyên bản từ source
│   │   ├── users.csv
│   │   ├── products.csv
│   │   ├── orders.csv
│   │   ├── order_items.csv
│   │   ├── events.csv
│   │   ├── inventory_items.csv
│   │   └── distribution_centers.csv
│   ├── interim/                 # Dữ liệu trung gian (cleaning, feature eng)
│   └── processed/               # Dữ liệu cuối cùng cho BI (Fact/Dim tables)
│
├── notebooks/                   # Jupyter notebooks cho EDA, modeling, forecasting
│
├── powerbi/
│   └── ET_Club_Dashboard.pbix   # Power BI file chính
│
├── reports/
│   ├── Report.pdf               # Báo cáo cuối cùng
│   └── Dashboard/               # Screenshots của dashboard
│
├── src/                         # Python scripts cho ETL, analysis
│
├── docs/
│   ├── documents/               # Tài liệu, hướng dẫn
│   └── tasks/                   # Task lists, memo
│
├── requirements.txt             # Python dependencies
├── .gitignore
└── README.md                    # File này
```

## Chuẩn Bị Môi Trường

### 1. Tạo virtual environment

```bash
python -m venv .venv
```

### 2. Kích hoạt môi trường

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
```

### 4. Cài Jupyter nếu cần mở notebook

```bash
pip install jupyter jupyterlab
```

## Quy Trình ETL Và Phân Tích

### Phase 1: Data Ingestion & Cleaning (Mục 1 - Nhật Ký Dữ Liệu)

Mục tiêu là đọc 7 bảng raw (3.35M dòng), kiểm tra chất lượng, làm sạch và chuẩn bị metric.

**Các bước chính:**
- Đọc CSV raw: users, products, distribution_centers, orders, order_items, events, inventory_items
- Xử lý missing values theo ý nghĩa nghiệp vụ (gán Unknown hoặc giữ null)
- Loại bỏ outliers (giá bán < $1, tuổi ngoài 13-120)
- Kiểm tra trùng lặp primary key, toàn vẹn khóa ngoại
- Tạo biến: GMV, recognized_revenue, gross_profit, status_leakage, inventory_aging, sell_through, repeat_purchase_rate, return_rate
- Xuất Fact/Dim tables sang Parquet/CSV cho Power BI

**Kết quả:** 168,528 dòng order items sạch (từ 181,759), 7 bảng dimension chuẩn hóa

### Phase 2: Exploratory Analysis & Insights (Mục 2 - Phân Tích & Insights)

Phân tích chuyên sâu theo **6 nhóm insight chính:**

1. **Tăng trưởng từ volume, chưa từ hiệu quả** → Doanh thu +23x, GM bất biến ở 51.9%, AOV hẹp 85-87
2. **Rò rỉ doanh thu toàn hệ thống** → $4M (44.9% GMV) mất qua Processing, Returns, Cancellations
3. **Khủng hoảng giữ chân khách hàng** → 50.4% one-time buyer, LTV:CAC 1.1:1, repeat rate 0.85
4. **Điểm nghẽn tại checkout** → 63% add-to-cart nhưng 42% checkout, 41% cancel tại cart
5. **Phân tầng chất lượng ẩn trong danh mục** → Jeans doanh thu cao nhưng margin 46.5%, return 12.3%
6. **Tồn kho mùa vụ chết** → $8.98M frozen capital, sell-through 36.1%, seasonal items dead stock

### Phase 3: Modeling & Forecasting (Advanced Analytics)

- **Customer Clustering:** Rule-based RFM segmentation (Champions/Loyal/At Risk/About to Lose/No Purchase)
- **Demand Forecasting:** Time-series forecast 12 tháng cho 3 danh mục chủ lực (MAPE ~50.9%)
- **ABC Inventory Analysis:** Phân loại hàng để ưu tiên markdown, rebalance hay monitor

### Phase 4: Actionable Recommendations (Mục 3 - Đề Xuất Hành Động)

Xuất phát từ các insight, đề xuất **5 khuyến nghị hành động** với KPI rõ ràng cho từng initiative.

## Các Insight Chính

### Insight 1: Tăng Trưởng Từ Volume, Chưa Từ Hiệu Quả
- **Dữ Liệu:** Revenue 23x, GM bất biến ở 51.9%, AOV ổn định 85-87
- **Ý Nghĩa:** Doanh nghiệp mở rộng volume quá tốt, nhưng chưa cải thiện chất lượng mỗi đơn hàng hay hiệu quả giữ chân

### Insight 2: Rò Rỉ Doanh Thu Không Tầm Thường
- **Dữ Liệu:** $4M GMV (44.9%) chuyển thành status không sinh lợi
  - Processing backlog: $2M (50%)
  - Returns: $1M (25%)
  - Cancellations: $1M (25%)
- **Root Causes:**
  - Fulfillment delays gây SLA violation → khách cancel
  - Sizing mismatch ở premium items → return rate cao
  - Checkout friction (hidden fees, shipping time) → session-level cancel 41%

### Insight 3: Khủng Hoảng Giữ Chân Khách Hàng
- **Dữ Liệu:** 
  - 50.4% users mua một lần
  - Avg orders/buyer: 0.85
  - LTV:CAC: 1.1:1 (với giả định CAC $40)
  - Cohort 2019 chỉ 9.1% quay lại năm 2023
- **Nguyên Nhân:** Đốt tiền acquisition, quên retention. Email Re-engagement có Purchase/User 20.8x tốt hơn Adwords 1.4x

### Insight 4: Điểm Nghẽn Tại Cart Checkout
- **Funnel:** 682K product views → 432K add-to-cart (63%) → 182K purchase (42% of cart)
- **Vấn Đề:** 126K cancel session (41% cancel rate) trong checkout
- **Giả Thuyết:** Shipping cost/ETA quá lâu, payment failed, hoặc guest checkout bị block

### Insight 5: Phân Tầng Chất Lượng Ẩn Trong Danh Mục
- **Stars (Scale):** Outerwear & Coats, Suits & Sport Coats → GM 59-62%, return <10%
- **Volume but High Leakage:** Jeans → $648K revenue nhưng GM chỉ 46.5%, return 12.3%
- **Premium Price Band Risk:** Men $200+ có return 12.3% vs $100-200 chỉ 8.8%

### Insight 6: Tồn Kho Mùa Vụ Không Giải Phóng Kịp
- **Frozen Capital:** $8.98M (22% annual holding cost = $4.47M)
  - Jeans: $1M (highest frozen capital, lowest sell-through)
  - Outerwear/Coats: $900K
  - Sweaters: $600K
  - Fashion Hoodies: $500K
- **Vấn Đề:** Seasonal items chưa markdown trước hết mùa thành dead stock

## Khuyến Nghị Hành Động

| # | Khuyến Nghị | Cơ Sở Dữ Liệu | Kết Quả Kỳ Vọng | KPI Theo Dõi |
|---|---|---|---|---|
| 1 | **Giải Phóng Vốn Bằng ABC-Aging Inventory Playbook** | Tồn kho 313K units, frozen capital $8.98M, sell-through 36.1% | Trong 2 quý, giảm aged inventory cost 15-20%, tăng sell-through từ 36.1% → 42-45% | aged_inventory_cost, sell_through_%, gross_margin_after_markdown, weeks_of_supply |
| 2 | **Xây Dựng Retention Engine Theo RFM Thay Vì Chỉ Acquisition** | 50.4% no purchase, 76.6% one-time, LTV:CAC 1.1:1, cohort 2019 chỉ 9.1% quay lại | Welcome series, post-purchase flow, win-back emails, loyalty program. Tăng repeat rate +3-5 điểm % trong 90 ngày | first_valid_purchase_rate, 90day_repeat_rate, reactivation_rate, gross_profit_LTV |
| 3 | **Kiểm Soát Status Leakage Theo Nhóm Rủi Ro Cao** | $2.3M status leakage (2023), Processing 19.85% GMV, return rate 10.1% | Dashboard tracking, SLA xử lý, audit root cause (stock sync, payment failure, fulfillment delay, size/fit) | leakage_rate, leakage_value, processing_aging, cancel_value, return_value |
| 4 | **Tăng Conversion Tại Cart Bằng CRM Recovery & Checkout Experiment** | 63% add-to-cart, 42% checkout, 41% cancel. Email Purchase/User 1.56x cao nhất | Abandoned-cart flow (1h/24h/72h), guest checkout test, early shipping ETA display, payment retry | cart_recovery_rate, cart_to_purchase_rate, product_to_purchase_rate, revenue_recovered |
| 5 | **Tối Ưu Product Mix Để Tăng Gross Profit (Không Chỉ Revenue)** | Jeans revenue $648K nhưng margin 46.5%, return 12.3%. Stars (Outerwear, Suits) margin 59-62%, return <10% | Scale Star categories, cải tiến cost/price/PDP confidence cho Jeans, markdown hoặc bundle test | gross_profit_mix, category_margin, category_leakage_value, AOV, bundle_attach_rate |

**Tóm Lại:** Chiến lược 2024 không phải tăng volume thêm mà **giải phóng dòng tiền, giảm leakage, xây dựng retention và tối ưu unit economics**.

## Chuẩn Bị Môi Trường

### 1. Tạo và Kích Hoạt Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

**File requirements.txt chứa:**
- pandas, numpy (xử lý dữ liệu)
- matplotlib, seaborn, plotly (visualize)
- scikit-learn (clustering, forecasting)
- statsmodels (time-series analysis)
- jupyter, jupyterlab (notebook)
- openpyxl (Excel export)

### 3. Cài Đặt Power BI & Excel

- **Power BI Desktop:** https://powerbi.microsoft.com/downloads/
- File Power BI: `powerbi/ET_Club_Dashboard.pbix`

## Tài Liệu Tham Khảo

### Tài Liệu Chính

1. **Report.pdf** - Báo cáo cuối cùng (24 trang) bao gồm:
   - Mục 1: Nhật Ký Dữ Liệu (Data Cleaning Log)
   - Mục 2: Phân Tích & Insights (6 main insights + dashboards)
   - Mục 3: Đề Xuất Hành Động (5 khuyến nghị với KPI)
   - Mục 4: Phụ Lục (Tài liệu tham khảo)

### Nguồn Dữ Liệu Kinh Tế Vĩ Mô

2. **U.S. Bureau of Labor Statistics** - Consumer Price Index (CPI)
   - Link: https://www.bls.gov/cpi/data.htm
   - Dùng để so sánh inflation context 2019-2023

3. **Drewry World Container Index**
   - Link: https://www.drewry.co.uk/wci
   - Phản ánh biến động cước vận tải biển

4. **National Retail Federation (2023)** - Consumer Returns in Retail Industry
   - Link: https://nrf.com/research/2023-consumer-returns-retail-industry
   - Benchmark return rate ngành thời trang

### Tài Liệu Kỹ Thuật

- **Pandas & SQL:** Data cleaning & aggregation
- **Scikit-learn:** RFM clustering
- **Statsmodels/Prophet:** Time-series forecasting
- **Power BI DAX:** Metric calculation & aggregation

## Liên Hệ & Ghi Chú

**Dự án được hoàn thành:** Tháng 5, 2026  
**Tác giả:** Trần Viết Gia Huy  
**Email/Contact:** [Thông tin liên hệ]

**Ghi Chú Kỹ Thuật:**
- Dữ liệu raw được giữ nguyên trong `data/raw/` để đảm bảo truy vết
- Tất cả xử lý dữ liệu được thực hiện qua Python/Pandas pipeline
- Power BI import processed data từ `data/processed/` (Parquet/CSV)
- Forecast MAPE ~50.9% - dùng để hướng dẫn trend, không phải tham chiếu tuyệt đối
