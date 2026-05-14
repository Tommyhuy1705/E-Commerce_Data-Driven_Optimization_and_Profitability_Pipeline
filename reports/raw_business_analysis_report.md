# Báo cáo phân tích kinh doanh ET Club từ raw dataset

**Lưu ý sử dụng:** đây là báo cáo exploratory trên raw full-history, có bao gồm dữ liệu 2024 chưa đủ năm và một số định nghĩa phục vụ kiểm tra nhanh. Narrative chính cho bài nộp nên dùng bộ processed 2019-2023 trong `docs/documents/key_insights_phase2.md`, nơi đã tách rõ `GMV all-status`, `recognized revenue`, `gross profit` và `status leakage`.

## 1. Tóm tắt điều hành

ET Club đang có quy mô giao dịch tốt nhưng hiệu quả kinh doanh bị rò rỉ ở ba điểm chính: tỷ lệ khách mua lại thấp, rơi rụng lớn giữa giỏ hàng và mua hàng, và tồn kho chưa bán chiếm vốn lớn. Với định nghĩa doanh thu ghi nhận là các item ở trạng thái `Complete` hoặc `Shipped`, doanh nghiệp đạt **$5.97M doanh thu**, **$3.10M lợi nhuận gộp**, biên gộp **51.9%**. Tuy nhiên, doanh thu bị mất do `Cancelled` và `Returned` lên tới **$2.70M**, tương đương **24.9% tổng GMV**.

Về khách hàng, chỉ **72.1%** trong **100,000** user đăng ký có phát sinh mua hàng hợp lệ; trong nhóm đã mua, tỷ lệ mua lặp lại chỉ **33.7%**. Đây là tín hiệu rõ rằng tăng trưởng hiện phụ thuộc nhiều vào acquisition hơn là retention.

Funnel website cho thấy **681,759 sessions** và purchase-session conversion chỉ **26.7%**; cart-to-purchase đạt **42.1%**. Trong vận hành, kho có **490,705 units**, nhưng **313,351 units chưa bán**, giá vốn tồn **$8.98M**; trong đó hàng tồn trên 180 ngày trị giá **$7.80M**. Nếu giữ quỹ đạo hiện tại, dự báo 12 tháng sau mốc **2023-12** đạt khoảng **$4.21M doanh thu** và **$2.19M lợi nhuận gộp**.

## 2. Nền dữ liệu và kiểm tra chất lượng

| table       | rows      | cols | memory_mb | duplicate_pk | null_cells |
| ----------- | --------- | ---- | --------- | ------------ | ---------- |
| users       | 100,000   | 15   | 20.8      | 0            | 3351       |
| products    | 29,120    | 9    | 4.9       | 0            | 26         |
| orders      | 125,226   | 9    | 9.7       | 0            | 244248     |
| order_items | 181,759   | 11   | 16.7      | 0            | 354202     |
| inventory   | 490,705   | 12   | 94.2      | 0            | 318186     |
| dcs         | 10        | 4    | 0.0       | 0            | 0          |
| events      | 2,431,963 | 8    | 276.2     | 0            | 1157172    |

- Giai đoạn order: **2019-01-06 đến 2024-01-21**; giai đoạn event: **2019-01-02 đến 2024-01-21**.
- Không phát hiện orphan nghiêm trọng ở khóa `order_items -> users/products/orders`; số item giá bán dưới $1 là **10**, tác động doanh thu không đáng kể.
- **46.3% events không có user_id**, cần hiểu là traffic ẩn danh/khách chưa đăng nhập; vì vậy funnel session nên dùng `session_id`, còn phân tích LTV dùng `users.traffic_source`.

## 3. Doanh thu, lợi nhuận và rò rỉ trạng thái đơn hàng

| status     | items  | orders | gmv    |
| ---------- | ------ | ------ | ------ |
| Shipped    | 54,440 | 37,577 | $3.26M |
| Complete   | 45,609 | 31,354 | $2.72M |
| Processing | 36,388 | 25,156 | $2.16M |
| Cancelled  | 27,090 | 18,609 | $1.60M |
| Returned   | 18,232 | 12,530 | $1.10M |

