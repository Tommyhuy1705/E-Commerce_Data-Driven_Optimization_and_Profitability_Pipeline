from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    from prophet import Prophet  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - local fallback path
    Prophet = None

try:
    from sklearn.cluster import KMeans  # type: ignore[import-not-found]
    from sklearn.preprocessing import StandardScaler  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - local fallback path
    KMeans = None
    StandardScaler = None


NO_PURCHASE_SEGMENT = "No Purchase / No Valid Purchase"


def _read_processed_table(processed_dir: Path, table_name: str) -> pd.DataFrame:
    csv_path = processed_dir / f"{table_name}.csv"
    parquet_path = processed_dir / f"{table_name}.parquet"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    raise FileNotFoundError(f"Missing processed table: {table_name} in {processed_dir}")


def load_inputs(dataset_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    processed_dir = dataset_root / "processed"
    fact_transactions = _read_processed_table(processed_dir, "fact_transactions")
    dim_users = _read_processed_table(processed_dir, "dim_users")
    dim_products = _read_processed_table(processed_dir, "dim_products")
    return fact_transactions, dim_users, dim_products


def build_enriched_rfm(
    fact_transactions: pd.DataFrame,
    dim_users: pd.DataFrame,
    dim_products: pd.DataFrame,
) -> pd.DataFrame:
    fact = fact_transactions.copy()
    if "is_recognized_revenue" not in fact.columns:
        fact["is_recognized_revenue"] = fact["status"].isin(["Complete", "Shipped"]).astype("int8")
    fact = fact.loc[fact["is_recognized_revenue"].eq(1)].copy()

    product_categories = dim_products[["product_id", "category"]].drop_duplicates()
    user_categories = fact.merge(product_categories, on="product_id", how="left")
    category_diversity = (
        user_categories.groupby("user_id", as_index=False)
        .agg(category_diversity=("category", "nunique"))
    )

    enriched = dim_users[
        ["user_id", "Recency", "Frequency", "Monetary", "return_rate_pct", "rfm_segment"]
    ].copy()
    enriched["Frequency"] = enriched["Frequency"].fillna(0)
    enriched["Monetary"] = enriched["Monetary"].fillna(0.0)
    enriched["return_rate_pct"] = enriched["return_rate_pct"].fillna(0.0)
    enriched["rfm_segment"] = enriched["rfm_segment"].fillna(NO_PURCHASE_SEGMENT)
    enriched["aov"] = enriched["Monetary"] / enriched["Frequency"].replace(0, np.nan)
    # Monetary is already gross profit in the ETL, so this is not multiplied again.
    enriched["profit_per_customer"] = enriched["Monetary"]
    enriched = enriched.merge(category_diversity, on="user_id", how="left")
    enriched["category_diversity"] = enriched["category_diversity"].fillna(0)
    enriched["aov"] = enriched["aov"].fillna(0)
    enriched["Recency"] = enriched["Recency"].fillna(9999)
    return enriched


def choose_cluster_count(feature_matrix: pd.DataFrame) -> tuple[int, list[float]]:
    if KMeans is None:
        return 6, []

    inertias: list[float] = []
    best_k = 6
    for k in range(2, 8):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        model.fit(feature_matrix)
        inertias.append(float(model.inertia_))

    if len(inertias) >= 3:
        deltas = np.diff(inertias)
        second_deltas = np.diff(deltas)
        if len(second_deltas):
            best_k = int(np.argmin(second_deltas) + 3)
            best_k = max(2, min(best_k, 7))
    return best_k, inertias


def label_clusters(profile: pd.DataFrame) -> dict[int, str]:
    labels: dict[int, str] = {}
    ordered = profile.sort_values(["Monetary", "Recency"], ascending=[False, True]).index.tolist()
    fallback_names = [
        "High-Value Loyal",
        "Selective Buyers",
        "At-Risk High Value",
        "Recent But Inactive",
        "Occasional Spenders",
        "Low-Value Browsers",
        "No Valid Purchase",
    ]
    for position, cluster_id in enumerate(ordered):
        labels[int(cluster_id)] = fallback_names[position % len(fallback_names)]
    return labels


def _run_rule_based_clustering(enriched: pd.DataFrame) -> pd.DataFrame:
    result = enriched.copy()
    conditions = [
        result["Frequency"].eq(0),
        result["Frequency"].ge(3) & result["Monetary"].ge(result["Monetary"].quantile(0.9)),
        result["Frequency"].ge(2) & result["Recency"].le(180),
        result["Monetary"].ge(result["Monetary"].quantile(0.75)) & result["Recency"].gt(365),
        result["Recency"].gt(730),
        result["Frequency"].eq(1),
    ]
    labels = [
        "No Valid Purchase",
        "High-Value Loyal",
        "Selective Buyers",
        "At-Risk High Value",
        "Low-Value Browsers",
        "Occasional Spenders",
    ]
    result["cluster_label"] = np.select(conditions, labels, default="Recent But Inactive")
    label_to_id = {label: idx for idx, label in enumerate(sorted(result["cluster_label"].unique()))}
    result["cluster"] = result["cluster_label"].map(label_to_id).astype(int)
    return result


def run_clustering(dataset_root: Path, final_k: Optional[int] = None) -> pd.DataFrame:
    fact_transactions, dim_users, dim_products = load_inputs(dataset_root)
    enriched = build_enriched_rfm(fact_transactions, dim_users, dim_products)

    if KMeans is None or StandardScaler is None:
        enriched = _run_rule_based_clustering(enriched)
    else:
        cluster_features = ["Recency", "Monetary", "aov", "category_diversity", "return_rate_pct"]
        feature_frame = enriched[cluster_features].fillna(enriched[cluster_features].median(numeric_only=True))
        scaler = StandardScaler()
        scaled = scaler.fit_transform(feature_frame)
        k = final_k or choose_cluster_count(pd.DataFrame(scaled, columns=cluster_features))[0]
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        enriched["cluster"] = model.fit_predict(scaled)
        profile = enriched.groupby("cluster")[["Recency", "Frequency", "Monetary", "aov", "category_diversity", "return_rate_pct"]].mean()
        cluster_labels = label_clusters(profile)
        enriched["cluster_label"] = enriched["cluster"].map(cluster_labels)

    processed_dir = dataset_root / "processed"
    enriched.to_csv(processed_dir / "clustering_analysis.csv", index=False)
    dim_users_updated = dim_users.merge(enriched[["user_id", "cluster_label"]], on="user_id", how="left")
    dim_users_updated.to_csv(processed_dir / "dim_users_with_clusters.csv", index=False)
    try:
        parquet_users = dim_users_updated.copy()
        for column in parquet_users.select_dtypes(include=["object"]).columns:
            parquet_users[column] = parquet_users[column].astype("string")
        parquet_users.to_parquet(processed_dir / "dim_users_with_clusters.parquet", index=False)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    summary = (
        enriched.groupby(["cluster", "cluster_label"], as_index=False)[
            ["Recency", "Frequency", "Monetary", "aov", "category_diversity", "return_rate_pct"]
        ]
        .mean()
        .sort_values("Monetary", ascending=False)
    )
    summary.to_csv(processed_dir / "cluster_profile_summary.csv", index=False)
    return enriched


def build_monthly_category_series(
    fact_transactions: pd.DataFrame,
    dim_products: pd.DataFrame,
) -> pd.DataFrame:
    fact = fact_transactions.copy()
    if "Recognized_Revenue" not in fact.columns:
        fact["Recognized_Revenue"] = fact["sale_price"].where(fact["status"].isin(["Complete", "Shipped"]), 0.0)
    fact["date_key"] = fact["date_key"].astype(str)
    fact["date"] = pd.to_datetime(fact["date_key"], format="%Y%m%d", errors="coerce")
    fact = fact.dropna(subset=["date"])
    fact["year_month"] = fact["date"].dt.to_period("M").dt.to_timestamp()

    monthly_sales = fact.groupby(["year_month", "product_id"], as_index=False)["Recognized_Revenue"].sum()
    monthly_sales = monthly_sales.rename(columns={"Recognized_Revenue": "revenue"})
    monthly_sales = monthly_sales.merge(dim_products[["product_id", "category"]], on="product_id", how="left")
    category_monthly = monthly_sales.groupby(["year_month", "category"], as_index=False)["revenue"].sum()
    category_monthly["ds"] = pd.to_datetime(category_monthly["year_month"])
    return category_monthly[["ds", "category", "revenue"]]


def make_regular_monthly_frame(category_frame: pd.DataFrame) -> pd.DataFrame:
    full_index = pd.date_range(category_frame["ds"].min(), category_frame["ds"].max(), freq="MS")
    regular = category_frame.set_index("ds").reindex(full_index).fillna(0.0)
    regular.index.name = "ds"
    return regular.reset_index()


def _seasonal_naive_forecast(category_frame: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    frame = category_frame.sort_values("ds").reset_index(drop=True).copy()
    train = frame.iloc[:-12].copy()
    test = frame.iloc[-12:].copy()
    if len(train) >= 12:
        prior_year = train.tail(12)["y"].to_numpy(dtype=float)
        actual = test["y"].to_numpy(dtype=float)
        nonzero = actual != 0
        mape = float(np.mean(np.abs((actual[nonzero] - prior_year[nonzero]) / actual[nonzero]) * 100)) if nonzero.any() else np.nan
        future_base = frame.tail(12)["y"].to_numpy(dtype=float)
        recent_growth = frame.tail(12)["y"].sum() / max(frame.iloc[-24:-12]["y"].sum(), 1) if len(frame) >= 24 else 1.0
        yhat = future_base * max(min(recent_growth, 1.5), 0.5)
    else:
        mape = np.nan
        yhat = np.repeat(frame["y"].mean(), 12)

    future_dates = pd.date_range(frame["ds"].max() + pd.offsets.MonthBegin(1), periods=12, freq="MS")
    forecast = pd.DataFrame(
        {
            "ds": future_dates,
            "yhat": yhat,
            "yhat_lower": yhat * 0.85,
            "yhat_upper": yhat * 1.15,
        }
    )
    return forecast, mape


def forecast_top_categories(dataset_root: Path, top_n: int = 3) -> pd.DataFrame:
    fact_transactions, _, dim_products = load_inputs(dataset_root)
    category_monthly = build_monthly_category_series(fact_transactions, dim_products)
    top_categories = (
        category_monthly.groupby("category", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
        .head(top_n)["category"]
        .tolist()
    )

    future_rows: list[pd.DataFrame] = []
    evaluation_rows: list[dict[str, object]] = []

    for category in top_categories:
        category_frame = category_monthly.loc[category_monthly["category"].eq(category), ["ds", "revenue"]].copy()
        category_frame = make_regular_monthly_frame(category_frame).rename(columns={"revenue": "y"})
        if len(category_frame) < 24:
            continue

        current_model_type = "prophet"
        try:
            if Prophet is None:
                raise RuntimeError("Prophet backend is unavailable")

            train_frame = category_frame.iloc[:-12].copy()
            test_frame = category_frame.iloc[-12:].copy()
            model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
            model.fit(train_frame)
            test_forecast = model.predict(test_frame[["ds"]])
            merged_test = test_frame.merge(test_forecast[["ds", "yhat"]], on="ds", how="left")
            actual = merged_test["y"].to_numpy(dtype=float)
            predicted = merged_test["yhat"].to_numpy(dtype=float)
            nonzero = actual != 0
            mape = float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero]) * 100)) if nonzero.any() else np.nan
            final_model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
            final_model.fit(category_frame)
            future = final_model.make_future_dataframe(periods=12, freq="MS")
            forecast = final_model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(12).copy()
        except Exception:
            forecast, mape = _seasonal_naive_forecast(category_frame)
            current_model_type = "seasonal_naive_fallback"

        forecast.insert(0, "category", category)
        forecast["mape_pct"] = round(mape, 2) if pd.notna(mape) else np.nan
        forecast["model_type"] = current_model_type
        future_rows.append(forecast)
        evaluation_rows.append(
            {
                "category": category,
                "train_months": max(len(category_frame) - 12, 0),
                "test_months": min(12, len(category_frame)),
                "mape_pct": round(mape, 2) if pd.notna(mape) else np.nan,
                "train_start": category_frame["ds"].min().date().isoformat(),
                "train_end": category_frame.iloc[-13]["ds"].date().isoformat() if len(category_frame) > 12 else "",
                "model_type": current_model_type,
            }
        )

    processed_dir = dataset_root / "processed"
    forecast_df = pd.concat(future_rows, ignore_index=True) if future_rows else pd.DataFrame()
    evaluation_df = pd.DataFrame(evaluation_rows)
    forecast_df.to_csv(processed_dir / "demand_forecast_12m.csv", index=False)
    evaluation_df.to_csv(processed_dir / "demand_forecast_evaluation.csv", index=False)

    powerbi_dir = dataset_root.parent / "Datavision2026" / "powerbi"
    if powerbi_dir.exists():
        forecast_df.to_csv(powerbi_dir / "demand_forecast_12m.csv", index=False)
    return forecast_df


