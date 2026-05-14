from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    import duckdb  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - fallback for environments without duckdb
    duckdb = None

CUTOFF_ANALYSIS = pd.Timestamp("2023-12-31")
CUTOFF_INVENTORY = pd.Timestamp("2024-01-17")
RECOGNIZED_REVENUE_STATUSES = {"Complete", "Shipped"}


def _to_datetime_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


@dataclass
class PipelineArtifacts:
    fact_transactions: pd.DataFrame
    agg_funnel_monthly: pd.DataFrame
    fact_inventory: pd.DataFrame
    dim_users: pd.DataFrame
    dim_products: pd.DataFrame
    dim_dcs: pd.DataFrame
    dim_date: pd.DataFrame


def load_raw_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    orders = pd.read_csv(raw_dir / "orders.csv")
    order_items = pd.read_csv(raw_dir / "order_items.csv")
    inventory = pd.read_csv(raw_dir / "inventory_items.csv")
    events = load_events(raw_dir / "events.csv")
    users = pd.read_csv(raw_dir / "users.csv")
    products = pd.read_csv(raw_dir / "products.csv")
    dcs = pd.read_csv(raw_dir / "distribution_centers.csv")

    for col in ["created_at", "shipped_at", "delivered_at", "returned_at"]:
        if col in orders.columns:
            orders[col] = _to_datetime_utc(orders[col])
    for col in ["created_at", "shipped_at", "delivered_at", "returned_at"]:
        if col in order_items.columns:
            order_items[col] = _to_datetime_utc(order_items[col])
    for col in ["created_at", "sold_at"]:
        if col in inventory.columns:
            inventory[col] = _to_datetime_utc(inventory[col])
    if "created_at" in events.columns:
        events["created_at"] = _to_datetime_utc(events["created_at"])
    if "created_at" in users.columns:
        users["created_at"] = _to_datetime_utc(users["created_at"])

    return {
        "orders": orders,
        "order_items": order_items,
        "inventory": inventory,
        "events": events,
        "users": users,
        "products": products,
        "dcs": dcs,
    }


def load_events(events_path: Path) -> pd.DataFrame:
    if duckdb is not None:
        connection = duckdb.connect(database=":memory:")
        query = "SELECT * FROM read_csv_auto(?, HEADER=TRUE)"
        return connection.execute(query, [str(events_path)]).df()
    return pd.read_csv(events_path)


def profile_tables(tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, object]]:
    profile: dict[str, dict[str, object]] = {}
    pk_map = {
        "orders": "order_id",
        "order_items": "id",
        "inventory": "id",
        "events": "id",
        "users": "id",
        "products": "id",
        "dcs": "id",
    }
    for name, df in tables.items():
        null_pct = ((df.isna().sum() / len(df)) * 100).round(4).to_dict() if len(df) else {}
        null_count = df.isna().sum().astype(int).to_dict()
        pk = pk_map.get(name)
        profile[name] = {
            "shape": [int(df.shape[0]), int(df.shape[1])],
            "memory_mb": round(float(df.memory_usage(deep=True).sum() / (1024 * 1024)), 3),
            "duplicate_pk": int(df.duplicated(pk).sum()) if pk and pk in df.columns else None,
            "null_count": {k: v for k, v in null_count.items() if v > 0},
            "null_pct": {k: v for k, v in null_pct.items() if v > 0},
        }
    return profile


def _count_valid_date_rule(df: pd.DataFrame, left_col: str, right_col: str) -> int:
    mask = df[left_col].notna() & df[right_col].notna()
    if not mask.any():
        return 0
    return int((df.loc[mask, left_col] <= df.loc[mask, right_col]).sum())


def validate_orders(orders: pd.DataFrame) -> dict[str, int]:
    status_lower = orders["status"].astype(str).str.lower()
    cancelled = status_lower.eq("cancelled")
    returned = status_lower.eq("returned")

    return {
        "cancelled_with_shipped_at": int((cancelled & orders["shipped_at"].notna()).sum()),
        "cancelled_with_delivered_at": int((cancelled & orders["delivered_at"].notna()).sum()),
        "cancelled_with_returned_at": int((cancelled & orders["returned_at"].notna()).sum()),
        "returned_without_delivered_at": int((returned & orders["delivered_at"].isna()).sum()),
        "returned_without_returned_at": int((returned & orders["returned_at"].isna()).sum()),
        "negative_num_of_item": int((orders["num_of_item"].fillna(0) < 0).sum()),
    }