Nhìn ở cấp item, rò rỉ doanh thu đến từ hai nhóm: đơn hủy trước khi fulfilment và đơn hoàn sau giao hàng. Nhóm này không chỉ làm mất doanh thu mà còn kéo theo chi phí vận hành, xử lý hoàn kho và chi phí marketing đã bỏ ra để tạo đơn. Do đó, chỉ số nên theo dõi hàng tuần là `leakage_rate = (GMV Cancelled + GMV Returned) / Total GMV`, tách theo category, brand, source và thời gian giao hàng.

## 4. Khách hàng: chân dung, loyalty và giá trị

**Metrics chính**

- Registered users: **100,000**
- Buyers hợp lệ: **72,123**; buyer penetration **72.1%**
- Repeat buyers: **24,318**; repeat rate **33.7%**
- AOV ghi nhận: **$87**; giá/item bình quân **$60**
- Median recency của buyers: **280 ngày**

**Nguồn acquisition theo doanh thu/LTV**

| traffic_source | users | buyers | revenue | profit  | buyer_rate | ltv_per_registered_user | arppu |
| -------------- | ----- | ------ | ------- | ------- | ---------- | ----------------------- | ----- |
| Search         | 70075 | 50508  | $4.20M  | $2.18M  | 72.1%      | $59.92                  | $83   |
| Organic        | 15110 | 10883  | $888.7K | $461.6K | 72.0%      | $58.82                  | $82   |
| Facebook       | 5816  | 4218   | $352.9K | $183.8K | 72.5%      | $60.68                  | $84   |
| Email          | 4947  | 3561   | $290.8K | $150.3K | 72.0%      | $58.79                  | $82   |
| Display        | 4052  | 2953   | $241.0K | $125.3K | 72.9%      | $59.48                  | $82   |

**RFM thô theo hành vi mua**

| segment             | customers | revenue | avg_orders | avg_recency |
| ------------------- | --------- | ------- | ---------- | ----------- |
| One-time low value  | 39585     | $2.27M  | 1.02       | 561         |
| Repeat at risk      | 11908     | $1.55M  | 2.33       | 490         |
| Champions           | 3523      | $894.6K | 2.74       | 40          |
| Loyal/active repeat | 8285      | $776.8K | 2.40       | 86          |
| New one-time        | 8822      | $486.6K | 1.00       | 42          |

Chẩn đoán: nguồn có buyer rate và LTV khác nhau nhưng loyalty chung còn mỏng; phần lớn người mua chỉ mua một lần. ET Club nên chuyển từ tối ưu chỉ theo số user/traffic sang tối ưu theo `LTV per registered user`, `repeat rate 90 ngày` và `gross profit per buyer`.

## 5. Sản phẩm và cơ cấu lợi nhuận

**Top category theo doanh thu ghi nhận**

| category                      | department | revenue | profit  | margin | return_rate | cancel_rate | items |
| ----------------------------- | ---------- | ------- | ------- | ------ | ----------- | ----------- | ----- |
| Outerwear & Coats             | Men        | $461.7K | $257.8K | 55.8%  | 15.6%       | 14.8%       | 3,081 |
| Jeans                         | Men        | $439.5K | $205.5K | 46.8%  | 15.0%       | 15.3%       | 4,277 |
| Suits & Sport Coats           | Men        | $363.6K | $217.5K | 59.8%  | 16.3%       | 14.7%       | 2,844 |
| Sweaters                      | Men        | $296.0K | $148.0K | 50.0%  | 15.4%       | 14.8%       | 3,813 |
| Outerwear & Coats             | Women      | $270.6K | $148.4K | 54.8%  | 15.6%       | 14.8%       | 1,898 |
| Dresses                       | Women      | $258.5K | $142.0K | 54.9%  | 15.3%       | 14.7%       | 3,029 |
| Jeans                         | Women      | $255.1K | $117.3K | 46.0%  | 15.0%       | 15.3%       | 2,720 |
| Intimates                     | Women      | $254.7K | $119.3K | 46.8%  | 15.5%       | 14.9%       | 7,420 |
| Pants                         | Men        | $240.9K | $130.3K | 54.1%  | 16.0%       | 14.6%       | 4,049 |
| Fashion Hoodies & Sweatshirts | Men        | $218.2K | $98.0K  | 44.9%  | 15.7%       | 14.7%       | 3,731 |

