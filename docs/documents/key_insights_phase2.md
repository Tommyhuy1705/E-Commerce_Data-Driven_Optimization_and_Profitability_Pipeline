# Phase 2 Key Insights: Phân tích & Insight

**Thời gian cập nhật:** 08/05/2026  
**Phạm vi chuẩn:** dữ liệu processed 2019-2023; năm 2024 không dùng để kết luận xu hướng năm vì chưa đủ kỳ.  
**Mục tiêu:** chuyển phát hiện từ mô tả hiện tượng sang chẩn đoán nguyên nhân, dự báo có kiểm soát và hành động đo lường được.

---

## 1. Metric Guardrails

Báo cáo sử dụng một bộ định nghĩa thống nhất để tránh lẫn giữa quy mô đơn hàng và doanh thu thực ghi nhận:

| Metric | Định nghĩa sử dụng trong phân tích | Cách diễn giải |
|---|---|---|
| GMV all-status | Tổng `sale_price` của mọi line item, gồm Complete, Shipped, Processing, Cancelled, Returned | Quy mô nhu cầu/đơn hàng phát sinh |
| Recognized revenue | Chỉ gồm line item `Complete` và `Shipped` | Doanh thu có thể ghi nhận ở mức phân tích hiện tại |
| Gross profit | `sale_price - cost` cho recognized revenue | Lợi nhuận gộp trước chi phí vận hành/marketing |
| Status leakage | GMV thuộc `Cancelled`, `Returned`, `Processing` | Giá trị chưa chuyển hóa thành recognized revenue |
| Return cost/CAC/Holding cost | Chỉ là scenario hoặc proxy khi thiếu dữ liệu chi phí thật | Không dùng để kết luận net profit hoặc ROI thực tế |

**Giới hạn dữ liệu quan trọng:** dataset không có marketing spend, discount, tax, shipping cost, return reason, net profit và carrier-level cost. Vì vậy, báo cáo không kết luận ROAS, CAC thực tế, contribution margin hoặc net margin thực tế.

---

## 2. Executive Diagnosis

ET Club tăng trưởng rất nhanh, nhưng chất lượng tăng trưởng chưa tốt. Từ 2019 đến 2023, GMV all-status tăng từ **$222.8K** lên **$5.121M**, còn recognized revenue tăng từ **$122.6K** lên **$2.819M**. Gross margin giữ gần như phẳng quanh **51.8-52.0%**, cho thấy vấn đề không nằm chủ yếu ở COGS trực tiếp, mà ở khả năng chuyển hóa nhu cầu thành doanh thu hợp lệ, giữ chân khách hàng và quay vòng tồn kho.

Ba điểm nghẽn trọng yếu:

1. **Status leakage lớn và ổn định:** khoảng **45% GMV mỗi năm** chưa chuyển thành recognized revenue do Cancelled, Returned hoặc Processing.
2. **Retention yếu:** **50.5% users không có valid purchase**, và trong nhóm khách đã mua hợp lệ, **76.6% chỉ mua một lần**.
3. **Tồn kho chậm luân chuyển:** **313,351 units** chưa bán, sell-through chỉ **36.1%**, vốn tồn theo cost khoảng **$8.98M**.

Hàm ý chiến lược: trước khi tăng ngân sách acquisition, ET Club nên ưu tiên giảm leakage, kích hoạt repeat purchase và giảm vốn kẹt trong inventory.

---

## 3. Insight 1 - Growth tăng nhanh nhưng 45% GMV chưa chuyển hóa thành revenue

| Năm | GMV all-status | Recognized revenue | Gross profit | Gross margin | Status leakage |
|---|---:|---:|---:|---:|---:|
| 2019 | $222.8K | $122.6K | $63.5K | 51.8% | 45.0% |
| 2020 | $749.8K | $412.2K | $214.2K | 52.0% | 45.0% |
| 2021 | $1.450M | $798.7K | $414.3K | 51.9% | 44.9% |
| 2022 | $2.486M | $1.378M | $714.5K | 51.9% | 44.6% |
| 2023 | $5.121M | $2.819M | $1.464M | 51.9% | 45.0% |

