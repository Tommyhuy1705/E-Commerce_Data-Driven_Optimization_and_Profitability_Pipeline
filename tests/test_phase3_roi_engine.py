from __future__ import annotations

import math

import pandas as pd

from src.phase3_step1_models import (
    SCENARIOS,
    build_budget_allocation,
    build_scenario_output,
    markdown_grid_for_candidates,
    pct,
    safe_divide,
    select_markdown_recommendations,
)


def test_pct_and_safe_divide_handle_zero_denominator() -> None:
    assert pct(25, 100) == 25.0
    assert pct(25, 0) == 0.0
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0) == 0.0


def test_markdown_grid_preserves_guardrail_and_selects_best_row() -> None:
    candidates = pd.DataFrame(
        [
            {
                "product_category": "Jeans",
                "department": "Women",
                "center_id": 1,
                "abc_class": "B",
                "eligible_for_markdown": True,
                "aged_180_units": 100,
                "avg_cost": 20.0,
                "avg_retail_price": 60.0,
                "aged_180_cost": 2_000.0,
                "price_elasticity": -1.2,
            },
            {
                "product_category": "Outerwear",
                "department": "Men",
                "center_id": 2,
                "abc_class": "A",
                "eligible_for_markdown": False,
                "aged_180_units": 100,
                "avg_cost": 30.0,
                "avg_retail_price": 90.0,
                "aged_180_cost": 3_000.0,
                "price_elasticity": -1.0,
            },
        ]
    )

    grid = markdown_grid_for_candidates(candidates, holding_cost_rate=0.22, forward_holding_days=180, discounts=[10, 20])
    recommendations = select_markdown_recommendations(grid)

    assert set(grid["abc_class"]) == {"B"}
    assert len(recommendations) == 1
    assert recommendations["recommended_action"].iloc[0] == "Markdown with guardrail"
    assert recommendations["gross_profit_after_markdown"].iloc[0] > 0


def test_scenario_output_calculates_roi_and_payback() -> None:
    baseline = {
        "recognized_revenue": 1_000_000.0,
        "cancel_sessions": 1_000.0,
        "aov": 100.0,
        "gross_margin_pct": 50.0,
        "one_time_buyers": 1_000.0,
        "returned_items": 100.0,
        "investment_budget": 100_000.0,
    }
    candidates = pd.DataFrame(
        [
            {
                "eligible_for_markdown": True,
                "aged_180_units": 100,
                "avg_retail_price": 100.0,
                "avg_cost": 40.0,
                "aged_180_cost": 4_000.0,
                "price_elasticity": -1.0,
            }
        ]
    )
    dc_transfers = pd.DataFrame(
        [{"expected_holding_value_protected": 2_000.0, "total_transfer_cost": 500.0}]
    )

    scenario = build_scenario_output(
        baseline=baseline,
        candidates=candidates,
        dc_transfers=dc_transfers,
        holding_cost_rate=0.22,
        forward_holding_days=180,
        reverse_logistics_cost=20.0,
    )

    assert set(scenario["scenario"]) == {item.name for item in SCENARIOS}
    base = scenario.loc[scenario["scenario"].eq("Base")].iloc[0]
    assert base["dc_rebalance_net_value"] == 1_500.0
    assert math.isfinite(base["roi_pct"])
    assert math.isfinite(base["payback_months"])


def test_budget_allocation_sums_to_full_budget_share() -> None:
    budget = build_budget_allocation()
    assert round(float(budget["budget_share_pct"].sum()), 6) == 100.0
    assert float(budget["budget_usd"].sum()) == 500_000.0
