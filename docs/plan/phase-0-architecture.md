# Phase 0 - Architecture and Contracts

## Goal

Create stable contracts so all later engines write to the same data model and yearly ledger.

## Scope

1. Domain models for people, household, accounts, pensions, assumptions, and objectives.
2. Timeline/event model including ages, dates, and mid-year transitions.
3. Canonical yearly ledger schema at person level and household level.
4. Input validation and fail-fast error handling.
5. Data storage architecture that separates user data from source code.
6. A project data directory that is ignored by git and supports symlink-based storage.

## Deliverables

1. Model package structure and typed data classes.
2. Central configuration schema with defaults.
3. Validation module with explicit error messages.
4. Ledger schema document with required columns.
5. Data directory convention document (for example, data/) including symlink usage guidance.
6. Git ignore rule that excludes local plan data while preserving a placeholder file for structure.

## Dependencies

1. This phase blocks all others.

## Exit Criteria

1. All required input objects can be instantiated and validated.
2. A sample timeline can be generated from start year to horizon.
3. Ledger rows can be created using one stable schema.
4. User data path is externalized from code modules and resolved through configuration.
5. The default local data directory is ignored by git and can be replaced by a symlink to a backup-managed location.
