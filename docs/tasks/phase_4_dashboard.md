# Phase 4: Dashboard & Insight Storyline

**Thời gian:** 10-12/05/2026  
**Trạng thái:** dashboard spec đã đồng bộ với narrative phân tích canonical.  
**Mục tiêu:** Power BI/Tableau phải làm nổi bật 5 điểm nghẽn chính: status leakage, retention, cart-to-purchase, product mix và inventory aging.

---

## 1. Dashboard principles

Dashboard dùng cùng định nghĩa metric với báo cáo:

- `GMV all-status`: tổng giá trị mọi line item.
- `Recognized revenue`: chỉ Complete + Shipped.
- `Gross profit`: recognized revenue trừ cost.
- `Status leakage`: Cancelled + Returned + Processing GMV.
- `Traffic source performance`: purchase intensity, không gọi là ROI vì thiếu spend.
- `Holding cost estimate`: chi phí lưu kho ước tính đến cutoff, không gọi là annual recurring cost thật.

Các page phải tránh kết luận net margin, true CAC, true ROAS hoặc contribution margin vì dataset không có đủ chi phí.

---

## 2. Page 1 - Executive Overview

### Mục tiêu

Cho Ban Giám đốc thấy ET Club tăng trưởng tốt nhưng chất lượng tăng trưởng bị bào mòn bởi leakage, retention yếu và inventory kẹt vốn.

### KPI cards

| Card | Giá trị gợi ý | Cách đọc |
|---|---:|---|
| Recognized revenue 2023 | $2.819M | doanh thu ghi nhận Complete + Shipped |
| GMV all-status 2023 | $5.121M | demand/order value phát sinh |
| Gross margin | 51.9% | ổn định, không phải điểm nghẽn COGS chính |
| Status leakage 2023 | $2.302M / 45.0% | giá trị chưa thành recognized revenue |
| Sell-through | 36.1% | inventory quay vòng chậm |

### Visuals

| Visual | Nội dung | Insight cần hiện rõ |
|---|---|---|
| Revenue + margin trend | recognized revenue và gross margin 2019-2023 | growth nhanh, margin phẳng |
| GMV waterfall | GMV -> recognized revenue -> Cancelled/Returned/Processing | leakage là vấn đề chuyển hóa |
| Status distribution | item count/value theo status | Processing cần SLA riêng |
| Executive action matrix | 5 ưu tiên + KPI | từ insight sang hành động |

---

## 3. Page 2 - Customer & Loyalty

### Mục tiêu

Giải thích vì sao customer base lớn nhưng lifetime value yếu.

### Visuals

| Visual | Nội dung |
|---|---|
| RFM segment bar | No valid purchase 50.5%, At Risk 18.8%, Loyal 13.7%, About to Lose 9.6%, Champions 6.8% |
| Cohort heatmap | signup cohort x purchase year; nhấn mạnh 2019 cohort còn 9.1% ở 2023 |
| Cluster profile table | 7 cluster từ Phase 3 và hướng xử lý |
| LTV:CAC scenario card | CAC $40 là giả định; ratio 1.1:1 chỉ là warning scenario |

### Actions shown

- First-purchase conversion cho `No Valid Purchase`.
- Post-purchase journey cho one-time buyers.
- Win-back cho `At-Risk High Value`.
- Loyalty/referral cho `High-Value Loyal`.

---

## 4. Page 3 - Product, Revenue & Leakage

### Mục tiêu

Không chỉ xếp hạng category theo revenue; phải chỉ ra category nào tạo profit tốt, category nào có leakage value lớn.

### Visuals

| Visual | Nội dung |
|---|---|
| Category matrix | X = recognized revenue, Y = gross margin, size = GMV, color = leakage rate |
| Category table | revenue, gross profit, margin, return rate, cancelled value, processing backlog |
| Top leakage categories | Outerwear & Coats, Jeans, Sweaters, Suits & Sport Coats... |
| Margin comparison | Star/Cash Cow/Dog |
| Price-band action table | category x department x price band, action: fit/size, cancellation, pricing |
| Basket affinity table | category pairs, orders, support, confidence, lift, bundle action |

### Interpretation guardrail

Return rate khoảng 9-11% giữa nhiều category, vì vậy không nên kết luận một category đơn lẻ là nguyên nhân toàn bộ margin puzzle. Ưu tiên phải dựa trên leakage value tuyệt đối, margin và khả năng xử lý.

### E-commerce add-ons

