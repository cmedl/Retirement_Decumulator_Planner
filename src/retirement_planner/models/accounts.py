"""Financial account models."""

from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    RRSP = "rrsp"
    SPOUSAL_RRSP = "spousal_rrsp"
    TFSA = "tfsa"
    NON_REGISTERED = "non_registered"


ACCOUNT_TYPE_VALUES: tuple[str, ...] = tuple(member.value for member in AccountType)


class ContributionFrequency(StrEnum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    PERCENT_OF_INCOME_ANNUAL = "percent_of_income_annual"


@dataclass(slots=True)
class ContributionRule:
    """Optional contribution configuration for an account."""

    frequency: ContributionFrequency
    amount: float | None = None
    percent_of_income: float | None = None
    income_person: str | None = None

    def annual_base_amount(self, employment_income_by_person: dict[str, float]) -> float:
        """Return annual contribution before retirement proration."""
        if self.frequency == ContributionFrequency.YEARLY:
            return float(self.amount or 0.0)
        if self.frequency == ContributionFrequency.MONTHLY:
            return float(self.amount or 0.0) * 12
        if self.frequency == ContributionFrequency.BIWEEKLY:
            return float(self.amount or 0.0) * 26
        if self.frequency == ContributionFrequency.PERCENT_OF_INCOME_ANNUAL:
            if self.income_person is None:
                return 0.0
            return employment_income_by_person.get(self.income_person, 0.0) * float(self.percent_of_income or 0.0)
        return 0.0


@dataclass(slots=True)
class AccountBalance:
    """Single account balance for an owner."""

    owner_name: str
    account_type: AccountType
    balance: float
    contribution: ContributionRule | None = None
