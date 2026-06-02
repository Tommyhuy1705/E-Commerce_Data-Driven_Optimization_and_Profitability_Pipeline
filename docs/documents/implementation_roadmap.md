# Implementation Roadmap

**Updated:** 2026-06-02  
**Purpose:** Convert the Phase 3 ROI scenario into an implementation-grade action plan with monthly milestones, phase gates, and kill-switches.

## Strategic Focus

The implementation should prioritize the largest controllable value pools:

1. Frozen inventory and aged stock.
2. Status leakage and checkout/OOS friction.
3. Repeat purchase and retention tail.
4. Forecast monitoring for inventory decisions.

DC rebalance remains a supporting diagnostic unless a stronger optimization model proves material value.

## Six-Month Roadmap

| Month | Workstream | Deliverable | Success Metric |
|---|---|---|---|
| 1 | Data foundation | Validate processed tables, ROI parameters, model artifacts | 100% model checks pass |
| 1 | Inventory | Confirm ABC-aging policy and excluded A-class SKUs | 0 A-class markdown rows |
| 2 | Forecast | Run benchmark backtest and publish model recommendation | Benchmark report completed |
| 2 | Operations | Define OOS/checkout leakage tracking | Cancel/OOS proxy dashboard ready |
| 3 | Markdown pilot | Launch controlled markdown on eligible aged inventory | Positive gross profit after markdown |
| 3 | CRM pilot | Launch reactivation journey for one-time buyers | Reactivation lift tracked |
| 4 | Review gate | Compare pilot ROI against Base scenario | Continue only if ROI remains positive |
| 5 | Scale | Expand winning markdown/CRM policies | Sell-through improvement visible |
| 6 | Governance | Publish final performance review and next-cycle budget | Payback and risk report completed |

## Phase Gates

| Gate | Timing | Continue If | Stop Or Revise If |
|---|---|---|---|
| Gate 1: Data readiness | End of Month 1 | Inputs reconcile with baseline metrics | Missing or inconsistent source tables |
| Gate 2: Forecast reliability | End of Month 2 | Priority-category MAPE improves or supports monitoring | MAPE remains high with no category-level usefulness |
| Gate 3: Markdown pilot | End of Month 4 | Gross profit after markdown is positive and sell-through improves | Margin erosion exceeds holding-cost benefit |
| Gate 4: Scale | End of Month 6 | Net benefit remains positive after implementation cost | Brand erosion, returns, or ops cost breaks ROI |

## Kill-Switches

| Risk | Kill-Switch |
|---|---|
| Brand erosion | Pause markdown if realized margin drops below policy guardrail or high-value category demand weakens |
| Forecast instability | Keep forecast as monitoring-only if MAPE exceeds `50%` after benchmark |
| Hidden logistics cost | Stop DC rebalance if transfer value/cost ratio falls below `1.2x` |
| CRM underperformance | Stop broad CRM spend if reactivation lift is below `2.5%` after pilot |
| ROI deterioration | Pause scale-up if cumulative net benefit turns negative after pilot costs |

## Owner Model

| Workstream | Owner | Responsibility |
|---|---|---|
| Data pipeline | Data Engineer | Tables, refresh, model inputs |
| ROI engine | Data Analyst | Scenario, budget, scorecard, reporting |
| Forecast | Data Scientist / Analyst | Benchmark, backtest, error interpretation |
| Inventory execution | Operations | Markdown policy and sell-through tracking |
| CRM execution | Marketing | Reactivation journeys and retention KPIs |

## Reporting Cadence

| Cadence | Report |
|---|---|
| Weekly | Pilot KPI tracker: sell-through, margin, return rate, stock movement |
| Monthly | ROI scenario refresh and forecast benchmark review |
| End of phase | Gate decision memo with continue/stop/revise recommendation |
