"""Canonical yearly ledger schema definitions."""

PERSON_LEDGER_COLUMNS = [
    "year",
    "person_name",
    "employment_income",
    "defined_benefit_pension_income",
    "cpp_income",
    "oas_income",
    "rrsp_withdrawal",
    "spousal_rrsp_withdrawal",
    "tfsa_withdrawal",
    "non_registered_withdrawal",
    "gross_income",
    "pension_split_in",
    "pension_split_out",
    "taxable_capital_gains",
    "federal_tax",
    "ontario_tax",
    "oas_clawback",
    "total_tax",
    "section7_expense",
    "net_income",
    "tfsa_room_available",
]

HOUSEHOLD_LEDGER_COLUMNS = [
    "year",
    "gross_income_total",
    "total_tax",
    "section7_expense_total",
    "net_income_total",
    "house_valuation",
    "rrsp_total",
    "spousal_rrsp_total",
    "tfsa_total",
    "non_registered_total",
    "estate_estimated_taxable_amount",
]