**Top brand theo doanh thu ghi nhận**

| brand             | category          | revenue | profit | margin | items |
| ----------------- | ----------------- | ------- | ------ | ------ | ----- |
| 7 For All Mankind | Jeans             | $87.1K  | $40.6K | 46.6%  | 547   |
| Diesel            | Jeans             | $65.1K  | $30.5K | 46.9%  | 334   |
| True Religion     | Jeans             | $65.0K  | $30.2K | 46.4%  | 275   |
| Carhartt          | Outerwear & Coats | $57.0K  | $31.7K | 55.6%  | 455   |
| Joe's Jeans       | Jeans             | $48.3K  | $22.3K | 46.2%  | 302   |
| The North Face    | Outerwear & Coats | $45.9K  | $25.5K | 55.4%  | 99    |
| Ray-Ban           | Accessories       | $44.7K  | $26.9K | 60.3%  | 372   |
| Arc'teryx         | Outerwear & Coats | $35.5K  | $19.4K | 54.7%  | 98    |
| Oakley            | Accessories       | $35.0K  | $20.8K | 59.6%  | 251   |
| Speedo            | Swim              | $30.9K  | $15.5K | 50.4%  | 610   |

Category top doanh thu không đồng nghĩa là top hiệu quả. Các category có revenue cao nhưng return/cancel rate cao cần được xử lý bằng mô tả size/fit tốt hơn, kiểm tra chất lượng ảnh, chính sách đổi trả theo nguyên nhân, và kiểm soát tồn kho. Với nhóm biên gộp cao, có thể tăng ngân sách paid search/remarketing nếu funnel sau giỏ hàng được cải thiện.

## 6. Marketing và chuyển đổi website

**Funnel theo traffic source**

| traffic_source | sessions | product_sessions | cart_sessions | purchase_sessions | purchase_rate | cart_to_purchase | cancel_per_cart | bounce_rate |
| -------------- | -------- | ---------------- | ------------- | ----------------- | ------------- | ---------------- | --------------- | ----------- |
| Email          | 306,313  | 306,313          | 193,988       | 81,706            | 26.7%         | 42.1%            | 29.0%           | 18.3%       |
| Adwords        | 205,010  | 205,010          | 130,001       | 54,542            | 26.6%         | 42.0%            | 29.1%           | 18.3%       |
| YouTube        | 68,202   | 68,202           | 43,182        | 18,082            | 26.5%         | 41.9%            | 29.3%           | 18.2%       |
| Facebook       | 67,933   | 67,933           | 43,372        | 18,305            | 26.9%         | 42.2%            | 29.2%           | 18.1%       |
| Organic        | 34,301   | 34,301           | 21,603        | 9,124             | 26.6%         | 42.2%            | 29.1%           | 18.4%       |

Tắc nghẽn lớn nhất nằm ở đoạn `cart -> purchase`: người dùng vào giỏ nhiều hơn đáng kể so với số hoàn tất mua. Conversion giữa các source khá đồng đều, nên `traffic_source` hiện chưa đủ granular để chẩn đoán campaign nào tốt/xấu; cần bổ sung campaign, medium, creative hoặc landing page. Vì event không có cost marketing, khuyến nghị không dùng ROAS tuyệt đối; thay vào đó dùng bộ chỉ số thay thế: `purchase session rate`, `cart-to-purchase`, `cancel/cart`, `revenue per registered user` theo source.

## 7. Vận hành, tồn kho và fulfilment

**Tồn kho theo category có giá vốn tồn cao nhất**