def validate_events(events: pd.DataFrame, users: pd.DataFrame) -> dict[str, int | list[str]]:
    traffic_sources = sorted(events["traffic_source"].dropna().astype(str).unique().tolist())
    user_sources = sorted(users["traffic_source"].dropna().astype(str).unique().tolist())
    source_mismatch = sorted(set(traffic_sources).difference(user_sources))
    monotonic_sessions = 0
    session_violations = 0

    if duckdb is not None:
        connection = duckdb.connect(database=":memory:")
        connection.register("events_frame", events)
        session_violation_df = connection.execute(
            """
            WITH ordered_events AS (
                SELECT
                    session_id,
                    created_at,
                    sequence_number,
                    LAG(created_at) OVER (
                        PARTITION BY session_id
                        ORDER BY sequence_number, created_at, id
                    ) AS previous_created_at
                FROM events_frame
                WHERE session_id IS NOT NULL
            )
            SELECT
                COUNT(*) FILTER (WHERE session_id IS NOT NULL) AS total_sessions,
                COUNT(*) FILTER (WHERE previous_created_at IS NOT NULL AND created_at < previous_created_at) AS sessions_with_regressions
            FROM ordered_events
            """
        ).df()
        monotonic_sessions = int(session_violation_df["total_sessions"].iloc[0])
        session_violations = int(session_violation_df["sessions_with_regressions"].iloc[0])
    else:
        monotonic_sessions = int(events["session_id"].nunique())

    return {
        "traffic_sources_events": traffic_sources,
        "traffic_sources_users": user_sources,
        "traffic_source_mismatch_count": len(source_mismatch),
        "traffic_source_mismatch_values": source_mismatch,
        "sessions_checked": monotonic_sessions,
        "sessions_with_time_regressions": session_violations,
    }


def clean_users(users: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    users = users.copy()
    duplicate_user_count = int(users.duplicated(subset=["id"], keep=False).sum())
    age_null_count = int(users["age"].isna().sum())
    gender_null_count = int(users["gender"].isna().sum())
    city_null_count = int(users["city"].isna().sum())
    invalid_age_count = int(((users["age"] < 13) | (users["age"] > 120)).fillna(False).sum())

    age_median = int(users["age"].dropna().median()) if users["age"].notna().any() else 28
    users["age"] = users["age"].clip(lower=13, upper=120).fillna(age_median).astype("int64")
    users["gender"] = users["gender"].fillna("Unknown")
    users["city"] = users["city"].fillna("Unknown")

    validation = {
        "duplicate_user_ids": duplicate_user_count,
        "null_age": age_null_count,
        "null_gender": gender_null_count,
        "null_city": city_null_count,
        "invalid_age": invalid_age_count,
    }

    return users.drop_duplicates(subset=["id"], keep="first"), validation


def validate_products(products: pd.DataFrame) -> dict[str, int]:
    return {
        "null_category": int(products["category"].isna().sum()),
        "null_cost": int(products["cost"].isna().sum()),
        "null_retail_price": int(products["retail_price"].isna().sum()),
        "cost_greater_than_retail_price": int((products["cost"] > products["retail_price"]).sum()),
    }


def validate_dcs(dcs: pd.DataFrame) -> dict[str, int]:
    return {
        "null_name": int(dcs["name"].isna().sum()),
        "null_latitude": int(dcs["latitude"].isna().sum()),
        "null_longitude": int(dcs["longitude"].isna().sum()),
    }


def validate_foreign_keys(tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, int | float]]:
    checks = [
        ("orders.user_id_to_users.id", tables["orders"]["user_id"], tables["users"]["id"]),
        ("order_items.order_id_to_orders.order_id", tables["order_items"]["order_id"], tables["orders"]["order_id"]),
        ("order_items.user_id_to_users.id", tables["order_items"]["user_id"], tables["users"]["id"]),
        ("order_items.product_id_to_products.id", tables["order_items"]["product_id"], tables["products"]["id"]),
        ("products.distribution_center_id_to_dcs.id", tables["products"]["distribution_center_id"], tables["dcs"]["id"]),
        (
            "inventory.product_id_to_products.id",
            tables["inventory"]["product_id"],
            tables["products"]["id"],
        ),
        (
            "inventory.product_distribution_center_id_to_dcs.id",
            tables["inventory"]["product_distribution_center_id"],
            tables["dcs"]["id"],
        ),
        ("events.user_id_to_users.id_non_null_only", tables["events"]["user_id"], tables["users"]["id"]),
    ]
    output: dict[str, dict[str, int | float]] = {}
    for name, child, parent in checks:
        child_non_null = child.dropna()
        orphan_count = int((~child_non_null.isin(parent)).sum())
        checked_count = int(len(child_non_null))
        output[name] = {
            "checked_rows": checked_count,
            "orphan_rows": orphan_count,
            "orphan_pct": round(orphan_count / checked_count * 100, 4) if checked_count else 0.0,
        }
    return output


