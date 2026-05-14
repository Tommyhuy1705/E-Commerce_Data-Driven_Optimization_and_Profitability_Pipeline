# Phase 2: Phân tích dữ liệu, Insight & E-commerce Specificity

**Thời gian:** 08-10/05/2026  
**Trạng thái:** hoàn thành, đã chuẩn hóa metric và đã bổ sung lớp phân tích đặc thù e-commerce.  
**Mục tiêu rubric:** đạt tối đa cho `Phân tích dữ liệu & Insight` và `Phân tích theo đặc thù lĩnh vực E-Commerce`.

---

## 1. Nguyên tắc phân tích

Phase 2 dùng dữ liệu processed làm nguồn chuẩn, loại năm 2024 khỏi phân tích xu hướng năm vì dữ liệu chưa đủ kỳ. Các metric quan trọng được tách rõ:

| Metric | Vai trò |
|---|---|
| GMV all-status | đo tổng nhu cầu/giá trị đơn hàng phát sinh |
| Recognized revenue | chỉ gồm Complete + Shipped |
| Gross profit | recognized revenue trừ cost |
| Status leakage | Cancelled + Returned + Processing GMV |
| Return/CAC/Holding cost | scenario/proxy, không dùng để kết luận net profit thật |

Điểm kiểm soát: không kết luận ROI, CAC thực tế, contribution margin hoặc net margin vì dataset thiếu marketing spend, shipping cost, tax, discount và chi phí vận hành.

---

## 2. Output phân tích đã sinh

| File processed | Nội dung |
|---|---|
| `annual_revenue_analysis.csv` | GMV, recognized revenue, gross profit, margin, leakage theo năm |
| `status_leakage_analysis.csv` | breakdown value theo status/năm |
| `rfm_segment_analysis.csv` | phân khúc RFM/valid purchase |
| `cohort_retention_analysis.csv` | retention theo cohort signup/purchase year |
| `ltv_cac_analysis.csv` | LTV:CAC scenario có khai báo giả định |
| `category_performance_analysis.csv` | revenue, profit, margin, return, leakage theo category |
| `funnel_analysis.csv` | product/cart/purchase conversion |
| `journey_funnel_by_source.csv` | source-level journey reach và product/cart/purchase CVR |
| `traffic_source_performance.csv` | purchase intensity theo traffic source |
| `basket_affinity_analysis.csv` | category pair support, confidence, lift cho bundle/cross-sell |
| `price_band_performance.csv` | price-band margin, return, cancel, leakage và action |
| `inventory_turnover_analysis.csv` | sell-through, sold/unsold units, holding days |
| `holding_cost_analysis.csv` | frozen capital và holding-cost-to-cutoff estimate |
| `inventory_abc_aging_by_category_dc.csv` | ABC inventory, aged cost, sell-through và action theo category/DC |
| `return_cost_analysis.csv` | return value và return cost scenario |
| `return_cancel_root_cause_proxy.csv` | proxy root-cause cho return/cancel/processing theo category-brand-price-fulfillment |
| `fulfillment_performance.csv` | thời gian ship/deliver trung bình |

---

## 3. Insight chính đã chọn cho báo cáo

### Insight 1 - Tăng trưởng nhanh nhưng leakage giữ quanh 45%

2019-2023, recognized revenue tăng từ **$122.6K** lên **$2.819M**, trong khi GMV all-status tăng từ **$222.8K** lên **$5.121M**. Gross margin giữ quanh **51.9%**, nhưng status leakage luôn quanh **44.6-45.0%**.

Chẩn đoán: ET Club có demand, nhưng năng lực chuyển hóa demand thành revenue hợp lệ chưa cải thiện tương ứng với tốc độ scale. Năm 2023 có **$2.302M** GMV nằm ở Cancelled, Returned hoặc Processing.

### Insight 2 - Retention là điểm nghẽn customer economics

RFM cho thấy **50.5% users không có valid purchase**. Trong nhóm valid customers, **76.6% là one-time buyers**. Cohort 2019 còn **9.1%** mua lại trong 2023.

Chẩn đoán: tăng trưởng đang phụ thuộc nhiều vào acquisition/volume mới. LTV:CAC chỉ được trình bày như scenario: giả định CAC **$40**, gross-profit LTV one-time buyer **$44.71**, ratio **1.1:1**.

### Insight 3 - Product mix cần tối ưu theo profit và leakage, không chỉ revenue

Top revenue categories như `Outerwear & Coats`, `Jeans`, `Sweaters`, `Suits & Sport Coats` có profile rất khác nhau. `Outerwear & Coats` có revenue **$673.8K**, margin **55.5%**, nhưng leakage **$528.5K**. `Jeans` có revenue **$648.1K**, nhưng margin thấp hơn **46.5%** và leakage **$518.1K**.

