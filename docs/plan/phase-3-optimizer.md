# Phase 3 - Decumulation Optimizer (Version 0.3)

## Goal

Generate optimized withdrawal and splitting strategies instead of manual trial and error.

## Scope

1. Objective stack with priority ordering.
2. RRSP depletion-by-age goal handling.
3. Flat or near-flat after-tax income targeting with planned step changes.
4. Tax smoothness objective after retirement.
5. Lifetime tax minimization objective.
6. Optional OAS threshold awareness objective.
7. Section 7 outflow model integrated into net-income and objective calculations.
8. Withdrawal sequencing across RRSP, TFSA, and non-registered accounts.

## Deliverables

1. Heuristic optimizer first (explainable and deterministic).
2. Optional numerical optimization mode after heuristic baseline is stable.
3. Decision trace outputs explaining annual strategy choices.

## Dependencies

1. Requires Phase 1 and Phase 2 outputs.

## Exit Criteria

1. Optimizer can satisfy priorities in feasible scenarios.
2. If infeasible, engine reports which objectives failed and why.
3. Results are reproducible given same inputs and settings.