**Chẩn đoán:** ET Club không thiếu demand. Vấn đề là tỷ lệ chuyển hóa từ GMV phát sinh sang revenue hợp lệ gần như không cải thiện khi scale. Năm 2023, phần leakage gồm:

- Cancelled value: **$754.3K**
- Returned value: **$531.0K**
- Processing backlog value: **$1.017M**
- Tổng status leakage: **$2.302M**

Processing chiếm gần **19.85% GMV 2023**, nên đây là nhóm cần tách rõ: có thể là backlog thật, hoặc trạng thái chưa được cập nhật ở thời điểm cut-off. Dù nguyên nhân là gì, nó làm báo cáo quản trị bị mờ giữa nhu cầu, doanh thu ghi nhận và pipeline chưa hoàn tất.

**Hành động đề xuất:**

| Hành động | KPI đo lường | Mục tiêu thực tế |
|---|---|---|
| Dashboard leakage theo tháng, status, category, DC | Leakage rate, value by status | Giảm 2-3 điểm % leakage trong 2 quý |
| SLA xử lý Processing backlog | Processing aging, backlog value | Tách đơn chờ xử lý thật với đơn thiếu cập nhật trạng thái |
| Review nguyên nhân Cancelled/Returned ở top category | Cancel rate, return rate, cancel+return value | Ưu tiên category có leakage value lớn, không chỉ leakage rate cao |

---

## 4. Insight 2 - Customer base lớn nhưng repeat engine yếu

| Metric | Giá trị hiện tại | Ý nghĩa |
|---|---:|---|
| Total users | 100,000 | Quy mô user đủ lớn để phân khúc |
| No valid purchase users | 50.5% | Một nửa user chưa tạo recognized revenue |
| One-time buyers trong valid customers | 76.6% | Repeat purchase là điểm nghẽn chính |
| 2019 cohort mua lại năm 2023 | 9.1% | Retention dài hạn thấp |
| 2022 cohort mua lại năm 2023 | 19.0% | Cohort mới tốt hơn nhưng vẫn thấp |

**Chẩn đoán:** tăng trưởng doanh thu đang phụ thuộc nhiều vào mở rộng volume hơn là giữ vòng đời khách hàng. Cohort 2019 giảm từ 100% ở năm mua đầu xuống **11.62%** ở 2020 và **9.10%** ở 2023. Điều này phù hợp với RFM: nhóm `No Purchase / No Valid Purchase` chiếm **50.5%**, `At Risk` chiếm **18.8%**, trong khi `Champions` chỉ **6.8%**.

**LTV/CAC scenario:** nếu giả định CAC trung bình **$40**, gross-profit LTV của one-time buyers chỉ khoảng **$44.71**, LTV:CAC **1.1:1**, thấp hơn benchmark khỏe mạnh **3:1**. Đây là cảnh báo scenario, không phải kết luận CAC thật vì dataset không có marketing spend.

**Hành động đề xuất:**

| Phân khúc | Vấn đề | Hành động | KPI |
|---|---|---|---|
| No valid purchase | Chưa chuyển đổi thành revenue | welcome offer có điều kiện, onsite personalization | first valid purchase rate |
| One-time buyers | Mua xong không quay lại | post-purchase email/SMS, bundle theo category đã mua | 60/90-day repeat rate |
| At Risk | Có giá trị nhưng recency cao | win-back theo AOV/category | reactivation rate, revenue recovered |
| Champions/Loyal | Nhóm nhỏ nhưng có giá trị | early access, loyalty tier, referral | repeat orders/customer, referral conversion |

Mục tiêu nên đặt là tăng repeat rate thêm **3-5 điểm %** trước khi mở rộng acquisition mạnh hơn.