| product_category              | inventory_units | unsold_units | unsold_cost | sell_through | aged_180_rate | avg_age_days |
| ----------------------------- | --------------- | ------------ | ----------- | ------------ | ------------- | ------------ |
| Jeans                         | 34,255          | 21,854       | $1.15M      | 36.2%        | 86.4%         | 481          |
| Outerwear & Coats             | 24,179          | 15,443       | $996.4K     | 36.1%        | 87.0%         | 484          |
| Sweaters                      | 30,479          | 19,498       | $701.1K     | 36.0%        | 86.9%         | 484          |
| Fashion Hoodies & Sweatshirts | 32,155          | 20,556       | $579.9K     | 36.1%        | 87.0%         | 486          |
| Swim                          | 30,870          | 19,724       | $570.6K     | 36.1%        | 86.9%         | 482          |
| Tops & Tees                   | 32,285          | 20,656       | $476.0K     | 36.0%        | 86.8%         | 482          |
| Suits & Sport Coats           | 14,090          | 9,020        | $464.6K     | 36.0%        | 86.9%         | 483          |
| Sleep & Lounge                | 29,648          | 18,922       | $450.2K     | 36.2%        | 86.8%         | 485          |
| Shorts                        | 29,697          | 18,911       | $438.9K     | 36.3%        | 87.1%         | 477          |
| Intimates                     | 36,353          | 23,233       | $420.2K     | 36.1%        | 86.7%         | 479          |

**Lệch pha tồn kho - nhu cầu theo distribution center**

| dc_name                                     | unsold_cost | revenue | stock_share | revenue_share | stock_minus_demand_share | sell_through |
| ------------------------------------------- | ----------- | ------- | ----------- | ------------- | ------------------------ | ------------ |
| Charleston SC                               | $566.3K     | $364.2K | 6.3%        | 6.1%          | 0.2%                     | 36.2%        |
| Savannah GA                                 | $678.9K     | $440.6K | 7.6%        | 7.4%          | 0.2%                     | 36.0%        |
| Port Authority of New York/New Jersey NY/NJ | $778.2K     | $507.5K | 8.7%        | 8.5%          | 0.2%                     | 36.1%        |
| Philadelphia PA                             | $911.1K     | $596.8K | 10.1%       | 10.0%         | 0.1%                     | 36.1%        |
| Los Angeles CA                              | $790.7K     | $517.4K | 8.8%        | 8.7%          | 0.1%                     | 36.1%        |
| Mobile AL                                   | $1.07M      | $703.6K | 11.9%       | 11.8%         | 0.1%                     | 36.1%        |
| New Orleans LA                              | $668.8K     | $446.7K | 7.4%        | 7.5%          | -0.0%                    | 36.1%        |
| Memphis TN                                  | $1.16M      | $778.5K | 12.9%       | 13.0%         | -0.1%                    | 36.1%        |
| Chicago IL                                  | $1.09M      | $741.1K | 12.1%       | 12.4%         | -0.3%                    | 36.2%        |
| Houston TX                                  | $1.27M      | $875.6K | 14.1%       | 14.7%         | -0.5%                    | 36.2%        |

**Return rate theo tốc độ fulfilment**

| fulfillment_bin | items  | returned | avg_fulfillment_days | return_rate |
| --------------- | ------ | -------- | -------------------- | ----------- |
| <=3d            | 29,539 | 8,456    | 1.2                  | 28.6%       |
| 3-5d            | 20,091 | 5,754    | 4.0                  | 28.6%       |
| 5-7d            | 11,266 | 3,193    | 5.8                  | 28.3%       |
| 7-10d           | 1,390  | 381      | 7.4                  | 27.4%       |

Fulfilment bình quân: ship sau **0.5 ngày**, giao sau ship **2.5 ngày**, end-to-end **3.0 ngày**. Return rate giữa các bin tốc độ giao hàng khá gần nhau, nên dữ liệu hiện không ủng hộ kết luận "giao chậm là nguyên nhân chính của hoàn trả"; nguyên nhân có khả năng nằm ở kỳ vọng sản phẩm, size/fit hoặc chính sách đổi trả. DC nhìn chung không lệch quá mạnh về stock share so với revenue share; điểm nghẽn vốn lưu động rõ nhất là tồn kho chưa bán và hàng trên 180 ngày theo category.

