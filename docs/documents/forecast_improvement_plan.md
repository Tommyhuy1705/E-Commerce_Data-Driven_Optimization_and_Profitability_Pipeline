# Forecast Improvement Plan

**Updated:** 2026-06-02  
**Purpose:** Address the Phase 3 feedback that the current demand forecast has high MAPE and needs a concrete improvement roadmap.

## Current State

The current forecast is useful as a baseline monitoring view, not as an automated procurement engine.

| Item | Current Position |
|---|---|
| Forecast scope | Top revenue categories |
| Current error level | MAPE around `50.9%` in the existing Phase 3 summary |
| Main use | Trend monitoring and inventory warning |
| Main limitation | No promotion calendar, discount history, stockout flag, campaign calendar, or reliable external demand signal |

## Implemented Benchmark Update

The project now includes `src/forecast_benchmark.py`, which runs rolling-origin one-step-ahead backtests for the top revenue categories.

Current benchmark output:

| Output | Path |
|---|---|
| Model benchmark | `data/processed/forecast_model_benchmark.csv` |
| Backtest predictions | `data/processed/forecast_backtest_predictions.csv` |
| Feature importance | `data/processed/forecast_feature_importance.csv` |
| Recommendation note | `data/processed/forecast_recommendation.md` |

The current average best-category MAPE is approximately `14.57%` across the top five categories. This should not be compared one-to-one against the older `50.9%` figure because the benchmark protocol is different: the new result is rolling-origin one-step-ahead, while the older forecast used a more conservative 12-month holdout/baseline framing.

## Target State

The forecast layer should become a benchmarked model selection framework, not a single forecast line.

| Horizon | Target |
|---|---|
| Short term | Build a reproducible benchmark across simple and ML models |
| Medium term | Validate whether one-step-ahead MAPE below `20%` remains stable across refreshes |
| Long term | Use forecast output as a monitored planning signal, not as direct automated replenishment |

## Model Benchmark

The benchmark should compare:

| Model | Role |
|---|---|
| Seasonal naive | Minimum credible baseline for monthly retail seasonality |
| Moving average 3M/6M | Simple smoothing baseline |
| Random Forest lag model | Nonlinear benchmark using calendar, lag, and rolling features |
| Prophet/SARIMA/ETS | Optional if dependencies and stability are acceptable |

The primary decision metric is MAPE. Secondary metrics are MAE, RMSE, forecast bias, and category-level stability.

## Feature Roadmap

| Feature Group | Examples | Expected Benefit |
|---|---|---|
| Calendar | month, quarter, year, seasonality flags | Captures monthly demand patterns |
| Lag demand | lag 1, 3, 6, 12 months | Captures recent and annual demand memory |
| Rolling statistics | rolling mean/std 3M and 6M | Captures demand momentum and volatility |
| Price/product | average realized price, category, department | Helps separate demand from price mix |
| Operations proxy | return rate, cancel rate, sell-through | Adds supply and friction context |
| External signals | CPI, freight cost, holidays | Only add after source validation |

## Backtest Protocol

Use rolling-origin backtesting:

```text
Train through month T -> predict T+1
Move one month forward
Repeat until the end of the historical window
```

This is stricter than a single train/test split and shows whether the model is stable over time.

## Acceptance Criteria

| Gate | Criteria | Decision |
|---|---|---|
| Baseline gate | New model beats seasonal naive by at least `10%` relative MAPE | Use as preferred forecast |
| Reliability gate | Category MAPE below `40%` for priority categories | Use for planning discussions |
| Stability gate | One-step-ahead MAPE below `20%` for priority categories across refreshes | Use as monthly monitored forecast |
| Risk gate | Category MAPE above `50%` | Keep as monitoring only |
| Explainability gate | Feature importance and error table are available | Accept for portfolio reporting |

## Deliverables

| Output | Purpose |
|---|---|
| `data/processed/forecast_model_benchmark.csv` | Model-level benchmark by category |
| `data/processed/forecast_backtest_predictions.csv` | Rolling-origin prediction audit |
| `data/processed/forecast_feature_importance.csv` | Feature importance for ML benchmark |
| `data/processed/forecast_recommendation.md` | Plain-language recommendation and caveats |

## Positioning

The forecast should be presented as a monitored decision-support signal. It should not be positioned as production procurement automation until external signals, promotion calendar, stockout flags, and operational constraints are available.
