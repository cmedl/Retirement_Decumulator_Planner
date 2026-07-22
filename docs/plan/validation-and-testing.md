# Validation and Testing Strategy

## Principles

1. Validate as each phase ships, not at the end.
2. Reconcile all money flows year to year.
3. Compare key tax results to external references.
4. Make optimizer behavior explainable and reproducible.

## Test Layers

1. Unit tests for isolated functions (growth, taxes, thresholds).
2. Integration tests for yearly cash-flow assembly.
3. Regression tests for fixed benchmark scenarios.
4. Scenario tests for sensitivity to major levers.
5. Export tests to verify sheet structure and numeric reconciliation.

## Core Validation Checks

1. Account balances reconcile exactly each year.
2. Salary and pension transitions trigger in expected years.
3. CPP/OAS start age changes propagate through all outputs.
4. Pension splitting percentages alter taxes as expected.
5. Section 7 outflows affect net income and objective scores correctly.
6. OAS clawback behavior is correct around threshold edges.

## Risk Controls

1. Keep tax tables versioned and explicit.
2. Use deterministic settings in optimizer tests.
3. Maintain a small set of trusted benchmark cases for quick sanity checks.
4. Treat unresolved reconciliation mismatches as blocking defects.
