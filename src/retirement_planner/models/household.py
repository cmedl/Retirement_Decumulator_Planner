"""Household and support-obligation models."""

from dataclasses import dataclass, field

from .accounts import AccountBalance
from .pension import DefinedBenefitPension
from .person import PersonProfile
from .residence import Residence


@dataclass(slots=True)
class Section7Obligation:
    """Section 7 support cost parameters."""

    payer_name: str
    payer_gross_income: float
    other_party_gross_income: float
    annual_expense: float
    indexed_to_inflation: bool = True

    @property
    def payer_share_fraction(self) -> float:
        """Compute the payer's proportional share from both gross incomes."""
        total_gross_income = self.payer_gross_income + self.other_party_gross_income
        if total_gross_income <= 0:
            raise ValueError("Section 7 gross incomes must total more than zero")
        return self.payer_gross_income / total_gross_income


@dataclass(slots=True)
class HouseholdPlan:
    """Top-level household planning input container."""

    people: list[PersonProfile]
    accounts: list[AccountBalance] = field(default_factory=list)
    pensions: list[DefinedBenefitPension] = field(default_factory=list)
    section7_obligation: Section7Obligation | None = None
    residence: Residence | None = None
