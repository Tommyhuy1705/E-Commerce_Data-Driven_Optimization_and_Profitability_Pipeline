# Phase 3 Modeling Summary

**Thời gian cập nhật:** 08/05/2026  
**Trạng thái:** hoàn thành clustering và forecast baseline; kết quả forecast cần dùng thận trọng.

---

## 1. Output đã tạo

| File | Mục đích |
|---|---|
| `dim_users_with_clusters.csv/parquet` | Gắn cluster label vào user dimension |
| `clustering_analysis.csv` | Bảng user-level phục vụ phân tích cluster |
| `cluster_profile_summary.csv` | Profile trung bình từng cluster |
| `demand_forecast_12m.csv` | Forecast baseline 12 tháng cho 3 category lớn |
| `demand_forecast_evaluation.csv` | Backtest MAPE theo category |
| `phase3_model_summary.csv` | Tóm tắt trạng thái mô hình |

---

## 2. Customer clustering

Mô hình clustering hiện tạo **7 nhóm** có ý nghĩa kinh doanh:

| Cluster label | Profile chính | Hướng sử dụng |
|---|---|---|
| No Valid Purchase | Chưa có purchase hợp lệ | chuyển đổi first purchase |
| Occasional Spenders | mua ít, monetary thấp | nurture và cross-sell nhẹ |
| At-Risk High Value | monetary/AOV cao nhưng recency lớn | win-back ưu tiên |
| Low-Value Browsers | giá trị thấp, recency cao | hạn chế ưu đãi sâu |
| Selective Buyers | recent, frequency tốt vừa phải | gợi ý category phù hợp |
| Recent But Inactive | đã mua gần đây nhưng chưa lặp lại đủ | post-purchase journey |
| High-Value Loyal | frequency/category diversity cao | loyalty, referral, early access |

Cluster labels có thể dùng trong Power BI vì các nhóm khác nhau rõ về `Recency`, `Frequency`, `Monetary`, `aov`, `category_diversity` và `return_rate_pct`.

---

## 3. Forecast baseline

Forecast hiện tại dùng `seasonal_naive_fallback`, không phải mô hình Prophet production-grade. Backtest hiện tại:

| Category | MAPE |
|---|---:|
| Outerwear & Coats | 55.51% |
| Jeans | 47.21% |
| Sweaters | 49.97% |

`phase3_model_summary.csv` ghi nhận top-category MAPE khoảng **50.9%** và khuyến nghị `Baseline only`.

**Quyết định sử dụng:** forecast được dùng để minh họa kịch bản xu hướng và cảnh báo inventory, không dùng làm quyết định mua hàng tự động. Muốn operationalize forecast cần bổ sung seasonality, promotion, price/discount, stockout, campaign calendar và external demand signals.

---

## 4. Insight đưa vào báo cáo

- Clustering giúp biến RFM từ mô tả thành phân khúc hành động: win-back, retention, loyalty và first-purchase conversion.
- Forecast hiện chưa đủ chính xác để là lợi thế chính của bài thi, nhưng việc ghi rõ MAPE và giới hạn sử dụng giúp tăng độ tin cậy phân tích.
- Phase 3 nên đóng vai trò hỗ trợ cho insight Phase 2, không thay thế các bằng chứng trực tiếp từ transaction, funnel và inventory.