def create_issue_samples(tables: dict[str, pd.DataFrame], order_items_clean: pd.DataFrame) -> dict[str, pd.DataFrame]:
    orders = tables["orders"]
    returned = orders["status"].astype(str).str.lower().eq("returned")
    samples = {
        "orders_shipped_before_created": orders.loc[
            orders["shipped_at"].notna()
            & orders["created_at"].notna()
            & (orders["shipped_at"] <= orders["created_at"])
        ].head(50),
        "orders_delivered_before_shipped": orders.loc[
            orders["delivered_at"].notna()
            & orders["shipped_at"].notna()
            & (orders["delivered_at"] <= orders["shipped_at"])
        ].head(50),
        "orders_returned_before_delivered": orders.loc[
            orders["returned_at"].notna()
            & orders["delivered_at"].notna()
            & (orders["returned_at"] <= orders["delivered_at"])
        ].head(50),
        "returned_orders_missing_timestamps": orders.loc[
            returned & (orders["delivered_at"].isna() | orders["returned_at"].isna())
        ].head(50),
        "order_items_sale_price_lt_1": order_items_clean.loc[order_items_clean["sale_price"] < 1].head(50),
        "events_null_user_id_sample": tables["events"].loc[tables["events"]["user_id"].isna()].head(50),
        "inventory_missing_created_at_sample": tables["inventory"].loc[tables["inventory"]["created_at"].isna()].head(50),
        "products_missing_name_or_brand_sample": tables["products"].loc[
            tables["products"]["name"].isna() | tables["products"]["brand"].isna()
        ].head(50),
    }
    return samples