---

## 5. Insight 3 - Product mix có doanh thu tốt nhưng leakage và margin khác biệt mạnh theo category

| Category | Recognized revenue | Gross margin | Return rate | Status leakage | Quadrant |
|---|---:|---:|---:|---:|---|
| Outerwear & Coats | $673.8K | 55.5% | 10.1% | $528.5K | Star |
| Jeans | $648.1K | 46.5% | 9.6% | $518.1K | Cash Cow |
| Sweaters | $432.8K | 51.9% | 10.2% | $347.8K | Star |
| Suits & Sport Coats | $333.9K | 59.8% | 10.3% | $275.4K | Star |
| Fashion Hoodies & Sweatshirts | $330.3K | 48.0% | 10.1% | $270.3K | Cash Cow |
| Clothing Sets | $8.2K | 37.3% | 9.1% | $8.1K | Dog |

**Chẩn đoán:** không nên chỉ nhìn doanh thu. `Outerwear & Coats` và `Suits & Sport Coats` vừa có quy mô vừa có margin tốt, nên là nhóm để scale có kiểm soát. `Jeans` là nhóm doanh thu lớn nhưng margin thấp hơn, đồng thời leakage value cao, nên cần tối ưu giá vốn/giá bán và giảm hủy/hoàn hơn là chỉ tăng volume.

Return rate giữa các category dao động quanh **9-11%**, không đủ để quy toàn bộ vấn đề cho một category duy nhất. Điểm cần ưu tiên là **leakage value tuyệt đối** và **gross profit bị khóa**, không chỉ tỷ lệ return.

**Hành động đề xuất:**

| Nhóm category | Hướng xử lý | KPI |
|---|---|---|
| Star | tăng visibility, bundle, ưu tiên tồn kho nhanh quay vòng | revenue share, gross profit, stockout rate |
| Cash Cow | tối ưu supplier cost/price, giảm leakage value | margin uplift, cancel+return value |
| Dog | giảm mua mới, markdown có kiểm soát, kiểm tra tồn kho lâu ngày | sell-through, aged inventory cost |

Mục tiêu prescriptive: tăng margin Jeans từ **46.5%** lên **48-50%** hoặc giảm leakage value Jeans **10-15%** sẽ có tác động lớn hơn nhiều so với tối ưu các category rất nhỏ.

---

## 6. Insight 4 - Funnel không thiếu traffic, điểm nghẽn là cart-to-purchase

| Stage | Events | Sessions | Conversion từ stage trước |
|---|---:|---:|---:|
| Product | 845,607 | 681,759 | 100.0% |
| Cart | 595,994 | 432,146 | 63.4% theo session |
| Purchase | 181,759 | 181,759 | 42.1% theo session |

**Chẩn đoán:** product-to-cart tương đối khỏe, nhưng `cart -> purchase` là đoạn mất nhiều intent nhất. Do dataset không có checkout step, payment failure, shipping fee hoặc promotion exposure, nguyên nhân gốc rễ chỉ có thể xác định ở mức giả thuyết: phí/ETA hiển thị muộn, friction trong checkout, thiếu ưu đãi ở giỏ hàng, hoặc hết hàng/không đồng bộ inventory.

Traffic source performance cho thấy:

| Source | Purchase events | Global unique users | Purchase events/user |
|---|---:|---:|---:|
| Email | 81,706 | 52,255 | 1.56 |
| Adwords | 54,542 | 39,641 | 1.38 |
| Facebook | 18,305 | 16,330 | 1.12 |
| YouTube | 18,082 | 16,138 | 1.12 |
| Organic | 9,124 | 8,589 | 1.06 |

Email có purchase intensity cao nhất, nhưng vì không có spend/cost, không kết luận ROI. Insight đúng là: **Email nên được ưu tiên cho retention và cart recovery test**, vì nhóm này tạo nhiều purchase events trên mỗi user hơn các source khác.

