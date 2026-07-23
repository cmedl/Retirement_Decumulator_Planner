"""Phase 2 baseline tax engine (approximate, retirement-focused)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TaxComputationResult:
    federal_tax: float
    ontario_tax: float
    oas_clawback: float

    @property
    def total_tax(self) -> float:
        return self.federal_tax + self.ontario_tax + self.oas_clawback


FEDERAL_BRACKETS = (57_375.0, 114_750.0, 177_882.0, 253_414.0)
FEDERAL_RATES = (0.15, 0.205, 0.26, 0.29, 0.33)

ONTARIO_BRACKETS = (51_446.0, 102_894.0, 150_000.0, 220_000.0)
ONTARIO_RATES = (0.0505, 0.0915, 0.1116, 0.1216, 0.1316)

FEDERAL_BASIC_PERSONAL_AMOUNT = 15_705.0
ONTARIO_BASIC_PERSONAL_AMOUNT = 12_399.0

FEDERAL_PENSION_CREDIT_MAX_AMOUNT = 2_000.0
ONTARIO_PENSION_CREDIT_MAX_AMOUNT = 1_739.0

FEDERAL_AGE_AMOUNT_MAX = 8_790.0
FEDERAL_AGE_AMOUNT_REDUCTION_THRESHOLD = 44_325.0
FEDERAL_AGE_AMOUNT_REDUCTION_RATE = 0.15

ONTARIO_AGE_AMOUNT_MAX = 6_020.0
ONTARIO_AGE_AMOUNT_REDUCTION_THRESHOLD = 45_522.0
ONTARIO_AGE_AMOUNT_REDUCTION_RATE = 0.15

OAS_RECOVERY_THRESHOLD = 90_997.0
OAS_RECOVERY_RATE = 0.15


def _progressive_tax(taxable_income: float, brackets: tuple[float, ...], rates: tuple[float, ...]) -> float:
    if taxable_income <= 0:
        return 0.0

    tax = 0.0
    lower = 0.0
    for index, upper in enumerate(brackets):
        if taxable_income <= lower:
            break
        amount_in_bracket = min(taxable_income, upper) - lower
        if amount_in_bracket > 0:
            tax += amount_in_bracket * rates[index]
        lower = upper

    if taxable_income > lower:
        tax += (taxable_income - lower) * rates[len(brackets)]

    return tax


def _non_refundable_credit_value(amount: float, lowest_rate: float) -> float:
    return max(0.0, amount) * lowest_rate


def _age_amount(
    age: int,
    taxable_income: float,
    max_amount: float,
    reduction_threshold: float,
    reduction_rate: float,
) -> float:
    if age < 65:
        return 0.0
    reduction = max(0.0, taxable_income - reduction_threshold) * reduction_rate
    return max(0.0, max_amount - reduction)


def compute_income_tax(
    taxable_income: float,
    age: int,
    oas_income: float,
    eligible_pension_income: float,
) -> TaxComputationResult:
    """Compute approximate federal and Ontario income tax with key retirement items."""
    taxable_income = max(0.0, taxable_income)

    federal_gross = _progressive_tax(taxable_income, FEDERAL_BRACKETS, FEDERAL_RATES)
    ontario_gross = _progressive_tax(taxable_income, ONTARIO_BRACKETS, ONTARIO_RATES)

    federal_credits_amount = FEDERAL_BASIC_PERSONAL_AMOUNT
    federal_credits_amount += min(FEDERAL_PENSION_CREDIT_MAX_AMOUNT, max(0.0, eligible_pension_income))
    federal_credits_amount += _age_amount(
        age,
        taxable_income,
        FEDERAL_AGE_AMOUNT_MAX,
        FEDERAL_AGE_AMOUNT_REDUCTION_THRESHOLD,
        FEDERAL_AGE_AMOUNT_REDUCTION_RATE,
    )
    federal_credits = _non_refundable_credit_value(federal_credits_amount, FEDERAL_RATES[0])

    ontario_credits_amount = ONTARIO_BASIC_PERSONAL_AMOUNT
    ontario_credits_amount += min(ONTARIO_PENSION_CREDIT_MAX_AMOUNT, max(0.0, eligible_pension_income))
    ontario_credits_amount += _age_amount(
        age,
        taxable_income,
        ONTARIO_AGE_AMOUNT_MAX,
        ONTARIO_AGE_AMOUNT_REDUCTION_THRESHOLD,
        ONTARIO_AGE_AMOUNT_REDUCTION_RATE,
    )
    ontario_credits = _non_refundable_credit_value(ontario_credits_amount, ONTARIO_RATES[0])

    federal_tax = max(0.0, federal_gross - federal_credits)
    ontario_tax = max(0.0, ontario_gross - ontario_credits)

    oas_clawback = 0.0
    if oas_income > 0:
        oas_clawback = min(
            max(0.0, taxable_income - OAS_RECOVERY_THRESHOLD) * OAS_RECOVERY_RATE,
            oas_income,
        )

    return TaxComputationResult(
        federal_tax=federal_tax,
        ontario_tax=ontario_tax,
        oas_clawback=oas_clawback,
    )
