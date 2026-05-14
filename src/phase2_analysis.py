from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

RECOGNIZED_REVENUE_STATUSES = {"Complete", "Shipped"}
NO_PURCHASE_SEGMENT = "No Purchase / No Valid Purchase"
PRICE_BINS = [0, 25, 50, 100, 200, np.inf]
PRICE_LABELS = ["<$25", "$25-50", "$50-100", "$100-200", "$200+"]


def _read_processed_table(processed_dir: Path, table_name: str) -> pd.DataFrame:
    """Prefer CSV companions so local reruns and Parquet stay easy to compare."""
    csv_path = processed_dir / f"{table_name}.csv"
    parquet_path = processed_dir / f"{table_name}.parquet"
    if csv_path.exists():
        return pd.read_csv(csv_path, low_memory=False)
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    raise FileNotFoundError(f"Missing processed table: {table_name} in {processed_dir}")


def _load_raw_events(raw_dir: Path | None) -> pd.DataFrame | None:
    if raw_dir is None:
        return None
    path = raw_dir / "events.csv"
    if not path.exists():
        return None
    return pd.read_csv(
        path,
        usecols=["id", "user_id", "session_id", "event_type", "traffic_source", "created_at"],
    )


def _load_raw_orders(raw_dir: Path | None) -> pd.DataFrame | None:
    if raw_dir is None:
        return None
    path = raw_dir / "orders.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def _ensure_revenue_columns(fact_transactions: pd.DataFrame) -> pd.DataFrame:
    fact = fact_transactions.copy()
    fact["status"] = fact["status"].astype(str)
    if "is_recognized_revenue" not in fact.columns:
        fact["is_recognized_revenue"] = fact["status"].isin(RECOGNIZED_REVENUE_STATUSES).astype("int8")
    if "is_gmv" not in fact.columns:
        fact["is_gmv"] = (fact["sale_price"] >= 1).astype("int8")
    metric_defaults = {
        "GMV_All_Status": fact["sale_price"],
        "Recognized_Revenue": fact["sale_price"].where(fact["is_recognized_revenue"].eq(1), 0.0),
        "Recognized_Gross_Profit": fact["gross_profit"].where(fact["is_recognized_revenue"].eq(1), 0.0),
        "Revenue_Lost_Cancelled": fact["sale_price"].where(fact["status"].eq("Cancelled"), 0.0),
        "Return_Value": fact["sale_price"].where(fact["status"].eq("Returned"), 0.0),
        "Processing_Backlog_Value": fact["sale_price"].where(fact["status"].eq("Processing"), 0.0),
    }
    for column, values in metric_defaults.items():
        if column not in fact.columns:
            fact[column] = values
    fact["date_key"] = fact["date_key"].astype(str)
    fact["year"] = fact["date_key"].str[:4].astype(int)
    return fact


def _add_price_band(frame: pd.DataFrame, price_col: str = "sale_price") -> pd.DataFrame:
    output = frame.copy()
    output["price_band"] = pd.cut(
        output[price_col].astype(float),
        bins=PRICE_BINS,
        labels=PRICE_LABELS,
        include_lowest=True,
        right=False,
    ).astype(str)
    return output


def _safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.replace(0, np.nan) * 100).round(1)


def load_processed_data(processed_dir: Path, raw_dir: Path | None = None) -> dict[str, pd.DataFrame | None]:
    fact_transactions = _ensure_revenue_columns(_read_processed_table(processed_dir, "fact_transactions"))
    fact_inventory = _read_processed_table(processed_dir, "fact_inventory")
    agg_funnel_monthly = _read_processed_table(processed_dir, "agg_funnel_monthly")
    dim_users = _read_processed_table(processed_dir, "dim_users")
    dim_products = _read_processed_table(processed_dir, "dim_products")
    dim_dcs = _read_processed_table(processed_dir, "dim_dcs")
    dim_date = _read_processed_table(processed_dir, "dim_date")

    if "rfm_segment" in dim_users.columns:
        dim_users["rfm_segment"] = dim_users["rfm_segment"].fillna(NO_PURCHASE_SEGMENT)
    if "Frequency" in dim_users.columns:
        dim_users["Frequency"] = dim_users["Frequency"].fillna(0)
    if "Monetary" in dim_users.columns:
        dim_users["Monetary"] = dim_users["Monetary"].fillna(0.0)
    if "return_rate_pct" in dim_users.columns:
        dim_users["return_rate_pct"] = dim_users["return_rate_pct"].fillna(0.0)

    return {
        "fact_transactions": fact_transactions,
        "fact_inventory": fact_inventory,
        "agg_funnel_monthly": agg_funnel_monthly,
        "dim_users": dim_users,
        "dim_products": dim_products,
        "dim_dcs": dim_dcs,
        "dim_date": dim_date,
        "raw_events": _load_raw_events(raw_dir),
        "raw_orders": _load_raw_orders(raw_dir),
    }


