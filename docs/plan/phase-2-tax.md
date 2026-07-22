# Phase 2 - Tax Engine (Version 0.2)

## Goal

Add a robust approximate Canadian tax layer focused on retirement planning decisions.

## Scope

1. Federal and Ontario bracket-based tax calculations.
2. Core retirement-relevant credits and age-related handling.
3. Pension splitting simulation and per-year best split selection.
4. OAS clawback calculations and reporting.
5. Capital gains treatment for non-registered withdrawals.
6. Effective and marginal tax rate outputs.

## Deliverables

1. Tax engine module and tax parameter tables.
2. Regression fixtures for selected benchmark years.
3. Tax output columns integrated into yearly ledger.

## Dependencies

1. Requires stable income streams and ledger from Phase 1.

## Exit Criteria

1. Benchmark sample years match trusted calculator outputs within agreed tolerance.
2. Pension splitting changes are reflected in person-level and household-level tax results.
3. OAS clawback behavior appears correctly near threshold conditions.
