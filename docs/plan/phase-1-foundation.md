# Phase 1 - Foundation Engine (Version 0.1)

## Goal

Build the first usable planning workflow by defining how user inputs are supplied, then using those inputs to drive deterministic projection mechanics.

## Phase Split

1. Phase 1A - Input layer
2. Phase 1B - Projection foundation
3. Phase 1C - Pre-retirement contribution modeling

## Scope

1. Phase 1A defines where variable inputs live and how they are loaded.
2. Inputs must live under the project data directory introduced in Phase 0, with support for the directory itself being a symlink.
3. The tracked input entrypoint is data/master_data.toml, which points to the actual data directory and file names.
4. Define the canonical input format for people, assumptions, retirement dates, account balances, pensions, section 7 obligations, and scenario settings.
5. Account types must come from a controlled canonical list so later tax logic can rely on stable categories.
6. Section 7 sharing must be computed from the payer and other-party gross incomes rather than entered manually.
7. Implement parsing and loading from user-editable input files into the Phase 0 model contracts.
8. Provide a sample input dataset and clear validation errors for malformed or incomplete input data.
9. Add a CLI validation or preview command so inputs can be checked before running projections.
10. Phase 1B uses loaded inputs to generate a timeline from 2026 through horizon (for example 2077).
11. Add inflation index and age tracking for each person.
12. Add account evolution for RRSP, spousal RRSP, TFSA, and non-registered assets.
13. Add salary growth with yearly override support.
14. Add defined benefit pension abstraction with HOOPP-compatible inputs.
15. Add CPP/OAS timing controls with start-age overrides and percentage-of-maximum inputs.
16. Build in-memory yearly output tables for Income/Expenses and Assets.
17. Add CLI path to run deterministic projection from loaded config and input data.
18. Add optional pre-retirement account contribution rules per account using yearly, monthly, biweekly, or annual percent-of-income inputs.
19. Ensure projections apply contributions only for pre-retirement periods and allow accounts with no contributions.

## Deliverables

1. Input file convention and loader module, including master_data.toml manifest handling.
2. Sample household input dataset stored under the gitignored data structure.
3. CLI input validation and preview path.
4. Foundation engines and orchestration flow.
5. Baseline tabular outputs suitable for export later.
6. Initial phase test suite for input loading, timeline logic, and balances.
7. Contribution regression tests covering fixed and income-linked contribution modes.

## Dependencies

1. Requires Phase 0 contracts.
2. Phase 1B must not begin until Phase 1A input loading is working and reviewed.

## Exit Criteria

1. A user can place editable input files in the configured data directory and load them successfully.
2. Validation failures for input files are explicit and understandable, including invalid account type values.
3. Year-by-year balances reconcile exactly in controlled scenarios.
4. Salary and retirement transitions occur in configured years.
5. Pension and CPP/OAS start events match configured dates and ages.
