# E-Commerce Data-Driven Optimization & Profitability Pipeline

> ET Club / DATAVISION 2026 - dữ liệu e-commerce, ETL, phân tích 4 trụ cột, mô hình dự báo và Power BI dashboard.

## Mục Lục

1. [Tổng Quan](#tổng-quan)
2. [Bài Toán Kinh Doanh](#bài-toán-kinh-doanh)
3. [Tài Liệu Báo Cáo](#tài-liệu-báo-cáo)
4. [Cấu Trúc Dữ Liệu Fact/Dim](#cấu-trúc-dữ-liệu-factdim)
5. [Power BI Dashboard](#power-bi-dashboard)
6. [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
7. [Chuẩn Bị Môi Trường](#chuẩn-bị-môi-trường)
8. [Quy Trình ETL Và Phân Tích](#quy-trình-etl-và-phân-tích)
9. [Hướng Dẫn Chạy](#hướng-dẫn-chạy)
10. [Tài Liệu Tham Khảo](#tài-liệu-tham-khảo)
11. [Liên Hệ](#liên-hệ)

## Tổng Quan

Dự án này phân tích hoạt động kinh doanh của ET Club trong giai đoạn 2019-2023, với mục tiêu chuẩn hóa metric, kiểm tra chất lượng tăng trưởng và đề xuất hành động tối ưu doanh thu, lợi nhuận và tồn kho.

Các trọng tâm chính của dự án:

- Chuẩn hóa các metric doanh thu thành GMV all-status, recognized revenue, recognized gross profit và status leakage.
- Phân tích 4 trụ cột: khách hàng, sản phẩm và doanh thu, marketing và chuyển đổi, vận hành và chuỗi cung ứng.
- Xây dựng pipeline ETL để tạo dữ liệu sạch cho Power BI.
- Tổng hợp báo cáo kinh doanh cuối cùng và dashboard 5 trang để hỗ trợ quyết định.

Tải báo cáo tổng hợp tại đây: [Download Report.pdf](reports/Report.pdf)

## Bài Toán Kinh Doanh

Câu hỏi trung tâm của dự án là: ET Club tăng trưởng rất nhanh, nhưng chất lượng tăng trưởng đang bị rò rỉ ở đâu và nên ưu tiên hành động gì trước?

Kết quả nổi bật cần lưu ý:

- Recognized revenue tăng từ khoảng 122.6K USD năm 2019 lên 2.819M USD năm 2023.
- Gross margin giữ ổn định quanh 51.9%, cho thấy vấn đề chính không nằm ở COGS trực tiếp.
- Status leakage đạt khoảng 4.50M USD, tương đương 44.9% GMV giai đoạn 2019-2023.
- 50.5% người dùng không có giao dịch hợp lệ.
- 76.6% khách hàng hợp lệ chỉ mua một lần.
- 313,351 đơn vị tồn kho chưa bán, sell-through khoảng 36.1%.
- Holding cost ước tính khoảng 4.47M USD và frozen capital khoảng 8.98M USD.

Thông điệp chính của báo cáo là: cần chuyển trọng tâm từ tăng volume sang giảm leakage, tăng repeat purchase, tối ưu funnel và giải phóng tồn kho.

## Tài Liệu Báo Cáo

Báo cáo và phụ lục đã được đặt trong thư mục `reports/` để dễ tải xuống và xem nhanh.

- Báo cáo chính: [reports/Report.pdf](reports/Report.pdf)
- Ảnh dashboard: [reports/Dashboard](reports/Dashboard)

## Cấu Trúc Dữ Liệu Fact/Dim

Dự án dùng star schema để tối ưu phân tích trong Power BI. Các bảng chính được chia thành fact tables, dimension tables và bảng aggregate cho funnel.

### Fact Tables

| Bảng | Số dòng | Grain | Vai trò |
|---|---:|---|---|
| Fact_Transactions | 168,528 | Mỗi dòng là một order item | Phân tích doanh thu, gross profit, status leakage, return value |
| Fact_Inventory | 490,705 | Mỗi dòng là một inventory item | Phân tích tồn kho, sell-through, holding days, frozen capital |
| Agg_Funnel_Monthly | 1,828 | year_month x event_type x traffic_source | Tối ưu Power BI cho funnel và journey analysis |

### Dimension Tables

| Bảng | Số dòng | Grain | Vai trò |
|---|---:|---|---|
| Dim_Users | 100,000 | Mỗi user | Hồ sơ khách hàng, RFM, traffic source, demographic features |
| Dim_Users_with_Clusters | 100,000 | Mỗi user | Bổ sung cluster label từ rule-based clustering |
| Dim_Products | 29,120 | Mỗi product | Danh mục, brand, department, retail price, cost |
| Dim_DCs | 10 | Mỗi distribution center | Thông tin trung tâm phân phối và state |
| Dim_Date | 1,826 | Mỗi ngày | Calendar attributes, year, quarter, month, weekday |

### Mối Quan Hệ Chính

- Fact_Transactions liên kết tới Dim_Users, Dim_Products và Dim_Date.
- Fact_Inventory liên kết tới Dim_Products, Dim_DCs và Dim_Date.
- Agg_Funnel_Monthly hỗ trợ phân tích funnel, event source và user journey theo tháng.
- Dim_Users_with_Clusters được dùng khi cần phân tích phân khúc nâng cao.

## Power BI Dashboard

File Power BI chính của dự án là: [powerbi/ET_Club_Dashboard.pbix](powerbi/ET_Club_Dashboard.pbix)

Thư mục `powerbi/` chỉ giữ file `.pbix` này để đảm bảo repo gọn và dễ tải. Các ảnh dưới đây nằm trong `reports/Dashboard/` và được chèn trực tiếp vào README để nhà tuyển dụng xem ngay mà không cần mở Power BI.

### Executive Overview

![Executive Overview](reports/Dashboard/Executive%20Overview.png)

Trang này tập trung vào các chỉ số tổng quan nhất: GMV, revenue, gross profit, gross margin, status leakage và AOV. Đây là trang dùng để đọc nhanh sức khỏe kinh doanh và xác định có đang tăng trưởng đúng chất lượng hay không.

### Customer & Marketing

![Customer & Marketing](reports/Dashboard/Customer%20%26%20Marketing.png)

Trang này cho thấy phân bố RFM, traffic source performance, funnel by sessions và purchase events theo nguồn. Phần này được dùng để đánh giá chất lượng traffic, mức độ chuyển đổi và hành vi mua lại.

### Product & Revenue

![Product & Revenue](reports/Dashboard/Product%20%26%20Revenue.png)

Trang này phân tích doanh thu theo category, gross profit, gross margin, leakage theo status và price band performance. Mục tiêu là xác định nhóm danh mục tạo doanh thu tốt nhưng đang bị rò rỉ lợi nhuận hoặc có rủi ro return cao.

### Operations & Root Causes

![Operations & Root Causes](reports/Dashboard/Operations%20%26%20Root%20Causes.png)

Trang này tập trung vào inventory sell-through, frozen capital, holding cost, aged inventory theo DC và các nhóm root cause của return/cancel. Đây là nơi phát hiện tồn kho nào cần markdown, rebalancing hoặc theo dõi sát.

### Forecast & Recommendations

![Forecast & Recommendations](reports/Dashboard/Forecast%20%26%20Recommendations.png)

Trang này trình bày forecast 12 tháng, sai số dự báo theo category và các khuyến nghị hành động cho tồn kho, giá bán và kế hoạch nhu cầu. Phần này đóng vai trò chuyển insight sang hành động vận hành.

## Cấu Trúc Thư Mục

```text
E-Commerce Data-Driven Optimization & Profitability Pipeline/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── docs/
│   ├── documents/
│   └── tasks/
├── notebooks/
├── powerbi/
│   └── ET_Club_Dashboard.pbix
├── reports/
│   ├── Report.pdf
│   └── Dashboard/
├── src/
├── .gitignore
├── README.md
└── requirements.txt
```

Lưu ý:

- `data/external/` và `docs/report/` đã được kiểm tra và bỏ vì là thư mục rỗng.
- Thư mục `powerbi/` chỉ giữ file `ET_Club_Dashboard.pbix`.

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

### Phase 1: Data Ingestion và Cleaning

Mục tiêu của phase 1 là đọc dữ liệu raw, kiểm tra chất lượng và tạo các bảng fact/dim phục vụ phân tích.

Các bước chính:

- Đọc `orders.csv`, `order_items.csv`, `inventory_items.csv`, `events.csv`, `users.csv`, `products.csv`, `distribution_centers.csv`.
- Làm sạch giá trị null và kiểm tra logic ngày tháng.
- Gắn cờ bot traffic, order lỗi và outlier giá bán thấp.
- Tạo các biến như gross profit, recognized revenue, revenue leakage và holding days.
- Xuất dữ liệu sang CSV và Parquet cho Power BI.

### Phase 2: Exploratory Analysis

Phase 2 phân tích theo 4 trụ cột:

- Customer: RFM, cohort, repeat rate, retention.
- Product: revenue, margin, leakage, return rate.
- Marketing: funnel, source journey, traffic source performance.
- Operations: sell-through, inventory aging, holding cost, fulfillment.

### Phase 3: Advanced Modeling

Phase 3 dùng các baseline/advanced models cho clustering và forecasting:

- Customer clustering.
- Demand forecasting 12 tháng.
- Đánh giá sai số dự báo theo category.

### Phase 4: Dashboard Delivery

Phase 4 tổng hợp các insight thành dashboard Power BI và báo cáo cuối cùng.