## 8. Dự báo xu hướng

Dự báo dưới đây dùng seasonal naive trên 12 tháng gần nhất. Do doanh thu 12 tháng gần nhất tăng **104.4%** so với 12 tháng trước, mô hình baseline chỉ dùng mức tăng **50.0%** để tránh ngoại suy quá mức. Đây là baseline vận hành, không phải mô hình demand planning cuối cùng.

| month   | forecast_revenue | forecast_profit |
| ------- | ---------------- | --------------- |
| 2024-01 | $234.6K          | $121.8K         |
| 2024-02 | $234.2K          | $121.6K         |
| 2024-03 | $272.3K          | $141.4K         |
| 2024-04 | $260.8K          | $135.4K         |
| 2024-05 | $284.0K          | $147.5K         |
| 2024-06 | $309.4K          | $160.6K         |
| 2024-07 | $342.1K          | $177.6K         |
| 2024-08 | $366.8K          | $190.5K         |
| 2024-09 | $398.3K          | $206.8K         |
| 2024-10 | $445.9K          | $231.5K         |

## 9. Đề xuất hành động ưu tiên

1. **Giảm rò rỉ GMV trước khi đẩy thêm acquisition.** Lập dashboard `Cancelled + Returned GMV` theo category/brand/source/fulfillment bin; ưu tiên 5 category có doanh thu lớn và return/cancel rate cao. Mục tiêu 90 ngày: giảm leakage rate 2-3 điểm phần trăm.
2. **Tối ưu checkout thay vì chỉ tăng traffic.** A/B test phí vận chuyển/ETA hiển thị sớm, guest checkout, phương thức thanh toán, trust badge và reminder sau cart. KPI: cart-to-purchase, cancel/cart, checkout completion.
3. **Xây retention playbook cho người mua lần đầu.** Kích hoạt chuỗi email/push trong 7-30 ngày sau đơn đầu tiên, bundle theo category đã mua, voucher có điều kiện margin. KPI: repeat rate 90 ngày, second-order conversion, gross profit per buyer.
4. **Phân bổ lại ngân sách marketing theo LTV.** Nguồn có traffic lớn nhưng buyer rate/LTV thấp chỉ nên giữ ngân sách prospecting có kiểm soát; nguồn có LTV và buyer rate cao nên ưu tiên remarketing và lookalike. KPI: LTV per registered user và profit per acquired buyer.
5. **Giải phóng tồn kho già.** Với hàng >180 ngày, dùng markdown có kiểm soát theo margin, bundle, liquidation hoặc chuyển DC. KPI: aged inventory cost, sell-through, holding days.
6. **Demand planning theo DC-category.** So sánh stock share với revenue share hàng tuần; DC có stock share cao hơn demand share cần giảm replenishment/transfer, DC thiếu hàng ở category bán tốt cần tăng safety stock. KPI: stock-demand imbalance, lost sales proxy, inventory days of supply.
7. **Liên kết fulfilment với returns.** Theo dõi return rate theo fulfilment_days và carrier/DC; nếu bin giao chậm có return cao hơn, đặt SLA vận hành và cảnh báo đơn chậm.

## 10. Metrics nên đưa vào dashboard ban điều hành

- Revenue: GMV, recognized revenue, gross profit, gross margin, AOV, ASP, YoY/MoM growth.
- Leakage: cancelled GMV, returned GMV, leakage rate, return rate, cancel rate.
- Customer: buyer penetration, repeat rate, one-time buyer rate, RFM segment revenue, LTV per registered user, ARPPU.
- Marketing: sessions, product rate, cart rate, purchase session rate, cart-to-purchase, cancel/cart, bounce rate theo source.
- Product: revenue/profit/margin by category-brand, return/cancel rate by category, price-band performance.
- Operations: unsold cost, aged 180/365 inventory, sell-through, avg holding days, stock share vs revenue share, ship/delivery/fulfillment days.
