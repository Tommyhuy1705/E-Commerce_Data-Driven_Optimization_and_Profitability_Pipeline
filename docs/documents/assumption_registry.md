# Assumption Registry

**Updated:** 2026-06-02  
**Purpose:** Make the Phase 3 ROI model auditable by separating observed data, proxy estimates, and scenario assumptions.

## Assumption Classes

| Class | Meaning | How To Use |
|---|---|---|
| Observed | Directly calculated from raw or processed data | Can be used as baseline evidence |
| Proxy | Estimated from available fields because the direct field is missing | Use for sensitivity, not causal proof |
| Scenario | Management assumption for possible future action | Expose as input and stress test |

## Registry

| Assumption | Value / Method | Class | Evidence | Risk | Mitigation |
|---|---|---|---|---|---|
| Recognized revenue | Complete + Shipped sale price | Observed | `fact_transactions` | Low | Reconcile against annual revenue table |
| Gross margin | Gross profit / recognized revenue | Observed | `fact_transactions` | Low | Keep metric definition stable |
| Frozen inventory | Unsold inventory cost | Observed | `fact_inventory`, holding cost table | Medium | Validate snapshot logic before business use |
| Holding cost rate | `22%` annual rate | Scenario | Phase 3 config | Medium | Test sensitivity from `15%` to `30%` |
| Reverse logistics cost | `$20` per returned item | Scenario | Phase 2 return-cost assumption | Medium | Replace with actual handling/shipping cost if available |
| Price elasticity | Category-level log-log monthly proxy | Proxy | `price_elasticity_weights.csv` | High | Present as sensitivity input, not causal elasticity |
| Markdown response | Scenario response multiplier | Scenario | Pessimistic/Base/Optimistic weights | High | Monitor realized sell-through during pilot |
| Brand erosion | Revenue share penalty | Scenario | Scenario weights | High | Use price fences and channel-specific markdown |
| OOS cancel share | Share of cancel sessions tied to OOS/checkout fix | Proxy/Scenario | Funnel and leakage proxy | High | Add real stockout flag if available |
| OOS resolution rate | Percent of OOS friction recovered | Scenario | Scenario weights | High | Validate through checkout A/B test |
| Retention reactivation | Percent of one-time buyers reactivated | Scenario | CRM scenario | Medium | Pilot CRM journey before scale |
| DC transfer cost | Distance/cost proxy | Proxy | DC rebalance model | High | Replace with actual carrier/internal transfer rates |
| DC rebalance net value | Expected protected value minus transfer cost | Proxy | `dc_rebalance_weights.csv` | High | Demote to supporting diagnostic unless value becomes material |

## Explicit Caveats

- Price elasticity is not causal because the dataset does not include explicit discount history or campaign assignment.
- Forecast output should not drive automated procurement while MAPE is high.
- DC rebalance is currently a deterministic heuristic and has low material value in the current run.
- ROI scenarios are decision-support estimates, not audited financial forecasts.

## Upgrade Path

| Gap | Data Needed | Model Upgrade |
|---|---|---|
| Discount causality | Discount/campaign history | Causal uplift or panel regression |
| Forecast accuracy | Promotion, holiday, stockout, external demand signals | Feature-rich ML or hierarchical forecasting |
| DC rebalance value | SKU-level stock, transfer cost, capacity, regional demand | LP/MIP optimization |
| Return reduction | Return reason and handling cost | Root-cause model and contribution margin estimate |