def build_phase3_report(dataset_root: Path) -> pd.DataFrame:
    processed_dir = dataset_root / "processed"
    clustering = pd.read_csv(processed_dir / "clustering_analysis.csv")
    forecast_evaluation = pd.read_csv(processed_dir / "demand_forecast_evaluation.csv")
    model_type = forecast_evaluation["model_type"].iloc[0] if "model_type" in forecast_evaluation.columns and not forecast_evaluation.empty else "unknown"
    summary_rows = [
        {"section": "Clustering", "metric": "cluster_count", "value": int(clustering["cluster_label"].nunique())},
        {"section": "Clustering", "metric": "top_cluster", "value": clustering["cluster_label"].value_counts().idxmax()},
        {"section": "Forecasting", "metric": "model_type", "value": model_type},
        {
            "section": "Forecasting",
            "metric": "top_category_mape_pct",
            "value": round(float(forecast_evaluation["mape_pct"].mean()), 2) if not forecast_evaluation.empty else np.nan,
        },
        {"section": "Forecasting", "metric": "use_for_demand_planning", "value": "Baseline only"},
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(processed_dir / "phase3_model_summary.csv", index=False)
    return summary_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DATAVISION Phase 3 advanced modeling")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="Path to the dataset folder containing processed/.",
    )
    parser.add_argument("--clusters", type=int, default=None, help="Override KMeans cluster count when sklearn is available.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    enriched = run_clustering(args.dataset_root, final_k=args.clusters)
    forecast_df = forecast_top_categories(args.dataset_root)
    summary_df = build_phase3_report(args.dataset_root)
    print("Phase 3 completed.")
    print(enriched["cluster_label"].value_counts().sort_index())
    print("Forecast rows:", len(forecast_df))
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
