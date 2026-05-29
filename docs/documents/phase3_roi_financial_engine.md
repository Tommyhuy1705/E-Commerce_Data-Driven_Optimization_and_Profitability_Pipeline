# Phase 3 ROI Financial Engine

**Updated:** 2026-05-29  
**Scope:** Personal portfolio version of the Datavision 2026 Round 3 modeling layer.

## Objective

Phase 3 converts the Phase 1-2 analytics outputs into a decision-support model for operational investment. The model tests whether a `$500,000` budget can create enough incremental gross profit through inventory markdowns, distribution-center rebalance, retention actions, checkout/OOS improvements, and return-cost reduction.

The model is not a production optimizer. It is a transparent financial engine with traceable inputs, explicit assumptions, and scenario outputs that can be audited or rebuilt.

## Main Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Model code | `src/phase3_step1_models.py` | Rebuilds baseline metrics, model weights, policies, scenarios, and scorecards. |
| Clean notebook | `notebooks/4.0_phase3_roi_financial_engine.ipynb` | Personal-project walkthrough for running and reviewing the ROI model. |
| Model artifacts | `models/` | Stores reusable baseline, scenario, elasticity, markdown, rebalance, retention, and budget weights. |
| Processed outputs | `data/processed/phase3_*.csv` and `parameters_output.csv` | CSV outputs for BI, Excel, reporting, and validation. |

## Baseline Inputs

| Metric | Value |
|---|---:|
| Recognized revenue | `$5.53M` |
| Recognized gross profit | `$2.87M` |
| Gross margin | `51.9%` |
| GMV all status | `$10.03M` |
| Status leakage | `$4.50M` |
| Frozen inventory value | `$8.98M` |
| Sell-through | `36.14%` |
| Current return rate | `10.03%` |
| Valid purchase users | `49,484` |
| Repeat buyers / valid customers | `23.40%` |

## Model Components

| Component | Role | Notes |
|---|---|---|
| Inventory Markdown ROI | Selects aged inventory groups and tests discount levels with gross-profit guardrails. | Primary model because frozen inventory is the largest short-term value pool. |
| Price Elasticity Proxy | Estimates category-level demand response from monthly units and realized prices. | Proxy only; the raw data has no explicit discount/campaign history. |
| DC Rebalance Plan | Finds transfer flows where expected protected value exceeds transfer cost. | Uses deterministic greedy min-cost fallback, not full linear programming. |
| Retention Tail | Estimates supporting upside from reactivating one-time or at-risk buyers. | Supporting benefit, not a standalone churn model. |
| Scenario Financial Layer | Combines benefits, costs, budget, ROI, and payback under three scenarios. | Used as the benchmark for Excel/BI financial views. |

## Scenario Results

| Scenario | Discount | Incremental GP | Net Benefit After Investment | ROI | Payback |
|---|---:|---:|---:|---:|---:|
| Pessimistic | `20%` | `$513.7K` | `$13.7K` | `2.74%` | `11.68 months` |
| Base | `30%` | `$1.06M` | `$562.6K` | `112.52%` | `5.65 months` |
| Optimistic | `40%` | `$1.52M` | `$1.02M` | `203.08%` | `3.96 months` |

## Quality Assessment

The generated scorecard gives the integrated model an overall score of `7.23/10`.

| Module | Score | Confidence |
|---|---:|---|
| Baseline Traceability | `9.00` | High |
| Scenario Robustness | `7.00` | Medium-High |
| Markdown Policy | `8.00` | Medium-High |
| Price Elasticity Evidence | `5.38` | Medium-Low |
| DC Rebalance Optimization | `6.50` | Medium |
| Retention Tail | `5.50` | Medium-Low |
| Assumption Transparency | `7.00` | Medium |

## Caveats

- Price elasticity is a sensitivity proxy because the dataset does not contain explicit discount history.
- OOS share, brand erosion, and reverse-logistics impact are scenario assumptions, not raw fields.
- DC rebalance is a deterministic transport heuristic; a production version should add SKU/size constraints, capacity constraints, and an LP/MIP solver.
- Forecasting remains baseline-only while MAPE is high, so forecast output should support inventory monitoring rather than automated procurement.

## Rebuild Command

```powershell
& "C:\Users\LEGION\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m src.phase3_step1_models --dataset-root data --models-dir models
```