- `price_band_performance.csv`: dùng để chỉ ra nhóm giá cần PDP confidence, cancellation diagnosis hoặc pricing/supplier review.
- `basket_affinity_analysis.csv`: dùng cho cross-sell/bundle candidates; chỉ triển khai thử nghiệm khi lift và order support đủ lớn.

---

## 5. Page 4 - Marketing Funnel & Conversion

### Mục tiêu

Tìm điểm nghẽn trong hành trình website mà không gọi nhầm là ROI.

### Funnel numbers

| Stage | Events | Sessions | Conversion |
|---|---:|---:|---:|
| Product | 845,607 | 681,759 | 100.0% |
| Cart | 595,994 | 432,146 | 63.4% theo session |
| Purchase | 181,759 | 181,759 | 42.1% theo session từ cart |

### Traffic source table

| Source | Purchase events | Global users | Purchase events/user |
|---|---:|---:|---:|
| Email | 81,706 | 52,255 | 1.56 |
| Adwords | 54,542 | 39,641 | 1.38 |
| Facebook | 18,305 | 16,330 | 1.12 |
| YouTube | 18,082 | 16,138 | 1.12 |
| Organic | 9,124 | 8,589 | 1.06 |

### Journey by source

Use `journey_funnel_by_source.csv` to show source-level stage reach:

| Field | Use |
|---|---|
| `event_share_within_source_pct` | event mix by source |
| `session_reach_within_source_pct` | stage reach inside source sessions |
| `product_to_cart_session_cvr_pct` | product-to-cart conversion by source |
| `cart_to_purchase_session_cvr_pct` | cart-to-purchase conversion by source |

### Actions shown

- A/B test checkout friction.
- Abandoned-cart email trong 1h/24h/72h.
- Hiển thị shipping ETA/fee sớm.
- Size guide/review/fit note cho category có return risk cao.

---

## 6. Page 5 - Operations & Inventory

### Mục tiêu

Biến inventory từ bảng vận hành thành câu chuyện vốn lưu động và tốc độ luân chuyển.

### KPI cards

| Metric | Giá trị |
|---|---:|
| Total inventory units | 490,705 |
| Unsold units | 313,351 |
| Sell-through | 36.1% |
| Avg holding days - unsold | 737 |
| Frozen capital | $8.98M |
| Holding cost estimate to cutoff | $4.47M |

### Visuals

| Visual | Nội dung |
|---|---|
| Inventory aging histogram | buckets 0-90, 91-180, 181-365, >365 ngày |
| ABC matrix | revenue/profit vs aged inventory cost |
| Unsold by category/DC | tìm nơi kẹt vốn |
| Markdown action table | category, aged cost, suggested action |
| Return/cancel proxy table | category-brand-price-fulfillment bucket, hypothesis, action |

### E-commerce add-ons

- `inventory_abc_aging_by_category_dc.csv`: phân nhóm `Rebalance allocation by DC`, `Markdown with margin guardrail`, `Monitor`.
- `return_cancel_root_cause_proxy.csv`: tạo queue điều tra cho checkout/payment/inventory sync, backlog SLA, size/fit/content confidence.

---

## 7. Page 6 - Forecast & Scenario

### Mục tiêu

Thể hiện predictive thinking nhưng không thổi phồng mô hình.

### Content

| Element | Nội dung |
|---|---|
| Forecast line | 12-month baseline forecast cho Outerwear & Coats, Jeans, Sweaters |
| MAPE card | 47.2-55.5%, summary 50.9% |
| Caveat box | `seasonal_naive_fallback`, dùng baseline only |
| Improvement backlog | promotion, price/discount, stockout, holiday/fashion calendar |

### Interpretation

Forecast giúp đặt kịch bản inventory và câu hỏi quản trị. Không dùng forecast hiện tại để quyết định mua hàng tự động.

---

## 8. Final dashboard checklist

- [ ] Tất cả page dùng recognized revenue, không dùng nhầm GMV làm revenue.
- [ ] Traffic source page không có cột ROI nếu chưa có spend.
- [ ] LTV:CAC luôn ghi rõ là scenario với CAC giả định.
- [ ] Holding cost ghi là estimate to cutoff.
- [ ] Có ít nhất một visual cho basket affinity hoặc price-band action.
- [ ] Có ít nhất một visual cho inventory ABC-aging theo category/DC.
- [ ] Return/cancel proxy được ghi là proxy/hypothesis, không gọi là nguyên nhân chắc chắn.
- [ ] Mỗi insight lớn có action và KPI đi kèm.
- [ ] Page executive có thể đọc trong 60 giây và nêu rõ 3 bottleneck: leakage, retention, inventory.