def clean_orders(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    orders = orders.copy()
    orders["is_2024_partial"] = orders["created_at"].dt.year.eq(2024)
    orders_analysis = orders.loc[~orders["is_2024_partial"]].copy()

    date_violations = {
        "shipped_before_created": _count_valid_date_rule(orders, "shipped_at", "created_at"),
        "delivered_before_shipped": _count_valid_date_rule(orders, "delivered_at", "shipped_at"),
        "returned_before_delivered": _count_valid_date_rule(orders, "returned_at", "delivered_at"),
    }

    negative_amount_count = int((orders.get("num_of_item", pd.Series(dtype=float)) < 0).sum())
    date_violations["negative_num_of_item"] = negative_amount_count

    return orders, orders_analysis, date_violations


def clean_order_items(order_items: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    product_cols = products[["id", "cost", "category"]].rename(columns={"id": "product_id"})
    enriched = order_items.merge(product_cols, on="product_id", how="left")
    enriched["gross_profit"] = enriched["sale_price"] - enriched["cost"]
    enriched["exclude_from_revenue"] = enriched["sale_price"] < 1

    outlier_count = int((enriched["sale_price"] < 1).sum())
    zero_price_count = int((enriched["sale_price"] == 0).sum())

    quality = {
        "sale_price_lt_1": outlier_count,
        "sale_price_eq_0": zero_price_count,
        "missing_product_cost": int(enriched["cost"].isna().sum()),
    }

    return enriched, quality


def clean_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    inventory = inventory.copy()
    inventory["is_sold"] = inventory["sold_at"].notna().astype("int8")
    inventory["holding_days"] = (CUTOFF_INVENTORY - inventory["created_at"]).dt.days.clip(lower=0)
    inventory["sunk_cost_risk"] = inventory["cost"] * (1 - inventory["is_sold"])
    inventory["holding_cost_annual"] = inventory["sunk_cost_risk"] * 0.25
    inventory["holding_cost_daily"] = inventory["holding_cost_annual"] / 365
    inventory["holding_cost_estimate"] = inventory["holding_cost_daily"] * inventory["holding_days"]
    return inventory


def detect_bot_candidates(events: pd.DataFrame) -> pd.DataFrame:
    if duckdb is not None:
        connection = duckdb.connect(database=":memory:")
        connection.register("events_frame", events)
        return connection.execute(
            """
            SELECT user_id, CAST(created_at AS DATE) AS day, COUNT(*) AS event_count
            FROM events_frame
            GROUP BY 1, 2
            HAVING COUNT(*) > 1000
            ORDER BY event_count DESC
            """
        ).df()

    by_user_day = (
        events.assign(day=events["created_at"].dt.date)
        .groupby(["user_id", "day"], as_index=False)
        .agg(event_count=("id", "count"))
    )
    return by_user_day.loc[by_user_day["event_count"] > 1000].sort_values("event_count", ascending=False)


def reconcile_processed_scope(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    order_items_revenue: pd.DataFrame,
    artifacts: PipelineArtifacts,
) -> dict[str, int | float]:
    orders_analysis = orders.loc[~orders["created_at"].dt.year.eq(2024)].copy()
    eligible_order_items = order_items.merge(
        orders_analysis[["order_id", "created_at"]].rename(columns={"created_at": "order_created_at"}),
        on="order_id",
        how="inner",
    )
    eligible_order_items = eligible_order_items.loc[eligible_order_items["order_created_at"].notna()].copy()
    raw_gmv = float(order_items["sale_price"].sum())
    processed_gmv = float(artifacts.fact_transactions["GMV_All_Status"].sum())
    return {
        "raw_order_item_rows": int(len(order_items)),
        "sub_1_price_rows_excluded": int((order_items["sale_price"] < 1).sum()),
        "rows_after_price_filter": int(len(order_items_revenue)),
        "eligible_rows_after_2024_and_missing_date_exclusion": int(len(eligible_order_items)),
        "fact_transaction_rows": int(len(artifacts.fact_transactions)),
        "raw_gmv": round(raw_gmv, 2),
        "processed_fact_gmv": round(processed_gmv, 2),
        "gmv_removed_from_model_scope": round(raw_gmv - processed_gmv, 2),
    }


def create_rfm(orders_analysis: pd.DataFrame, order_items_clean: pd.DataFrame) -> pd.DataFrame:
    orders_for_join = orders_analysis[["order_id", "created_at", "status"]].rename(
        columns={"created_at": "order_created_at", "status": "order_status"}
    )
    orders_enriched = order_items_clean.merge(orders_for_join, on="order_id", how="inner")
    valid_orders = orders_enriched.loc[
        orders_enriched["order_created_at"].notna()
        & orders_enriched["order_status"].isin(RECOGNIZED_REVENUE_STATUSES)
    ].copy()

    rfm = (
        valid_orders.groupby("user_id", as_index=False)
        .agg(
            Recency=("order_created_at", lambda x: (CUTOFF_ANALYSIS - x.max()).days),
            Frequency=("order_id", "nunique"),
            Monetary=("gross_profit", "sum"),
        )
    )

    def _quintile_score(series: pd.Series, reverse: bool = False) -> pd.Series:
        pct_rank = series.rank(method="first", pct=True)
        score = pd.cut(
            pct_rank,
            bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            labels=[1, 2, 3, 4, 5],
            include_lowest=True,
        ).astype("float")
        score = score.fillna(3).astype("int8")
        return (6 - score) if reverse else score

    rfm["R_score"] = _quintile_score(rfm["Recency"], reverse=True)
    rfm["F_score"] = _quintile_score(rfm["Frequency"], reverse=False)
    rfm["M_score"] = _quintile_score(rfm["Monetary"], reverse=False)

    def _segment(row: pd.Series) -> str:
        score = int(row["R_score"]) + int(row["F_score"]) + int(row["M_score"])
        if score >= 13:
            return "Champions"
        if score >= 10:
            return "Loyal"
        if score >= 7:
            return "At Risk"
        if score >= 4:
            return "About to Lose"
        return "Lost"

    rfm["rfm_segment"] = rfm.apply(_segment, axis=1)

    return_summary = (
        orders_enriched.groupby("user_id", as_index=False)
        .agg(
            total_items=("id", "count"),
            returned_items=("order_status", lambda s: int((s == "Returned").sum())),
        )
        .assign(return_rate_pct=lambda x: (x["returned_items"] / x["total_items"] * 100).fillna(0.0))
    )

    rfm = rfm.merge(return_summary[["user_id", "return_rate_pct"]], on="user_id", how="left")
    return rfm


def build_model_tables(
    orders_analysis: pd.DataFrame,
    order_items_clean: pd.DataFrame,
    inventory_clean: pd.DataFrame,
    events: pd.DataFrame,
    users: pd.DataFrame,
    products: pd.DataFrame,
    dcs: pd.DataFrame,
    rfm: pd.DataFrame,
) -> PipelineArtifacts:
    orders_light = orders_analysis[["order_id", "created_at", "status"]].rename(
        columns={"created_at": "order_created_at", "status": "order_status"}
    )
    fact_transactions = order_items_clean.merge(orders_light, on="order_id", how="inner")
    fact_transactions = fact_transactions.loc[fact_transactions["order_created_at"].notna()].copy()
    fact_transactions["date_key"] = (
        fact_transactions["order_created_at"].dt.strftime("%Y%m%d").astype("int32")
    )
    fact_transactions["is_returned"] = fact_transactions["order_status"].eq("Returned").astype("int8")
    fact_transactions["is_gmv"] = (~fact_transactions["exclude_from_revenue"]).astype("int8")
    fact_transactions["is_recognized_revenue"] = (
        fact_transactions["order_status"].isin(RECOGNIZED_REVENUE_STATUSES)
    ).astype("int8")
    fact_transactions["GMV_All_Status"] = fact_transactions["sale_price"]
    fact_transactions["Recognized_Revenue"] = fact_transactions["sale_price"].where(
        fact_transactions["is_recognized_revenue"].eq(1), 0.0
    )
    fact_transactions["Recognized_Gross_Profit"] = fact_transactions["gross_profit"].where(
        fact_transactions["is_recognized_revenue"].eq(1), 0.0
    )
    fact_transactions["Revenue_Lost_Cancelled"] = fact_transactions["sale_price"].where(
        fact_transactions["order_status"].eq("Cancelled"), 0.0
    )
    fact_transactions["Return_Value"] = fact_transactions["sale_price"].where(
        fact_transactions["order_status"].eq("Returned"), 0.0
    )
    fact_transactions["Processing_Backlog_Value"] = fact_transactions["sale_price"].where(
        fact_transactions["order_status"].eq("Processing"), 0.0
    )
    fact_transactions = fact_transactions[
        [
            "id",
            "order_id",
            "user_id",
            "product_id",
            "date_key",
            "sale_price",
            "cost",
            "gross_profit",
            "order_status",
            "is_returned",
            "is_gmv",
            "is_recognized_revenue",
            "GMV_All_Status",
            "Recognized_Revenue",
            "Recognized_Gross_Profit",
            "Revenue_Lost_Cancelled",
            "Return_Value",
            "Processing_Backlog_Value",
            "order_created_at",
        ]
    ].rename(columns={"id": "order_item_id", "order_status": "status", "order_created_at": "created_at"})

    agg_funnel_monthly = (
        events.assign(year_month=events["created_at"].dt.to_period("M").astype(str))
        .groupby(["year_month", "event_type", "traffic_source"], as_index=False)
        .agg(event_count=("id", "count"), unique_users=("user_id", "nunique"))
    )

    fact_inventory = inventory_clean[
        [
            "id",
            "product_id",
            "product_name",
            "product_brand",
            "product_category",
            "product_department",
            "product_distribution_center_id",
            "cost",
            "is_sold",
            "holding_days",
            "sunk_cost_risk",
            "holding_cost_estimate",
        ]
    ].rename(
        columns={
            "id": "inventory_id",
            "product_department": "department",
            "product_distribution_center_id": "center_id",
        }
    )

    dim_users = users.rename(columns={"id": "user_id"}).merge(rfm, on="user_id", how="left")
    dim_users["Frequency"] = dim_users["Frequency"].fillna(0).astype("int64")
    dim_users["Monetary"] = dim_users["Monetary"].fillna(0.0)
    dim_users["return_rate_pct"] = dim_users["return_rate_pct"].fillna(0.0)
    dim_users["rfm_segment"] = dim_users["rfm_segment"].fillna("No Purchase / No Valid Purchase")
    dim_users = dim_users[
        [
            "user_id",
            "first_name",
            "last_name",
            "age",
            "gender",
            "state",
            "street_address",
            "postal_code",
            "city",
            "country",
            "latitude",
            "longitude",
            "traffic_source",
            "Recency",
            "Frequency",
            "Monetary",
            "return_rate_pct",
            "rfm_segment",
        ]
    ]

    dim_products = products[["id", "category", "brand", "retail_price", "cost", "department"]].rename(
        columns={"id": "product_id"}
    )

    dim_dcs = dcs[["id", "name", "latitude", "longitude"]].rename(columns={"id": "dc_id"})

    date_range = pd.date_range("2019-01-01", "2024-01-17", freq="D")
    dim_date = pd.DataFrame(
        {
            "date_key": date_range.strftime("%Y%m%d").astype(int),
            "date": date_range,
            "year": date_range.year,
            "month": date_range.month,
            "quarter": date_range.quarter,
            "day_of_week": date_range.dayofweek,
            "week_of_year": date_range.isocalendar().week.astype(int),
            "year_month": date_range.strftime("%Y-%m"),
        }
    )

    return PipelineArtifacts(
        fact_transactions=fact_transactions,
        agg_funnel_monthly=agg_funnel_monthly,
        fact_inventory=fact_inventory,
        dim_users=dim_users,
        dim_products=dim_products,
        dim_dcs=dim_dcs,
        dim_date=dim_date,
    )


def save_artifacts(artifacts: PipelineArtifacts, processed_dir: Path) -> dict[str, int]:
    processed_dir.mkdir(parents=True, exist_ok=True)

    mapping = {
        "fact_transactions.parquet": artifacts.fact_transactions,
        "agg_funnel_monthly.parquet": artifacts.agg_funnel_monthly,
        "fact_inventory.parquet": artifacts.fact_inventory,
        "dim_users.parquet": artifacts.dim_users,
        "dim_products.parquet": artifacts.dim_products,
        "dim_dcs.parquet": artifacts.dim_dcs,
        "dim_date.parquet": artifacts.dim_date,
    }

    row_counts: dict[str, int] = {}
    for file_name, df in mapping.items():
        csv_name = f"{Path(file_name).stem}.csv"
        df.to_csv(processed_dir / csv_name, index=False)
        try:
            df.to_parquet(processed_dir / file_name, index=False)
            row_counts[file_name] = int(len(df))
        except (ImportError, ModuleNotFoundError, ValueError) as exc:
            row_counts[csv_name] = int(len(df))
            row_counts[f"{Path(file_name).stem}_parquet_error"] = str(exc)

    return row_counts


def run_pipeline(project_root: Path, dataset_root: Path | None = None) -> dict[str, object]:
    base_dir = dataset_root if dataset_root is not None else project_root / "data"
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"
    report_dir = base_dir / "interim"
    report_dir.mkdir(parents=True, exist_ok=True)

    tables = load_raw_tables(raw_dir)
    table_profile = profile_tables(tables)

    _orders_clean, orders_analysis, date_validation = clean_orders(tables["orders"])
    order_items_clean, order_item_quality = clean_order_items(tables["order_items"], tables["products"])
    order_items_revenue = order_items_clean.loc[~order_items_clean["exclude_from_revenue"]].copy()
    inventory_clean = clean_inventory(tables["inventory"])
    cleaned_users, users_validation = clean_users(tables["users"])
    product_validation = validate_products(tables["products"])
    dcs_validation = validate_dcs(tables["dcs"])
    events_validation = validate_events(tables["events"], cleaned_users)
    foreign_key_validation = validate_foreign_keys(tables)
    bot_candidates = detect_bot_candidates(tables["events"])
    rfm = create_rfm(orders_analysis, order_items_revenue)

    artifacts = build_model_tables(
        orders_analysis=orders_analysis,
        order_items_clean=order_items_revenue,
        inventory_clean=inventory_clean,
        events=tables["events"],
        users=cleaned_users,
        products=tables["products"],
        dcs=tables["dcs"],
        rfm=rfm,
    )

    row_counts = save_artifacts(artifacts, processed_dir)
    scope_reconciliation = reconcile_processed_scope(
        tables["orders"], tables["order_items"], order_items_revenue, artifacts
    )
    issue_samples = create_issue_samples(tables, order_items_clean)
    samples_dir = report_dir / "quality_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    sample_row_counts: dict[str, int] = {}
    for sample_name, sample_df in issue_samples.items():
        sample_path = samples_dir / f"{sample_name}.csv"
        sample_df.to_csv(sample_path, index=False)
        sample_row_counts[sample_name] = int(len(sample_df))

    report = {
        "table_profile": table_profile,
        "date_validation": date_validation,
        "order_status_validation": validate_orders(tables["orders"]),
        "users_validation": users_validation,
        "products_validation": product_validation,
        "dcs_validation": dcs_validation,
        "events_validation": events_validation,
        "foreign_key_validation": foreign_key_validation,
        "order_item_quality": order_item_quality,
        "scope_reconciliation": scope_reconciliation,
        "excluded_revenue_item_rows": int(order_item_quality["sale_price_lt_1"] + order_item_quality["sale_price_eq_0"]),
        "bot_candidate_rows": int(len(bot_candidates)),
        "sample_row_counts": sample_row_counts,
        "rfm_users": int(len(rfm)),
        "recognized_revenue_statuses": sorted(RECOGNIZED_REVENUE_STATUSES),
        "dataset_root": str(base_dir),
        "processed_row_counts": row_counts,
    }

    (report_dir / "phase1_quality_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    validation_rows = []
    for section, values in report.items():
        if isinstance(values, dict):
            for key, value in values.items():
                if isinstance(value, (int, float, str, bool)):
                    validation_rows.append({"section": section, "check": key, "value": value})
                elif isinstance(value, dict):
                    for child_key, child_value in value.items():
                        if isinstance(child_value, (int, float, str, bool)):
                            validation_rows.append(
                                {"section": section, "check": f"{key}.{child_key}", "value": child_value}
                            )
    pd.DataFrame(validation_rows).to_csv(report_dir / "phase1_validation_summary.csv", index=False)
    bot_candidates.to_csv(report_dir / "bot_candidates.csv", index=False)

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DATAVISION Phase 1 ETL pipeline")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to DATAVISION2026_ET_CLUB root folder",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help="Path to the dataset folder containing raw/, processed/, and interim/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_pipeline(args.project_root, dataset_root=args.dataset_root)
    print("Phase 1 ETL completed. Row counts:")
    for name, count in report["processed_row_counts"].items():
        print(f"- {name}: {count}")
    print(f"Bot candidate rows: {report['bot_candidate_rows']}")
    print(f"Quality summary saved under {report['dataset_root']}/interim")


if __name__ == "__main__":
    main()