**Hành động đề xuất:**

| Vấn đề | Experiment | KPI |
|---|---|---|
| Cart bỏ dở | abandoned-cart email trong 1h/24h/72h | cart recovery rate |
| Checkout friction | A/B test guest checkout, shipping ETA/fee hiển thị sớm | cart-to-purchase +3-5 điểm % |
| Thiếu confidence trước mua | size guide, review, fit note theo category | return rate, purchase conversion |

---

## 7. Insight 5 - Inventory là rủi ro vận hành lớn nhất

| Metric | Giá trị |
|---|---:|
| Total inventory units | 490,705 |
| Sold units | 177,354 |
| Unsold units | 313,351 |
| Sell-through rate | 36.1% |
| Avg holding days của unsold inventory | 737 ngày |
| Max holding days | 1,476 ngày |
| Frozen capital theo cost | $8.98M |
| Holding cost estimate to cutoff | $4.47M |

**Chẩn đoán:** tồn kho chưa bán chiếm **63.9% units** và có tuổi kho bình quân khoảng **2 năm**. Đây là rủi ro vận hành và vốn lưu động lớn hơn cả return cost scenario. Holding cost ở đây là **ước tính đến cut-off**, không gọi là chi phí thường niên thật.

Sell-through thấp trên diện rộng gợi ý vấn đề không chỉ là một vài category yếu, mà là chính sách mua hàng/phân bổ tồn kho chưa theo kịp demand thực tế. Tuy vậy, xử lý vẫn cần ưu tiên theo category/brand/DC vì markdown toàn bộ sẽ làm mất margin không cần thiết.

**Hành động đề xuất:**

| Hành động | KPI | Mục tiêu |
|---|---|---|
| ABC inventory theo revenue, margin, holding days | aged inventory cost by category/DC | giảm aged cost 15-20% |
| Markdown có kiểm soát cho nhóm Dog/slow-moving | markdown recovery, gross profit after markdown | thu hồi vốn thay vì giữ hàng quá lâu |
| Replenishment rule cho Star/Cash Cow | sell-through, stockout, weeks of supply | tăng sell-through từ 36.1% lên 42-45% trước |
| Forecast baseline theo category | forecast error, bias | dùng như cảnh báo kế hoạch, không tự động mua hàng |

---

## 8. Predictive Outlook & Model Caveat

Phase 3 đã tạo forecast 12 tháng cho 3 category lớn nhất, nhưng output mới cho thấy model hiện là `seasonal_naive_fallback`, MAPE theo category khoảng **47.2-55.5%**, top-category MAPE summary **50.9%**. Vì vậy:

- Có thể dùng forecast như **baseline scenario** để thảo luận xu hướng và inventory policy.
- Không nên dùng forecast như quyết định mua hàng tự động.
- Cần nâng cấp bằng external calendar, promotion, seasonality, stockout và price/discount features nếu muốn dùng cho demand planning thật.

---

## 9. Prioritized Action Matrix

| Ưu tiên | Insight | Hành động | KPI chính | Kỳ vọng |
|---:|---|---|---|---|
| 1 | 45% GMV bị leakage | dashboard status leakage + SLA xử lý Processing | leakage rate, processing aging | giảm 2-3 điểm % leakage |
| 2 | Repeat yếu | lifecycle email cho one-time/at-risk users | 90-day repeat rate | tăng 3-5 điểm % |
| 3 | Cart-to-purchase nghẽn | A/B test checkout và abandoned cart | cart-to-purchase | tăng 3-5 điểm % |
| 4 | Inventory kẹt vốn | ABC aging + markdown có kiểm soát | aged inventory cost, sell-through | giảm aged cost 15-20% |
| 5 | Product mix chưa tối ưu | scale Star, fix Cash Cow, reduce Dog | gross profit mix, category leakage | tăng gross profit mix |
| 6 | Forecast còn yếu | dùng baseline + bổ sung feature | MAPE, forecast bias | đưa MAPE xuống <30% trước khi operationalize |

