from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


RECOGNIZED_STATUSES = {"Complete", "Shipped"}
VALID_PURCHASE_STATUSES = {"Complete", "Shipped", "Processing", "Returned"}


def to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


def find_dataset_root(base: Path) -> Path:
    for path in base.iterdir():
        if path.is_dir() and path.name.startswith("[DATAVISION2026]"):
            raw = path / "raw"
            if raw.exists():
                return path
    raise FileNotFoundError("Could not find [DATAVISION2026] dataset folder with raw/")


def pct(num: float, den: float) -> float:
    if den == 0 or pd.isna(den):
        return 0.0
    return float(num) / float(den)


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def number(value: float) -> str:
    return f"{value:,.0f}"


def md_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "_Không có dữ liệu._"
    table = df.head(max_rows).copy()
    table = table.fillna("")
    columns = [str(col) for col in table.columns]
    rows = [[str(value) for value in row] for row in table.to_numpy()]
    widths = [
        max(len(columns[idx]), *(len(row[idx]) for row in rows)) if rows else len(columns[idx])
        for idx in range(len(columns))
    ]

    def fmt_row(values: list[str]) -> str:
        return "| " + " | ".join(values[idx].ljust(widths[idx]) for idx in range(len(values))) + " |"

    header = fmt_row(columns)
    sep = "| " + " | ".join("-" * width for width in widths) + " |"
    body = [fmt_row(row) for row in rows]
    return "\n".join([header, sep, *body])


