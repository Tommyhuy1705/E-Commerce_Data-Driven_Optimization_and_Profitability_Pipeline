from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - dependency is optional in constrained envs
    RandomForestRegressor = None


MODEL_SEASONAL_NAIVE = "seasonal_naive_12m"
MODEL_MOVING_AVG_3 = "moving_average_3m"
MODEL_MOVING_AVG_6 = "moving_average_6m"
MODEL_RANDOM_FOREST = "random_forest_lag_features"


def _read_processed_table(processed_dir: Path, table_name: str) -> pd.DataFrame:
    csv_path = processed_dir / f"{table_name}.csv"
    parquet_path = processed_dir / f"{table_name}.parquet"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    raise FileNotFoundError(f"Missing processed table {table_name!r} under {processed_dir}")


def mape_pct(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    mask = actual_array != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual_array[mask] - predicted_array[mask]) / actual_array[mask])) * 100)


def rmse(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    return float(np.sqrt(np.mean((actual_array - predicted_array) ** 2)))


def build_monthly_category_series(dataset_root: Path) -> pd.DataFrame:
    processed_dir = dataset_root / "processed"
    fact = _read_processed_table(processed_dir, "fact_transactions")
    products = _read_processed_table(processed_dir, "dim_products")

    fact = fact.copy()
    fact["date_key"] = fact["date_key"].astype(str)
    fact["date"] = pd.to_datetime(fact["date_key"], format="%Y%m%d", errors="coerce")
    fact = fact.dropna(subset=["date"])
    fact["year_month"] = fact["date"].dt.to_period("M").dt.to_timestamp()
    if "Recognized_Revenue" not in fact.columns:
        fact["Recognized_Revenue"] = fact["sale_price"].where(fact["status"].isin(["Complete", "Shipped"]), 0.0)

    product_lookup = products[["product_id", "category", "department"]].drop_duplicates()
    enriched = fact.merge(product_lookup, on="product_id", how="left")
    monthly = (
        enriched.groupby(["year_month", "category", "department"], as_index=False)
        .agg(
            revenue=("Recognized_Revenue", "sum"),
            units=("order_item_id", "count"),
            avg_sale_price=("sale_price", "mean"),
            return_rate_pct=("is_returned", "mean"),
        )
    )
    monthly["return_rate_pct"] = monthly["return_rate_pct"].fillna(0.0) * 100
    return monthly.rename(columns={"year_month": "ds"})


def make_regular_category_frame(monthly: pd.DataFrame, category: str) -> pd.DataFrame:
    frame = monthly.loc[monthly["category"].eq(category)].copy()
    if frame.empty:
        return pd.DataFrame(columns=["ds", "category", "department", "revenue", "units", "avg_sale_price", "return_rate_pct"])

    grouped = (
        frame.groupby(["ds", "category"], as_index=False)
        .agg(
            department=("department", lambda values: values.mode().iloc[0] if not values.mode().empty else "Unknown"),
            revenue=("revenue", "sum"),
            units=("units", "sum"),
            avg_sale_price=("avg_sale_price", "mean"),
            return_rate_pct=("return_rate_pct", "mean"),
        )
        .sort_values("ds")
    )
    full_months = pd.date_range(grouped["ds"].min(), grouped["ds"].max(), freq="MS")
    regular = grouped.set_index("ds").reindex(full_months)
    regular.index.name = "ds"
    regular["category"] = category
    regular["department"] = regular["department"].ffill().bfill().fillna("Unknown")
    for column in ["revenue", "units", "avg_sale_price", "return_rate_pct"]:
        regular[column] = regular[column].fillna(0.0)
    return regular.reset_index()


def add_lag_features(frame: pd.DataFrame, target_col: str = "revenue") -> pd.DataFrame:
    featured = frame.sort_values("ds").reset_index(drop=True).copy()
    featured["month"] = featured["ds"].dt.month
    featured["quarter"] = featured["ds"].dt.quarter
    featured["year_index"] = featured["ds"].dt.year - featured["ds"].dt.year.min()
    for lag in [1, 2, 3, 6, 12]:
        featured[f"lag_{lag}"] = featured[target_col].shift(lag)
    featured["rolling_mean_3"] = featured[target_col].shift(1).rolling(3).mean()
    featured["rolling_mean_6"] = featured[target_col].shift(1).rolling(6).mean()
    featured["rolling_std_3"] = featured[target_col].shift(1).rolling(3).std()
    featured["rolling_std_6"] = featured[target_col].shift(1).rolling(6).std()
    featured["price_lag_1"] = featured["avg_sale_price"].shift(1)
    featured["return_rate_lag_1"] = featured["return_rate_pct"].shift(1)
    return featured


def _predict_simple(train: pd.DataFrame, model_name: str, target_col: str) -> float:
    if model_name == MODEL_SEASONAL_NAIVE and len(train) >= 12:
        return float(train[target_col].iloc[-12])
    if model_name == MODEL_MOVING_AVG_3:
        return float(train[target_col].tail(3).mean())
    if model_name == MODEL_MOVING_AVG_6:
        return float(train[target_col].tail(6).mean())
    return float(train[target_col].mean())


def _predict_random_forest(featured: pd.DataFrame, test_idx: int, target_col: str) -> tuple[float, pd.Series]:
    feature_cols = [
        "month",
        "quarter",
        "year_index",
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_6",
        "lag_12",
        "rolling_mean_3",
        "rolling_mean_6",
        "rolling_std_3",
        "rolling_std_6",
        "price_lag_1",
        "return_rate_lag_1",
    ]
    if RandomForestRegressor is None:
        return _predict_simple(featured.iloc[:test_idx], MODEL_SEASONAL_NAIVE, target_col), pd.Series(dtype=float)

    train = featured.iloc[:test_idx].dropna(subset=feature_cols + [target_col]).copy()
    test_row = featured.iloc[[test_idx]].dropna(subset=feature_cols)
    if len(train) < 12 or test_row.empty:
        return _predict_simple(featured.iloc[:test_idx], MODEL_SEASONAL_NAIVE, target_col), pd.Series(dtype=float)

    model = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42, min_samples_leaf=2)
    model.fit(train[feature_cols], train[target_col])
    prediction = float(model.predict(test_row[feature_cols])[0])
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    return max(prediction, 0.0), importance