---

## 10. E-commerce Domain Add-ons

Để tăng chiều sâu đặc thù e-commerce, Phase 2 đã bổ sung các bảng phân tích chuyên ngành:

| Output | Insight ngành | Cách dùng trong báo cáo/dashboard |
|---|---|---|
| `journey_funnel_by_source.csv` | source-level journey từ home/department/product/cart/purchase/cancel | xác định source nào mạnh ở purchase reach và cart-to-purchase |
| `basket_affinity_analysis.csv` | cặp category có support, confidence và lift | đề xuất bundle/cross-sell test thay vì chỉ tối ưu category đơn lẻ |
| `price_band_performance.csv` | margin, return, cancel, leakage theo price band | phân biệt vấn đề pricing, PDP confidence và cancellation friction |
| `inventory_abc_aging_by_category_dc.csv` | ABC class + aged cost + sell-through theo category/DC | quyết định replenish, rebalance, markdown hoặc stop-buy |
| `return_cancel_root_cause_proxy.csv` | proxy root-cause theo category-brand-price-fulfillment bucket | ưu tiên điều tra checkout/payment/inventory sync, backlog SLA, size/fit |

Một số kết quả mới:

- `Blazers & Jackets + Leggings` có lift **1.50** và đủ volume để test bundle/cross-sell.
- Price-band analysis tạo **40 nhóm** cần cải thiện fit/size confidence và **30 nhóm** cần chẩn đoán cancellation friction.
- Inventory ABC-aging tạo **66 nhóm category-DC** cần rebalance allocation và **37 nhóm** cần markdown có guardrail margin.
- Return/cancel proxy cho thấy **835 nhóm** nghiêng về checkout/payment/inventory cancellation friction và **186 nhóm** liên quan backlog/status-update SLA.

Các bổ sung này giúp bài phân tích chuyển từ 4 trụ cột tổng quát sang một e-commerce operating playbook đầy đủ: acquisition -> activation -> conversion -> merchandising -> fulfillment -> retention -> inventory.

---

## 11. What We Can Defend in Front of Judges

**Kết luận có bằng chứng mạnh:**

- Recognized revenue 2019-2023 tăng mạnh nhưng status leakage giữ quanh 45%.
- Gross margin ổn định quanh 51.9%, nên COGS trực tiếp không phải nguyên nhân chính của “margin puzzle”.
- Repeat behavior yếu: 50.5% no valid purchase, 76.6% valid customers chỉ mua một lần.
- Funnel nghẽn ở cart-to-purchase.
- Inventory sell-through thấp và vốn tồn kho lớn là rủi ro vận hành trọng yếu.

**Kết luận chỉ nên trình bày dạng giả thuyết/scenario:**

- CAC thực tế, ROI kênh marketing, net margin, contribution margin.
- Nguyên nhân return cụ thể như size/fit/quality.
- Forecast dùng cho demand planning chi tiết.

**Thông điệp chiến lược:** ET Club nên chuyển trọng tâm từ “scale traffic và volume” sang “quality of growth”: giảm leakage, tăng repeat purchase, tối ưu checkout và giải phóng inventory chậm luân chuyển.

---

**Output liên quan:**  
`annual_revenue_analysis.csv`, `status_leakage_analysis.csv`, `rfm_segment_analysis.csv`, `cohort_retention_analysis.csv`, `ltv_cac_analysis.csv`, `category_performance_analysis.csv`, `funnel_analysis.csv`, `journey_funnel_by_source.csv`, `traffic_source_performance.csv`, `basket_affinity_analysis.csv`, `price_band_performance.csv`, `inventory_turnover_analysis.csv`, `holding_cost_analysis.csv`, `inventory_abc_aging_by_category_dc.csv`, `return_cancel_root_cause_proxy.csv`, `phase3_model_summary.csv`.
