# Phase 3: Advanced Modeling

**Thời gian:** 10-11/05/2026  
**Trạng thái:** hoàn thành clustering; forecast hiện là baseline và có caveat rõ.  
**Vai trò trong bài thi:** hỗ trợ tiêu chí predictive/diagnostic, không thay thế các insight trực tiếp từ transaction, funnel và inventory.

---

## 1. Customer clustering

### Feature set

Clustering dùng các biến hành vi có ý nghĩa kinh doanh:

- `Recency`
- `Frequency`
- `Monetary`
- `aov`
- `category_diversity`
- `return_rate_pct`

### Output

| File | Nội dung |
|---|---|
| `dim_users_with_clusters.csv/parquet` | user dimension đã gắn cluster |
| `clustering_analysis.csv` | dữ liệu user-level để drill-down |
| `cluster_profile_summary.csv` | profile trung bình từng cluster |

### Cluster labels hiện tại

| Cluster | Cách dùng |
|---|---|
| No Valid Purchase | first-purchase conversion |
| Occasional Spenders | nurture/cross-sell nhẹ |
| At-Risk High Value | win-back ưu tiên |
| Low-Value Browsers | hạn chế incentive sâu |
| Selective Buyers | recommendation theo category |
| Recent But Inactive | post-purchase journey |
| High-Value Loyal | loyalty/referral/early access |

Kết luận: cluster labels có thể đưa vào dashboard và action plan vì gắn được với chiến lược CRM khác nhau.

---

## 2. Demand forecast baseline

Forecast đã sinh cho 3 category lớn:

| File | Nội dung |
|---|---|
| `demand_forecast_12m.csv` | forecast 12 tháng |
| `demand_forecast_evaluation.csv` | backtest MAPE |
| `phase3_model_summary.csv` | tóm tắt model |

Kết quả hiện tại:

| Category | MAPE | Model |
|---|---:|---|
| Outerwear & Coats | 55.51% | seasonal_naive_fallback |
| Jeans | 47.21% | seasonal_naive_fallback |
| Sweaters | 49.97% | seasonal_naive_fallback |

`phase3_model_summary.csv` ghi `use_for_demand_planning = Baseline only`.

### Quyết định sử dụng

Forecast chỉ dùng để minh họa xu hướng/kịch bản và làm baseline cho inventory planning. Không dùng forecast để khuyến nghị mua hàng tự động vì MAPE còn cao.

### Cải thiện nếu có thêm thời gian

| Hạn chế hiện tại | Cải thiện |
|---|---|
| Chưa có promotion/discount calendar | bổ sung campaign features |
| Chưa có stockout signal | điều chỉnh observed demand theo availability |
| Chưa có price elasticity | thêm price/markdown features |
| Chưa có seasonality ngành | thêm holiday/fashion season calendar |
| MAPE 47-56% | thử Prophet/ARIMA/LightGBM và backtest rolling window |

---

## 3. Cách đưa Phase 3 vào báo cáo

Nên trình bày Phase 3 như một lớp hỗ trợ:

1. Clustering giúp biến RFM thành CRM action segments.
2. Forecast baseline cho thấy hướng đi để quản trị inventory tốt hơn.
3. Việc công khai MAPE cao làm báo cáo đáng tin hơn vì không thổi phồng predictive power.

Không nên viết rằng forecast đã đủ để demand planning chi tiết hoặc rằng mô hình đã tối ưu. Điểm mạnh của bài thi vẫn là insight Phase 2: leakage, retention, checkout và inventory.