def rolling_origin_backtest(
    category_frame: pd.DataFrame,
    target_col: str = "revenue",
    min_train_months: int = 24,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = category_frame.sort_values("ds").reset_index(drop=True).copy()
    featured = add_lag_features(frame, target_col=target_col)
    prediction_rows: list[dict[str, object]] = []
    importance_rows: list[pd.Series] = []

    for test_idx in range(min_train_months, len(frame)):
        train = frame.iloc[:test_idx].copy()
        actual = float(frame[target_col].iloc[test_idx])
        for model_name in [MODEL_SEASONAL_NAIVE, MODEL_MOVING_AVG_3, MODEL_MOVING_AVG_6]:
            prediction_rows.append(
                {
                    "ds": frame["ds"].iloc[test_idx],
                    "category": frame["category"].iloc[test_idx],
                    "model_name": model_name,
                    "actual": actual,
                    "prediction": max(_predict_simple(train, model_name, target_col), 0.0),
                }
            )
        rf_prediction, importance = _predict_random_forest(featured, test_idx, target_col)
        prediction_rows.append(
            {
                "ds": frame["ds"].iloc[test_idx],
                "category": frame["category"].iloc[test_idx],
                "model_name": MODEL_RANDOM_FOREST,
                "actual": actual,
                "prediction": rf_prediction,
            }
        )
        if not importance.empty:
            importance_rows.append(importance)

    predictions = pd.DataFrame(prediction_rows)
    if importance_rows:
        importance_df = pd.concat(importance_rows, axis=1).mean(axis=1).reset_index()
        importance_df.columns = ["feature", "importance"]
        importance_df.insert(0, "category", frame["category"].iloc[0])
    else:
        importance_df = pd.DataFrame(columns=["category", "feature", "importance"])
    return predictions, importance_df


def summarize_benchmark(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (category, model_name), group in predictions.groupby(["category", "model_name"]):
        actual = group["actual"].astype(float)
        prediction = group["prediction"].astype(float)
        rows.append(
            {
                "category": category,
                "model_name": model_name,
                "backtest_months": len(group),
                "mape_pct": mape_pct(actual, prediction),
                "mae": float(np.mean(np.abs(actual - prediction))),
                "rmse": rmse(actual, prediction),
                "bias_pct": float((prediction.sum() - actual.sum()) / actual.sum() * 100) if actual.sum() else np.nan,
            }
        )
    benchmark = pd.DataFrame(rows)
    benchmark["rank_within_category"] = benchmark.groupby("category")["mape_pct"].rank(method="dense", ascending=True)
    return benchmark.sort_values(["category", "rank_within_category", "model_name"]).reset_index(drop=True)


def write_recommendation(processed_dir: Path, benchmark: pd.DataFrame) -> Path:
    output = processed_dir / "forecast_recommendation.md"
    if benchmark.empty:
        output.write_text("# Forecast Recommendation\n\nNo benchmark output was generated.\n", encoding="utf-8")
        return output

    best = benchmark.loc[benchmark["rank_within_category"].eq(1)].copy()
    avg_best_mape = float(best["mape_pct"].mean())
    if avg_best_mape <= 40:
        recommendation = "Use the best model as a planning signal with monthly monitoring."
    elif avg_best_mape <= 50:
        recommendation = "Use the forecast for monitored inventory review, not automated procurement."
    else:
        recommendation = "Keep the forecast as directional monitoring only until additional features are available."

    lines = [
        "# Forecast Recommendation",
        "",
        f"Average best-category MAPE: `{avg_best_mape:.2f}%`.",
        "",
        f"Recommendation: {recommendation}",
        "",
        "## Best Model By Category",
        "",
        "| Category | Best Model | MAPE | Bias |",
        "|---|---|---:|---:|",
    ]
    for _, row in best.sort_values("category").iterrows():
        lines.append(
            f"| {row['category']} | {row['model_name']} | {float(row['mape_pct']):.2f}% | {float(row['bias_pct']):.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- The benchmark does not include promotion calendar, discount history, stockout flags, or external demand signals.",
            "- Random Forest feature importance is useful for interpretation, but it is not causal.",
            "- Forecast output should remain a decision-support signal while category-level MAPE is high.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run_forecast_benchmark(dataset_root: Path, top_n: int = 5) -> dict[str, Path]:
    processed_dir = dataset_root / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    monthly = build_monthly_category_series(dataset_root)
    top_categories = (
        monthly.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False).head(top_n)["category"].tolist()
    )

    all_predictions: list[pd.DataFrame] = []
    all_importance: list[pd.DataFrame] = []
    for category in top_categories:
        frame = make_regular_category_frame(monthly, category)
        if len(frame) < 30:
            continue
        predictions, importance = rolling_origin_backtest(frame)
        all_predictions.append(predictions)
        all_importance.append(importance)

    predictions_df = pd.concat(all_predictions, ignore_index=True) if all_predictions else pd.DataFrame()
    benchmark_df = summarize_benchmark(predictions_df)
    importance_df = pd.concat(all_importance, ignore_index=True) if all_importance else pd.DataFrame()

    outputs = {
        "benchmark": processed_dir / "forecast_model_benchmark.csv",
        "predictions": processed_dir / "forecast_backtest_predictions.csv",
        "importance": processed_dir / "forecast_feature_importance.csv",
        "recommendation": processed_dir / "forecast_recommendation.md",
    }
    benchmark_df.to_csv(outputs["benchmark"], index=False)
    predictions_df.to_csv(outputs["predictions"], index=False)
    importance_df.to_csv(outputs["importance"], index=False)
    write_recommendation(processed_dir, benchmark_df)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rolling-origin forecast benchmark")
    parser.add_argument("--dataset-root", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_forecast_benchmark(args.dataset_root, top_n=args.top_n)
    print("Forecast benchmark completed.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
