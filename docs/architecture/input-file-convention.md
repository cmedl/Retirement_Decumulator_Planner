# Input File Convention (Phase 1A Contract)

## Entry Point

1. The tracked entrypoint file is data/master_data.toml.
2. This manifest declares the base data directory and the filenames to load.
3. The base data directory may be a normal directory or a symlink.

## Manifest Example

```toml
[data]
base_dir = "my_retirement_data"

[files]
config = "config.toml"
people = "people.toml"
accounts = "accounts.toml"
pensions = "pensions.toml"
section7 = "section7.toml"
residence = "residence.toml"
```

## Account Type Contract

The `account_type` field in accounts files is a controlled string and must be one of:

1. `rrsp`
2. `spousal_rrsp`
3. `tfsa`
4. `non_registered`

These values are intentionally fixed because each account type will have different tax and withdrawal handling in later phases.

## Accounts File Example

```toml
[[accounts]]
owner_name = "Chris"
account_type = "rrsp"
balance = 250000

[[accounts]]
owner_name = "Chris"
account_type = "tfsa"
balance = 110000
contribution-frequency = "monthly"
contribution-amount = 500
```

## Contribution Contract (Phase 1C)

Each `[[accounts]]` entry may optionally include contribution metadata fields.

Supported contribution frequencies:

1. `yearly` with `amount`
2. `monthly` with `amount`
3. `biweekly` with `amount`
4. `percent_of_income_annual` with `contribution-percent-of-income` and `contribution-income-source`

Notes:

1. Contribution metadata is optional; accounts can have no additional contributions.
2. Contributions are applied in projection pre-retirement only.
3. `contribution-income-source` must match a person name from `people.toml`.

Example for percent-of-income:

```toml
[[accounts]]
owner_name = "Chris"
account_type = "non_registered"
balance = 350
contribution-frequency = "percent_of_income_annual"
contribution-percent-of-income = 0.03
contribution-income-source = "Chris"
```

## Validation Behavior

1. Unknown account types are rejected during input loading.
2. Error messages include the accepted values.
3. The canonical code-level list is defined in src/retirement_planner/models/accounts.py.

## Section 7 Contract

The Section 7 input file supplies the payer and both gross incomes. The payer share fraction is derived in code and is not entered manually.

```toml
[section7_obligation]
payer_name = "Chris"
payer_gross_income = 195000
other_party_gross_income = 130000
annual_expense = 38000
indexed_to_inflation = true
```

The computed payer share is:

1. payer_gross_income / (payer_gross_income + other_party_gross_income)
2. If the combined gross income is zero, the input is invalid and must fail validation.