Chẩn đoán: category strategy phải tách thành Star/Cash Cow/Dog. Scale category có margin tốt, tối ưu cost/price ở Cash Cow và giảm mua mới với Dog/slow-moving.

### Insight 4 - Funnel nghẽn ở cart-to-purchase

Funnel processed ghi nhận **681,759 product sessions**, **432,146 cart sessions**, **181,759 purchase sessions**. Product-to-cart theo session là **63.4%**, cart-to-purchase là **42.1%**.

Chẩn đoán: website không thiếu browsing intent; điểm nghẽn là đóng đơn ở cart/checkout. Vì thiếu checkout-step data, nguyên nhân được nêu dưới dạng giả thuyết kiểm chứng bằng A/B test.

### Insight 5 - Inventory là rủi ro vận hành lớn nhất

Inventory có **490,705 units**, trong đó **313,351 units** chưa bán. Sell-through chỉ **36.1%**, average holding days của unsold inventory **737 ngày**, frozen capital theo cost khoảng **$8.98M**.

Chẩn đoán: đây là rủi ro vốn lưu động và vận hành rõ nhất. Holding cost hiện là estimate đến cut-off, không diễn giải là annual recurring cost thật.

---

## 4. E-commerce domain extensions

Đã bổ sung các phân tích đặc thù để tăng điểm tiêu chí E-commerce:

| Phân tích | Kết quả chính | Ý nghĩa ngành |
|---|---|---|
| Journey funnel by source | product-to-cart quanh 63%, cart-to-purchase quanh 42% theo source lớn | tối ưu checkout/cart recovery thay vì chỉ tăng traffic |
| Basket affinity | `Blazers & Jackets + Leggings` có lift 1.50 | có candidate để test bundle/cross-sell |
| Price-band performance | 40 nhóm cần fit/size confidence, 30 nhóm cần cancellation diagnosis | PDP content và checkout friction khác nhau theo price band |
| Inventory ABC-aging | 66 nhóm cần rebalance DC, 37 nhóm cần markdown có guardrail | chuyển inventory insight thành quyết định replenish/markdown |
| Return/cancel proxy | 835 nhóm nghiêng về checkout/payment/inventory cancellation friction | tạo queue điều tra nguyên nhân vận hành thay vì đo return chung |

---

## 5. Action framework dùng trong báo cáo

| Ưu tiên | Hành động | KPI | Mục tiêu |
|---:|---|---|---|
| 1 | Dashboard status leakage + SLA Processing | leakage rate, processing aging | giảm 2-3 điểm % |
| 2 | Lifecycle email cho one-time/at-risk users | 90-day repeat rate | tăng 3-5 điểm % |
| 3 | A/B test checkout, abandoned-cart flow | cart-to-purchase | tăng 3-5 điểm % |
| 4 | ABC aging + markdown có kiểm soát | aged inventory cost, sell-through | giảm aged cost 15-20% |
| 5 | Product mix governance | gross profit mix, category leakage | tăng share Star, giảm Dog |
| 6 | Forecast baseline + feature enrichment | MAPE, bias | MAPE <30% trước khi operationalize |
| 7 | Basket/bundle test | attach rate, AOV uplift | tăng basket value ở pair có lift cao |
| 8 | Price-band PDP optimization | return rate, purchase CVR | giảm return 1-2 điểm % ở nhóm ưu tiên |

---

## 6. Trạng thái scoring

| Thành phần rubric | Trạng thái sau chỉnh sửa |
|---|---|
| Phương pháp phân tích | đủ 4 trụ cột, có RFM/cohort/funnel/category/inventory/forecast |
| Insight có chiều sâu | có diagnosis theo leakage, retention, funnel, inventory |
| So sánh có giá trị | so sánh theo năm, status, category, source, cohort, inventory |
| E-commerce specificity | có journey funnel, basket affinity, price band, ABC inventory, return/cancel proxy |
| Predictive | có forecast baseline và caveat MAPE |
| Prescriptive | action matrix có KPI, owner logic và mục tiêu định lượng |
| Tính bảo vệ khi vấn đáp | có guardrail cho giả định và giới hạn dữ liệu |

**Đánh giá nội bộ sau chỉnh sửa:**  
- Phân tích & Insight: **24-25/25**.  
- Đặc thù E-commerce: **19.5-20/20**, miễn là báo cáo PDF/dashboard dùng các output mới và tài liệu `ecommerce_domain_strategy.md`.
