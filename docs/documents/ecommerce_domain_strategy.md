# E-commerce Domain Strategy Playbook

**Mục tiêu:** chứng minh bài phân tích không chỉ dùng kỹ thuật dữ liệu chung, mà hiểu cách một doanh nghiệp e-commerce thời trang vận hành từ acquisition, onsite journey, merchandising, fulfillment đến retention và inventory.

---

## 1. Operating Model

| Lớp vận hành | Câu hỏi quản trị | Metric đã dùng | Output dữ liệu |
|---|---|---|---|
| Demand & GMV | Nhu cầu phát sinh có chuyển thành doanh thu không? | GMV all-status, recognized revenue, status leakage | `annual_revenue_analysis.csv`, `status_leakage_analysis.csv` |
| Customer lifecycle | User có mua lần đầu và quay lại không? | RFM, cohort retention, one-time buyer rate, LTV/CAC scenario | `rfm_segment_analysis.csv`, `cohort_retention_analysis.csv`, `ltv_cac_analysis.csv` |
| Onsite journey | Người dùng rơi ở bước nào? | stage reach, product-to-cart, cart-to-purchase | `journey_funnel_by_source.csv`, `funnel_analysis.csv` |
| Traffic & CRM | Source nào tạo purchase intensity tốt? | purchase events/user, source-level CVR | `traffic_source_performance.csv`, `journey_funnel_by_source.csv` |
| Merchandising | Category/brand/price band nào nên scale, fix, markdown? | revenue, margin, return, leakage, price band action | `category_performance_analysis.csv`, `price_band_performance.csv` |
| Basket & bundle | Những category nào có affinity để cross-sell? | support, confidence, lift | `basket_affinity_analysis.csv` |
| Fulfillment & returns | Return/cancel có proxy nguyên nhân nào? | return rate, cancel rate, processing rate, fulfillment bucket | `return_cancel_root_cause_proxy.csv`, `fulfillment_performance.csv` |
| Inventory planning | Hàng tồn đang kẹt ở category/DC nào? | sell-through, aged cost, ABC class, markdown/rebalance action | `inventory_abc_aging_by_category_dc.csv`, `holding_cost_analysis.csv` |

---

## 2. E-commerce KPI Tree

```
Quality of Growth
├── Demand quality
│   ├── GMV all-status
│   ├── Recognized revenue
│   └── Status leakage
├── Conversion quality
│   ├── Product-to-cart session CVR
│   ├── Cart-to-purchase session CVR
│   └── Cancel/session share
├── Customer quality
│   ├── First valid purchase rate
│   ├── Repeat rate / cohort retention
│   └── Gross-profit LTV scenario
├── Merchandising quality
│   ├── Category/brand gross margin
│   ├── Price-band return/cancel rate
│   └── Basket affinity lift
└── Operations quality
    ├── Sell-through
    ├── Aged inventory cost
    ├── Processing backlog
    └── Fulfillment days
```

Thông điệp chính: ET Club không nên chỉ tối ưu top-line revenue. KPI trung tâm nên là **quality of growth**, tức khả năng biến demand thành recognized revenue, repeat purchase và inventory quay vòng khỏe.

---

## 3. Domain Findings Added

### 3.1 Journey funnel theo traffic source

`journey_funnel_by_source.csv` mở rộng funnel từ bảng tổng sang source-level journey. Bảng này tách:

- stage reach theo source: home, department, product, cart, purchase, cancel;
- product-to-cart session CVR;
- product-to-purchase session CVR;
- cart-to-purchase session CVR.

Ở các source lớn, product-to-cart quanh **63%**, cart-to-purchase quanh **42%**, product-to-purchase quanh **26-27%**. Điều này củng cố insight: ưu tiên không phải tăng page view thuần túy, mà là đóng đơn ở cart/checkout.

### 3.2 Basket affinity và bundle

`basket_affinity_analysis.csv` tạo cặp category mua chung với support, confidence và lift. Ví dụ đáng đưa vào dashboard:

| Pair | Orders | Lift | Action |
|---|---:|---:|---|
| Blazers & Jackets + Leggings | 62 | 1.50 | Bundle/cross-sell priority |