def analyze_rfm_segmentation(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    dim_users = data["dim_users"].copy()
    dim_users["rfm_segment"] = dim_users["rfm_segment"].fillna(NO_PURCHASE_SEGMENT)
    segment_dist = dim_users["rfm_segment"].value_counts(dropna=False).reset_index()
    segment_dist.columns = ["segment", "count"]
    segment_dist["percentage"] = (segment_dist["count"] / len(dim_users) * 100).round(1)
    segment_dist.to_csv(processed_dir / "rfm_segment_analysis.csv", index=False)
    return segment_dist


def analyze_cohort_retention(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    valid = fact.loc[fact["is_recognized_revenue"].eq(1), ["user_id", "year"]].drop_duplicates()
    first_year = valid.groupby("user_id", as_index=False)["year"].min().rename(columns={"year": "cohort_year"})
    cohort = valid.merge(first_year, on="user_id", how="inner")
    counts = cohort.groupby(["cohort_year", "year"])["user_id"].nunique().unstack(fill_value=0).sort_index()

    cohort_sizes = pd.Series({year: counts.loc[year, year] for year in counts.index}, dtype=float)
    retention = counts.div(cohort_sizes.replace(0, np.nan), axis=0).mul(100).round(2)
    retention = retention.replace([np.inf, -np.inf], np.nan)
    retention.reset_index().to_csv(processed_dir / "cohort_retention_analysis.csv", index=False)
    return retention


def analyze_ltv_cac(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    dim_users = data["dim_users"]
    valid_customers = dim_users.loc[dim_users["Frequency"].fillna(0).gt(0)].copy()
    no_valid_purchase_pct = (1 - len(valid_customers) / len(dim_users)) * 100
    one_time = valid_customers.loc[valid_customers["Frequency"].eq(1)]

    cac = 40.0
    ltv_one_time_gp = one_time["Monetary"].mean() if len(one_time) else 0.0
    ltv_all_gp = valid_customers["Monetary"].mean() if len(valid_customers) else 0.0
    ltv_cac_ratio = ltv_one_time_gp / cac if cac else np.nan

    ltv_analysis = pd.DataFrame(
        {
            "metric": [
                "No Valid Purchase Users %",
                "One-time Buyers % (valid customers)",
                "Gross Profit LTV (1-time buyers)",
                "Gross Profit LTV (all valid customers)",
                "CAC Assumption",
                "LTV:CAC Ratio",
                "Healthy Benchmark",
            ],
            "value": [
                f"{no_valid_purchase_pct:.1f}%",
                f"{(len(one_time) / len(valid_customers) * 100) if len(valid_customers) else 0:.1f}%",
                f"${ltv_one_time_gp:.2f}",
                f"${ltv_all_gp:.2f}",
                f"${cac:.2f}",
                f"{ltv_cac_ratio:.1f}:1",
                "3:1",
            ],
        }
    )
    ltv_analysis.to_csv(processed_dir / "ltv_cac_analysis.csv", index=False)
    return ltv_analysis


def analyze_status_leakage(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    status = fact.groupby(["year", "status"], as_index=False).agg(
        items=("order_item_id", "count"),
        orders=("order_id", "nunique"),
        value=("sale_price", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    year_total = status.groupby("year")["value"].transform("sum")
    status["share_of_gmv_pct"] = (status["value"] / year_total * 100).round(2)
    status["is_recognized_revenue"] = status["status"].isin(RECOGNIZED_REVENUE_STATUSES)
    status.to_csv(processed_dir / "status_leakage_analysis.csv", index=False)
    return status


def analyze_annual_revenue(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    recognized = fact.loc[fact["is_recognized_revenue"].eq(1)]
    orders_by_year = recognized.groupby("year")["order_id"].nunique()

    annual = fact.groupby("year", as_index=False).agg(
        gmv_all_status=("GMV_All_Status", "sum"),
        revenue=("Recognized_Revenue", "sum"),
        gross_profit=("Recognized_Gross_Profit", "sum"),
        num_items=("is_recognized_revenue", "sum"),
        total_items=("order_item_id", "count"),
        returns=("is_returned", "sum"),
        return_value=("Return_Value", "sum"),
        cancelled_value=("Revenue_Lost_Cancelled", "sum"),
        processing_backlog_value=("Processing_Backlog_Value", "sum"),
    )
    annual["num_orders"] = annual["year"].map(orders_by_year).fillna(0).astype(int)
    annual["aov"] = annual["revenue"] / annual["num_orders"].replace(0, np.nan)
    annual["gross_margin_pct"] = (annual["gross_profit"] / annual["revenue"] * 100).round(1)
    annual["return_rate_pct"] = (annual["returns"] / annual["total_items"].replace(0, np.nan) * 100).round(1)
    annual["status_leakage_value"] = annual["gmv_all_status"] - annual["revenue"]
    annual["status_leakage_pct"] = (annual["status_leakage_value"] / annual["gmv_all_status"] * 100).round(1)
    annual["yoy_growth_pct"] = annual["revenue"].pct_change() * 100
    annual = annual.loc[annual["year"].le(2023)].copy()
    annual.to_csv(processed_dir / "annual_revenue_analysis.csv", index=False)
    return annual


def analyze_category_performance(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    products = data["dim_products"][["product_id", "category"]].drop_duplicates()
    category_data = fact.merge(products, on="product_id", how="left")
    category = category_data.groupby("category", as_index=False).agg(
        gmv_all_status=("GMV_All_Status", "sum"),
        revenue=("Recognized_Revenue", "sum"),
        gross_profit=("Recognized_Gross_Profit", "sum"),
        num_items=("is_recognized_revenue", "sum"),
        total_items=("order_item_id", "count"),
        returns=("is_returned", "sum"),
        return_value=("Return_Value", "sum"),
        cancelled_value=("Revenue_Lost_Cancelled", "sum"),
        processing_backlog_value=("Processing_Backlog_Value", "sum"),
    )
    category["cancelled_returned_leakage"] = category["cancelled_value"] + category["return_value"]
    category["status_leakage_value"] = category["gmv_all_status"] - category["revenue"]
    category["status_leakage_pct"] = (category["status_leakage_value"] / category["gmv_all_status"] * 100).round(1)
    category["gross_margin_pct"] = (category["gross_profit"] / category["revenue"] * 100).round(1)
    category["return_rate_pct"] = (category["returns"] / category["total_items"].replace(0, np.nan) * 100).round(1)

    median_rev = category["revenue"].median()
    median_margin = category["gross_margin_pct"].median()

    def assign_quadrant(row: pd.Series) -> str:
        if row["revenue"] > median_rev and row["gross_margin_pct"] > median_margin:
            return "Star"
        if row["revenue"] > median_rev and row["gross_margin_pct"] <= median_margin:
            return "Cash Cow"
        if row["revenue"] <= median_rev and row["gross_margin_pct"] > median_margin:
            return "Problem Child"
        return "Dog"

    category["quadrant"] = category.apply(assign_quadrant, axis=1)
    category.to_csv(processed_dir / "category_performance_analysis.csv", index=False)
    return category


def analyze_return_costs(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    total_items = int(len(fact))
    returned_items = int(fact["is_returned"].sum())
    cost_per_return = 20
    total_return_cost = returned_items * cost_per_return
    return_analysis = pd.DataFrame(
        {
            "metric": [
                "Total GMV Items",
                "Total Returned Items",
                "Return Rate % (all-status items)",
                "Return Value",
                "Cost per Return",
                "Total Return Cost (2019-2023)",
                "Annual Return Cost Estimate",
            ],
            "value": [
                f"{total_items:,}",
                f"{returned_items:,}",
                f"{returned_items / total_items * 100:.1f}%",
                f"${fact['Return_Value'].sum():,.0f}",
                f"${cost_per_return:.0f}",
                f"${total_return_cost:,.0f}",
                f"${total_return_cost / 5:,.0f}",
            ],
        }
    )
    return_analysis.to_csv(processed_dir / "return_cost_analysis.csv", index=False)
    return return_analysis


def analyze_funnel(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    raw_events = data["raw_events"]
    if raw_events is not None:
        events = raw_events.copy()
        event_summary = events.groupby("event_type").agg(
            event_count=("id", "count"),
            sessions=("session_id", "nunique"),
            global_unique_users=("user_id", "nunique"),
        )
    else:
        agg = data["agg_funnel_monthly"]
        event_summary = agg.groupby("event_type").agg(event_count=("event_count", "sum"), global_unique_users=("unique_users", "sum"))
        event_summary["sessions"] = np.nan

    stages = ["product", "cart", "purchase", "cancel"]
    rows: list[dict[str, object]] = []
    previous_event = previous_session = previous_user = None
    for stage in stages:
        values = event_summary.loc[stage] if stage in event_summary.index else pd.Series(dtype=float)
        event_count = int(values.get("event_count", 0))
        sessions = values.get("sessions", np.nan)
        users = values.get("global_unique_users", np.nan)
        rows.append(
            {
                "stage": stage,
                "event_count": event_count,
                "sessions": sessions,
                "global_unique_users": users,
                "event_conversion_from_prev_pct": 100.0 if previous_event is None else event_count / previous_event * 100 if previous_event else np.nan,
                "session_conversion_from_prev_pct": 100.0 if previous_session is None else sessions / previous_session * 100 if previous_session else np.nan,
                "user_conversion_from_prev_pct": 100.0 if previous_user is None else users / previous_user * 100 if previous_user else np.nan,
            }
        )
        previous_event, previous_session, previous_user = event_count, sessions, users

    funnel = pd.DataFrame(rows)
    funnel.to_csv(processed_dir / "funnel_analysis.csv", index=False)
    return funnel


def analyze_journey_funnel_by_source(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    raw_events = data["raw_events"]
    stages = ["home", "department", "product", "cart", "purchase", "cancel"]
    if raw_events is not None:
        events = raw_events.copy()
        grouped = events.groupby(["traffic_source", "event_type"], as_index=False).agg(
            event_count=("id", "count"),
            sessions=("session_id", "nunique"),
            unique_users=("user_id", "nunique"),
        )
        source_totals = events.groupby("traffic_source", as_index=False).agg(
            source_event_count=("id", "count"),
            source_sessions=("session_id", "nunique"),
            source_unique_users=("user_id", "nunique"),
        )
    else:
        grouped = data["agg_funnel_monthly"].groupby(["traffic_source", "event_type"], as_index=False).agg(
            event_count=("event_count", "sum"),
            unique_users=("unique_users", "sum"),
        )
        grouped["sessions"] = np.nan
        source_totals = grouped.groupby("traffic_source", as_index=False).agg(
            source_event_count=("event_count", "sum"),
            source_sessions=("sessions", "max"),
            source_unique_users=("unique_users", "sum"),
        )

    complete_index = pd.MultiIndex.from_product(
        [sorted(grouped["traffic_source"].dropna().unique()), stages],
        names=["traffic_source", "event_type"],
    )
    journey = (
        grouped.set_index(["traffic_source", "event_type"])
        .reindex(complete_index, fill_value=0)
        .reset_index()
        .merge(source_totals, on="traffic_source", how="left")
    )
    stage_order = {stage: index + 1 for index, stage in enumerate(stages)}
    journey["stage_order"] = journey["event_type"].map(stage_order)
    journey = journey.sort_values(["traffic_source", "stage_order"]).reset_index(drop=True)
    journey["event_share_within_source_pct"] = _safe_pct(journey["event_count"], journey["source_event_count"])
    journey["session_reach_within_source_pct"] = _safe_pct(journey["sessions"], journey["source_sessions"])
    journey["user_reach_within_source_pct"] = _safe_pct(journey["unique_users"], journey["source_unique_users"])

    purchase_sessions = (
        journey.loc[journey["event_type"].eq("purchase"), ["traffic_source", "sessions"]]
        .rename(columns={"sessions": "purchase_sessions"})
    )
    product_sessions = (
        journey.loc[journey["event_type"].eq("product"), ["traffic_source", "sessions"]]
        .rename(columns={"sessions": "product_sessions"})
    )
    cart_sessions = (
        journey.loc[journey["event_type"].eq("cart"), ["traffic_source", "sessions"]]
        .rename(columns={"sessions": "cart_sessions"})
    )
    source_rates = product_sessions.merge(cart_sessions, on="traffic_source", how="outer").merge(
        purchase_sessions, on="traffic_source", how="outer"
    )
    source_rates["product_to_purchase_session_cvr_pct"] = _safe_pct(
        source_rates["purchase_sessions"], source_rates["product_sessions"]
    )
    source_rates["product_to_cart_session_cvr_pct"] = _safe_pct(
        source_rates["cart_sessions"], source_rates["product_sessions"]
    )
    source_rates["cart_to_purchase_session_cvr_pct"] = _safe_pct(
        source_rates["purchase_sessions"], source_rates["cart_sessions"]
    )
    journey = journey.merge(
        source_rates[
            [
                "traffic_source",
                "product_to_cart_session_cvr_pct",
                "product_to_purchase_session_cvr_pct",
                "cart_to_purchase_session_cvr_pct",
            ]
        ],
        on="traffic_source",
        how="left",
    )
    journey.to_csv(processed_dir / "journey_funnel_by_source.csv", index=False)
    return journey


def analyze_traffic_source_performance(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    raw_events = data["raw_events"]
    if raw_events is not None:
        purchases = raw_events.loc[raw_events["event_type"].eq("purchase")].copy()
        source = purchases.groupby("traffic_source", as_index=False).agg(
            purchase_events=("id", "count"),
            global_unique_users=("user_id", "nunique"),
            sessions=("session_id", "nunique"),
        )
    else:
        purchases = data["agg_funnel_monthly"].loc[data["agg_funnel_monthly"]["event_type"].eq("purchase")]
        source = purchases.groupby("traffic_source", as_index=False).agg(
            purchase_events=("event_count", "sum"),
            global_unique_users=("unique_users", "sum"),
        )
        source["sessions"] = np.nan

    source["purchase_events_per_global_user"] = (
        source["purchase_events"] / source["global_unique_users"].replace(0, np.nan)
    ).round(2)
    source = source.sort_values("purchase_events", ascending=False)
    source.to_csv(processed_dir / "traffic_source_performance.csv", index=False)
    legacy_path = processed_dir / "traffic_source_roi.csv"
    if legacy_path.exists():
        legacy_path.unlink()
    return source


def analyze_basket_affinity(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = data["fact_transactions"]
    products = data["dim_products"][["product_id", "category"]].drop_duplicates()
    recognized = fact.loc[fact["is_recognized_revenue"].eq(1), ["order_id", "user_id", "product_id", "Recognized_Revenue"]]
    order_categories = recognized.merge(products, on="product_id", how="left").dropna(subset=["category"])

    total_orders = max(order_categories["order_id"].nunique(), 1)
    category_orders = order_categories.groupby("category")["order_id"].nunique().to_dict()

    pair_rows: list[dict[str, object]] = []
    for order_id, order_frame in order_categories.groupby("order_id"):
        categories = sorted(order_frame["category"].dropna().unique())
        if len(categories) < 2:
            continue
        revenue = float(order_frame["Recognized_Revenue"].sum())
        user_id = order_frame["user_id"].iloc[0]
        for category_a, category_b in combinations(categories, 2):
            pair_rows.append(
                {
                    "category_a": category_a,
                    "category_b": category_b,
                    "order_id": order_id,
                    "user_id": user_id,
                    "pair_order_revenue": revenue,
                }
            )

    if not pair_rows:
        affinity = pd.DataFrame(
            columns=[
                "category_a",
                "category_b",
                "orders_with_pair",
                "users_with_pair",
                "pair_revenue",
                "support_pct",
                "confidence_a_to_b_pct",
                "confidence_b_to_a_pct",
                "lift",
                "bundle_action",
            ]
        )
    else:
        pairs = pd.DataFrame(pair_rows)
        affinity = pairs.groupby(["category_a", "category_b"], as_index=False).agg(
            orders_with_pair=("order_id", "nunique"),
            users_with_pair=("user_id", "nunique"),
            pair_revenue=("pair_order_revenue", "sum"),
        )
        affinity["support_pct"] = (affinity["orders_with_pair"] / total_orders * 100).round(3)
        affinity["category_a_orders"] = affinity["category_a"].map(category_orders).fillna(0)
        affinity["category_b_orders"] = affinity["category_b"].map(category_orders).fillna(0)
        affinity["confidence_a_to_b_pct"] = _safe_pct(affinity["orders_with_pair"], affinity["category_a_orders"])
        affinity["confidence_b_to_a_pct"] = _safe_pct(affinity["orders_with_pair"], affinity["category_b_orders"])
        expected_support = (
            (affinity["category_a_orders"] / total_orders)
            * (affinity["category_b_orders"] / total_orders)
        ).replace(0, np.nan)
        actual_support = affinity["orders_with_pair"] / total_orders
        affinity["lift"] = (actual_support / expected_support).round(2)
        affinity["bundle_action"] = np.select(
            [
                affinity["lift"].ge(1.5) & affinity["orders_with_pair"].ge(50),
                affinity["confidence_a_to_b_pct"].ge(15) | affinity["confidence_b_to_a_pct"].ge(15),
            ],
            [
                "Bundle/cross-sell priority",
                "Recommendation module candidate",
            ],
            default="Monitor",
        )
        affinity = affinity.sort_values(["lift", "orders_with_pair"], ascending=[False, False])

    affinity.to_csv(processed_dir / "basket_affinity_analysis.csv", index=False)
    return affinity


def analyze_price_band_performance(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    fact = _add_price_band(data["fact_transactions"])
    products = data["dim_products"][["product_id", "category", "department"]].drop_duplicates()
    enriched = fact.merge(products, on="product_id", how="left")
    price_band = enriched.groupby(["department", "category", "price_band"], as_index=False, observed=True).agg(
        gmv_all_status=("GMV_All_Status", "sum"),
        revenue=("Recognized_Revenue", "sum"),
        gross_profit=("Recognized_Gross_Profit", "sum"),
        total_items=("order_item_id", "count"),
        recognized_items=("is_recognized_revenue", "sum"),
        returned_items=("is_returned", "sum"),
        cancelled_value=("Revenue_Lost_Cancelled", "sum"),
        return_value=("Return_Value", "sum"),
        processing_backlog_value=("Processing_Backlog_Value", "sum"),
        avg_sale_price=("sale_price", "mean"),
    )
    price_band["status_leakage_value"] = price_band["gmv_all_status"] - price_band["revenue"]
    price_band["gross_margin_pct"] = _safe_pct(price_band["gross_profit"], price_band["revenue"])
    price_band["return_rate_pct"] = _safe_pct(price_band["returned_items"], price_band["total_items"])
    price_band["status_leakage_pct"] = _safe_pct(price_band["status_leakage_value"], price_band["gmv_all_status"])
    price_band["cancel_value_share_pct"] = _safe_pct(price_band["cancelled_value"], price_band["gmv_all_status"])
    price_band["price_band_action"] = np.select(
        [
            price_band["return_rate_pct"].ge(11),
            price_band["cancel_value_share_pct"].ge(16),
            price_band["gross_margin_pct"].lt(45) & price_band["revenue"].gt(price_band["revenue"].median()),
            price_band["status_leakage_pct"].ge(47),
        ],
        [
            "Improve fit/size confidence",
            "Diagnose cancellation friction",
            "Review pricing or supplier cost",
            "Leakage reduction priority",
        ],
        default="Maintain / monitor",
    )
    price_band = price_band.sort_values(["revenue", "status_leakage_value"], ascending=False)
    price_band.to_csv(processed_dir / "price_band_performance.csv", index=False)
    return price_band


def analyze_inventory_turnover(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    inv = data["fact_inventory"]
    total_items = len(inv)
    sold_items = int(inv["is_sold"].sum())
    unsold_items = total_items - sold_items
    sell_through = sold_items / total_items * 100
    unsold = inv.loc[inv["is_sold"].eq(0)]
    inventory_analysis = pd.DataFrame(
        {
            "metric": [
                "Total Inventory Units",
                "Sold Units",
                "Unsold Units",
                "Sell-Through Rate",
                "Avg Holding Days (Unsold)",
                "Max Holding Days",
            ],
            "value": [
                f"{total_items:,}",
                f"{sold_items:,}",
                f"{unsold_items:,}",
                f"{sell_through:.1f}%",
                f"{unsold['holding_days'].mean():.0f}",
                f"{unsold['holding_days'].max():.0f}",
            ],
        }
    )
    inventory_analysis.to_csv(processed_dir / "inventory_turnover_analysis.csv", index=False)
    return inventory_analysis


def analyze_holding_cost(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    inv = data["fact_inventory"]
    unsold = inv.loc[inv["is_sold"].eq(0)].copy()
    total_frozen = unsold["sunk_cost_risk"].sum()
    total_holding_cost = unsold["holding_cost_estimate"].sum()
    holding_analysis = pd.DataFrame(
        {
            "metric": [
                "Total Unsold Units",
                "Total Frozen Capital",
                "Est. Holding Cost To Cutoff",
                "Combined Financial Impact",
                "Avg Cost per Unit (Frozen)",
                "Avg Holding Days",
            ],
            "value": [
                f"{len(unsold):,}",
                f"${total_frozen:,.0f}",
                f"${total_holding_cost:,.0f}",
                f"${total_frozen + total_holding_cost:,.0f}",
                f"${total_frozen / len(unsold):.0f}",
                f"{unsold['holding_days'].mean():.0f}",
            ],
        }
    )
    holding_analysis.to_csv(processed_dir / "holding_cost_analysis.csv", index=False)
    return holding_analysis


def analyze_inventory_abc_aging_by_category_dc(
    data: dict[str, pd.DataFrame | None], processed_dir: Path
) -> pd.DataFrame:
    inv = data["fact_inventory"].copy()
    dcs = data["dim_dcs"][["dc_id", "name"]].rename(columns={"dc_id": "center_id", "name": "dc_name"})
    category_perf = analyze_category_performance(data, processed_dir).rename(
        columns={
            "category": "product_category",
            "revenue": "category_revenue",
            "gross_profit": "category_gross_profit",
            "quadrant": "category_quadrant",
        }
    )[
        [
            "product_category",
            "category_revenue",
            "category_gross_profit",
            "gross_margin_pct",
            "status_leakage_value",
            "category_quadrant",
        ]
    ]

    category_rank = category_perf.sort_values("category_revenue", ascending=False).copy()
    total_revenue = category_rank["category_revenue"].sum()
    category_rank["category_revenue_share_pct"] = (
        category_rank["category_revenue"] / total_revenue * 100 if total_revenue else 0
    )
    category_rank["category_cumulative_revenue_share_pct"] = category_rank["category_revenue_share_pct"].cumsum()
    category_rank["abc_class"] = np.select(
        [
            category_rank["category_cumulative_revenue_share_pct"].le(80),
            category_rank["category_cumulative_revenue_share_pct"].le(95),
        ],
        ["A", "B"],
        default="C",
    )

    inv["aged_180_cost"] = inv["sunk_cost_risk"].where(inv["holding_days"].ge(180), 0.0)
    inv["aged_365_cost"] = inv["sunk_cost_risk"].where(inv["holding_days"].ge(365), 0.0)
    inv["aged_180_units"] = (inv["is_sold"].eq(0) & inv["holding_days"].ge(180)).astype(int)
    inv["aged_365_units"] = (inv["is_sold"].eq(0) & inv["holding_days"].ge(365)).astype(int)

    inventory_abc = inv.groupby(["product_category", "department", "center_id"], as_index=False).agg(
        total_units=("inventory_id", "count"),
        sold_units=("is_sold", "sum"),
        unsold_units=("sunk_cost_risk", lambda values: int((values > 0).sum())),
        frozen_capital=("sunk_cost_risk", "sum"),
        holding_cost_to_cutoff=("holding_cost_estimate", "sum"),
        avg_holding_days_unsold=("holding_days", lambda values: values[inv.loc[values.index, "is_sold"].eq(0)].mean()),
        aged_180_units=("aged_180_units", "sum"),
        aged_365_units=("aged_365_units", "sum"),
        aged_180_cost=("aged_180_cost", "sum"),
        aged_365_cost=("aged_365_cost", "sum"),
    )
    inventory_abc["sell_through_pct"] = _safe_pct(inventory_abc["sold_units"], inventory_abc["total_units"])
    inventory_abc = (
        inventory_abc.merge(dcs, on="center_id", how="left")
        .merge(category_rank, on="product_category", how="left")
    )
    median_aged_cost = inventory_abc["aged_180_cost"].median()
    inventory_abc["inventory_action"] = np.select(
        [
            inventory_abc["aged_365_cost"].gt(median_aged_cost) & inventory_abc["sell_through_pct"].lt(35),
            inventory_abc["abc_class"].eq("A") & inventory_abc["sell_through_pct"].lt(36),
            inventory_abc["abc_class"].isin(["B", "C"]) & inventory_abc["aged_180_cost"].gt(median_aged_cost),
            inventory_abc["abc_class"].eq("A") & inventory_abc["sell_through_pct"].ge(42),
        ],
        [
            "Clearance / stop-buy",
            "Rebalance allocation by DC",
            "Markdown with margin guardrail",
            "Protect availability / replenish carefully",
        ],
        default="Monitor",
    )
    inventory_abc = inventory_abc.sort_values(["aged_180_cost", "frozen_capital"], ascending=False)
    inventory_abc.to_csv(processed_dir / "inventory_abc_aging_by_category_dc.csv", index=False)
    return inventory_abc


def analyze_fulfillment(data: dict[str, pd.DataFrame | None], processed_dir: Path) -> pd.DataFrame:
    orders = data["raw_orders"]
    if orders is None:
        fulfillment = pd.DataFrame(
            {"metric": ["Fulfillment Data"], "value": ["Raw orders unavailable"]}
        )
    else:
        for column in ["created_at", "shipped_at", "delivered_at"]:
            orders[column] = pd.to_datetime(orders[column], errors="coerce", utc=True).dt.tz_localize(None)
        orders["days_to_ship"] = (orders["shipped_at"] - orders["created_at"]).dt.total_seconds() / 86400
        orders["days_ship_to_deliver"] = (orders["delivered_at"] - orders["shipped_at"]).dt.total_seconds() / 86400
        orders["total_delivery_days"] = (orders["delivered_at"] - orders["created_at"]).dt.total_seconds() / 86400
        fulfillment = pd.DataFrame(
            {
                "metric": [
                    "Avg Days to Ship",
                    "Median Days to Ship",
                    "Avg Days to Deliver after Ship",
                    "Median Days to Deliver after Ship",
                    "Total Avg Delivery Days",
                    "Median Delivery Days",
                ],
                "value": [
                    f"{orders['days_to_ship'].mean():.2f}",
                    f"{orders['days_to_ship'].median():.2f}",
                    f"{orders['days_ship_to_deliver'].mean():.2f}",
                    f"{orders['days_ship_to_deliver'].median():.2f}",
                    f"{orders['total_delivery_days'].mean():.2f}",
                    f"{orders['total_delivery_days'].median():.2f}",
                ],
            }
        )
    fulfillment.to_csv(processed_dir / "fulfillment_performance.csv", index=False)
    return fulfillment


def analyze_return_cancel_root_cause_proxy(
    data: dict[str, pd.DataFrame | None], processed_dir: Path
) -> pd.DataFrame:
    fact = _add_price_band(data["fact_transactions"])
    products = data["dim_products"][["product_id", "category", "brand", "department"]].drop_duplicates()
    enriched = fact.merge(products, on="product_id", how="left")

    orders = data["raw_orders"]
    if orders is not None:
        orders = orders[["order_id", "created_at", "shipped_at", "delivered_at"]].copy()
        for column in ["created_at", "shipped_at", "delivered_at"]:
            orders[column] = pd.to_datetime(orders[column], errors="coerce", utc=True).dt.tz_localize(None)
        orders["fulfillment_days"] = (orders["delivered_at"] - orders["created_at"]).dt.total_seconds() / 86400
        orders["fulfillment_bucket"] = pd.cut(
            orders["fulfillment_days"],
            bins=[-np.inf, 2, 4, 7, np.inf],
            labels=["<=2 days", "3-4 days", "5-7 days", "8+ days"],
        ).astype(str)
        orders.loc[orders["fulfillment_days"].isna(), "fulfillment_bucket"] = "not delivered / open"
        enriched = enriched.merge(
            orders[["order_id", "fulfillment_days", "fulfillment_bucket"]],
            on="order_id",
            how="left",
        )
    else:
        enriched["fulfillment_days"] = np.nan
        enriched["fulfillment_bucket"] = "unknown"

    enriched["is_cancelled"] = enriched["status"].eq("Cancelled").astype(int)
    enriched["is_processing"] = enriched["status"].eq("Processing").astype(int)
    grouped = enriched.groupby(
        ["department", "category", "brand", "price_band", "fulfillment_bucket"],
        as_index=False,
        observed=True,
    ).agg(
        total_items=("order_item_id", "count"),
        recognized_items=("is_recognized_revenue", "sum"),
        returned_items=("is_returned", "sum"),
        cancelled_items=("is_cancelled", "sum"),
        processing_items=("is_processing", "sum"),
        gmv_all_status=("GMV_All_Status", "sum"),
        revenue=("Recognized_Revenue", "sum"),
        return_value=("Return_Value", "sum"),
        cancelled_value=("Revenue_Lost_Cancelled", "sum"),
        processing_backlog_value=("Processing_Backlog_Value", "sum"),
        gross_profit=("Recognized_Gross_Profit", "sum"),
        avg_sale_price=("sale_price", "mean"),
        avg_fulfillment_days=("fulfillment_days", "mean"),
    )
    grouped = grouped.loc[grouped["total_items"].ge(25)].copy()
    grouped["return_rate_pct"] = _safe_pct(grouped["returned_items"], grouped["total_items"])
    grouped["cancel_rate_pct"] = _safe_pct(grouped["cancelled_items"], grouped["total_items"])
    grouped["processing_rate_pct"] = _safe_pct(grouped["processing_items"], grouped["total_items"])
    grouped["status_leakage_value"] = grouped["gmv_all_status"] - grouped["revenue"]
    grouped["status_leakage_pct"] = _safe_pct(grouped["status_leakage_value"], grouped["gmv_all_status"])
    grouped["gross_margin_pct"] = _safe_pct(grouped["gross_profit"], grouped["revenue"])
    grouped["proxy_hypothesis"] = np.select(
        [
            grouped["return_rate_pct"].ge(12) & grouped["price_band"].isin(["$100-200", "$200+"]),
            grouped["return_rate_pct"].ge(12),
            grouped["cancel_rate_pct"].ge(17),
            grouped["processing_rate_pct"].ge(22),
            grouped["fulfillment_bucket"].isin(["5-7 days", "8+ days"]) & grouped["return_rate_pct"].ge(10),
        ],
        [
            "High-price fit/expectation mismatch",
            "Size/fit/content confidence risk",
            "Checkout/payment/inventory cancellation friction",
            "Backlog or status-update SLA risk",
            "Fulfillment-delay experience risk",
        ],
        default="No strong proxy signal",
    )
    grouped["recommended_action"] = np.select(
        [
            grouped["proxy_hypothesis"].eq("High-price fit/expectation mismatch"),
            grouped["proxy_hypothesis"].eq("Size/fit/content confidence risk"),
            grouped["proxy_hypothesis"].eq("Checkout/payment/inventory cancellation friction"),
            grouped["proxy_hypothesis"].eq("Backlog or status-update SLA risk"),
            grouped["proxy_hypothesis"].eq("Fulfillment-delay experience risk"),
        ],
        [
            "Add premium PDP proof, fit notes, review snippets",
            "Improve size guide, product images, material details",
            "Audit stock sync, payment failure, checkout messaging",
            "Create processing aging SLA and exception queue",
            "Surface ETA earlier and monitor late-delivery cohorts",
        ],
        default="Monitor with category dashboard",
    )
    grouped = grouped.sort_values(["status_leakage_value", "return_rate_pct"], ascending=False)
    grouped.to_csv(processed_dir / "return_cancel_root_cause_proxy.csv", index=False)
    return grouped


def run_phase2_analysis(dataset_root: Path) -> None:
    processed_dir = dataset_root / "processed"
    raw_dir = dataset_root / "raw"
    data = load_processed_data(processed_dir, raw_dir=raw_dir)

    analyze_rfm_segmentation(data, processed_dir)
    analyze_cohort_retention(data, processed_dir)
    analyze_ltv_cac(data, processed_dir)
    analyze_status_leakage(data, processed_dir)
    analyze_annual_revenue(data, processed_dir)
    analyze_category_performance(data, processed_dir)
    analyze_return_costs(data, processed_dir)
    analyze_funnel(data, processed_dir)
    analyze_journey_funnel_by_source(data, processed_dir)
    analyze_traffic_source_performance(data, processed_dir)
    analyze_basket_affinity(data, processed_dir)
    analyze_price_band_performance(data, processed_dir)
    analyze_inventory_turnover(data, processed_dir)
    analyze_holding_cost(data, processed_dir)
    analyze_inventory_abc_aging_by_category_dc(data, processed_dir)
    analyze_fulfillment(data, processed_dir)
    analyze_return_cancel_root_cause_proxy(data, processed_dir)

    print("Phase 2 analysis completed with recognized revenue and e-commerce domain metrics.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DATAVISION Phase 2 analysis")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="Path to the dataset folder containing raw/ and processed/.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_phase2_analysis(args.dataset_root)
