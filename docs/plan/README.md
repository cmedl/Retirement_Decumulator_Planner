# Retirement Planner Build Plan

This folder contains the implementation roadmap only. No feature implementation should start until this plan is reviewed and approved.

Formal phase gates are enforced in:

1. [Phase Gate Policy](./phase-gate-policy.md)
2. [Phase Approval Register](./phase-approval-register.md)

## Roadmap Files

1. [Phase 0 - Architecture and Contracts](./phase-0-architecture.md)
2. [Phase 1 - Foundation Engine (Version 0.1)](./phase-1-foundation.md)
3. [Phase 2 - Tax Engine (Version 0.2)](./phase-2-tax.md)
4. [Phase 3 - Decumulation Optimizer (Version 0.3)](./phase-3-optimizer.md)
5. [Phase 4 - Outputs and Review Workflow](./phase-4-outputs.md)
6. [Phase 5 - Comparisons and Plan Health](./phase-5-comparisons.md)
7. [Phase 6 - Hardening and Maintenance](./phase-6-hardening.md)
8. [Validation and Test Strategy](./validation-and-testing.md)

## Operating Rules for Implementation

1. Implement one phase at a time.
2. Keep core business logic in Python package modules.
3. Use Jupyter notebooks as a review and analysis surface, not the source of truth.
4. Keep tax engine target as approximate but robust in early versions.
5. Add tests as each phase is implemented; do not postpone validation.
6. Do not start any phase unless that phase status is Approved in the Phase Approval Register.