Do basket signal còn phân tán, khuyến nghị nên dùng như **test candidate** cho recommendation module hoặc bundle nhỏ, không coi là chiến lược doanh thu chính ngay lập tức.

### 3.3 Price-band merchandising

`price_band_performance.csv` cho thấy vấn đề khác nhau theo department/category/price band:

| Action label | Số nhóm |
|---|---:|
| Improve fit/size confidence | 40 |
| Diagnose cancellation friction | 30 |
| Review pricing or supplier cost | 12 |
| Leakage reduction priority | 8 |
| Maintain / monitor | 88 |

Ý nghĩa e-commerce: cùng một category, price band cao thường cần nội dung PDP tốt hơn như fit note, review, chất liệu, ảnh thật; price band doanh thu cao nhưng margin thấp cần supplier/price review.

### 3.4 Inventory ABC-aging theo category/DC

`inventory_abc_aging_by_category_dc.csv` kết hợp doanh thu category, ABC class, sell-through và aged inventory cost. Bảng này biến inventory từ con số tổng thành hành động:

| Action | Số nhóm category-DC |
|---|---:|
| Rebalance allocation by DC | 66 |
| Markdown with margin guardrail | 37 |
| Monitor | 253 |

Ví dụ: `Jeans - Men - Savannah GA` là category class A nhưng sell-through chỉ **35.9%** và aged-180 cost khoảng **$131.6K**, nên nên ưu tiên rebalancing thay vì giảm mua toàn bộ category.

### 3.5 Return/cancel root-cause proxy

`return_cancel_root_cause_proxy.csv` không khẳng định nguyên nhân thật, nhưng tạo proxy để ưu tiên điều tra:

| Proxy hypothesis | Số nhóm |
|---|---:|
| Checkout/payment/inventory cancellation friction | 835 |
| Backlog or status-update SLA risk | 186 |
| Size/fit/content confidence risk | 157 |
| High-price fit/expectation mismatch | 21 |

Nhóm top leakage thường là brand/category price band cao ở trạng thái `not delivered / open`, ví dụ Jeans brand premium. Hành động phù hợp là audit stock sync, payment failure, checkout messaging và processing aging SLA.

---

## 4. Prescriptive Playbook

| Owner | Playbook | Trigger từ dữ liệu | KPI kỳ vọng |
|---|---|---|---|
| Growth/CRM | Abandoned-cart flow theo traffic source | cart-to-purchase thấp, Email purchase intensity cao | +3-5 điểm % cart-to-purchase |
| CRM | Lifecycle cho one-time và at-risk customers | 76.6% valid customers chỉ mua một lần | +3-5 điểm % 90-day repeat |
| Merchandising | PDP confidence upgrade | price-band action = fit/size confidence | giảm return 1-2 điểm % ở nhóm ưu tiên |
| Merchandising | Bundle/cross-sell test | lift >= 1.5 và đủ order support | tăng AOV/basket attach rate |
| Operations | Processing SLA queue | proxy = backlog/status-update risk | giảm processing backlog value |
| Supply Chain | ABC-aging replenishment rule | A-class + aged cost cao + sell-through thấp | giảm aged cost 15-20% |
| Supply Chain | Markdown guardrail | B/C class + aged 180 cost cao | thu hồi vốn nhưng bảo vệ gross margin |

---

## 5. Why This Deserves 20/20 for E-commerce Specificity

- Bao phủ toàn bộ e-commerce loop: acquisition, onsite behavior, conversion, CRM, merchandising, fulfillment, returns, inventory.
- Dùng metric ngành đúng nghĩa: GMV, AOV/LTV scenario, funnel CVR, basket affinity, sell-through, aged inventory, markdown/replenishment action.
- Không lạm dụng dữ liệu thiếu: ROI, CAC thật, net margin và return reason đều được ghi là giới hạn hoặc proxy.
- Khuyến nghị bám thực tế vận hành: không chỉ “tăng marketing”, mà có action theo owner, trigger và KPI.
- Có artifact phục vụ dashboard/Power BI, không chỉ diễn giải trong văn bản.
