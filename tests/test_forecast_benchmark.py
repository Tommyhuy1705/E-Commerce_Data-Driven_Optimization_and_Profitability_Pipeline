from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecast_benchmark import (
    MODEL_MOVING_AVG_3,
    MODEL_RANDOM_FOREST,
    MODEL_SEASONAL_NAIVE,
    add_lag_features,
    mape_pct,
    rolling_origin_backtest,
    summarize_benchmark,
)


def _sample_category_frame(months: int = 36) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=months, freq="MS")
    seasonal = 1000 + 80 * np.sin(np.arange(months) / 12 * 2 * np.pi)
    trend = np.arange(months) * 10
    return pd.DataFrame(
        {
            "ds": dates,
            "category": "Jeans",
            "department": "Women",
            "revenue": seasonal + trend,
            "units": 100 + np.arange(months),
            "avg_sale_price": 50.0,
            "return_rate_pct": 10.0,
        }
    )


def test_mape_ignores_zero_actuals() -> None:
    assert round(mape_pct([0, 100, 200], [50, 90, 220]), 2) == 10.0


def test_add_lag_features_creates_expected_columns() -> None:
    featured = add_lag_features(_sample_category_frame(), target_col="revenue")
    for column in ["lag_1", "lag_12", "rolling_mean_3", "month", "price_lag_1"]:
        assert column in featured.columns


def test_rolling_origin_backtest_returns_all_models() -> None:
    predictions, importance = rolling_origin_backtest(_sample_category_frame(), min_train_months=24)

    assert not predictions.empty
    assert {MODEL_SEASONAL_NAIVE, MODEL_MOVING_AVG_3, MODEL_RANDOM_FOREST}.issubset(
        set(predictions["model_name"])
    )
    assert {"actual", "prediction", "category"}.issubset(predictions.columns)
    assert "feature" in importance.columns


def test_summarize_benchmark_ranks_models() -> None:
    predictions, _ = rolling_origin_backtest(_sample_category_frame(), min_train_months=24)
    benchmark = summarize_benchmark(predictions)

    assert not benchmark.empty
    assert benchmark["rank_within_category"].min() == 1
    assert benchmark["mape_pct"].notna().all()