def scalarize(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    return value


def load_raw(raw_dir: Path) -> dict[str, pd.DataFrame]:
    print("Loading raw CSV files...")
    users = pd.read_csv(raw_dir / "users.csv")
    products = pd.read_csv(raw_dir / "products.csv")
    orders = pd.read_csv(raw_dir / "orders.csv")
    order_items = pd.read_csv(raw_dir / "order_items.csv")
    inventory = pd.read_csv(raw_dir / "inventory_items.csv")
    dcs = pd.read_csv(raw_dir / "distribution_centers.csv")
    events = pd.read_csv(
        raw_dir / "events.csv",
        usecols=[
            "id",
            "user_id",
            "sequence_number",
            "session_id",
            "created_at",
            "browser",
            "traffic_source",
            "event_type",
        ],
    )

    for col in ["created_at"]:
        users[col] = to_datetime(users[col])
    for col in ["created_at", "returned_at", "shipped_at", "delivered_at"]:
        orders[col] = to_datetime(orders[col])
        order_items[col] = to_datetime(order_items[col])
    for col in ["created_at", "sold_at"]:
        inventory[col] = to_datetime(inventory[col])
    events["created_at"] = to_datetime(events["created_at"])

    return {
        "users": users,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "inventory": inventory,
        "dcs": dcs,
        "events": events,
    }


def profile_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    pk_map = {
        "users": "id",
        "products": "id",
        "orders": "order_id",
        "order_items": "id",
        "inventory": "id",
        "dcs": "id",
        "events": "id",
    }
    for name, df in tables.items():
        pk = pk_map[name]
        null_cells = int(df.isna().sum().sum())
        rows.append(
            {
                "table": name,
                "rows": len(df),
                "cols": df.shape[1],
                "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 1),
                "duplicate_pk": int(df.duplicated(pk).sum()),
                "null_cells": null_cells,
            }
        )
    return pd.DataFrame(rows)


def enrich_transactions(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    products = tables["products"].rename(
        columns={
            "id": "product_id",
            "cost": "product_cost",
            "category": "category",
            "name": "product_name",
            "brand": "brand",
            "retail_price": "retail_price",
            "department": "department",
            "distribution_center_id": "dc_id",
        }
    )
    product_cols = [
        "product_id",
        "product_cost",
        "category",
        "product_name",
        "brand",
        "retail_price",
        "department",
        "dc_id",
    ]
    users = tables["users"][["id", "age", "gender", "country", "city", "traffic_source"]].rename(
        columns={"id": "user_id", "traffic_source": "user_traffic_source"}
    )
    items = tables["order_items"].merge(products[product_cols], on="product_id", how="left")
    items = items.merge(users, on="user_id", how="left")
    items["gross_profit"] = items["sale_price"] - items["product_cost"]
    items["margin"] = items["gross_profit"] / items["sale_price"].replace(0, np.nan)
    items["month"] = items["created_at"].dt.to_period("M").astype(str)
    items["year"] = items["created_at"].dt.year
    items["is_recognized"] = items["status"].isin(RECOGNIZED_STATUSES)
    items["is_valid_purchase"] = items["status"].isin(VALID_PURCHASE_STATUSES)
    items["is_cancelled"] = items["status"].eq("Cancelled")
    items["is_returned"] = items["status"].eq("Returned")
    items["ship_days"] = (items["shipped_at"] - items["created_at"]).dt.total_seconds() / 86400
    items["delivery_days"] = (items["delivered_at"] - items["shipped_at"]).dt.total_seconds() / 86400
    items["fulfillment_days"] = (items["delivered_at"] - items["created_at"]).dt.total_seconds() / 86400
    return items


def quality_checks(tables: dict[str, pd.DataFrame], items: pd.DataFrame) -> dict[str, object]:
    users = tables["users"]
    products = tables["products"]
    orders = tables["orders"]
    inventory = tables["inventory"]
    events = tables["events"]
    order_item_counts = tables["order_items"].groupby("order_id").size()
    order_counts = orders.set_index("order_id")["num_of_item"]
    common_orders = order_counts.index.intersection(order_item_counts.index)
    order_item_mismatch = int((order_counts.loc[common_orders] != order_item_counts.loc[common_orders]).sum())
    return {
        "orphan_item_user_ids": int(~items["user_id"].isin(users["id"]).sum()) if False else int((~items["user_id"].isin(users["id"])).sum()),
        "orphan_item_product_ids": int((~items["product_id"].isin(products["id"])).sum()),
        "orphan_item_order_ids": int((~items["order_id"].isin(orders["order_id"])).sum()),
        "inventory_orphan_product_ids": int((~inventory["product_id"].isin(products["id"])).sum()),
        "events_user_id_null_pct": pct(events["user_id"].isna().sum(), len(events)),
        "event_time_min": events["created_at"].min(),
        "event_time_max": events["created_at"].max(),
        "order_time_min": items["created_at"].min(),
        "order_time_max": items["created_at"].max(),
        "sale_price_lt_1_items": int((items["sale_price"] < 1).sum()),
        "product_cost_gt_retail": int((products["cost"] > products["retail_price"]).sum()),
        "order_item_count_mismatch": order_item_mismatch,
    }


def transaction_metrics(items: pd.DataFrame, orders: pd.DataFrame) -> dict[str, object]:
    status = (
        items.groupby("status")
        .agg(items=("id", "count"), orders=("order_id", "nunique"), gmv=("sale_price", "sum"))
        .reset_index()
        .sort_values("gmv", ascending=False)
    )
    recognized = items[items["is_recognized"]].copy()
    valid = items[items["is_valid_purchase"]].copy()
    returned = items[items["is_returned"]]
    cancelled = items[items["is_cancelled"]]
    metrics = {
        "total_gmv": float(items["sale_price"].sum()),
        "recognized_revenue": float(recognized["sale_price"].sum()),
        "recognized_profit": float(recognized["gross_profit"].sum()),
        "recognized_margin": pct(recognized["gross_profit"].sum(), recognized["sale_price"].sum()),
        "completed_revenue": float(items.loc[items["status"].eq("Complete"), "sale_price"].sum()),
        "open_processing_revenue": float(items.loc[items["status"].eq("Processing"), "sale_price"].sum()),
        "returned_revenue": float(returned["sale_price"].sum()),
        "cancelled_revenue": float(cancelled["sale_price"].sum()),
        "leakage_revenue": float(returned["sale_price"].sum() + cancelled["sale_price"].sum()),
        "leakage_rate": pct(returned["sale_price"].sum() + cancelled["sale_price"].sum(), items["sale_price"].sum()),
        "return_rate_items": pct(returned["id"].count(), valid["id"].count()),
        "cancel_rate_items": pct(cancelled["id"].count(), items["id"].count()),
        "orders": int(orders["order_id"].nunique()),
        "recognized_orders": int(recognized["order_id"].nunique()),
        "items": int(len(items)),
        "avg_order_value": pct(recognized["sale_price"].sum(), recognized["order_id"].nunique()),
        "avg_item_price": float(recognized["sale_price"].mean()),
    }
    return {"metrics": metrics, "status": status}


def customer_analysis(items: pd.DataFrame, users: pd.DataFrame) -> dict[str, object]:
    recognized = items[items["is_recognized"]].copy()
    valid = items[items["is_valid_purchase"]].copy()
    customer_valid = (
        valid.groupby("user_id")
        .agg(
            valid_orders=("order_id", "nunique"),
            valid_items=("id", "count"),
            first_order=("created_at", "min"),
            last_order=("created_at", "max"),
        )
        .reset_index()
    )
    customer_rev = (
        recognized.groupby("user_id")
        .agg(
            recognized_orders=("order_id", "nunique"),
            revenue=("sale_price", "sum"),
            profit=("gross_profit", "sum"),
            last_recognized_order=("created_at", "max"),
        )
        .reset_index()
    )
    cust = users.rename(columns={"id": "user_id"}).merge(customer_valid, on="user_id", how="left")
    cust = cust.merge(customer_rev, on="user_id", how="left")
    for col in ["valid_orders", "valid_items", "recognized_orders", "revenue", "profit"]:
        cust[col] = cust[col].fillna(0)
    max_order_date = items["created_at"].max()
    cust["recency_days"] = (max_order_date - cust["last_order"]).dt.days
    cust["buyer"] = cust["valid_orders"].gt(0)
    cust["recognized_buyer"] = cust["recognized_orders"].gt(0)
    cust["repeat_buyer"] = cust["valid_orders"].ge(2)

    bins = [0, 24, 34, 44, 54, 64, 200]
    labels = ["<=24", "25-34", "35-44", "45-54", "55-64", "65+"]
    cust["age_group"] = pd.cut(cust["age"], bins=bins, labels=labels, right=True, include_lowest=True)

    source = (
        cust.groupby("traffic_source", dropna=False)
        .agg(users=("user_id", "count"), buyers=("buyer", "sum"), revenue=("revenue", "sum"), profit=("profit", "sum"))
        .reset_index()
    )
    source["buyer_rate"] = source["buyers"] / source["users"]
    source["ltv_per_registered_user"] = source["revenue"] / source["users"]
    source["arppu"] = source["revenue"] / source["buyers"].replace(0, np.nan)
    source = source.sort_values("revenue", ascending=False)

    demographics = (
        cust.groupby(["gender", "age_group"], observed=False)
        .agg(users=("user_id", "count"), buyers=("buyer", "sum"), revenue=("revenue", "sum"))
        .reset_index()
    )
    demographics["buyer_rate"] = demographics["buyers"] / demographics["users"]
    demographics = demographics.sort_values("revenue", ascending=False)

    rfm_base = cust[cust["buyer"]].copy()
    rfm_base["segment"] = "One-time low value"
    recent_cut = 90
    stale_cut = 180
    high_value = rfm_base["revenue"].quantile(0.75)
    rfm_base.loc[
        (rfm_base["recency_days"].le(recent_cut))
        & (rfm_base["valid_orders"].ge(2))
        & (rfm_base["revenue"].ge(high_value)),
        "segment",
    ] = "Champions"
    rfm_base.loc[
        (rfm_base["recency_days"].le(stale_cut))
        & (rfm_base["valid_orders"].ge(2))
        & (rfm_base["segment"].eq("One-time low value")),
        "segment",
    ] = "Loyal/active repeat"
    rfm_base.loc[
        (rfm_base["recency_days"].gt(stale_cut))
        & (rfm_base["valid_orders"].ge(2)),
        "segment",
    ] = "Repeat at risk"
    rfm_base.loc[
        (rfm_base["recency_days"].le(recent_cut))
        & (rfm_base["valid_orders"].eq(1)),
        "segment",
    ] = "New one-time"
    rfm = (
        rfm_base.groupby("segment")
        .agg(customers=("user_id", "count"), revenue=("revenue", "sum"), avg_orders=("valid_orders", "mean"), avg_recency=("recency_days", "mean"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    summary = {
        "registered_users": int(users["id"].nunique()),
        "buyers": int(cust["buyer"].sum()),
        "recognized_buyers": int(cust["recognized_buyer"].sum()),
        "buyer_penetration": pct(cust["buyer"].sum(), users["id"].nunique()),
        "repeat_buyers": int(cust["repeat_buyer"].sum()),
        "repeat_rate": pct(cust["repeat_buyer"].sum(), cust["buyer"].sum()),
        "one_time_rate": pct((cust["buyer"] & ~cust["repeat_buyer"]).sum(), cust["buyer"].sum()),
        "avg_valid_orders_per_buyer": float(cust.loc[cust["buyer"], "valid_orders"].mean()),
        "median_recency_days": float(cust.loc[cust["buyer"], "recency_days"].median()),
    }
    return {"summary": summary, "source": source, "demographics": demographics, "rfm": rfm, "customers": cust}


def product_analysis(items: pd.DataFrame) -> dict[str, pd.DataFrame]:
    all_items = items.copy()
    recognized = all_items[all_items["is_recognized"]].copy()
    category = (
        recognized.groupby(["category", "department"], dropna=False)
        .agg(revenue=("sale_price", "sum"), profit=("gross_profit", "sum"), items=("id", "count"), orders=("order_id", "nunique"))
        .reset_index()
    )
    category["margin"] = category["profit"] / category["revenue"]
    status_by_cat = (
        all_items.pivot_table(index="category", columns="status", values="id", aggfunc="count", fill_value=0)
        .reset_index()
        .rename_axis(None, axis=1)
    )
    for col in ["Cancelled", "Returned", "Complete", "Shipped", "Processing"]:
        if col not in status_by_cat.columns:
            status_by_cat[col] = 0
    status_by_cat["all_items"] = status_by_cat[["Cancelled", "Returned", "Complete", "Shipped", "Processing"]].sum(axis=1)
    status_by_cat["return_rate"] = status_by_cat["Returned"] / status_by_cat[["Returned", "Complete", "Shipped"]].sum(axis=1).replace(0, np.nan)
    status_by_cat["cancel_rate"] = status_by_cat["Cancelled"] / status_by_cat["all_items"].replace(0, np.nan)
    category = category.merge(status_by_cat[["category", "return_rate", "cancel_rate", "all_items"]], on="category", how="left")
    category = category.sort_values("revenue", ascending=False)

    brand = (
        recognized.groupby(["brand", "category"], dropna=False)
        .agg(revenue=("sale_price", "sum"), profit=("gross_profit", "sum"), items=("id", "count"))
        .reset_index()
    )
    brand["margin"] = brand["profit"] / brand["revenue"]
    brand = brand.sort_values("revenue", ascending=False)

    price_bins = pd.cut(
        recognized["sale_price"],
        bins=[0, 25, 50, 100, 200, 500, np.inf],
        labels=["<$25", "$25-50", "$50-100", "$100-200", "$200-500", "$500+"],
    )
    price_band = (
        recognized.assign(price_band=price_bins)
        .groupby("price_band", observed=True)
        .agg(revenue=("sale_price", "sum"), profit=("gross_profit", "sum"), items=("id", "count"))
        .reset_index()
    )
    price_band["margin"] = price_band["profit"] / price_band["revenue"]
    return {"category": category, "brand": brand, "price_band": price_band}


def marketing_analysis(events: pd.DataFrame, customers: pd.DataFrame) -> dict[str, object]:
    event_counts = events["event_type"].value_counts().rename_axis("event_type").reset_index(name="events")
    source_counts = events["traffic_source"].value_counts().rename_axis("traffic_source").reset_index(name="events")

    session_info = (
        events.groupby("session_id")
        .agg(
            traffic_source=("traffic_source", "first"),
            start=("created_at", "min"),
            end=("created_at", "max"),
            event_count=("id", "count"),
        )
        .reset_index()
    )
    flags = (
        events.groupby(["session_id", "event_type"])["id"]
        .count()
        .unstack(fill_value=0)
        .clip(upper=1)
        .astype("int8")
        .reset_index()
    )
    sessions = session_info.merge(flags, on="session_id", how="left")
    for col in ["home", "department", "product", "cart", "purchase", "cancel"]:
        if col not in sessions.columns:
            sessions[col] = 0
    sessions["duration_min"] = (sessions["end"] - sessions["start"]).dt.total_seconds() / 60
    sessions["bounce"] = sessions["event_count"].eq(1)

    funnel = (
        sessions.groupby("traffic_source", dropna=False)
        .agg(
            sessions=("session_id", "count"),
            product_sessions=("product", "sum"),
            cart_sessions=("cart", "sum"),
            purchase_sessions=("purchase", "sum"),
            cancel_sessions=("cancel", "sum"),
            bounce_sessions=("bounce", "sum"),
            avg_events=("event_count", "mean"),
        )
        .reset_index()
    )
    funnel["product_rate"] = funnel["product_sessions"] / funnel["sessions"]
    funnel["cart_rate"] = funnel["cart_sessions"] / funnel["product_sessions"].replace(0, np.nan)
    funnel["purchase_rate"] = funnel["purchase_sessions"] / funnel["sessions"]
    funnel["cart_to_purchase"] = funnel["purchase_sessions"] / funnel["cart_sessions"].replace(0, np.nan)
    funnel["cancel_per_cart"] = funnel["cancel_sessions"] / funnel["cart_sessions"].replace(0, np.nan)
    funnel["bounce_rate"] = funnel["bounce_sessions"] / funnel["sessions"]
    funnel = funnel.sort_values("sessions", ascending=False)

    monthly = (
        sessions.assign(month=sessions["start"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(sessions=("session_id", "count"), purchases=("purchase", "sum"), carts=("cart", "sum"))
        .reset_index()
    )
    monthly["purchase_rate"] = monthly["purchases"] / monthly["sessions"]

    summary = {
        "sessions": int(sessions["session_id"].nunique()),
        "events": int(len(events)),
        "overall_purchase_session_rate": pct(sessions["purchase"].sum(), len(sessions)),
        "overall_cart_to_purchase": pct(sessions["purchase"].sum(), sessions["cart"].sum()),
        "overall_bounce_rate": pct(sessions["bounce"].sum(), len(sessions)),
        "anonymous_event_pct": pct(events["user_id"].isna().sum(), len(events)),
        "avg_events_per_session": float(sessions["event_count"].mean()),
    }
    return {
        "summary": summary,
        "event_counts": event_counts,
        "source_counts": source_counts,
        "funnel": funnel,
        "monthly": monthly,
        "sessions": sessions,
    }


def operations_analysis(items: pd.DataFrame, inventory: pd.DataFrame, dcs: pd.DataFrame) -> dict[str, object]:
    cutoff = max(items["created_at"].max(), inventory["created_at"].max(), inventory["sold_at"].max())
    inv = inventory.copy()
    inv["is_sold"] = inv["sold_at"].notna()
    inv["age_days"] = np.where(
        inv["is_sold"],
        (inv["sold_at"] - inv["created_at"]).dt.total_seconds() / 86400,
        (cutoff - inv["created_at"]).dt.total_seconds() / 86400,
    )
    inv["unsold_cost"] = np.where(inv["is_sold"], 0, inv["cost"])
    inv["aged_180"] = (~inv["is_sold"]) & (inv["age_days"] > 180)
    inv["aged_365"] = (~inv["is_sold"]) & (inv["age_days"] > 365)
    inv["dc_id"] = inv["product_distribution_center_id"]

    dc_names = dcs.rename(columns={"id": "dc_id", "name": "dc_name"})[["dc_id", "dc_name"]]
    inv_dc = (
        inv.groupby("dc_id")
        .agg(
            inventory_units=("id", "count"),
            sold_units=("is_sold", "sum"),
            unsold_units=("is_sold", lambda s: int((~s).sum())),
            unsold_cost=("unsold_cost", "sum"),
            avg_age_days=("age_days", "mean"),
            aged_180_units=("aged_180", "sum"),
            aged_365_units=("aged_365", "sum"),
        )
        .reset_index()
        .merge(dc_names, on="dc_id", how="left")
    )
    inv_dc["sell_through"] = inv_dc["sold_units"] / inv_dc["inventory_units"]
    inv_dc["aged_180_rate"] = inv_dc["aged_180_units"] / inv_dc["unsold_units"].replace(0, np.nan)
    inv_dc = inv_dc.sort_values("unsold_cost", ascending=False)

    inv_cat = (
        inv.groupby("product_category")
        .agg(
            inventory_units=("id", "count"),
            sold_units=("is_sold", "sum"),
            unsold_units=("is_sold", lambda s: int((~s).sum())),
            unsold_cost=("unsold_cost", "sum"),
            avg_age_days=("age_days", "mean"),
            aged_180_units=("aged_180", "sum"),
        )
        .reset_index()
    )
    inv_cat["sell_through"] = inv_cat["sold_units"] / inv_cat["inventory_units"]
    inv_cat["aged_180_rate"] = inv_cat["aged_180_units"] / inv_cat["unsold_units"].replace(0, np.nan)
    inv_cat = inv_cat.sort_values("unsold_cost", ascending=False)

    recognized = items[items["is_recognized"]].copy()
    demand_dc = (
        recognized.groupby("dc_id")
        .agg(revenue=("sale_price", "sum"), profit=("gross_profit", "sum"), sold_order_items=("id", "count"))
        .reset_index()
    )
    dc_compare = inv_dc.merge(demand_dc, on="dc_id", how="left").fillna({"revenue": 0, "profit": 0, "sold_order_items": 0})
    dc_compare["stock_share"] = dc_compare["unsold_cost"] / dc_compare["unsold_cost"].sum()
    dc_compare["revenue_share"] = dc_compare["revenue"] / dc_compare["revenue"].sum()
    dc_compare["stock_minus_demand_share"] = dc_compare["stock_share"] - dc_compare["revenue_share"]
    dc_compare = dc_compare.sort_values("stock_minus_demand_share", ascending=False)

    delivered = items[items["status"].isin(["Complete", "Returned"]) & items["fulfillment_days"].notna()].copy()
    delivered["fulfillment_bin"] = pd.cut(
        delivered["fulfillment_days"],
        bins=[-np.inf, 3, 5, 7, 10, np.inf],
        labels=["<=3d", "3-5d", "5-7d", "7-10d", ">10d"],
    )
    return_by_delivery = (
        delivered.groupby("fulfillment_bin", observed=True)
        .agg(items=("id", "count"), returned=("is_returned", "sum"), avg_fulfillment_days=("fulfillment_days", "mean"))
        .reset_index()
    )
    return_by_delivery["return_rate"] = return_by_delivery["returned"] / return_by_delivery["items"]

    fulfillment = {
        "avg_ship_days": float(items.loc[items["shipped_at"].notna(), "ship_days"].mean()),
        "avg_delivery_days": float(items.loc[items["delivered_at"].notna(), "delivery_days"].mean()),
        "avg_fulfillment_days": float(delivered["fulfillment_days"].mean()),
        "processing_items": int(items["status"].eq("Processing").sum()),
        "shipped_not_complete_items": int(items["status"].eq("Shipped").sum()),
        "processing_revenue": float(items.loc[items["status"].eq("Processing"), "sale_price"].sum()),
        "shipped_revenue": float(items.loc[items["status"].eq("Shipped"), "sale_price"].sum()),
    }
    inventory_summary = {
        "cutoff": cutoff,
        "inventory_units": int(len(inv)),
        "sold_units": int(inv["is_sold"].sum()),
        "unsold_units": int((~inv["is_sold"]).sum()),
        "sell_through": pct(inv["is_sold"].sum(), len(inv)),
        "unsold_cost": float(inv["unsold_cost"].sum()),
        "aged_180_units": int(inv["aged_180"].sum()),
        "aged_180_cost": float(inv.loc[inv["aged_180"], "cost"].sum()),
        "aged_365_units": int(inv["aged_365"].sum()),
        "avg_unsold_age_days": float(inv.loc[~inv["is_sold"], "age_days"].mean()),
        "avg_sold_holding_days": float(inv.loc[inv["is_sold"], "age_days"].mean()),
    }
    return {
        "inventory_summary": inventory_summary,
        "fulfillment": fulfillment,
        "inv_dc": inv_dc,
        "inv_cat": inv_cat,
        "dc_compare": dc_compare,
        "return_by_delivery": return_by_delivery,
    }


def forecast_revenue(items: pd.DataFrame) -> dict[str, object]:
    recognized = items[items["is_recognized"]].copy()
    monthly = recognized.groupby(pd.Grouper(key="created_at", freq="MS")).agg(revenue=("sale_price", "sum"), profit=("gross_profit", "sum"))
    monthly = monthly.sort_index()
    max_date = recognized["created_at"].max()
    last_full_month = (max_date.to_period("M") - 1).to_timestamp() if max_date.day < max_date.days_in_month else max_date.to_period("M").to_timestamp()
    monthly_full = monthly.loc[:last_full_month].copy()
    last12 = monthly_full.tail(12)
    prev12 = monthly_full.iloc[-24:-12] if len(monthly_full) >= 24 else monthly_full.iloc[:0]
    raw_growth = pct(last12["revenue"].sum(), prev12["revenue"].sum()) - 1 if len(prev12) == 12 and prev12["revenue"].sum() > 0 else 0.0
    growth = float(np.clip(raw_growth, -0.2, 0.5))
    margin = pct(last12["profit"].sum(), last12["revenue"].sum())

    future_months = pd.date_range(last_full_month + pd.offsets.MonthBegin(1), periods=12, freq="MS")
    rows = []
    for month in future_months:
        prior_year = month - pd.DateOffset(years=1)
        if prior_year in monthly_full.index:
            base = monthly_full.loc[prior_year, "revenue"]
        else:
            base = last12["revenue"].mean()
        revenue = float(base * (1 + growth))
        rows.append({"month": month.strftime("%Y-%m"), "forecast_revenue": revenue, "forecast_profit": revenue * margin})
    forecast = pd.DataFrame(rows)
    summary = {
        "last_full_month": last_full_month,
        "last12_revenue": float(last12["revenue"].sum()),
        "prev12_revenue": float(prev12["revenue"].sum()) if len(prev12) == 12 else None,
        "raw_yoy_growth": raw_growth,
        "used_yoy_growth": growth,
        "last12_margin": margin,
        "next12_revenue_forecast": float(forecast["forecast_revenue"].sum()),
        "next12_profit_forecast": float(forecast["forecast_profit"].sum()),
    }
    return {"summary": summary, "monthly": monthly_full.reset_index(), "forecast": forecast}


def format_for_report(results: dict[str, object]) -> str:
    table_profile = results["profile"].copy()
    table_profile["rows"] = table_profile["rows"].map(lambda x: f"{x:,.0f}")
    table_profile["memory_mb"] = table_profile["memory_mb"].map(lambda x: f"{x:,.1f}")

    status = results["transactions"]["status"].copy()
    status["gmv"] = status["gmv"].map(money)
    status["items"] = status["items"].map(number)
    status["orders"] = status["orders"].map(number)

    source = results["customers"]["source"].copy()
    for col in ["revenue", "profit"]:
        source[col] = source[col].map(money)
    source["buyer_rate"] = source["buyer_rate"].map(percent)
    source["ltv_per_registered_user"] = source["ltv_per_registered_user"].map(lambda x: f"${x:,.2f}")
    source["arppu"] = source["arppu"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "")

    rfm = results["customers"]["rfm"].copy()
    rfm["revenue"] = rfm["revenue"].map(money)
    rfm["avg_orders"] = rfm["avg_orders"].map(lambda x: f"{x:.2f}")
    rfm["avg_recency"] = rfm["avg_recency"].map(lambda x: f"{x:.0f}")

    category = results["products"]["category"].copy()
    category_display = category[["category", "department", "revenue", "profit", "margin", "return_rate", "cancel_rate", "items"]].head(10).copy()
    for col in ["revenue", "profit"]:
        category_display[col] = category_display[col].map(money)
    for col in ["margin", "return_rate", "cancel_rate"]:
        category_display[col] = category_display[col].map(lambda x: percent(x) if pd.notna(x) else "")
    category_display["items"] = category_display["items"].map(number)

    brand = results["products"]["brand"].copy()
    brand_display = brand[["brand", "category", "revenue", "profit", "margin", "items"]].head(10).copy()
    for col in ["revenue", "profit"]:
        brand_display[col] = brand_display[col].map(money)
    brand_display["margin"] = brand_display["margin"].map(percent)
    brand_display["items"] = brand_display["items"].map(number)

    funnel = results["marketing"]["funnel"].copy()
    funnel_display = funnel[
        [
            "traffic_source",
            "sessions",
            "product_sessions",
            "cart_sessions",
            "purchase_sessions",
            "purchase_rate",
            "cart_to_purchase",
            "cancel_per_cart",
            "bounce_rate",
        ]
    ].copy()
    for col in ["sessions", "product_sessions", "cart_sessions", "purchase_sessions"]:
        funnel_display[col] = funnel_display[col].map(number)
    for col in ["purchase_rate", "cart_to_purchase", "cancel_per_cart", "bounce_rate"]:
        funnel_display[col] = funnel_display[col].map(percent)

    inv_cat = results["operations"]["inv_cat"].copy()
    inv_cat_display = inv_cat[["product_category", "inventory_units", "unsold_units", "unsold_cost", "sell_through", "aged_180_rate", "avg_age_days"]].head(10).copy()
    for col in ["inventory_units", "unsold_units"]:
        inv_cat_display[col] = inv_cat_display[col].map(number)
    inv_cat_display["unsold_cost"] = inv_cat_display["unsold_cost"].map(money)
    for col in ["sell_through", "aged_180_rate"]:
        inv_cat_display[col] = inv_cat_display[col].map(lambda x: percent(x) if pd.notna(x) else "")
    inv_cat_display["avg_age_days"] = inv_cat_display["avg_age_days"].map(lambda x: f"{x:.0f}")

    dc_compare = results["operations"]["dc_compare"].copy()
    dc_display = dc_compare[["dc_name", "unsold_cost", "revenue", "stock_share", "revenue_share", "stock_minus_demand_share", "sell_through"]].copy()
    for col in ["unsold_cost", "revenue"]:
        dc_display[col] = dc_display[col].map(money)
    for col in ["stock_share", "revenue_share", "stock_minus_demand_share", "sell_through"]:
        dc_display[col] = dc_display[col].map(percent)

    delivery = results["operations"]["return_by_delivery"].copy()
    delivery["items"] = delivery["items"].map(number)
    delivery["returned"] = delivery["returned"].map(number)
    delivery["return_rate"] = delivery["return_rate"].map(percent)
    delivery["avg_fulfillment_days"] = delivery["avg_fulfillment_days"].map(lambda x: f"{x:.1f}")

    forecast = results["forecast"]["forecast"].copy()
    forecast["forecast_revenue"] = forecast["forecast_revenue"].map(money)
    forecast["forecast_profit"] = forecast["forecast_profit"].map(money)

    tx = results["transactions"]["metrics"]
    cust = results["customers"]["summary"]
    mkt = results["marketing"]["summary"]
    inv = results["operations"]["inventory_summary"]
    fulf = results["operations"]["fulfillment"]
    fc = results["forecast"]["summary"]
    q = results["quality"]

    return f"""# Báo cáo phân tích kinh doanh ET Club từ raw dataset

## 1. Tóm tắt điều hành

ET Club đang có quy mô giao dịch tốt nhưng hiệu quả kinh doanh bị rò rỉ ở ba điểm chính: tỷ lệ khách mua lại thấp, rơi rụng lớn giữa giỏ hàng và mua hàng, và tồn kho chưa bán chiếm vốn lớn. Với định nghĩa doanh thu ghi nhận là các item ở trạng thái `Complete` hoặc `Shipped`, doanh nghiệp đạt **{money(tx["recognized_revenue"])} doanh thu**, **{money(tx["recognized_profit"])} lợi nhuận gộp**, biên gộp **{percent(tx["recognized_margin"])}**. Tuy nhiên, doanh thu bị mất do `Cancelled` và `Returned` lên tới **{money(tx["leakage_revenue"])}**, tương đương **{percent(tx["leakage_rate"])} tổng GMV**.

Về khách hàng, chỉ **{percent(cust["buyer_penetration"])}** trong **{number(cust["registered_users"])}** user đăng ký có phát sinh mua hàng hợp lệ; trong nhóm đã mua, tỷ lệ mua lặp lại chỉ **{percent(cust["repeat_rate"])}**. Đây là tín hiệu rõ rằng tăng trưởng hiện phụ thuộc nhiều vào acquisition hơn là retention.

Funnel website cho thấy **{number(mkt["sessions"])} sessions** và purchase-session conversion chỉ **{percent(mkt["overall_purchase_session_rate"])}**; cart-to-purchase đạt **{percent(mkt["overall_cart_to_purchase"])}**. Trong vận hành, kho có **{number(inv["inventory_units"])} units**, nhưng **{number(inv["unsold_units"])} units chưa bán**, giá vốn tồn **{money(inv["unsold_cost"])}**; trong đó hàng tồn trên 180 ngày trị giá **{money(inv["aged_180_cost"])}**. Nếu giữ quỹ đạo hiện tại, dự báo 12 tháng sau mốc **{fc["last_full_month"].strftime("%Y-%m")}** đạt khoảng **{money(fc["next12_revenue_forecast"])} doanh thu** và **{money(fc["next12_profit_forecast"])} lợi nhuận gộp**.

## 2. Nền dữ liệu và kiểm tra chất lượng

{md_table(table_profile)}

- Giai đoạn order: **{q["order_time_min"].strftime("%Y-%m-%d")} đến {q["order_time_max"].strftime("%Y-%m-%d")}**; giai đoạn event: **{q["event_time_min"].strftime("%Y-%m-%d")} đến {q["event_time_max"].strftime("%Y-%m-%d")}**.
- Không phát hiện orphan nghiêm trọng ở khóa `order_items -> users/products/orders`; số item giá bán dưới $1 là **{number(q["sale_price_lt_1_items"])}**, tác động doanh thu không đáng kể.
- **{percent(q["events_user_id_null_pct"])} events không có user_id**, cần hiểu là traffic ẩn danh/khách chưa đăng nhập; vì vậy funnel session nên dùng `session_id`, còn phân tích LTV dùng `users.traffic_source`.

## 3. Doanh thu, lợi nhuận và rò rỉ trạng thái đơn hàng

{md_table(status)}

Nhìn ở cấp item, rò rỉ doanh thu đến từ hai nhóm: đơn hủy trước khi fulfilment và đơn hoàn sau giao hàng. Nhóm này không chỉ làm mất doanh thu mà còn kéo theo chi phí vận hành, xử lý hoàn kho và chi phí marketing đã bỏ ra để tạo đơn. Do đó, chỉ số nên theo dõi hàng tuần là `leakage_rate = (GMV Cancelled + GMV Returned) / Total GMV`, tách theo category, brand, source và thời gian giao hàng.

## 4. Khách hàng: chân dung, loyalty và giá trị

**Metrics chính**

- Registered users: **{number(cust["registered_users"])}**
- Buyers hợp lệ: **{number(cust["buyers"])}**; buyer penetration **{percent(cust["buyer_penetration"])}**
- Repeat buyers: **{number(cust["repeat_buyers"])}**; repeat rate **{percent(cust["repeat_rate"])}**
- AOV ghi nhận: **{money(tx["avg_order_value"])}**; giá/item bình quân **{money(tx["avg_item_price"])}**
- Median recency của buyers: **{cust["median_recency_days"]:.0f} ngày**

**Nguồn acquisition theo doanh thu/LTV**

{md_table(source)}

**RFM thô theo hành vi mua**

{md_table(rfm)}

Chẩn đoán: nguồn có buyer rate và LTV khác nhau nhưng loyalty chung còn mỏng; phần lớn người mua chỉ mua một lần. ET Club nên chuyển từ tối ưu chỉ theo số user/traffic sang tối ưu theo `LTV per registered user`, `repeat rate 90 ngày` và `gross profit per buyer`.

## 5. Sản phẩm và cơ cấu lợi nhuận

**Top category theo doanh thu ghi nhận**

{md_table(category_display)}

**Top brand theo doanh thu ghi nhận**

{md_table(brand_display)}

Category top doanh thu không đồng nghĩa là top hiệu quả. Các category có revenue cao nhưng return/cancel rate cao cần được xử lý bằng mô tả size/fit tốt hơn, kiểm tra chất lượng ảnh, chính sách đổi trả theo nguyên nhân, và kiểm soát tồn kho. Với nhóm biên gộp cao, có thể tăng ngân sách paid search/remarketing nếu funnel sau giỏ hàng được cải thiện.

## 6. Marketing và chuyển đổi website

**Funnel theo traffic source**

{md_table(funnel_display)}

Tắc nghẽn lớn nhất nằm ở đoạn `cart -> purchase`: người dùng vào giỏ nhiều hơn đáng kể so với số hoàn tất mua. Conversion giữa các source khá đồng đều, nên `traffic_source` hiện chưa đủ granular để chẩn đoán campaign nào tốt/xấu; cần bổ sung campaign, medium, creative hoặc landing page. Vì event không có cost marketing, khuyến nghị không dùng ROAS tuyệt đối; thay vào đó dùng bộ chỉ số thay thế: `purchase session rate`, `cart-to-purchase`, `cancel/cart`, `revenue per registered user` theo source.

## 7. Vận hành, tồn kho và fulfilment

**Tồn kho theo category có giá vốn tồn cao nhất**

{md_table(inv_cat_display)}

**Lệch pha tồn kho - nhu cầu theo distribution center**

{md_table(dc_display)}

**Return rate theo tốc độ fulfilment**

{md_table(delivery)}

Fulfilment bình quân: ship sau **{fulf["avg_ship_days"]:.1f} ngày**, giao sau ship **{fulf["avg_delivery_days"]:.1f} ngày**, end-to-end **{fulf["avg_fulfillment_days"]:.1f} ngày**. Return rate giữa các bin tốc độ giao hàng khá gần nhau, nên dữ liệu hiện không ủng hộ kết luận "giao chậm là nguyên nhân chính của hoàn trả"; nguyên nhân có khả năng nằm ở kỳ vọng sản phẩm, size/fit hoặc chính sách đổi trả. DC nhìn chung không lệch quá mạnh về stock share so với revenue share; điểm nghẽn vốn lưu động rõ nhất là tồn kho chưa bán và hàng trên 180 ngày theo category.

## 8. Dự báo xu hướng

Dự báo dưới đây dùng seasonal naive trên 12 tháng gần nhất. Do doanh thu 12 tháng gần nhất tăng **{percent(fc["raw_yoy_growth"])}** so với 12 tháng trước, mô hình baseline chỉ dùng mức tăng **{percent(fc["used_yoy_growth"])}** để tránh ngoại suy quá mức. Đây là baseline vận hành, không phải mô hình demand planning cuối cùng.

{md_table(forecast)}

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
"""


def to_jsonable(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.map(scalarize).to_dict(orient="records")
    if isinstance(obj, dict):
        output = {}
        for k, v in obj.items():
            if k in {"customers", "sessions"} and isinstance(v, pd.DataFrame):
                continue
            output[k] = to_jsonable(v)
        return output
    if isinstance(obj, list):
        return [to_jsonable(v) for v in obj]
    return scalarize(obj)


def main() -> None:
    base = Path.cwd()
    dataset_root = find_dataset_root(base)
    raw_dir = dataset_root / "raw"
    out_dir = base / "Datavision2026" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = load_raw(raw_dir)
    print("Enriching transactions...")
    items = enrich_transactions(tables)
    print("Computing metrics...")
    results: dict[str, object] = {
        "profile": profile_tables(tables),
        "quality": quality_checks(tables, items),
        "transactions": transaction_metrics(items, tables["orders"]),
        "customers": customer_analysis(items, tables["users"]),
        "products": product_analysis(items),
        "marketing": marketing_analysis(tables["events"], pd.DataFrame()),
        "operations": operations_analysis(items, tables["inventory"], tables["dcs"]),
        "forecast": forecast_revenue(items),
    }

    report = format_for_report(results)
    report_path = out_dir / "raw_business_analysis_report.md"
    metrics_path = out_dir / "raw_business_analysis_metrics.json"
    report_path.write_text(report, encoding="utf-8")
    metrics_path.write_text(json.dumps(to_jsonable(results), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
